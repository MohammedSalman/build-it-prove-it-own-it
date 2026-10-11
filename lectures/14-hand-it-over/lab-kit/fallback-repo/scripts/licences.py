"""List the licences that your dependencies declare, including the dependencies' dependencies.

    python scripts/licences.py                          # print a Markdown table
    python scripts/licences.py --out docs/licences.md   # write it to a file

With --out, the file must either not exist yet, or contain the line
    <!-- licences.py writes below this line -->
Everything above that line (your own notes) is kept; only the part below is replaced. A file
without the line is never overwritten.

Run it inside the project's virtual environment, after pip install -r requirements.txt.
It reads requirements.txt (following `-r other-file.txt` includes), then follows each
package's own requirements, including those behind extras you asked for (`httpx2[http2]`),
for as far as they are installed here. Anything it cannot follow (editable installs, bare
URLs or paths) and anything required but not installed is listed at the end, never skipped
silently. For each package it reports the licence the package *declares* in its
metadata, taking the first of these that exists:

  1. License-Expression   an SPDX expression such as "MIT" (newer packages, PEP 639)
  2. License              the older free-text field, if it is short
  3. Classifiers          "License :: OSI Approved :: ..." lines
  otherwise               "not declared: read the licence file"

Declared metadata is a starting point, not proof. Read the actual licence file for anything
marked "read the licence file", and for any licence you have not met before.

Standard library only, plus the "packaging" library if it is installed (pytest installs it),
to evaluate environment markers such as python_version < "3.11".
"""

import argparse
import datetime
import re
import sys
from importlib import metadata
from pathlib import Path

try:  # optional: evaluates environment markers exactly
    from packaging.requirements import Requirement as _Requirement
except ImportError:  # pragma: no cover
    _Requirement = None

ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- licences.py writes below this line -->"


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse(requirement: str, parent_extras: frozenset = frozenset()) -> tuple[str, bool, frozenset]:
    """Return (normalised name, applies here, extras it asks for) for one requirement.

    A dependency behind a marker such as `extra == "http2"` applies only when its parent was
    asked for with that extra (for example `httpx2[http2]`). Other markers, such as
    python_version < "3.11", are evaluated for this machine when "packaging" is installed.
    """
    if _Requirement is not None:
        req = _Requirement(requirement)
        applies = True
        if req.marker is not None:
            applies = req.marker.evaluate({"extra": ""}) or any(
                req.marker.evaluate({"extra": e}) for e in sorted(parent_extras))
        return normalise(req.name), applies, frozenset(normalise(e) for e in req.extras)
    match = re.match(r"\s*([A-Za-z0-9._-]+)\s*(?:\[([^\]]*)\])?", requirement)
    extras = frozenset(normalise(e) for e in (match.group(2) or "").split(",") if e.strip())
    marker = requirement.split(";", 1)[1] if ";" in requirement else ""
    wanted = re.search(r"extra\s*==\s*['\"]([^'\"]+)['\"]", marker)
    applies = normalise(wanted.group(1)) in parent_extras if wanted else True
    return normalise(match.group(1)), applies, extras


def read_requirements(path: Path, seen: set | None = None) -> tuple[list[str], list[str]]:
    """Requirement lines from a requirements file, following -r includes.

    Returns (requirements, notes). Anything this script cannot follow (editable installs,
    bare URLs or paths, other options) goes into notes, so it is reported, never skipped
    silently. Constraint files (-c) add no packages, so they are only noted.
    """
    seen = seen if seen is not None else set()
    path = path.resolve()
    if path in seen:
        return [], []
    seen.add(path)
    requirements, notes = [], []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        include = re.match(r"(?:-r|--requirement)(?:=|\s+)?(\S+)$", line)
        if include:
            more, more_notes = read_requirements(path.parent / include.group(1), seen)
            requirements += more
            notes += more_notes
        elif re.match(r"(?:-c|--constraint)(?:=|\s+)?\S+$", line):
            notes.append(f"{path.name}: constraints file `{line}` noted (it adds no packages)")
        elif line.startswith("-") or "://" in line.split(" @ ")[0] or line.startswith((".", "/")):
            notes.append(f"{path.name}: not followed, check by hand: `{line}`")
        else:
            requirements.append(line)
    return requirements, notes


