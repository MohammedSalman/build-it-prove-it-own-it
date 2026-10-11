"""Show what one request does inside the database: every SQL statement, its plan, its work.

    python scripts/explain.py                                    # GET /api/events/3601
    python scripts/explain.py /api/events/3700
    python scripts/explain.py "/api/events?from=2026-10-09&to=2026-10-12"
    python scripts/explain.py --db demo.db /api/events/1
    python scripts/explain.py --sql "SELECT COUNT(*) FROM reservations WHERE event_id = 3601"

It runs the request inside this process (no server needed) against the database named by
--db, or AFTERHOURS_DB, or afterhours.db, and prints:

  * how many SQL statements the request ran, and each one with its values filled in;
  * SQLite's query plan for each SELECT (the output of EXPLAIN QUERY PLAN);
  * the work SQLite did for each statement, counted in virtual-machine steps;
  * how long the whole request took (median of 5 runs, without the step counting);
  * the SQLite version, because plans and step counts can change between versions.

Reading a plan:
  SCAN t                          SQLite reads every row of table t, one after another.
  SEARCH t USING ... INDEX i      SQLite uses index i to jump straight to the matching rows.
  USING COVERING INDEX i          ...and everything it needs is in the index itself.
  AUTOMATIC ... INDEX             SQLite builds a temporary index just for this one statement,
                                  and throws it away afterwards.

About the steps: SQLite runs every statement as a small program for its virtual machine.
The step count is how many of its instructions ran. For the same data and the same SQLite
version it is the same on every computer, however fast or busy, so it is a measure of work
you can compare exactly. It is counted with sqlite3's set_progress_handler.

With --sql it shows the plan and the steps for one SELECT statement of your own instead.
Only GET requests and SELECT statements are run, so nothing in the database changes.
"""

import argparse
import os
import re
import sqlite3
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AFTERHOURS_PAYMENT_DELAY", "0")
# The app is imported inside main(), after --db is read: importing app.main builds the app,
# and building it would create an empty demo database if the file did not exist yet.


def one_line(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def explain_sql(conn: sqlite3.Connection, sql: str) -> None:
    for row in conn.execute("EXPLAIN QUERY PLAN " + sql).fetchall():
        print(f"      {row[3]}")


def count_steps(conn: sqlite3.Connection, sql: str) -> int:
    steps = 0

    def on_step() -> int:
        nonlocal steps
        steps += 1
        return 0                         # 0 means: carry on

    conn.set_progress_handler(on_step, 1)
    try:
        conn.execute(sql).fetchall()
    finally:
        conn.set_progress_handler(None, 1)
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default="/api/events/3601")
    parser.add_argument("--db", help="database file (default: AFTERHOURS_DB or afterhours.db)")
    parser.add_argument("--sql", help="explain this SELECT statement instead of a request")
    args = parser.parse_args()
    if args.db:
        os.environ["AFTERHOURS_DB"] = args.db
    path = os.environ.get("AFTERHOURS_DB", "afterhours.db")
    if not os.path.exists(path):
        sys.exit(f"No database at {path}. Run scripts/seed_festival.py first.")

    from fastapi.testclient import TestClient
    from app import db
    from app.main import create_app

    if args.sql:
        sql = one_line(args.sql)
        if not sql.upper().startswith("SELECT"):
            sys.exit("Only SELECT statements, please: explain.py never changes the database.")
        conn = sqlite3.connect(db.db_path())
        print(sql)
        print("    plan:")
        explain_sql(conn, sql)
        print(f"    work: {count_steps(conn, sql):,} SQLite steps")
        print(f"SQLite version: {sqlite3.sqlite_version}")
        conn.close()
        return

    client = TestClient(create_app())   # creates any missing tables or indexes from schema.sql
    real_connect = db.connect
    statements: list[dict] = []

    def traced_connect(*a, **kw):
        conn = real_connect(*a, **kw)

        def on_statement(sql: str) -> None:
            statements.append({"sql": one_line(sql), "steps": 0})

        def on_step() -> int:
            if statements:
                statements[-1]["steps"] += 1
            return 0                     # 0 means: carry on

        conn.set_trace_callback(on_statement)
        conn.set_progress_handler(on_step, 1)
        return conn

    db.connect = traced_connect
    try:
        response = client.get(args.path)
    finally:
        db.connect = real_connect

    times = []
    for _ in range(5):
        started = time.perf_counter()
        client.get(args.path)
        times.append((time.perf_counter() - started) * 1000)

    print(f"GET {args.path} -> HTTP {response.status_code}, "
          f"{statistics.median(times):.1f} ms (median of 5, this machine)")
    print(f"The request ran {len(statements)} SQL statement(s).\n")

    conn = sqlite3.connect(db.db_path())
    for n, st in enumerate(statements, 1):
        print(f"[{n}] {st['sql']}")
        if st["sql"].upper().startswith("SELECT"):
            print("    plan:")
            explain_sql(conn, st["sql"])
        print(f"    work: {st['steps']:,} SQLite steps\n")

    sizes = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("events", "reservations")}
    indexes = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'reservations' "
        "AND name NOT LIKE 'sqlite_autoindex%'")]
    conn.close()
    print(f"Table sizes: events {sizes['events']:,} rows, reservations {sizes['reservations']:,} rows")
    print("Indexes on reservations: " + (", ".join(indexes) if indexes else "none"))
    print(f"SQLite version: {sqlite3.sqlite_version} (plans and step counts can differ between versions)")


if __name__ == "__main__":
    main()
