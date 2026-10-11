"""The runbook's commands work: back up, check the copy, see migration status.

Each test runs the real script in a subprocess, the way docs/runbook.md tells you to.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

from app import db

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, timeout=60)


def test_a_backup_is_a_complete_copy_that_passes_the_checks(tmp_path):
    live = tmp_path / "afterhours.db"
    db.init_db(str(live))
    copy = tmp_path / "backups" / "before-release.db"

    backup = run("scripts/backup.py", "--db", str(live), str(copy))
    seeded = sum(reserved for *_, reserved in db.SEED_EVENTS)      # 227
    assert backup.returncode == 0, backup.stderr
    assert f"5 events, {seeded} reservations" in backup.stdout

    checked = run("scripts/check_data.py", str(copy))
    assert checked.returncode == 0, checked.stdout
    assert checked.stdout.startswith(f"{copy}: 5 events, {seeded} reservations")


def test_a_backup_never_overwrites_an_existing_file(tmp_path):
    live = tmp_path / "afterhours.db"
    db.init_db(str(live))
    existing = tmp_path / "old-backup.db"
    existing.write_text("keep me")
    again = run("scripts/backup.py", "--db", str(live), str(existing))
    assert again.returncode == 2
    assert existing.read_text() == "keep me"


def test_the_data_check_catches_a_broken_promise(tmp_path):
    database = tmp_path / "afterhours.db"
    db.init_db(str(database))
    conn = sqlite3.connect(database)
    # Break the promise directly in the database: the escape room has 39 of 40, add two more.
    conn.executemany(
        "INSERT INTO reservations (event_id, attendee) VALUES (1, ?)", [("Maya",), ("Sam",)]
    )
    conn.commit()
    conn.close()

    checked = run("scripts/check_data.py", str(database))
    assert checked.returncode == 1
    assert "41 reservations for 40 places" in checked.stdout


def test_migration_status_lists_every_migration(tmp_path):
    database = tmp_path / "afterhours.db"
    db.init_db(str(database))
    status = run("scripts/migrate.py", "--status", str(database))
    assert status.returncode == 0, status.stderr
    names = [p.name for p in db.migration_files()]
    if names:
        assert all(f"applied  {n}" in status.stdout for n in names)
    else:
        assert "no migrations" in status.stdout
