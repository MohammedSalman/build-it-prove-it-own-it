"""Restore rehearsal: restore a backup into a SEPARATE instance, then check it.

    python ops/restore_check.py backups/production-20261009T181502Z.db
    python ops/restore_check.py backups/nightly-20261009.db --release 1.4.0

It never touches staging or production. The separate instance is the "restore"
environment in ops/pipeline.json: its own port and its own database file
(envs/restore/afterhours.db). Steps:

  1 restore   copy the snapshot into envs/restore/afterhours.db (SQLite backup API)
  2 start     start the release that production ran when the backup was taken
  3 checks    look at the result the way a visitor would, and the way an owner would

Part A4: write the two queries below. Each must return ONE ROW PER PROBLEM it finds,
and NO ROWS when the data keeps the promise. Test them without any server:
    python -m pytest -q ops/tests/test_restore_check.py
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dbfacts import canonical_dump, describe, integrity, sha256
from envs import KIT, base_url, db_path, http, load_state, start, stop

# Every reservation references an existing event.
# One row per reservation whose event_id matches no row in events.
ORPHANS_SQL = None  # TODO (Part A4)

# Confirmed reservations <= capacity, for every event. (In this schema every
# reservation is a confirmed one.) One row per event that has more reservations
# than places.
OVER_CAPACITY_SQL = None  # TODO (Part A4)


def find_problems(conn: sqlite3.Connection, sql: str | None, name: str) -> list:
    if sql is None:
        raise NotImplementedError(f"not written yet: {name} in ops/restore_check.py (Part A4)")
    return conn.execute(sql).fetchall()


# ---------- the checks: each returns (passed, what it saw) ----------

def check_answers() -> tuple[bool, str]:
    status, body, _ = http("GET", base_url("restore") + "/api/events")
    if status != 200 or not isinstance(body, list):
        return False, f"GET /api/events -> {status or 'no answer'}"
    return True, f"GET /api/events -> 200, the programme lists {len(body)} events"


def check_integrity(database: Path) -> tuple[bool, str]:
    result = integrity(database)
    return result == "ok", f"PRAGMA integrity_check says: {result}"


def check_query(database: Path, sql: str | None, name: str, what: str) -> tuple[bool, str]:
    conn = sqlite3.connect(database, timeout=10)
    try:
        rows = find_problems(conn, sql, name)
    except NotImplementedError as exc:
        return False, str(exc)
    except sqlite3.Error as exc:
        return False, f"{name} does not run: {exc}"
    finally:
        conn.close()
    if not rows:
        return True, f"0 {what}s found"
    shown = "; ".join(str(tuple(r)) for r in rows[:3])
    return False, f"{len(rows)} {what}{'' if len(rows) == 1 else 's'} found, e.g. {shown}"


def check_has_data(snapshot: Path, taken_at: datetime | None,
                   max_age_hours: float) -> tuple[bool, str]:
    facts = describe(snapshot)
    detail = (f"the snapshot holds {facts['events']} events and {facts['reservations']} "
              f"reservations (newest: {facts['newest_reservation']})")
    has_data = facts["events"] > 0 and facts["reservations"] > 0
    if taken_at is None:
        # A file's date changes when it is copied, so it says nothing about the data's age.
        return False, detail + "; no manifest, so nothing records when it was taken"
    age_hours = (datetime.now(timezone.utc) - taken_at).total_seconds() / 3600
    detail += f"; taken {age_hours:.1f} h ago according to its manifest"
    return has_data and age_hours <= max_age_hours, detail


def check_dump(snapshot: Path, database: Path, manifest: dict | None) -> tuple[bool, str]:
    expected = canonical_dump(snapshot)
    actual = canonical_dump(database)
    if manifest and manifest.get("dump_sha256") != sha256(expected):
        return False, "the snapshot no longer matches its manifest (changed after the backup?)"
    if expected == actual:
        return True, (f"canonical dumps match: {expected.count(chr(10))} lines, "
                      f"sha256 {sha256(actual)[:12]}... on both sides")
    want, got = expected.splitlines(), actual.splitlines()
    line = next((i for i, (a, b) in enumerate(zip(want, got)) if a != b), min(len(want), len(got)))
    show = lambda lines: repr(lines[line][:60]) if line < len(lines) else "(end of dump)"
    return False, (f"the restored instance is NOT the snapshot: snapshot {len(want)} lines, "
                   f"restored {len(got)} lines; first difference at line {line + 1}: "
                   f"snapshot {show(want)}, restored {show(got)}")


# ---------- the rehearsal ----------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("snapshot", help="a backup file, e.g. backups/production-....db")
    parser.add_argument("--release", help="release to start (default: from the manifest)")
    parser.add_argument("--max-age-hours", type=float, default=24.0,
                        help="a snapshot older than this fails the data check (default 24)")
    parser.add_argument("--keep", action="store_true", help="leave the restored instance running")
    args = parser.parse_args()

    snapshot = Path(args.snapshot)
    if not snapshot.exists() and (KIT / args.snapshot).exists():
        snapshot = KIT / args.snapshot
    if not snapshot.exists():
        sys.exit(f"No such backup file: {args.snapshot}")
    manifest_path = snapshot.with_suffix(".json")
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.exists() else None)
    taken_at = None
    if manifest:
        taken_at = datetime.strptime(manifest["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    release = (args.release or (manifest or {}).get("release")
               or load_state("production").get("release"))
    if not release:
        sys.exit("Which release should run the restored data? Give --release, e.g. --release 1.4.0")

    print(f"Restore rehearsal: {snapshot.name} -> a separate instance "
          f"(environment 'restore', {base_url('restore')})")
    print(f"  manifest: {manifest_path.name if manifest else 'none: the snapshot file itself is the reference, and its age is unknown'}")
    started = time.monotonic()

    stop("restore")
    target = db_path("restore")
    for leftover in (target, Path(f"{target}-wal"), Path(f"{target}-shm")):
        leftover.unlink(missing_ok=True)
    src = sqlite3.connect(snapshot)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    copied = time.monotonic()
    print(f"  [1] restore   copied into envs/restore/afterhours.db in {copied - started:.2f} s")

    answer, error = start("restore", release)
    if answer is None:
        print(f"  [2] start     FAIL  {error}")
        print("RESULT: FAIL (the restored instance did not start)")
        sys.exit(1)
    running = time.monotonic()
    print(f"  [2] start     release {release} answers on port {base_url('restore').rsplit(':', 1)[1]}"
          f" after {running - copied:.2f} s")

    checks = [
        ("a visitor can load the programme", check_answers()),
        ("the database file is intact", check_integrity(target)),
        ("every reservation references an existing event",
         check_query(target, ORPHANS_SQL, "ORPHANS_SQL", "problem row")),
        ("confirmed <= capacity for every event",
         check_query(target, OVER_CAPACITY_SQL, "OVER_CAPACITY_SQL", "problem row")),
        ("the snapshot has recent data", check_has_data(snapshot, taken_at, args.max_age_hours)),
        ("the restored instance holds exactly the snapshot", check_dump(snapshot, target, manifest)),
    ]
    finished = time.monotonic()
    print("  [3] checks")
    for label, (passed, detail) in checks:
        print(f"      {'PASS' if passed else 'FAIL'}  {label}: {detail}")

    if not args.keep:
        stop("restore")
    passed = sum(1 for _, (ok, _) in checks if ok)
    print(f"Time to a checked restore of this data: {finished - started:.1f} s "
          f"(copy {copied - started:.1f}, start {running - copied:.1f}, checks {finished - running:.1f}).")
    if passed == len(checks):
        lost = datetime.now(timezone.utc) - taken_at
        minutes, secs = divmod(int(lost.total_seconds()), 60)
        print(f"Data-loss window if production failed now and this backup were used: "
              f"{minutes} min {secs} s (everything after "
              f"{taken_at.strftime('%Y-%m-%d %H:%M:%S')} UTC).")
    else:
        print("Data-loss window: none can be claimed. This backup failed its checks, so it "
              "could not be used; only an earlier backup that passes would count.")
    print(f"RESULT: {'PASS' if passed == len(checks) else 'FAIL'} ({passed} of {len(checks)} checks passed)")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
