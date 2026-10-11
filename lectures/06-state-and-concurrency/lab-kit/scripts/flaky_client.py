"""Lose a response after the server has saved the reservation, then retry. Count the places.

Maya is on bad Wi-Fi. She presses Reserve once. Her request reaches the server, which
checks, pays and COMMITS the reservation, then sends "201 Created". On the way back the
Wi-Fi drops, so her phone never sees that answer. The phone does what the AfterHours page
does: it waits a moment and sends the same request once more, with the same Idempotency-Key.

In this scenario (one answer lost, the retry gets through), one press should give Maya
exactly one place, and her phone should learn its number.

How the answer is lost: this script puts a small "lossy link" (a relay on your own machine)
between the phone and the server. The link passes the request to the server and waits for
the server's COMPLETE answer, so the server has already finished and committed. It then asks
the server how many places are taken, to show the reservation really is saved, and closes
the phone's connection without passing the answer on. The server itself is not changed.

Usage (with the app running in another terminal):
    python scripts/flaky_client.py                # 3 trials; the first answer of each is lost
    python scripts/flaky_client.py --trials 5
    python scripts/flaky_client.py --impatient    # nothing is lost, but the phone stops waiting
                                                  # after 0.1 s and resends while the first
                                                  # request is still being processed
    python scripts/flaky_client.py --no-key       # an older page that sends no key

Each trial books a fresh event with 5 places, so only Maya's presses count.
Exit status: 0 if every trial ended with Maya holding exactly one place and her phone knowing
its number; 1 otherwise. Only the Python standard library is used.
"""

import argparse
import http.client
import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

print_lock = threading.Lock()


def say(text: str) -> None:
    with print_lock:
        print(text, flush=True)


