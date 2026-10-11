"""Make a DAMAGED copy of a backup, to test that restore_check.py can see damage.

    python ops/tamper.py backups/production-....db --orphan    # a reservation for an event that does not exist
    python ops/tamper.py backups/production-....db --oversell  # one event gets more reservations than places

The original backup is never changed. The damaged copy is written next to it as
<name>-orphan.db or <name>-oversell.db. If the original has a manifest, the copy gets one
too, with the original's time and release and its own counts and dump: a backup that was
damaged before anyone looked. A check you have never seen fail is a check you cannot
trust (Week 5).
"""

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path

from dbfacts import canonical_dump, describe, sha256
from envs import KIT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("snapshot")
    damage = parser.add_mutually_exclusive_group(required=True)
    damage.add_argument("--orphan", action="store_true")
    damage.add_argument("--oversell", action="store_true")
    args = parser.parse_args()

    source = Path(args.snapshot)
    if not source.exists() and (KIT / args.snapshot).exists():
        source = KIT / args.snapshot
    if not source.exists():
        sys.exit(f"No such backup file: {args.snapshot}")
    kind = "orphan" if args.orphan else "oversell"
    copy = source.with_name(f"{source.stem}-{kind}.db")
    shutil.copyfile(source, copy)

    conn = sqlite3.connect(copy)  # foreign keys are OFF by default in SQLite
    try:
        if args.orphan:
            conn.execute("INSERT INTO reservations (event_id, attendee) VALUES (99999, 'ghost')")
            what = "added a reservation for event 99999, which does not exist"
        else:
            event_id, capacity, taken = conn.execute(
                "SELECT e.id, e.capacity, COUNT(r.id) FROM events e "
                "LEFT JOIN reservations r ON r.event_id = e.id "
                "GROUP BY e.id ORDER BY e.id LIMIT 1").fetchone()
            extra = capacity - taken + 1
            conn.executemany("INSERT INTO reservations (event_id, attendee) VALUES (?, ?)",
                             [(event_id, f"extra-{i}") for i in range(extra)])
            what = f"event {event_id} now has {capacity + 1} reservations for {capacity} places"
        conn.commit()
    finally:
        conn.close()
    manifest = source.with_suffix(".json")
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data.update(describe(copy), snapshot=copy.name, damaged=kind,
                    bytes=copy.stat().st_size, dump_sha256=sha256(canonical_dump(copy)))
        copy.with_suffix(".json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Damaged copy: {copy.relative_to(KIT) if copy.is_relative_to(KIT) else copy} ({what})")
    print(f"Now: python ops/restore_check.py {copy.relative_to(KIT) if copy.is_relative_to(KIT) else copy}")


if __name__ == "__main__":
    main()
