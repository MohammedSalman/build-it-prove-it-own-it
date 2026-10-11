"""Send requests at a steady rate and report how long the answers took.

    python scripts/load.py                              # 20 requests/s for 10 s, 3 runs
    python scripts/load.py --rate 200                   # the 8 pm estimate
    python scripts/load.py --rates 10,20,40,80,160 --duration 5   # a sweep: find the knee
    python scripts/load.py --csv results.csv --label before     # also save one line per run

By default each request is GET /api/events/{id} for a random event of this term's festival
(ids 3601-4000), which is what a phone asks when it shows "places left". The app must be
running (uvicorn app.main:app) with the festival data (python scripts/seed_festival.py).

What it reports, for every run:
  target     the rate at which requests are scheduled (requests per second): the demand
  achieved   successful answers per second, counted until the last answer of the run arrived
  requests   how many requests the run scheduled and counted
  errors     requests that did not end in a timely 200 OK, broken down as:
               late      answered, but more than --timeout seconds after it was due
               not sent  never sent, because it was already --timeout seconds overdue when
                         a connection came free (the person would have given up)
               HTTP ...  answered in time with another status
  p50 p95 p99 max
             latency percentiles of the successful answers (requests minus errors):
             95% of them took p95 or less

How it measures:
  * Open loop. Requests are due at fixed times (every 1/rate seconds) whether or not earlier
    answers have come back, the way 2,000 phones don't wait for each other.
  * Latency is measured from the moment a request was due, so time spent waiting behind
    earlier requests counts, as it would for a real person.
  * At most --connections requests are in flight at once; the rest wait in load.py's queue,
    and that wait counts as latency. A request that is already --timeout seconds overdue
    when its turn comes is not sent at all ("not sent").
  * A request that was sent is waited for even when it is late, so the server never carries
    leftover work into the next run; an answer that arrives more than --timeout seconds
    after the request was due counts as an error ("late"), not as a latency.
  * Percentiles use the nearest-rank method on the successful answers of one run.
  * Each run starts with --warmup seconds of requests that are sent but not counted.

Your numbers depend on your machine and on what else it is doing. Compare runs made on the
same machine, close together in time, and repeat each measurement (default: 3 runs).
Only the Python standard library is used.
"""

import argparse
import csv
import http.client
import math
import os
import queue
import random
import statistics
import sys
import threading
import time
import urllib.parse
from datetime import datetime


def percentile(sorted_values: list[float], p: float) -> float:
    """Nearest-rank percentile: the smallest value with at least p% of values at or below it."""
    if not sorted_values:
        return math.nan
    rank = math.ceil(p / 100 * len(sorted_values))
    return sorted_values[max(rank, 1) - 1]


def sleep_until(deadline: float) -> None:
    """Sleep until time.perf_counter() reaches deadline.

    One long time.sleep() can oversleep by several milliseconds on some systems, so we sleep
    in shrinking steps and finish with very short ones.
    """
    while True:
        left = deadline - time.perf_counter()
        if left <= 0:
            return
        time.sleep(left / 2 if left > 0.002 else 0.0002)


IDLE_LIMIT = 2.0     # seconds; servers close idle connections (uvicorn after 5 s)
HARD_LIMIT = 60.0    # seconds; a request already sent is waited for this long at most


class Worker(threading.Thread):
    """One connection to the server, reused for many requests (like one browser tab).

    A request that was due more than `timeout` seconds ago is not sent at all ("not sent"):
    the person would have given up. A request that was sent is waited for, even when it is
    late, so the server is never left working on requests nobody is waiting for (which would
    slow down the next run). A late answer counts as an error ("late"), not as a latency.
    """

    def __init__(self, host, port, jobs, results, timeout):
        super().__init__(daemon=True)
        self.host, self.port, self.jobs, self.results, self.timeout = host, port, jobs, results, timeout
        self.conn = None
        self.last_used = 0.0

    def fresh(self) -> None:
        if self.conn is not None:
            self.conn.close()
        self.conn = http.client.HTTPConnection(self.host, self.port, timeout=HARD_LIMIT)

    def send(self, path: str) -> int:
        self.conn.request("GET", path)
        response = self.conn.getresponse()
        response.read()
        return response.status

    def run(self) -> None:
        while True:
            job = self.jobs.get()
            if job is None:
                if self.conn is not None:
                    self.conn.close()
                return
            due, path, counted = job
            started = time.perf_counter()
            if started - due > self.timeout:        # waited so long it would have given up
                self.results.append((due, started, started, "not sent", counted))
                continue
            reused = self.conn is not None and started - self.last_used < IDLE_LIMIT
            if not reused:
                self.fresh()
            try:
                try:
                    outcome = self.send(path)
                except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError):
                    if not reused:
                        raise
                    self.fresh()                    # the server closed an idle connection:
                    outcome = self.send(path)       # try once more, as browsers do
            except TimeoutError:
                outcome = "no answer"
            except (OSError, http.client.HTTPException) as exc:
                outcome = type(exc).__name__
            finished = time.perf_counter()
            if not isinstance(outcome, int):
                self.conn.close()                   # start clean after any trouble
                self.conn = None
            elif finished - due > self.timeout:
                outcome = "late"                    # answered, but too late
            self.last_used = finished
            self.results.append((due, started, finished, outcome, counted))


