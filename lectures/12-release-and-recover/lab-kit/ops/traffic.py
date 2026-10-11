"""Simulated festival visitors, with the service level indicator measured as they go.

    python ops/traffic.py production                 # until you press Ctrl+C
    python ops/traffic.py production --seconds 60

Four visitors send about 10 requests a second in total: they look at the programme,
open events, book places (as visitor-NNNN) and, now and then, an organiser adds a
pop-up event. Every 5 seconds one line is printed: how many requests, how many were
good according to ops/sli.py, the SLI for that window, which answers came back, and
which release was serving. The same lines go to envs/<env>/traffic.csv.

Until you write is_good() in ops/sli.py (Part A3) you see the raw answers only.
"""

import argparse
import csv
import random
import sys
import threading
import time
from collections import Counter
from datetime import datetime

import sli
from envs import base_url, env_dir, health, http, load_pipeline

MIX = [("list", 50), ("event", 30), ("book", 17), ("create", 3)]


CRASHES: list[str] = []


def judge(kind, status, seconds, body):
    """True or False from ops/sli.py, or None if it cannot say (not written yet, or it crashed)."""
    try:
        return bool(sli.is_good(kind, status, seconds, body))
    except NotImplementedError:
        return None
    except Exception as exc:  # a bug in is_good(): report it, do not count the request
        CRASHES.append(f"{type(exc).__name__}: {exc} (kind {kind!r}, status {status})")
        return None


def sli_written() -> bool:
    try:
        sli.is_good("list", 200, 0.0, [])
    except NotImplementedError:
        return False
    except Exception:
        return True  # written, but with a bug; judge() reports it
    return True


def visitor(number, base, pace, stop, results, lock):
    rng = random.Random(1200 + number)
    kinds = [k for k, _ in MIX]
    weights = [w for _, w in MIX]
    event_ids = [1, 2, 3, 4, 5]
    while not stop.is_set():
        kind = rng.choices(kinds, weights)[0]
        if kind == "list":
            status, body, seconds = http("GET", base + "/api/events")
            if status == 200 and isinstance(body, list) and body:
                event_ids = [e["id"] for e in body if isinstance(e, dict) and "id" in e] or event_ids
        elif kind == "event":
            status, body, seconds = http("GET", f"{base}/api/events/{rng.choice(event_ids)}")
        elif kind == "book":
            status, body, seconds = http(
                "POST", f"{base}/api/events/{rng.choice(event_ids)}/reservations",
                {"attendee": f"visitor-{rng.randrange(10000):04d}"})
        else:
            status, body, seconds = http("POST", base + "/api/events", {
                "title": f"Pop-up session {rng.randrange(1000)}", "venue": "The Tent",
                "starts_at": "2026-10-10T22:00", "capacity": 30})
        verdict = judge(kind, status, seconds, body)
        with lock:
            results.append((kind, status, verdict))
        stop.wait(max(0.0, pace - seconds))


def answers(window):
    counts = Counter("none" if status is None else str(status) for _, status, _ in window)
    return ", ".join(f"{code} x{n}" for code, n in sorted(counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("env", help="staging or production")
    parser.add_argument("--seconds", type=float, default=0, help="stop after this long (0: Ctrl+C)")
    parser.add_argument("--rate", type=float, default=10, help="requests per second, in total")
    parser.add_argument("--window", type=float, default=5, help="seconds per printed line")
    parser.add_argument("--visitors", type=int, default=4)
    args = parser.parse_args()

    base = base_url(args.env)
    if health(args.env) is None:
        sys.exit(f"Nothing answers at {base}. Deploy a release to {args.env} first.")
    target = float(load_pipeline().get("sli_target", 0.99))
    defined = sli_written()

    print(f"Simulated visitors on {args.env} ({base}), about {args.rate:g} requests/s. "
          f"Ctrl+C to stop.")
    if defined:
        print(f"SLI = share of requests answered correctly within {sli.SLOW} s (ops/sli.py).")
    else:
        print("The SLI is not defined yet (ops/sli.py, Part A3): showing the raw answers only.")
    print(f"{'time':<9} {'reqs':>5} {'good':>5} {'bad':>5} {'SLI':>7}  {'release':<8} answers")

    csv_path = env_dir(args.env) / "traffic.csv"
    csv_file = open(csv_path, "a", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    if csv_file.tell() == 0:
        writer.writerow(["time", "requests", "good", "bad", "sli", "release", "answers"])

    results, lock, stop = [], threading.Lock(), threading.Event()
    pace = args.visitors / args.rate
    threads = [threading.Thread(target=visitor, args=(i, base, pace, stop, results, lock),
                                daemon=True) for i in range(args.visitors)]
    for t in threads:
        t.start()

    seen = 0
    total = Counter()
    started = time.monotonic()
    try:
        while True:
            time.sleep(args.window)
            with lock:
                window = results[seen:]
                seen = len(results)
            answer = health(args.env, timeout=1.0)
            release = answer.get("release") if answer else "-"
            good = sum(1 for _, _, v in window if v is True)
            bad = sum(1 for _, _, v in window if v is False)
            share = f"{good / (good + bad):.1%}" if defined and good + bad else "-"
            stamp = datetime.now().strftime("%H:%M:%S")
            shown_good, shown_bad = (good, bad) if defined else ("-", "-")
            print(f"{stamp:<9} {len(window):>5} {shown_good:>5} {shown_bad:>5} {share:>7}  "
                  f"{release:<8} {answers(window)}", flush=True)
            if CRASHES:
                print(f"          ops/sli.py crashed {len(CRASHES)} time(s), e.g. {CRASHES[0]}; "
                      f"those requests were not judged", flush=True)
                CRASHES.clear()
            writer.writerow([stamp, len(window), good if defined else "",
                             bad if defined else "", share, release, answers(window)])
            csv_file.flush()
            total.update(requests=len(window), good=good, bad=bad)
            if args.seconds and time.monotonic() - started >= args.seconds:
                break
    except KeyboardInterrupt:
        pass
    stop.set()
    csv_file.close()

    n = total["requests"]
    print(f"\n{n} requests in {time.monotonic() - started:.0f} s. Lines saved to {csv_path}.")
    if defined and n:
        budget = n * (1 - target)
        print(f"Bad: {total['bad']} of {n} ({total['bad'] / n:.1%}). An SLO of {target:.0%} "
              f"allows {budget:.1f} bad out of {n}: this run used "
              f"{total['bad'] / budget if budget else 0:.1f} times that error budget.")


if __name__ == "__main__":
    main()
