"""Rehearse the whole migration on a copy of production, with v1 and v2 both writing.

    python scripts/rehearse.py                  one rehearsal (seed 1)
    python scripts/rehearse.py --runs 3         three rehearsals (seeds 1, 2, 3)
    python scripts/rehearse.py --backfill some.module:function   try another backfill

Both apps run inside this process (FastAPI's TestClient) on ONE database file, so no
ports are needed. The clock is pinned to Thursday 1 October 2026, before the festival,
so every day change is allowed. The steps follow docs/migration-plan.md:

   0  copy of production: a v1 database with 600 day tickets
   1  expand
   2  migration window: v1 and v2 sell and move tickets WHILE the backfill runs
     (three writes land in each gap between its batches)
   3  v1 keeps writing after the backfill: it moves copied tickets and sells new ones
   4  passes can't go on sale yet, and contract is refused: v1 is live
   5  retire v1
   6  contract is refused again: the data has not caught up
   7  backfill again (catch-up), then verify
   8  passes go on sale; v2 sells passes
   9  contract
  10  v2 keeps working after the contract; a v1 server started by mistake fails loudly
  11  compare meaning: every ticket must mean exactly what the writes said it should

The rehearsal keeps its own record of every write the apps confirmed (201 or 200), and
that record is the expected meaning at the end. It passes only if the database agrees.
"""

import argparse
import importlib
import importlib.util
import os
import random
import sqlite3
import sys
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import v1.main  # noqa: E402
import v2.main  # noqa: E402
from migrations import meaning as mm  # noqa: E402
from migrations import steps  # noqa: E402
from migrations.contract import _rebuild, contract  # noqa: E402
from scripts.make_production_db import make  # noqa: E402
from v1.clock import FixedClock  # noqa: E402

DAYS = list(mm.FESTIVAL_DAYS)
PEOPLE = ["Maya", "Sam", "Lee", "Ada", "Tom", "Noor", "Jonas", "Priya", "Kofi", "Mei"]


class SlowCommits:
    """Wraps the backfill's connection and gives the apps a turn after each COMMIT.

    On a real table with millions of rows a backfill runs for minutes or hours, and the apps'
    writes land between its batches. With 600 rows it would finish in a few milliseconds,
    before the apps could write anything. So after each commit this wrapper opens a gap and
    waits (up to one second) until the apps have written in it.
    """

    def __init__(self, conn, gap_open: threading.Event, gap_done: threading.Event):
        self._conn, self._gap_open, self._gap_done = conn, gap_open, gap_done

    def _give_a_turn(self) -> None:
        self._gap_open.set()
        self._gap_done.wait(timeout=1.0)
        self._gap_done.clear()

    def execute(self, sql, *args, **kwargs):
        cur = self._conn.execute(sql, *args, **kwargs)
        if sql.strip().upper().startswith(("COMMIT", "END")):
            self._give_a_turn()
        return cur

    def commit(self):
        self._conn.commit()
        self._give_a_turn()

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, *exc):
        return self._conn.__exit__(*exc)


def batches(n: int) -> str:
    return f"{n} batch" if n == 1 else f"{n} batches"