def one_run(args, rate: float, run: int) -> dict:
    url = urllib.parse.urlsplit(args.url)
    jobs: queue.Queue = queue.Queue()
    results: list = []
    workers = [Worker(url.hostname, url.port or 80, jobs, results, args.timeout)
               for _ in range(args.connections)]
    for w in workers:
        w.start()

    rnd = random.Random(f"{args.seed}-{rate}-{run}")
    warm = int(rate * args.warmup)
    total = warm + max(1, round(rate * args.duration))
    t0 = time.perf_counter() + 0.05
    for i in range(total):
        due = t0 + i / rate
        sleep_until(due)
        path = args.path.replace("{id}", str(rnd.randint(args.first_id, args.last_id)))
        jobs.put((due, path, i >= warm))
    for _ in workers:
        jobs.put(None)
    for w in workers:
        w.join(HARD_LIMIT + 5)

    counted = [r for r in results if r[4]]
    ok = sorted((finished - due) * 1000 for due, _, finished, outcome, _ in counted if outcome == 200)
    errors: dict = {}
    for r in counted:
        if r[3] != 200:
            key = f"HTTP {r[3]}" if isinstance(r[3], int) else str(r[3])
            errors[key] = errors.get(key, 0) + 1
    first_due = t0 + warm / rate
    last_done = max((r[2] for r in counted), default=first_due)
    window = max(last_done - first_due, 1e-9)
    lag = sum(1 for due, started, _, outcome, _ in counted
              if outcome != "not sent" and started - due > 0.010)
    not_sent = errors.get("not sent", 0)
    return {
        "run": run, "target": rate, "achieved": len(ok) / window, "requests": len(counted),
        "errors": sum(errors.values()), "error_kinds": errors, "lag": lag,
        "sent": len(counted) - not_sent, "not_sent": not_sent, "late": errors.get("late", 0),
        "p50": percentile(ok, 50), "p95": percentile(ok, 95), "p99": percentile(ok, 99),
        "max": ok[-1] if ok else math.nan, "mean": statistics.fmean(ok) if ok else math.nan,
        "latencies": ok,
    }


def ms(x: float) -> str:
    if math.isnan(x):
        return "-"
    return f"{x:,.0f} ms" if x >= 100 else f"{x:.1f} ms"


def show(r: dict) -> None:
    kinds = ", ".join(f"{k}: {v}" for k, v in sorted(r["error_kinds"].items()))
    print(f"{r['run']:>3}  {r['target']:>6g}/s  {r['achieved']:>7.1f}/s  {r['requests']:>8}  "
          f"{r['errors']:>6}  {ms(r['p50']):>9}  {ms(r['p95']):>9}  {ms(r['p99']):>9}  "
          f"{ms(r['max']):>9}" + (f"   ({kinds})" if kinds else ""), flush=True)


