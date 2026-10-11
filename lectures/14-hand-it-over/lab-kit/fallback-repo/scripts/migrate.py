"""Apply pending migrations to a database file without starting the app.

    python scripts/migrate.py --status backups/copy.db    # which migrations are applied
    python scripts/migrate.py backups/copy.db             # apply the pending ones

The app applies pending migrations by itself when it starts. Use this script to rehearse a
release on a backup copy first (docs/runbook.md, section 3). It never seeds data.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so "app" can be imported

from app import db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("database", help="the database file to migrate (must exist)")
    parser.add_argument("--status", action="store_true", help="only list migrations and whether each is applied")
    args = parser.parse_args()

    path = Path(args.database)
    if not path.exists():
        print(f"no database at {path}", file=sys.stderr)
        return 2

    if args.status:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            has_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
            ).fetchone()
            done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")} if has_table else set()
        finally:
            conn.close()
        files = db.migration_files()
        if not files:
            print("no migrations in app/migrations/")
        for f in files:
            print(("applied  " if f.name in done else "PENDING  ") + f.name)
        return 0

    applied = db.init_db(str(path), seed=False)
    print("applied: " + (", ".join(applied) if applied else "nothing (already up to date)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