class Rehearsal:
    def __init__(self, seed: int, backfill, workdir: str, quiet: bool = False, skip_guard: bool = False):
        self.seed, self.backfill, self.quiet, self.skip_guard = seed, backfill, quiet, skip_guard
        self.rng = random.Random(seed)
        self.db = os.path.join(workdir, f"rehearsal-{seed}.db")
        self.clock = FixedClock("2026-10-01T12:00:00")
        self.writes = Counter()
        self.problems: list[str] = []

    # ---- output -------------------------------------------------------------------
    def say(self, step: str, text: str) -> None:
        if not self.quiet:
            print(f"  {step:>3}  {text}")

    def expect(self, ok: bool, what: str) -> None:
        if not ok:
            self.problems.append(what)
            self.say("!!", "UNEXPECTED: " + what)

    # ---- writes through the real apps, recorded in self.expected ---------------------
    def buy(self, client, who: str, day: str | None = None) -> int | None:
        day = day or self.rng.choice(DAYS)
        holder = self.rng.choice(PEOPLE)
        res = client.post("/api/tickets", json={"holder": holder, "day": day})
        self.expect(res.status_code == 201, f"{who} buy: HTTP {res.status_code} {res.text}")
        if res.status_code != 201:
            return None
        body = res.json()
        self.expected[body["id"]] = (holder, body["code"], (day,))
        self.writes[f"{who} sold"] += 1
        return body["id"]

    def move(self, client, who: str, ticket_id: int | None = None) -> None:
        if ticket_id is None:
            ticket_id = self.rng.choice([t for t, v in self.expected.items() if len(v[2]) == 1])
        holder, code, (old_day,) = self.expected[ticket_id]
        new_day = self.rng.choice([d for d in DAYS if d != old_day])
        res = client.post(f"/api/tickets/{ticket_id}/change-day", json={"day": new_day})
        self.expect(res.status_code == 200, f"{who} move #{ticket_id}: HTTP {res.status_code} {res.text}")
        if res.status_code == 200:
            self.expected[ticket_id] = (holder, code, (new_day,))
            self.writes[f"{who} moved"] += 1

    def random_write(self, client, who: str) -> None:
        if self.rng.random() < 0.5:
            self.buy(client, who)
        else:
            self.move(client, who)

    def sell_pass(self, client) -> int | None:
        first, last = self.rng.choice([(DAYS[0], DAYS[1]), (DAYS[1], DAYS[2]), (DAYS[0], DAYS[2])])
        holder = self.rng.choice(PEOPLE)
        res = client.post("/api/passes", json={"holder": holder, "first_day": first, "last_day": last})
        self.expect(res.status_code == 201, f"v2 pass: HTTP {res.status_code} {res.text}")
        if res.status_code != 201:
            return None
        body = res.json()
        self.expected[body["id"]] = (holder, body["code"], mm.admitted_days(first, last))
        self.writes["v2 passes"] += 1
        return body["id"]

    # ---- the rehearsal --------------------------------------------------------------
    def run(self) -> bool:
        os.environ["AFTERHOURS_DB"] = self.db
        os.environ["AFTERHOURS_PAYMENT_DELAY"] = "0"
        make(self.db, tickets=600, seed=100 + self.seed)
        conn = steps.connect(self.db)
        try:
            return self._run(conn)
        finally:
            conn.close()

    def _run(self, conn) -> bool:
        self.expected = mm.meaning(conn)
        self.say("0", f"copy of production: {len(self.expected)} day tickets, v1 table")

        steps.expand(conn)
        self.say("1", "expand: tickets.first_day and tickets.last_day added (NULL everywhere)")

        v1_client = TestClient(v1.main.create_app(clock=self.clock), raise_server_exceptions=False)
        v2_client = TestClient(v2.main.create_app(clock=self.clock), raise_server_exceptions=False)
        v1_client.__enter__()
        v2_client.__enter__()
        clients = {"v1": v1_client, "v2": v2_client}

        # 2. Both versions write while the backfill runs in another thread.
        result = {}
        gap_open, gap_done = threading.Event(), threading.Event()

        def run_backfill():
            bconn = steps.connect(self.db)
            try:
                result["report"] = self.backfill(SlowCommits(bconn, gap_open, gap_done), batch_size=20)
            except BaseException as exc:  # reported below
                result["error"] = exc
            finally:
                bconn.close()
                gap_open.set()          # never leave the writers waiting

        worker = threading.Thread(target=run_backfill)
        worker.start()
        while worker.is_alive():
            # Three writes in each gap between batches, one at a time otherwise.
            in_gap = gap_open.wait(timeout=0.005)
            for _ in range(3 if in_gap else 1):
                who = self.rng.choice(["v1", "v2"])
                self.random_write(clients[who], who)
                self.writes["during the backfill"] += 1
            if in_gap:
                gap_open.clear()
                gap_done.set()
        worker.join()
        if "error" in result:
            v1_client.__exit__(None, None, None)
            v2_client.__exit__(None, None, None)
            if isinstance(result["error"], NotImplementedError):
                self.say("2", f"backfill: {result['error']}")
            else:
                self.say("2", f"backfill raised {type(result['error']).__name__}: {result['error']}")
            self.problems.append("the backfill did not run")
            return False
        report = result["report"]
        self.say("2", f"backfill: {report.rows} rows in {batches(report.batches)}, while v1 and v2 "
                      f"made {self.writes['during the backfill']} writes "
                      f"(v1 {self.writes['v1 sold'] + self.writes['v1 moved']}, "
                      f"v2 {self.writes['v2 sold'] + self.writes['v2 moved']})")
        checks = steps.verify(conn)
        self.say("", f"checks: missing {checks['missing']}, disagree {checks['disagree']}")

        # 3. v1 keeps writing after the backfill: moves tickets it already copied, sells new ones.
        copied = [row["id"] for row in conn.execute(
            "SELECT id FROM tickets WHERE first_day = day AND last_day = day ORDER BY id")]
        for ticket_id in self.rng.sample(copied, 12):
            self.move(v1_client, "v1", ticket_id)
        for _ in range(12):
            self.buy(v1_client, "v1")
        for _ in range(12):
            self.random_write(v2_client, "v2")
        checks = steps.verify(conn)
        self.say("3", f"after the backfill: v1 moved 12 copied tickets and sold 12; v2 made 12 writes")
        self.say("", f"checks: missing {checks['missing']}, disagree {checks['disagree']}")
        self.expect(checks["missing"] >= 1 and checks["disagree"] >= 1,
                    "v1's late writes should show up in the checks")

        # 4. Guards while v1 is live.
        try:
            steps.set_flag(conn, "multi_day_passes", True)
            self.expect(False, "passes went on sale while v1 was live")
        except steps.StepRefused:
            self.say("4", "flag multi_day_passes on: REFUSED (v1 is live)")
        try:
            contract(conn)
            self.expect(False, "contract ran while v1 was live")
        except steps.StepRefused as exc:
            self.say("", f"contract: REFUSED ({len(exc.reasons)} reasons, first: v1 is still live)")

        # 5. Retire v1: stop its server, then record it.
        v1_client.__exit__(None, None, None)
        steps.retire(conn, "v1")
        self.say("5", "v1 stopped and recorded as retired")

        if self.skip_guard:
            # DEMONSTRATION ONLY: what the guard is for. Catch up with whatever backfill was
            # given, then rebuild the table with no checks at all.
            report = self.backfill(conn, batch_size=50)
            self.say("6", f"backfill again: {report.rows} rows in {batches(report.batches)}")
            conn.execute("BEGIN IMMEDIATE")
            try:
                copied_rows = _rebuild(conn)
                conn.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                conn.execute("ROLLBACK")
                self.say("7", f"contract WITHOUT the guard: stopped by the new table's constraints ({exc})")
                self.problems.append("contract without the guard failed")
                v2_client.__exit__(None, None, None)
                return False
            self.say("7", f"contract WITHOUT the guard (demonstration): `day` dropped, {copied_rows} tickets copied")
            v2_client.__exit__(None, None, None)
            return self.compare(conn, step="8")

        # 6. Contract refused: the data has not caught up.
        try:
            contract(conn)
            self.expect(False, "contract ran before the catch-up backfill")
        except steps.StepRefused as exc:
            self.say("6", "contract: REFUSED")
            for reason in exc.reasons:
                self.say("", "  - " + reason)

        # 7. Catch-up backfill, then verify.
        report = self.backfill(conn, batch_size=50)
        checks = steps.verify(conn)
        self.say("7", f"backfill again: {report.rows} rows in {batches(report.batches)}; "
                      f"checks: missing {checks['missing']}, disagree {checks['disagree']}, "
                      f"backwards {checks['backwards']}")
        self.expect(not any(checks.values()), f"checks not all zero after the catch-up: {checks}")

        # 8. Passes on sale.
        steps.set_flag(conn, "multi_day_passes", True)
        passes = [self.sell_pass(v2_client) for _ in range(20)]
        refused = 0
        for ticket_id in [p for p in passes if p][:3]:
            res = v2_client.post(f"/api/tickets/{ticket_id}/change-day", json={"day": DAYS[0]})
            refused += res.status_code == 409
        self.expect(refused == 3, "a pass changed days")
        for _ in range(10):
            self.random_write(v2_client, "v2")
        self.say("8", f"passes on sale: v2 sold {self.writes['v2 passes']} passes "
                      f"(moving a pass: refused {refused} of 3), plus 10 more writes")

        # 9. Contract.
        try:
            copied_rows = contract(conn)
            self.say("9", f"contract: `day` dropped, {copied_rows} tickets copied")
        except steps.StepRefused as exc:
            self.say("9", "contract: REFUSED")
            for reason in exc.reasons:
                self.say("", "  - " + reason)
            self.problems.append("contract refused after the catch-up backfill")
            v2_client.__exit__(None, None, None)
            return False

        # 10. After the contract.
        before = sum(self.writes.values())
        for _ in range(10):
            self.random_write(v2_client, "v2")
        self.sell_pass(v2_client)
        after = sum(self.writes.values()) - before
        v2_client.__exit__(None, None, None)
        with TestClient(v1.main.create_app(clock=self.clock), raise_server_exceptions=False) as late_v1:
            res = late_v1.post("/api/tickets", json={"holder": "Maya", "day": DAYS[0]})
        self.expect(res.status_code == 500, f"v1 after the contract answered {res.status_code}")
        self.say("10", f"v2 after the contract: {after} of 11 writes succeeded; "
                       f"a v1 server started by mistake: HTTP {res.status_code} on its first sale")
        self.expect(after == 11, "v2 writes failed after the contract")
        return self.compare(conn)

    def compare(self, conn, step: str = "11") -> bool:
        final = mm.meaning(conn)
        diffs = mm.differences(self.expected, final)
        fresh = self.fresh_shape()
        migrated = [tuple(r) for r in conn.execute("SELECT name, type, \"notnull\", pk FROM pragma_table_info('tickets')")]
        self.expect(migrated == fresh, "the migrated tickets table differs from a fresh v2 table")
        self.say(step, f"meaning: expected {len(self.expected)} tickets, found {len(final)}, "
                       f"{len(mm.differences(self.expected, final, limit=10**9))} differences")
        for line in diffs:
            self.say("", "  - " + line)
        if diffs:
            self.problems.append("meaning differs")
        return not self.problems

    def fresh_shape(self):
        path = self.db + ".fresh"
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(path + suffix):
                os.remove(path + suffix)
        v2.db.init_db(path)
        conn = steps.connect(path)
        try:
            return [tuple(r) for r in conn.execute("SELECT name, type, \"notnull\", pk FROM pragma_table_info('tickets')")]
        finally:
            conn.close()