def check_server(args) -> None:
    url = urllib.parse.urlsplit(args.url)
    for event_id in (args.first_id, args.last_id):
        path = args.path.replace("{id}", str(event_id))
        try:
            conn = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=30)
            conn.request("GET", path)
            status = conn.getresponse().status
            conn.close()
        except OSError as exc:
            sys.exit(f"Cannot reach {args.url} ({exc}). Is the app running?")
        if status == 404:
            sys.exit(f"GET {path} answered 404. Did you run scripts/seed_festival.py "
                     f"(and restart the app)? Or set --ids to event ids that exist.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--path", default="/api/events/{id}",
                        help="path to request; {id} is replaced by a random event id")
    parser.add_argument("--ids", default="3601-4000", help="range of event ids, e.g. 1-10")
    parser.add_argument("--rate", type=float, default=20, help="requests per second")
    parser.add_argument("--rates", help="several rates for a sweep, e.g. 10,20,40,80,160")
    parser.add_argument("--duration", type=float, default=10, help="seconds per run")
    parser.add_argument("--repeat", type=int, default=3, help="runs per rate")
    parser.add_argument("--connections", type=int, default=50,
                        help="most requests in flight at once")
    parser.add_argument("--timeout", type=float, default=5,
                        help="seconds after a request is due: a later answer counts as late, "
                             "and a request this overdue is not sent")
    parser.add_argument("--warmup", type=float, default=1, help="uncounted seconds before each run")
    parser.add_argument("--pause", type=float, default=2, help="seconds of rest between runs")
    parser.add_argument("--seed", default="11", help="random seed for the choice of events")
    parser.add_argument("--label", default="", help="a name for this measurement, saved in the CSV")
    parser.add_argument("--csv", help="append one line per run to this CSV file")
    parser.add_argument("--raw", help="append every successful request's latency to this CSV file")
    args = parser.parse_args()
    args.first_id, args.last_id = (int(x) for x in args.ids.split("-"))
    rates = [float(x) for x in args.rates.split(",")] if args.rates else [args.rate]
    if min(rates) <= 0:
        sys.exit("Rates must be positive.")

    check_server(args)
    print(f"GET {args.path} (ids {args.ids}) at {args.url}")
    print(f"{len(rates)} rate(s) x {args.repeat} run(s), {args.duration:g} s each, "
          f"up to {args.connections} requests in flight, timeout {args.timeout:g} s")
    print(f"{'run':>3}  {'target':>8}  {'achieved':>9}  {'requests':>8}  {'errors':>6}  "
          f"{'p50':>9}  {'p95':>9}  {'p99':>9}  {'max':>9}")

    results = []
    # Interleave: all rates once, then all rates again. A slow drift on the machine then
    # affects every rate a little, instead of hitting one rate badly.
    for run in range(1, args.repeat + 1):
        for rate in rates:
            if results:
                time.sleep(args.pause)
            r = one_run(args, rate, run)
            results.append(r)
            show(r)
            stamp = datetime.now().isoformat(timespec="seconds")
            if args.csv:
                new = not os.path.exists(args.csv)
                with open(args.csv, "a", newline="") as f:
                    w = csv.writer(f)
                    if new:
                        w.writerow(["time", "label", "path", "run", "target", "achieved",
                                    "requests", "errors", "p50_ms", "p95_ms", "p99_ms",
                                    "max_ms", "mean_ms", "sent", "late", "not_sent"])
                    w.writerow([stamp, args.label, args.path, r["run"], r["target"],
                                f"{r['achieved']:.2f}", r["requests"], r["errors"],
                                *(f"{r[k]:.2f}" for k in ("p50", "p95", "p99", "max", "mean")),
                                r["sent"], r["late"], r["not_sent"]])
            if args.raw:
                new = not os.path.exists(args.raw)
                with open(args.raw, "a", newline="") as f:
                    w = csv.writer(f)
                    if new:
                        w.writerow(["label", "target", "run", "latency_ms"])
                    w.writerows([args.label, r["target"], r["run"], f"{x:.3f}"]
                                for x in r["latencies"])

    print("\nSummary: median of the runs at each rate")
    print(f"{'target':>8}  {'achieved':>9}  {'errors':>6}  {'p50':>9}  {'p95':>9}  {'p99':>9}"
          f"  p95 range over runs")
    for rate in rates:
        rs = [r for r in results if r["target"] == rate]
        med = {k: statistics.median(r[k] for r in rs) for k in ("achieved", "p50", "p95", "p99")}
        lo, hi = min(r["p95"] for r in rs), max(r["p95"] for r in rs)
        print(f"{rate:>6g}/s  {med['achieved']:>7.1f}/s  {sum(r['errors'] for r in rs):>6}  "
              f"{ms(med['p50']):>9}  {ms(med['p95']):>9}  {ms(med['p99']):>9}  "
              f"{ms(lo)} to {ms(hi)}")

    notes = []
    if any(r["requests"] < 100 for r in results):
        notes.append("Some runs have fewer than 100 requests: their p99 is little more than "
                     "the maximum. Run longer for a meaningful p99.")
    if any(r["errors"] for r in results):
        notes.append("Some requests failed, came back late, or were never sent. Errors are not "
                     "in the percentiles, so those runs look better than what people experienced.")
    if any(r["lag"] > 0.05 * r["requests"] and r["achieved"] > 0.95 * r["target"]
           for r in results):
        notes.append("load.py sent more than 5% of requests over 10 ms late while the server "
                     "kept up: this computer may be too busy to generate the load. Close other "
                     "programs or lower the rate.")
    for n in notes:
        print("Note: " + n)
    print("These numbers are observations from this machine at this time, not a benchmark.")


if __name__ == "__main__":
    main()
