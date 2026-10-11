"""The spec divergence test: run the same acceptance examples against several apps.

For each app folder (by default base/, waitlist-agent-a/ and waitlist-agent-b/) this script
makes a scratch copy, drops the examples file into the copy's tests/ folder, runs pytest
there, and prints one row per example:

    example                                              base   agent A   agent B
    1 someone with a place cannot also wait for one      fail   PASS      fail

Nothing in the app folders is changed. Usage, from the lab-kit folder:

    python scripts/compare.py                  # tests/test_waitlist_examples.py
    python scripts/compare.py --why            # also say why each example failed
    python scripts/compare.py --examples PATH  # run a different examples file

Only the Python standard library is used here; pytest must be installed (requirements.txt).
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
APPS = {"base": "base", "waitlist-agent-a": "agent A", "waitlist-agent-b": "agent B"}
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.db", "*.db-wal", "*.db-shm")


def run_examples(app_dir: Path, examples: Path) -> tuple[dict[str, tuple[str, str]], str, int]:
    """Run the examples inside a scratch copy of app_dir.

    Returns ({test name: (outcome, reason)}, pytest's console output, pytest's exit code).
    Outcomes: PASS, fail (an assertion or exception in the example), error (the example
    could not be set up), skip.
    """
    with tempfile.TemporaryDirectory(prefix="afterhours-examples-", ignore_cleanup_errors=True) as tmp:
        copy = Path(tmp) / app_dir.name
        shutil.copytree(app_dir, copy, ignore=IGNORE)
        shutil.copy(examples, copy / "tests" / "test_waitlist_examples.py")
        report = Path(tmp) / "report.xml"
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             f"--junitxml={report}", "tests/test_waitlist_examples.py"],
            cwd=copy, env=env, capture_output=True, text=True, timeout=300,
        )
        results: dict[str, tuple[str, str]] = {}
        if report.exists():
            for case in ET.parse(report).getroot().iter("testcase"):
                outcome, reason = "PASS", ""
                for tag, label in (("failure", "fail"), ("error", "error"), ("skipped", "skip")):
                    node = case.find(tag)
                    if node is not None:
                        outcome = label
                        reason = (node.get("message") or node.text or "").strip()
                        break
                results[case.get("name")] = (outcome, reason)
        return results, proc.stdout + proc.stderr, proc.returncode


def label(test_name: str) -> str:
    name = test_name.removeprefix("test_").removeprefix("example_")
    return name.replace("_", " ")


def first_line(text: str, width: int = 100) -> str:
    line = text.splitlines()[0] if text else ""
    return line if len(line) <= width else line[: width - 3] + "..."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--examples", default=str(KIT / "tests" / "test_waitlist_examples.py"),
                        help="the examples file to run (default: tests/test_waitlist_examples.py)")
    parser.add_argument("--apps", default=",".join(APPS),
                        help="comma-separated app folders inside lab-kit (default: all three)")
    parser.add_argument("--why", action="store_true", help="print why each example failed")
    args = parser.parse_args()

    examples = Path(args.examples).resolve()
    if not examples.is_file():
        sys.exit(f"No examples file at {examples}")
    apps = [a.strip() for a in args.apps.split(",") if a.strip()]

    table: dict[str, dict[str, tuple[str, str]]] = {}
    order: list[str] = []
    for app in apps:
        app_dir = KIT / app
        if not (app_dir / "app").is_dir():
            sys.exit(f"{app_dir} is not an AfterHours app folder")
        print(f"running the examples against {app}/ ...", file=sys.stderr)
        results, output, code = run_examples(app_dir, examples)
        # pytest exit codes: 0 all passed, 1 some failed. Anything else (2 interrupted, for
        # example by a syntax error; 3 internal error; 4 usage error; 5 nothing collected)
        # means the comparison could not run, and its table would be meaningless.
        if code not in (0, 1) or not results:
            print(output[-3000:])
            sys.exit(f"\nThe examples could not run in {app}/ (pytest exit code {code}). "
                     "Fix the examples file first: see pytest's output above.")
        table[app] = results
        for name in results:
            if name not in order:
                order.append(name)

    heads = [APPS.get(a, a) for a in apps]
    width = max([len("example")] + [len(label(n)) for n in order])
    width = min(width, 64)
    print()
    print("example".ljust(width) + "".join(f"  {h:<8}" for h in heads))
    print("-" * (width + 10 * len(heads)))
    for name in order:
        cells = [table[a].get(name, ("-", ""))[0] for a in apps]
        print(label(name)[:width].ljust(width) + "".join(f"  {c:<8}" for c in cells))
        if args.why:
            for a, (outcome, reason) in ((a, table[a].get(name, ("-", ""))) for a in apps):
                if outcome != "PASS":
                    print(f"{'':4}{APPS.get(a, a)}: {first_line(reason)}")
    print()

    unusable = [n for n in order if any(table[a].get(n, ("-",))[0] in ("error", "skip", "-")
                                         for a in apps)]
    if unusable:
        print("Examples that did not run cleanly everywhere (error, skip or missing); they are")
        print("left out of the summary below. Fix them before reading anything into them:")
        for n in unusable:
            print(f"  - {label(n)}")
    if "waitlist-agent-a" in table and "waitlist-agent-b" in table:
        a, b = table["waitlist-agent-a"], table["waitlist-agent-b"]
        usable = [n for n in order if n not in unusable]
        split = [n for n in usable if a[n][0] != b[n][0]]
        nowhere = [n for n in usable if a[n][0] != "PASS" and b[n][0] != "PASS"]
        print(f"Examples that split agent A from agent B: {len(split)}")
        for n in split:
            print(f"  - {label(n)}")
        print(f"Examples that pass on neither agent's app: {len(nowhere)}"
              + ("  (investigate: a bug in both, a wrong example, or a decision nobody made?)"
                 if nowhere else ""))
        for n in nowhere:
            print(f"  - {label(n)}")
    if "base" in table:
        on_base = [n for n in order if n not in unusable and table["base"][n][0] == "PASS"]
        if on_base:
            print("Examples that pass on base, which has no waitlist (do they test the waitlist?):")
            for n in on_base:
                print(f"  - {label(n)}")
    if unusable:
        sys.exit(1)   # the table is incomplete; say so to anything scripting this


if __name__ == "__main__":
    main()