def call(method: str, url: str, body: dict | None = None, headers: dict | None = None,
         timeout: float = 15) -> tuple[int, dict]:
    """One HTTP request. Returns (status, JSON body). Network failures raise."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as err:
        try:
            return err.code, json.loads(err.read() or b"{}")
        except ValueError:
            return err.code, {}


# ---------------------------------------------------------------- the lossy link

def read_http_message(sock: socket.socket) -> bytes | None:
    """Read one complete HTTP message (head and body) from a socket."""
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(65536)
        if not chunk:
            return data or None
        data += chunk
    head, _, rest = data.partition(b"\r\n\r\n")
    length = None
    for line in head.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            length = int(value.strip())
    if length is None:                       # no length given: read until the other side closes
        while chunk := sock.recv(65536):
            rest += chunk
    while length is not None and len(rest) < length:
        chunk = sock.recv(65536)
        if not chunk:
            break
        rest += chunk
    return head + b"\r\n\r\n" + rest


def status_and_body(message: bytes) -> tuple[int, dict]:
    head, _, body = message.partition(b"\r\n\r\n")
    status = int(head.split(b" ", 2)[1])
    try:
        return status, json.loads(body or b"{}")
    except ValueError:
        return status, {}


class LossyLink:
    """A relay on 127.0.0.1 between the phone and the server that can lose answers."""

    def __init__(self, server_host: str, server_port: int, port: int = 0):
        self.server = (server_host, server_port)
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", port))
        self.listener.listen(16)
        self.port = self.listener.getsockname()[1]
        self.lock = threading.Lock()
        self.lose_next = 0          # how many server answers to lose
        self.answers = []           # (status, body) of every answer the server sent
        self.before_losing = None   # called with (status, body) before an answer is lost
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        while True:
            try:
                phone, _ = self.listener.accept()
            except OSError:
                return
            threading.Thread(target=self._relay, args=(phone,), daemon=True).start()

    def _relay(self, phone: socket.socket) -> None:
        with phone:
            request = read_http_message(phone)
            if not request:
                return
            with socket.create_connection(self.server, timeout=60) as server:
                server.sendall(request)
                answer = read_http_message(server)   # the server has finished: it answered
            if not answer:
                return
            status, body = status_and_body(answer)
            with self.lock:
                self.answers.append((status, body))
                lose = self.lose_next > 0
                if lose:
                    self.lose_next -= 1
            if lose:
                if self.before_losing:
                    self.before_losing(status, body)
                return                                # close the phone's connection: no answer
            try:
                phone.sendall(answer)
            except OSError:
                pass                                  # the phone had stopped waiting

    def close(self) -> None:
        self.listener.close()


# ---------------------------------------------------------------- the phone

def is_timeout(exc: BaseException) -> bool:
    return isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError)


def trial(number: int, base: str, link: LossyLink, attendee: str, client_id: str,
          use_key: bool, impatient: bool) -> str:
    status, event = call("POST", f"{base}/api/events", {
        "title": f"Flaky trial {number}", "venue": "Lab", "starts_at": "2026-10-09T20:00",
        "capacity": 5,
    })
    if status != 201:
        sys.exit(f"Could not create a test event (HTTP {status}). Is the app running at {base}?")
    event_url = f"{base}/api/events/{event['id']}"
    key = uuid.uuid4().hex if use_key else None
    started = time.perf_counter()

    def log(who: str, text: str) -> None:
        say(f"  +{(time.perf_counter() - started) * 1000:5.0f} ms  {who:<6} {text}")

    def before_losing(status: int, body: dict) -> None:
        _, now = call("GET", event_url)
        log("link", f"server answered {status}: reservation #{body.get('id')} "
                    f"(server now shows {now['reserved']} of 5 places taken)")
        log("link", "Wi-Fi drops: that answer never reaches the phone")

    with link.lock:
        link.answers = []
        link.lose_next = 0 if impatient else 1
    link.before_losing = before_losing

    say(f"Trial {number} · event #{event['id']} (5 places) · {attendee} presses Reserve once")
    headers = {"Idempotency-Key": key, "Client-Id": client_id} if key else {}
    final_status, final_body, attempts = None, {}, 0
    for attempt in range(1, 3):                  # like the page: one automatic retry
        attempts = attempt
        shown_key = f"key {key[:8]}" if key else "no key"
        log("phone", f"attempt {attempt} ({shown_key})")
        timeout = 0.1 if impatient and attempt == 1 else 15
        try:
            final_status, final_body = call(
                "POST", f"http://127.0.0.1:{link.port}/api/events/{event['id']}/reservations",
                {"attendee": attendee}, headers, timeout=timeout)
            break
        except (OSError, http.client.HTTPException) as exc:
            why = f"nothing within {timeout} s" if is_timeout(exc) else "connection closed"
            same = "with the same key" if key else "(no key to reuse)"
            if attempt < 2:
                log("phone", f"no answer ({why}); retrying {same}")
                if not impatient:
                    time.sleep(0.2 * attempt)
            else:
                log("phone", f"no answer ({why}); giving up")

    # Wait until the server has answered every request it received (an abandoned request
    # keeps running on the server after the phone stops waiting).
    deadline = time.perf_counter() + 10
    while len(link.answers) < attempts and time.perf_counter() < deadline:
        time.sleep(0.02)

    if final_status == 201:
        log("phone", f"got 201 Created: reservation #{final_body.get('id')}")
    elif final_status is not None:
        log("phone", f"got {final_status}: {final_body.get('detail', final_body)}")

    _, after = call("GET", event_url)
    places = after["reserved"]
    saved = [body.get("id") for status, body in link.answers if status == 201]
    shown = ", ".join(f"#{i}" for i in saved) or "none"
    say(f"  Server answers along the way: {len(link.answers)} (201 with reservation {shown})")
    if places > 1:
        verdict = "DUPLICATE"
        say(f"  Result: {attendee} pressed once and now holds {places} places   -> DUPLICATE")
    elif places == 1 and final_status == 201 and final_body.get("id") in saved[:1]:
        verdict = "ok"
        say(f"  Result: {attendee} pressed once and holds 1 place; the phone knows it is "
            f"#{final_body['id']}   -> ok")
    elif places == 1:
        verdict = "CONFUSED"
        say(f"  Result: {attendee} holds 1 place, but her phone was told "
            f"{final_status}, not her reservation number   -> CONFUSED")
    else:
        verdict = "NO PLACE"
        say(f"  Result: {attendee} holds no place   -> NO PLACE")
    say("")
    return verdict


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--attendee", default="Maya")
    parser.add_argument("--impatient", action="store_true",
                        help="lose nothing, but stop waiting after 0.1 s and resend at once")
    parser.add_argument("--no-key", action="store_true", help="send no Idempotency-Key")
    parser.add_argument("--link-port", type=int, default=0,
                        help="port for the lossy link (default: any free port)")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    parsed = urllib.parse.urlparse(base)
    try:
        call("GET", f"{base}/api/events", timeout=5)
    except OSError:
        sys.exit(f"No AfterHours server answered at {base}. Start it first: uvicorn app.main:app")

    link = LossyLink(parsed.hostname or "127.0.0.1", parsed.port or 80, args.link_port)
    client_id = f"flaky-phone-{uuid.uuid4().hex[:6]}"
    mode = ("impatient phone (answers are not lost; the phone resends after 0.1 s)"
            if args.impatient else "lossy Wi-Fi (the first answer of each trial is lost)")
    say(f"Mode: {mode}. Client-Id: {client_id}\n")
    try:
        verdicts = [trial(n, base, link, args.attendee, client_id, not args.no_key, args.impatient)
                    for n in range(1, args.trials + 1)]
    finally:
        link.close()

    counts = {v: verdicts.count(v) for v in dict.fromkeys(verdicts)}
    say("Summary: " + ", ".join(f"{n} x {v}" for v, n in counts.items())
        + f"  (out of {args.trials} trials)")
    if counts.get("DUPLICATE"):
        say("One press made more than one reservation: retrying this request is not safe.")
    if set(verdicts) != {"ok"}:
        sys.exit(1)
    say("Every press made exactly one reservation, and the phone learned its number.")


if __name__ == "__main__":
    main()
