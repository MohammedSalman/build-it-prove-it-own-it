"""Send reservations for the same last places at the same moment, and check the promise.

The promise (our invariant):   confirmed reservations for an event <= its capacity

Each trial creates a fresh event with --capacity places (default 1), then several people
press "Reserve" at the same instant. A correct system gives exactly `capacity` people a
place (HTTP 201), tells everyone else the event is full (HTTP 409), and has no errors.

Usage (with the app running in another terminal):
    python scripts/race.py                                   # 10 trials, Maya vs Sam, 1 place
    python scripts/race.py --trials 30 --people Maya,Sam,Lee
    python scripts/race.py --people Maya,Sam,Lee --capacity 2

Only the Python standard library is used, so this runs anywhere Python does.
"""

import argparse
import json
import sys
import threading
import urllib.error
import urllib.request


def call(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as err:
        return err.code, {}


def trial(base: str, number: int, people: list[str], capacity: int) -> bool:
    status, event = call("POST", f"{base}/api/events", {
        "title": f"Race trial {number}", "venue": "Lab", "starts_at": "2026-10-09T20:00",
        "capacity": capacity,
    })
    if status != 201:
        sys.exit(f"Could not create a test event (HTTP {status}). Is the app running at {base}?")

    start_line = threading.Barrier(len(people))
    results: dict[str, str] = {}

    def press_reserve(name: str) -> None:
        start_line.wait()  # everyone presses at the same instant
        try:
            code, _ = call("POST", f"{base}/api/events/{event['id']}/reservations",
                           {"attendee": name})
            results[name] = str(code)
        except Exception as exc:  # a dropped connection is a result too
            results[name] = f"error ({type(exc).__name__})"

    threads = [threading.Thread(target=press_reserve, args=(p,)) for p in people]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    _, after = call("GET", f"{base}/api/events/{event['id']}")
    outcomes = [results.get(p, "no answer") for p in people]
    winners = min(capacity, len(people))
    ok = (outcomes.count("201") == winners
          and outcomes.count("409") == len(people) - winners
          and after["reserved"] == winners)

    if after["reserved"] > after["capacity"]:
        verdict = "OVERSOLD"
    elif ok:
        verdict = "ok"
    else:
        verdict = "WRONG (promise kept, but not a clean result)"
    shown = "  ".join(f"{p}->{results.get(p, 'no answer')}" for p in people)
    print(f"Trial {number:>2}: {shown}   reserved {after['reserved']} of {capacity}   {verdict}")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--people", default="Maya,Sam",
                        help="comma-separated names that all try to book at once")
    parser.add_argument("--capacity", type=int, default=1, help="places in each test event")
    args = parser.parse_args()
    people = [p.strip() for p in args.people.split(",") if p.strip()]
    if len(people) < 2:
        sys.exit("A race needs at least two people.")
    if args.capacity < 1:
        sys.exit("Capacity must be at least 1.")

    base = args.url.rstrip("/")
    passed = sum(trial(base, n, people, args.capacity) for n in range(1, args.trials + 1))
    failed = args.trials - passed
    print()
    if failed:
        print(f"{failed} of {args.trials} trials broke the promise "
              f"'confirmed reservations <= capacity' or did not give a clean result.")
        sys.exit(1)
    winners = min(args.capacity, len(people))
    print(f"All {args.trials} trials kept the promise: {winners} got a place, "
          f"everyone else got 409.")


if __name__ == "__main__":
    main()