def declared_licence(dist: metadata.Distribution) -> tuple[str, str]:
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression.strip(), "License-Expression"
    text = (meta.get("License") or "").strip()
    if text and len(text) <= 60 and "\n" not in text and text.upper() != "UNKNOWN":
        return text, "License"
    classifiers = [c.split("::")[-1].strip() for c in (meta.get_all("Classifier") or [])
                   if c.startswith("License ::")]
    if classifiers:
        return " / ".join(classifiers), "Classifier"
    return "not declared: read the licence file", "none"


def walk(requirements: list[str]) -> dict[str, dict]:
    """Breadth-first over installed dependencies, following extras. Returns name -> info."""
    found: dict[str, dict] = {}
    queue = []
    for line in requirements:
        name, applies, extras = parse(line)
        if applies:
            queue.append((name, extras, "requirements.txt"))
    while queue:
        name, extras, parent = queue.pop(0)
        info = found.get(name)
        if info is not None:
            info["needed_by"].add(parent)
            if extras <= info["extras"] or info["version"] == "not installed":
                continue
            info["extras"] |= extras          # asked for with a new extra: follow its deps too
        else:
            try:
                dist = metadata.distribution(name)
            except metadata.PackageNotFoundError:
                found[name] = {"version": "not installed", "licence": "?", "source": "-",
                               "needed_by": {parent}, "extras": set(extras)}
                continue
            licence, source = declared_licence(dist)
            found[name] = {"version": dist.version, "licence": licence, "source": source,
                           "needed_by": {parent}, "extras": set(extras)}
        for requirement in metadata.distribution(name).requires or []:
            child, applies, child_extras = parse(requirement, frozenset(found[name]["extras"]))
            if applies:
                queue.append((child, child_extras, name))
    return found


def table(found: dict[str, dict]) -> str:
    lines = [
        "| Package | Version | Declared licence | Declared in | Needed by |",
        "|---|---|---|---|---|",
    ]
    for name in sorted(found):
        info = found[name]
        needed = ", ".join(sorted(info["needed_by"]))
        shown = name + (f"[{','.join(sorted(info['extras']))}]" if info["extras"] else "")
        lines.append(f"| {shown} | {info['version']} | {info['licence']} | {info['source']} | {needed} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--requirements", default=str(ROOT / "requirements.txt"))
    parser.add_argument("--out", help="write the report to this file instead of printing it")
    args = parser.parse_args()

    requirements, notes_found = read_requirements(Path(args.requirements))
    found = walk(requirements)
    unclear = sorted(n for n, i in found.items() if i["source"] == "none")
    missing = sorted(n for n, i in found.items() if i["version"] == "not installed")
    today = datetime.date.today().isoformat()
    lines = [
        f"Generated {today} by `python scripts/licences.py` with Python "
        f"{sys.version.split()[0]}, from `{Path(args.requirements).name}` and what is installed.",
        "",
        table(found),
        "",
        f"{len(found)} packages. Licence not declared, check by hand: {', '.join(unclear) or 'none'}. "
        f"Required but not installed here, check by hand: {', '.join(missing) or 'none'}.",
    ]
    if notes_found:
        lines += ["", "Lines this script could not follow:", *[f"- {n}" for n in notes_found]]
    report = "\n".join(lines)
    if args.out:
        out = Path(args.out)
        notes = ""
        if out.exists():
            if MARKER not in out.read_text():
                print(f"{out} exists and has no line {MARKER!r}. Add that line where the table "
                      "should start (your notes above it are kept), or delete the file.", file=sys.stderr)
                return 2
            notes = out.read_text().split(MARKER, 1)[0]
        out.write_text(notes + MARKER + "\n\n" + report + "\n")
        print(f"wrote {out}: {len(found)} packages" + (" (kept your notes above the marker)" if notes else ""))
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
