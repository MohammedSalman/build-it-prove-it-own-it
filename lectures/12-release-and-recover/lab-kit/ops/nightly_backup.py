"""Nightly backup: the team's job, run by cron at 03:00 since Week 3.

    python ops/nightly_backup.py

PLANTED FOR THE LAB. This job has a defect we put in on purpose. Do not fix it
before Part A4 asks you to test it: the point of the exercise is to find out
whether a backup job that "succeeds" every night has produced anything you could
restore.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = os.environ.get("AFTERHOURS_DB", "afterhours.db")


def main() -> None:
    out_dir = Path("backups")
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"nightly-{datetime.now(timezone.utc).strftime('%Y%m%d')}.db"
    src = sqlite3.connect(DB)
    dst = sqlite3.connect(out)
    src.backup(dst)
    dst.close()
    src.close()
    print(f"Backup OK: {out}")


if __name__ == "__main__":
    main()
