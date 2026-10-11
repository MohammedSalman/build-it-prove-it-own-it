"""Back up an environment's database with SQLite's online backup API.

    python ops/backup.py production

Safe while the app is serving visitors: the backup API copies a consistent snapshot
of the database as it was when the copy began, even if bookings arrive meanwhile.
(Copying the file with cp or Copy-Item while the app writes is not safe.)

Writes three files to backups/:
  <env>-<UTC time>.db         the snapshot, a complete SQLite database
  <env>-<UTC time>.dump.txt   its canonical logical dump (see dbfacts.py)
  <env>-<UTC time>.json       the manifest: when, from where, what release, what is in it
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone

from dbfacts import canonical_dump, describe, sha256
from envs import BACKUPS, db_path, env_config, health, load_state


def backup(env: str) -> dict:
    env_config(env)  # exits if the name is unknown
    source = db_path(env)
    if not source.exists():
        sys.exit(f"{env} has no database yet ({source}). Deploy a release to it first.")
    BACKUPS.mkdir(exist_ok=True)
    moment = datetime.now(timezone.utc)
    name = f"{env}-{moment.strftime('%Y%m%dT%H%M%SZ')}"
    snapshot = BACKUPS / f"{name}.db"
    if snapshot.exists():
        sys.exit(f"{snapshot} already exists; wait a second and run again.")

    started = time.monotonic()
    src = sqlite3.connect(source, timeout=10)
    dst = sqlite3.connect(snapshot)
    try:
        src.backup(dst)                          # the online backup API
        dst.execute("PRAGMA journal_mode = DELETE")  # one self-contained file, no -wal
    finally:
        dst.close()
        src.close()
    seconds = time.monotonic() - started

    facts = describe(snapshot)
    dump = canonical_dump(snapshot)
    (BACKUPS / f"{name}.dump.txt").write_text(dump, encoding="utf-8")
    running = health(env)
    manifest = {
        "env": env,
        "source": str(source),
        "snapshot": snapshot.name,
        "created_at": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "release": (running or {}).get("release") or load_state(env).get("release"),
        "seconds": round(seconds, 3),
        "bytes": snapshot.stat().st_size,
        **facts,
        "dump_sha256": sha256(dump),
    }
    (BACKUPS / f"{name}.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Backed up {env} with SQLite's online backup API in {seconds:.2f} s.")
    print(f"  snapshot  backups/{snapshot.name}  ({manifest['bytes']:,} bytes)")
    print(f"  contents  {facts['events']} events, {facts['reservations']} reservations; "
          f"newest reservation {facts['newest_reservation']}")
    print(f"  dump      backups/{name}.dump.txt  (sha256 {manifest['dump_sha256'][:12]}...)")
    print(f"  manifest  backups/{name}.json  (release {manifest['release']})")
    print(f"Next: python ops/restore_check.py backups/{snapshot.name}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("env", help="the environment to back up, e.g. production")
    backup(parser.parse_args().env)


if __name__ == "__main__":
    main()
