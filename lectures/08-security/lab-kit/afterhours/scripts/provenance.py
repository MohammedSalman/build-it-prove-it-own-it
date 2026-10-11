"""Where did our dependencies come from, and what licences do they carry?

Reads requirements.txt, then looks at what is really installed in the active environment:
every package the requirements pull in, directly or indirectly, with its version, its
licence, what pip recorded about where it came from, and why it is here.

Usage (with the project's environment active):
    python scripts/provenance.py                       # uses requirements.txt
    python scripts/provenance.py path/to/requirements.txt --urls

Everything shown comes from each package's own metadata, which its authors wrote. Treat
it as a claim to check, not as proof. Only the Python standard library is used.
"""

import argparse
import json
import re
import sys
from importlib import metadata
from pathlib import Path

# Licences this project has agreed to accept without a closer look (a team decision).
ACCEPTED = {"MIT", "BSD", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "Python-2.0"}

NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_requirements(path: Path) -> dict[str, str]:
    """{package: the line that asks for it}. Comments and options are skipped."""
    wanted = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = NAME.match(line)
        if match:
            wanted[canonical(match.group(1))] = line
    return wanted


def installed() -> dict[str, metadata.Distribution]:
    return {canonical(d.metadata["Name"]): d for d in metadata.distributions() if d.metadata["Name"]}


def dependencies(dist: metadata.Distribution) -> list[str]:
    """Packages this one needs (optional extras left out)."""
    out = []
    for req in dist.requires or []:
        if "extra ==" in req.replace("extra==", "extra =="):
            continue
        match = NAME.match(req)
        if match:
            out.append(canonical(match.group(1)))
    return out


def licence(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression.strip()
    text = (meta.get("License") or "").strip()
    if text and len(text) <= 40 and "\n" not in text:
        return text
    classifiers = [c.split(" :: ")[-1] for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return " / ".join(classifiers)
    return "unknown" if not text else "(long text: see the package's licence file)"


def normalised(lic: str) -> set[str]:
    words = {
        "MIT License": "MIT", "BSD License": "BSD", "Apache Software License": "Apache-2.0",
        "Python Software Foundation License": "PSF-2.0", "ISC License (ISCL)": "ISC",
    }
    parts = re.split(r"\s+(?:OR|AND)\s+|\s*/\s*", lic)
    return {words.get(p.strip("() "), p.strip("() ")) for p in parts if p.strip("() ")}


def source(dist: metadata.Distribution) -> str:
    """What the installer recorded about where the package came from.

    pip writes direct_url.json only when you install from a URL, a git repository or a
    folder. For a package found by name (on PyPI, another index, or --find-links) nothing
    is recorded, so the honest answer is "not recorded".
    """
    installer = (dist.read_text("INSTALLER") or "?").strip()
    direct = dist.read_text("direct_url.json")
    if not direct:
        return f"not recorded ({installer})"
    info = json.loads(direct)
    if "vcs_info" in info:
        return f"git/VCS: {info.get('url')}"
    if info.get("dir_info", {}).get("editable"):
        return f"local folder (editable): {info.get('url')}"
    return f"direct URL: {info.get('url')}"


def project_url(dist: metadata.Distribution) -> str:
    urls = dict(u.split(", ", 1) for u in dist.metadata.get_all("Project-URL") or [] if ", " in u)
    for key in ("Source", "Source Code", "Repository", "Homepage", "Home"):
        if key in urls:
            return urls[key]
    return dist.metadata.get("Home-page") or "-"


def main() -> int:
    p = argparse.ArgumentParser(description="Dependency and licence provenance")
    p.add_argument("requirements", nargs="?", default="requirements.txt")
    p.add_argument("--urls", action="store_true", help="also show the source URL each package claims")
    a = p.parse_args()

    wanted = read_requirements(Path(a.requirements))
    have = installed()
    missing = [n for n in wanted if n not in have]
    if missing:
        print(f"Not installed in this environment: {', '.join(missing)}. Activate the project's venv first.")
        return 2

    # Walk the dependency tree from what requirements.txt asks for.
    why: dict[str, str] = {name: f"requirements.txt: {line}" for name, line in wanted.items()}
    queue = list(wanted)
    while queue:
        parent = queue.pop(0)
        for child in dependencies(have[parent]):
            if child in have and child not in why:
                why[child] = f"needed by {have[parent].metadata['Name']}"
                queue.append(child)

    rows = []
    for name in sorted(why, key=lambda n: (n not in wanted, n)):
        dist = have[name]
        lic = licence(dist)
        check = "" if normalised(lic) <= ACCEPTED else "  <- check"
        rows.append((dist.metadata["Name"], dist.version, lic + check, source(dist), why[name], project_url(dist)))

    headers = ("package", "version", "licence", "origin recorded", "why it is here", "claims its source is")
    columns = 6 if a.urls else 5
    widths = [max(len(str(r[i])) for r in rows + [headers]) for i in range(columns)]
    for row in [headers] + rows:
        print("  ".join(str(row[i]).ljust(widths[i]) for i in range(columns)).rstrip())

    chosen, pulled = len(wanted), len(why) - len(wanted)
    to_check = [r[0] for r in rows if r[2].endswith("<- check")]
    direct = [r[0] for r in rows if not r[3].startswith("not recorded")]
    print()
    print(f"{a.requirements} names {chosen} packages. Installing them brought in {pulled} more "
          f"that nobody on the team chose by name.")
    print(f"Not pinned by us: {', '.join(r[0] for r in rows if canonical(r[0]) not in wanted) or 'none'}.")
    print(f"Licences outside the accepted list ({', '.join(sorted(ACCEPTED))}): "
          f"{', '.join(to_check) if to_check else 'none'}.")
    print(f"Installed from a URL, a git repository or a folder: {', '.join(direct) if direct else 'none'}. "
          f"For packages found by name, pip records no origin; a lockfile with hashes is what pins the exact files.")
    print("Licences and source links are what the packages' own metadata claims. It is where checking starts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
