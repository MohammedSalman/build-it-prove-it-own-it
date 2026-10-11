"""Test the tests: apply small deliberate mistakes (mutants) and see which ones the tests catch.

For every mutant listed in mutants.toml, this script
  1. copies this folder to a fresh temporary directory (so mutants never mix),
  2. makes the one change the mutant describes,
  3. runs pytest on the chosen tests in that copy,
  4. reports "caught" if the tests failed, "survived" if they all passed.
Your own files are never modified.

Usage (from the kit folder, with your virtual environment active):
    python mutants.py                          # all tests: tests/ and properties/
    python mutants.py --tests tests            # only the tests in tests/
    python mutants.py --tests tests/test_checkin.py tests/test_cancel.py
    python mutants.py --only M1,M7             # just some mutants
    python mutants.py --list                   # show the mutants without running anything
    python mutants.py --fail-under 80          # exit with status 1 if the score is below 80%

The score is raw: caught mutants divided by all mutants that could be applied. If you show that
a survivor is equivalent (it can never change anything anyone sees), you may report an adjusted
score without it, and say so. --fail-under always uses the raw score.

Only the Python standard library is used (tomllib needs Python 3.11 or newer).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

SKIP = shutil.ignore_patterns(
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".hypothesis",
    "*.db", "*.db-wal", "*.db-shm", "node_modules", ".DS_Store",
)


def load_mutants(path: Path) -> list[dict]:
    with path.open("rb") as f:
        mutants = tomllib.load(f).get("mutant", [])
    for m in mutants:
        missing = {"id", "file", "find", "replace"} - m.keys()
        if missing:
            sys.exit(f"{path}: mutant {m.get('id', '?')} is missing {', '.join(sorted(missing))}")
        m.setdefault("why", "")
    return mutants


def run_pytest(folder: Path, tests: list[str], timeout: float) -> tuple[str, str]:
    """Run pytest in `folder`. Returns (outcome, detail)."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for name in ("AFTERHOURS_DB", "AFTERHOURS_CLASSROOM_GATE"):
        env.pop(name, None)  # never touch a real database; never wait at the demo gate
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests]
    try:
        done = subprocess.run(cmd, cwd=folder, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "caught", f"timed out after {timeout:.0f} s"
    output = done.stdout + done.stderr
    lines = [line for line in output.splitlines() if line.strip()]
    summary = lines[-1].strip("= ") if lines else "(no output)"
    if done.returncode == 0:
        return "passed", summary
    if done.returncode in (4, 5):  # usage error, or no tests collected
        sys.exit(f"pytest could not run these tests ({summary}).\nCheck the --tests paths: {' '.join(tests)}")
    first = next((m.group(2) for line in lines if (m := re.match(r"(FAILED|ERROR) (.+?)(?: - |$)", line))), summary)
    return "caught", first


def fresh_copy(root: Path) -> tuple[Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="mutant-"))
    copy = tmp / "project"
    shutil.copytree(root, copy, ignore=SKIP)
    return tmp, copy


def apply(copy: Path, mutant: dict) -> str | None:
    """Make the mutant's change in `copy`. Returns None, or why it can't be applied."""
    target = copy / mutant["file"]
    if not target.is_file():
        return f"not applicable: {mutant['file']} does not exist"
    with target.open(encoding="utf-8", newline="") as f:
        text = f.read()
    count = text.count(mutant["find"])
    if count != 1:
        where = "not found (was this line changed?)" if count == 0 else f"found {count} times"
        return f"not applicable: text {where}"
    with target.open("w", encoding="utf-8", newline="") as f:
        f.write(text.replace(mutant["find"], mutant["replace"]))
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mutants", default="mutants.toml", help="mutant list (default: mutants.toml)")
    parser.add_argument("--tests", nargs="+", help="test files or folders (default: tests and properties)")
    parser.add_argument("--only", help="comma-separated mutant ids, e.g. M1,M7")
    parser.add_argument("--timeout", type=float, default=120, help="seconds per run (default 120)")
    parser.add_argument("--list", action="store_true", help="list the mutants and stop")
    parser.add_argument("--fail-under", type=float, help="exit 1 if the score (%%) is below this")
    args = parser.parse_args()

    root = Path.cwd()
    mutants = load_mutants(root / args.mutants)
    if args.only:
        wanted = {x.strip() for x in args.only.split(",")}
        mutants = [m for m in mutants if m["id"] in wanted]
    if args.list:
        for m in mutants:
            print(f"{m['id']:<5} {m['file']}\n      {m['find']!r}  ->  {m['replace']!r}\n      {m['why']}")
        return

    tests = args.tests or [p for p in ("tests", "properties") if (root / p).exists()]
    for t in tests:
        if not (root / t.split("::")[0]).exists():
            sys.exit(f"No such test path: {t}")
    started = time.perf_counter()
    print(f"Mutation testing: {len(mutants)} mutants from {args.mutants}; tests: {' '.join(tests)}")
    print("Each mutant is applied on its own to a fresh copy of this folder.\n")

    tmp, copy = fresh_copy(root)
    try:
        outcome, detail = run_pytest(copy, tests, args.timeout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if outcome != "passed":
        print(f"Baseline (no mutant): the tests FAIL ({detail}).")
        print("Fix that first: a mutation score only means something when the tests pass on the real code.")
        sys.exit(2)
    print(f"Baseline (no mutant): {detail}\n")

    results = []
    for m in mutants:
        tmp, copy = fresh_copy(root)
        try:
            problem = apply(copy, m)
            if problem:
                outcome, detail = "n/a", problem
            else:
                outcome, detail = run_pytest(copy, tests, args.timeout)
                outcome = "survived" if outcome == "passed" else "caught"
                detail = "-" if outcome == "survived" else detail
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        results.append((m, outcome))
        print(f"  {m['id']:<5} {m['file']:<22} {outcome:<9} {detail}", flush=True)

    scored = [(m, o) for m, o in results if o != "n/a"]
    caught = sum(1 for _, o in scored if o == "caught")
    survivors = [m for m, o in scored if o == "survived"]
    score = 100 * caught / len(scored) if scored else 0.0
    print(f"\nMutation score: {caught} of {len(scored)} caught ({score:.0f}%)"
          f"   [{time.perf_counter() - started:.0f} s]")
    if len(scored) < len(results):
        print(f"Not applicable (left out of the score): {len(results) - len(scored)}")
    if survivors:
        print("\nSurvived. For each one, write a test from the requirements that fails on it,")
        print("or explain why it can never change what anyone sees (an equivalent mutant; the score")
        print("above still counts it, so report an adjusted score if you exclude it):")
        for m in survivors:
            print(f"  {m['id']:<5} {m['why']}")
    if args.fail_under is not None and score < args.fail_under:
        sys.exit(1)


if __name__ == "__main__":
    main()
