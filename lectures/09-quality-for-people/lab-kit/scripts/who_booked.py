"""Show the system state: what the database holds, whatever the page told the user.

The page shows what a person is told. This script shows what is actually stored, so you can
compare the two after a test run (for example: Maya saw "Sorry, that event just filled up",
but does she hold a place?).

Usage (from the kit folder; the app does not need to be running):
    python scripts/who_booked.py                 # every event: places reserved / capacity
    python scripts/who_booked.py --name Maya     # reservations whose name contains "Maya"

It reads the same database file as the app (AFTERHOURS_DB, default afterhours.db).
Seeded guests are called guest-001, guest-002, ...; they are counted but not listed.
Only the Python standard library is used.
"""

import argparse
import os
import sqlite3
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", help="only list reservations whose name contains this text")
    parser.add_argument("--db", default=os.environ.get("AFTERHOURS_DB", "afterhours.db"))
    args = parser.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f"No database at {args.db}. Start the app once (uvicorn app.main:app) to create it.")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        events = conn.execute(
            """SELECT e.id, e.title, e.capacity, COUNT(r.id) AS reserved
               FROM events e LEFT JOIN reservations r ON r.event_id = e.id
               GROUP BY e.id ORDER BY e.starts_at"""
        ).fetchall()
        print("Places reserved per event (system state):")
        for e in events:
            flag = "  <-- over capacity!" if e["reserved"] > e["capacity"] else ""
            print(f"  #{e['id']:<3} {e['reserved']:>3} / {e['capacity']:<3} {e['title']}{flag}")

        where, params = "r.attendee NOT LIKE 'guest-%'", ()
        if args.name:
            where += " AND r.attendee LIKE ?"
            params = (f"%{args.name}%",)
        rows = conn.execute(
            f"""SELECT r.id, r.attendee, r.created_at, e.title
                FROM reservations r JOIN events e ON e.id = r.event_id
                WHERE {where} ORDER BY r.id""",
            params,
        ).fetchall()
        print()
        print("Reservations (not counting seeded guests):" if not args.name
              else f'Reservations with a name containing "{args.name}":')
        if not rows:
            print("  none")
        for r in rows:
            print(f"  #{r['id']:<4} {r['attendee']:<16} {r['created_at']}  {r['title']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
