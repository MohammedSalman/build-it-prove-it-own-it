"""Back up the AfterHours database, safely, even while the app is running.

    python scripts/backup.py backups/afterhours-before-release.db
    python scripts/backup.py --db other.db backups/other-copy.db

Uses SQLite's online backup API, which copies one consistent snapshot while other
connections keep writing. Do not copy afterhours.db with cp or Copy-Item while the app
runs: in WAL mode the latest changes can still be in afterhours.db-wal, so a plain file copy
can miss them or catch a half-written state.

After a backup, check the copy: python scripts/check_data.py <copy>
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="where to write the copy (must not exist yet)")
    parser.add_argument("--db", default=os.environ.get("AFTERHOURS_DB", "afterhours.db"),
                        help="database to back up (default: $AFTERHOURS_DB or afterhours.db)")
    args = parser.parse_args()

    source_path = Path(args.db)
    target_path = Path(args.target)
    if not source_path.exists():
        print(f"no database at {source_path}", file=sys.stderr)
        return 2
    if target_path.exists():
        print(f"{target_path} already exists; choose a new name (backups are never overwritten)",
              file=sys.stderr)
        return 2
    target_path.parent.mkdir(parents=True, exist_ok=True)

    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    target = sqlite3.connect(target_path)
    try:
        source.backup(target)
        events = target.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        reservations = target.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    finally:
        target.close()
        source.close()
    print(f"backed up {source_path} -> {target_path}: {events} events, {reservations} reservations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
