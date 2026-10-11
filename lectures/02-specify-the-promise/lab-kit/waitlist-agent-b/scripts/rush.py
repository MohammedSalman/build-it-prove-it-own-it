"""Festival rush: many people book DIFFERENT events at the same moment.

race.py asks "does the last place go to exactly one person?".
rush.py asks a different question: "when lots of people book at once, how long do they
wait, and does anyone get an error?". A fix can pass one check and fail the other.

Usage (with the app running in another terminal):
    python scripts/rush.py              # 20 people, 20 different events
    python scripts/rush.py --people 50

Only the Python standard library is used.
"""

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter


def call(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as err:
        return err.code, {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--people", type=int, default=20)
    args = parser.parse_args()
    base = args.url.rstrip("/")

    event_ids = []
    for n in range(1, args.people + 1):
        status, event = call("POST", f"{base}/api/events", {
            "title": f"Rush event {n}", "venue": "Lab", "starts_at": "2026-10-09T20:00",
            "capacity": 5,
        })
        if status != 201:
            sys.exit(f"Could not create a test event (HTTP {status}). Is the app running at {base}?")
        event_ids.append(event["id"])

    start_line = threading.Barrier(len(event_ids))
    outcomes: dict[str, tuple[str, float]] = {}   # one entry per person: (result, seconds)

    def book(event_id: int, name: str) -> None:
        start_line.wait()
        started = time.perf_counter()
        try:
            status, _ = call("POST", f"{base}/api/events/{event_id}/reservations",
                             {"attendee": name})
            result = f"HTTP {status}"
        except Exception as exc:  # a dropped connection is a result too
            result = f"error ({type(exc).__name__})"
        outcomes[name] = (result, time.perf_counter() - started)

    threads = [threading.Thread(target=book, args=(eid, f"person-{i}"))
               for i, eid in enumerate(event_ids, 1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    people = [f"person-{i}" for i in range(1, len(event_ids) + 1)]
    results = [outcomes.get(p, ("no answer", float("nan")))[0] for p in people]
    waits = sorted(outcomes[p][1] for p in people if p in outcomes)
    counts = Counter(results)
    print(f"{len(people)} people tried to book {len(people)} different events at the same moment.")
    if waits:
        print(f"  fastest answer: {waits[0]:.2f} s")
        print(f"  median answer:  {waits[len(waits) // 2]:.2f} s")
        print(f"  slowest answer: {waits[-1]:.2f} s")
    print("  responses:      " + ", ".join(f"{n} x {r}" for r, n in sorted(counts.items())))
    not_booked = len(people) - counts["HTTP 201"]
    if not_booked:
        print(f"\n{not_booked} of {len(people)} people did not get a place, although every event had room.")
        sys.exit(1)
    print("\nEveryone got a place.")


if __name__ == "__main__":
    main()