def split_spec(spec: str) -> tuple[str, str]:
    """'package.module:function' or 'path/to/file.py:function' -> (module or path, function).

    Splits at the LAST colon, so a Windows path such as C:\\course\\naive_backfill.py:backfill
    works. Without a function name, the function is `backfill`.
    """
    head, sep, tail = spec.rpartition(":")
    if sep and head and tail.isidentifier():
        return head, tail
    return spec, "backfill"


def load_backfill(spec: str):
    """'package.module:function' or 'path/to/file.py:function'."""
    module, name = split_spec(spec)
    if module.endswith(".py"):
        loader = importlib.util.spec_from_file_location("custom_backfill", module)
        mod = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(mod)
    else:
        mod = importlib.import_module(module)
    return getattr(mod, name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1, help="first seed (default 1)")
    parser.add_argument("--backfill", default="migrations.backfill:backfill")
    parser.add_argument("--workdir", default=None, help="where to put the rehearsal databases")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--skip-guard", action="store_true",
                        help="DEMONSTRATION ONLY: contract without the guard, to see what it prevents")
    args = parser.parse_args()
    backfill = load_backfill(args.backfill)
    workdir = args.workdir or tempfile.mkdtemp(prefix="rehearsal-")
    passed = 0
    for seed in range(args.seed, args.seed + args.runs):
        print(f"rehearsal, seed {seed}:")
        rehearsal = Rehearsal(seed, backfill, workdir, quiet=args.quiet, skip_guard=args.skip_guard)
        ok = rehearsal.run()
        passed += ok
        print(f"  {'PASS' if ok else 'FAIL'}" + ("" if ok else ": " + "; ".join(rehearsal.problems)))
    print(f"{passed} of {args.runs} rehearsals passed")
    return 0 if passed == args.runs else 1


if __name__ == "__main__":
    sys.exit(main())
