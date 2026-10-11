"""Deploy a release to an environment, through the pipeline's gates.

    python ops/deploy.py staging 1.5.0
    python ops/deploy.py production 1.5.0

Four steps, printed as they happen:
  1 tests      the release's own test suite (run in releases/<release>/)
  2 promotion  production only: the release must have passed staging first
  3 switch     stop what runs now, start the new release on the environment's port
  4 gates      the checks listed in ops/pipeline.json ("gates")

If a gate fails and "auto_rollback" is true in ops/pipeline.json, the release that ran
before is started again and checked (see rollback.py).
"""

import argparse
import os
import subprocess
import sys
import time

from envs import (env_config, last_good, load_pipeline, load_state, record, release_dir,
                  step, switch)
from gates import run_gates
from rollback import rollback


def run_tests(folder) -> tuple[bool, str]:
    # Keep this shell's AFTERHOURS_* settings away from the tests: they must never
    # point at a real environment's database.
    env = {k: v for k, v in os.environ.items() if not k.startswith("AFTERHOURS_")}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"})
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                          cwd=folder, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    summary = lines[-1].strip("= ") if lines else "no output"
    return done.returncode == 0, summary


def deploy(env: str, release: str) -> int:
    config = load_pipeline()
    port = env_config(env)["port"]
    folder = release_dir(release)
    before = load_state(env)["release"]
    print(f"Deploying {release} to {env} (port {port}). Running now: {before or 'nothing'}")
    started = time.monotonic()

    passed, summary = run_tests(folder)
    step("1/4", "tests", passed, f"releases/{release}: {summary}")
    if not passed:
        print("STOPPED: the release's own tests fail. Nothing was changed.")
        return 1

    earlier = env_config(env).get("must_pass_first")
    if earlier:
        tries = [h for h in load_state(earlier)["history"]
                 if h["action"] == "deploy" and h["release"] == release]
        if not tries or tries[-1]["result"] != "ok":
            why = (f"its latest deploy to {earlier} failed ({tries[-1]['time']})" if tries
                   else f"it was never deployed to {earlier}")
            step("2/4", "promotion", False, f"{release} has not passed {earlier}: {why}")
            print(f"STOPPED: {release} must pass {earlier} first. Nothing was changed.")
            return 2
        step("2/4", "promotion", True, f"{release} passed {earlier} at {tries[-1]['time']}")
    else:
        step("2/4", "promotion", None, "not needed: this is the first environment")

    answer, error, stopped = switch(env, release)
    if answer is None:
        step("3/4", "switch", False, f"{stopped}; {error}")
        failure = error
        results = []
    else:
        step("3/4", "switch", True, f"{stopped}; started {release} (pid {answer['pid']})")
        results = run_gates(env, release)
        for name, ok, detail in results:
            step("4/4", name, ok, detail)
        failure = next((f"gate '{name}' failed" for name, ok, _ in results if not ok), "")

    seconds = time.monotonic() - started
    if not failure:
        record(env, "deploy", release, "ok", seconds=round(seconds, 1),
               gates=[name for name, _, _ in results])
        print(f"Deployed {release} to {env} in {seconds:.1f} s. "
              f"Gates passed: {', '.join(name for name, _, _ in results)}.")
        return 0

    record(env, "deploy", release, "failed", reason=failure, seconds=round(seconds, 1))
    print(f"STOPPED: {failure}.")
    previous = last_good(env, exclude=release)
    if config.get("auto_rollback") and previous:
        rollback(env, previous)
    else:
        print(f"{release} may still be running on {env}. To go back: python ops/rollback.py {env}")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("env", help="staging or production")
    parser.add_argument("release", help="a folder name in releases/, e.g. 1.5.0")
    args = parser.parse_args()
    sys.exit(deploy(args.env, args.release))


if __name__ == "__main__":
    main()
