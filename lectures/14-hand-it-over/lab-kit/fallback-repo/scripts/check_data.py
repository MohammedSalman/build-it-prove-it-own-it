"""Check that an AfterHours database keeps its promises.

    python scripts/check_data.py                      # $AFTERHOURS_DB, or afterhours.db
    python scripts/check_data.py backups/copy.db      # any copy, for example a restored backup

Checks, in order:
  1. SQLite's own integrity check says "ok".
  2. Every reservation belongs to an event that exists.
  3. The promise: confirmed reservations for an event <= its capacity, for every event.

Prints the counts, so you can compare a restored copy with the original. Opens the file
read-only and never changes it. Exit code: 0 all checks hold, 1 a check failed, 2 no file.
"""

import os
import sqlite3
import sys
from pathlib import Path


def check(path: Path) -> list[str]:
    """Return a list of problems (empty when the database keeps its promises)."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    problems = []
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            problems.append(f"integrity_check: {integrity}")

        orphans = conn.execute(
            "SELECT r.id FROM reservations r LEFT JOIN events e ON e.id = r.event_id "
            "WHERE e.id IS NULL"
        ).fetchall()
        for row in orphans:
            problems.append(f"reservation #{row['id']} belongs to no event")

        oversold = conn.execute(
            "SELECT e.id, e.title, e.capacity, COUNT(r.id) AS reserved "
            "FROM events e LEFT JOIN reservations r ON r.event_id = e.id "
            "GROUP BY e.id HAVING COUNT(r.id) > e.capacity"
        ).fetchall()
        for row in oversold:
            problems.append(
                f"event #{row['id']} ({row['title']}): {row['reserved']} reservations "
                f"for {row['capacity']} places"
            )

        events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        reservations = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
        print(f"{path}: {events} events, {reservations} reservations")
    finally:
        conn.close()
    return problems


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AFTERHOURS_DB", "afterhours.db"))
    if not path.exists():
        print(f"no database at {path}", file=sys.stderr)
        return 2
    problems = check(path)
    if problems:
        for p in problems:
            print("FAIL  " + p)
        return 1
    print("OK    integrity, every reservation has an event, confirmed <= capacity everywhere")
    return 0


if __name__ == "__main__":
    sys.exit(main())
