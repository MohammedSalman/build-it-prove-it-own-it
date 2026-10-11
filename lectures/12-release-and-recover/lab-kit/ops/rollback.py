"""Put the previous good release back on an environment, and check it.

    python ops/rollback.py production              # the last release that passed its gates
    python ops/rollback.py production --to 1.4.0   # a release you name

A rollback changes code, not data. It is safe when the running release has not
changed the database in a way the older release cannot read. Say so in your runbook.
"""

import argparse
import sys
import time

from envs import env_config, load_state, last_good, record, step, switch
from gates import run_gates


def rollback(env: str, target: str | None = None) -> bool:
    """Switch `env` back to `target` (default: the last good release) and run the gates."""
    current = load_state(env)["release"]
    target = target or last_good(env, exclude=current)
    if not target:
        print(f"No earlier good release is recorded for {env}; nothing to roll back to.")
        return False

    print(f"Rolling back {env} (port {env_config(env)['port']}): {current} -> {target}")
    started = time.monotonic()
    answer, error, stopped = switch(env, target)
    if answer is None:
        step("1/2", "switch", False, f"{stopped}; {error}")
        record(env, "rollback", target, "failed", reason=error, from_release=current)
        print(f"ROLLBACK FAILED: {error}")
        return False
    step("1/2", "switch", True,
         f"{stopped}; started {target} (pid {answer['pid']})")

    results = run_gates(env, target)
    for name, passed, detail in results:
        step("2/2", name, passed, detail)
    passed = all(ok for _, ok, _ in results)
    seconds = time.monotonic() - started
    record(env, "rollback", target, "ok" if passed else "failed",
           from_release=current, seconds=round(seconds, 1))
    if passed:
        print(f"Service restored: {target} passed its gates {seconds:.1f} s after the rollback started.")
    else:
        print(f"ROLLBACK FAILED: {target} is running but did not pass its gates. "
              f"Look at envs/{env}/server.log.")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("env", help="staging or production")
    parser.add_argument("--to", dest="target", help="the release to go back to")
    args = parser.parse_args()
    sys.exit(0 if rollback(args.env, args.target) else 1)


if __name__ == "__main__":
    main()
