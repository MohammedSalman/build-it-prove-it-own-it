"""Look for secrets and personal data that should not be in the repository.

A teaching scanner: a few dozen lines of patterns, so you can read every rule. Real teams
use a maintained tool as well (for example GitHub's secret scanning, or gitleaks), which
knows hundreds of key formats. Neither can prove a repository is clean. They find what
they have a pattern for.

The output never repeats what it found: a key is shown as its first four characters and
its length, and email addresses only as a count. A scan report is safe to save and hand in.

Usage (from the project folder):
    python scripts/secret_scan.py                  # the files in this folder
    python scripts/secret_scan.py --history        # also every version of every file ever committed

Exit code 0 if nothing was found, 1 if something was. Only the standard library is used.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
SKIP_SUFFIXES = {".db", ".db-wal", ".db-shm", ".png", ".jpg", ".gif", ".ico", ".pyc", ".bundle"}
SELF = "scripts/secret_scan.py"

RULES = [
    # (what it is, pattern with a group called "value": the part that must not be printed)
    ("a secret-looking name set to a literal",
     re.compile(r"""(?i)\b(?P<name>\w*(api_?key|secret|token|passw(or)?d)\w*)\s*[:=]\s*["'](?P<value>[^"'\s]{12,})["']""")),
    ("a private key", re.compile(r"(?P<value>-----BEGIN [A-Z ]*PRIVATE KEY-----)")),
    ("an AWS access key id", re.compile(r"\b(?P<value>AKIA[0-9A-Z]{16})\b")),
    ("a GitHub token", re.compile(r"\b(?P<value>gh[pousr]_[A-Za-z0-9]{36,})\b")),
    ("an Anthropic or OpenAI style key", re.compile(r"\b(?P<value>sk-(ant-)?[A-Za-z0-9_-]{20,})\b")),
    ("a Slack token", re.compile(r"\b(?P<value>xox[abprs]-[A-Za-z0-9-]{10,})\b")),
]
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
RISKY_NAMES = re.compile(r"(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_rsa|id_ed25519)$")


def masked(match: re.Match) -> str:
    """Enough to find the line again, never the secret itself."""
    value = match.group("value")
    hint = f'"{value[:4]}…" ({len(value)} characters)'
    name = match.groupdict().get("name")
    return f"{name} = {hint}" if name else hint


def scan_text(label: str, text: str) -> list[str]:
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for what, pattern in RULES:
            match = pattern.search(line)
            if match:
                findings.append(f"{label}:{number}: {what}: {masked(match)}")
    emails = set(EMAIL.findall(text))
    if len(emails) >= 3:
        findings.append(f"{label}: {len(emails)} different email addresses: personal data?")
    return findings


def scan_file(label: str, path_name: str, data: bytes) -> list[str]:
    findings = [f"{label}: a file that usually holds secrets"] if RISKY_NAMES.search(path_name) else []
    try:
        return findings + scan_text(label, data.decode("utf-8"))
    except UnicodeDecodeError:
        return findings


def working_tree(root: Path) -> list[str]:
    findings = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir() or any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix in SKIP_SUFFIXES or rel == SELF:
            continue
        try:
            findings += scan_file(rel, rel, path.read_bytes())
        except OSError:
            continue
    return findings


def history(root: Path) -> list[str]:
    """Every version of every file ever committed on any branch (git's blobs), each scanned
    whole, so a secret that was later deleted, or built up over several commits, is found."""
    try:
        listing = subprocess.run(["git", "rev-list", "--all", "--objects"], cwd=root,
                                 capture_output=True, check=True).stdout.decode(errors="replace")
    except (OSError, subprocess.CalledProcessError):
        return ["(no git history here: skipped --history)"]
    paths: dict[str, str] = {}
    for line in listing.splitlines():
        sha, _, name = line.partition(" ")
        if name and sha not in paths:
            paths[sha] = name
    if not paths:
        return []
    batch = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input=("\n".join(paths) + "\n").encode(),
                           capture_output=True, check=True).stdout
    findings, pos = [], 0
    while pos < len(batch):
        end = batch.index(b"\n", pos)
        header = batch[pos:end].decode(errors="replace").split()
        if len(header) < 3:                        # "<sha> missing"
            pos = end + 1
            continue
        sha, kind, size = header[0], header[1], int(header[2])
        data = batch[end + 1:end + 1 + size]
        pos = end + 1 + size + 1
        name = paths.get(sha, "?")
        if kind == "blob" and name != SELF and Path(name).suffix not in SKIP_SUFFIXES:
            findings += scan_file(f"history {name} [{sha[:10]}]", name, data)
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="A small, readable secret scanner")
    p.add_argument("folder", nargs="?", default=".")
    p.add_argument("--history", action="store_true", help="also scan every version of every committed file")
    a = p.parse_args()
    root = Path(a.folder).resolve()
    findings = working_tree(root) + (history(root) if a.history else [])
    for finding in findings:
        print(finding)
    real = [f for f in findings if not f.startswith("(")]
    print(f"\n{len(real)} finding(s) in {root.name}/" + (" and its git history" if a.history else ""))
    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(main())
