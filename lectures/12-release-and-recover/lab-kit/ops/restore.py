"""Restore an environment from a backup, but only a backup that has passed its rehearsal.

    python ops/restore.py production backups/production-20261009T181502Z.db --confirm production

Steps, printed as they happen:
  1 rehearse   run restore_check.py on the backup (a separate instance); stop if any check fails
  2 stop       stop the environment's server
  3 set aside  keep the current database as envs/<env>/replaced-<UTC time>.db (never deleted)
  4 restore    copy the backup into envs/<env>/afterhours.db with SQLite's backup API
  5 start      start the release named in the backup's manifest, and run the gates

--confirm must repeat the environment's name. GitLab's engineer wiped the wrong host; a
tool that makes you type the name of the machine you are about to overwrite is a fence,
where a warning in a runbook is only a sign.
"""

import argparse
import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from envs import KIT, db_path, env_config, env_dir, record, start, step, stop
from gates import run_gates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("env", help="the environment to overwrite, e.g. production")
    parser.add_argument("snapshot", help="a backup made by ops/backup.py (with its manifest)")
    parser.add_argument("--confirm", required=True, metavar="ENV",
                        help="type the environment's name again")
    args = parser.parse_args()
    env_config(args.env)  # exits if unknown
    if args.confirm != args.env:
        sys.exit(f"Refusing: --confirm says '{args.confirm}', but you asked to overwrite "
                 f"'{args.env}'. Nothing was changed.")

    snapshot = Path(args.snapshot)
    if not snapshot.exists() and (KIT / args.snapshot).exists():
        snapshot = KIT / args.snapshot
    manifest_path = snapshot.with_suffix(".json")
    if not snapshot.exists() or not manifest_path.exists():
        sys.exit(f"Refusing: {args.snapshot} and its manifest (.json) must both exist. "
                 f"Only restore backups made by ops/backup.py. Nothing was changed.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    release = manifest["release"]
    print(f"Restoring {args.env} from {snapshot.name} (taken {manifest['created_at']}, "
          f"release {release})")
    started = time.monotonic()

    rehearsal = subprocess.run([sys.executable, str(KIT / "ops" / "restore_check.py"), str(snapshot)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
    result = next((l for l in rehearsal.stdout.splitlines() if l.startswith("RESULT")), "no result")
    step("1/5", "rehearse", rehearsal.returncode == 0, result)
    if rehearsal.returncode != 0:
        print(rehearsal.stdout)
        print("STOPPED: this backup failed its rehearsal. Nothing was changed.")
        sys.exit(1)

    step("2/5", "stop", True, stop(args.env))

    target = db_path(args.env)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    kept = env_dir(args.env) / f"replaced-{stamp}.db"
    if target.exists():
        for suffix in ("", "-wal", "-shm"):  # the database and its journal files move together
            old = Path(f"{target}{suffix}")
            if old.exists():
                old.rename(Path(f"{kept}{suffix}"))
        step("3/5", "set aside", True, f"the old database is kept as envs/{args.env}/{kept.name}")
    else:
        step("3/5", "set aside", None, "there was no database to keep")

    src = sqlite3.connect(snapshot)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    step("4/5", "restore", True, f"copied {snapshot.name} into envs/{args.env}/afterhours.db")

    answer, error = start(args.env, release)
    results = run_gates(args.env, release) if answer else []
    for name, ok, detail in results:
        step("5/5", name, ok, detail)
    passed = answer is not None and all(ok for _, ok, _ in results)
    if answer is None:
        step("5/5", "start", False, error)
    seconds = time.monotonic() - started
    record(args.env, "restore", release, "ok" if passed else "failed",
           snapshot=snapshot.name, seconds=round(seconds, 1))
    if passed:
        print(f"Restored {args.env} in {seconds:.1f} s. Everything written after "
              f"{manifest['created_at']} is not in this database; the replaced one is kept.")
    else:
        print(f"RESTORE FAILED at the last step. The replaced database is kept as "
              f"envs/{args.env}/{kept.name}. Look at envs/{args.env}/server.log.")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
