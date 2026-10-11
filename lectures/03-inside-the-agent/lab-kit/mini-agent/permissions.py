"""The permission layer: decides, in code, whether a requested tool call may run.

A prompt or an AGENTS.md rule asks the model to behave. This file does not ask. The
dispatcher calls Permissions.check() before every tool call, recorded or live, and a
"no" means the tool function is never called.

It is a teaching model, not a security boundary. It only controls the tools that go
through this harness. Code that run_tests executes can still do anything your user
account can do. Real isolation is a container or an operating-system sandbox, with no
secrets and no network inside it.

The rules live in a JSON file (permissions.json):

    {
      "allow":       ["list_files", "read_file", "write_file", "run_tests"],
      "write_paths": ["app/*", "tests/*"],
      "read_deny":   [".env", "*.pem"]
    }

- allow        tools that may run. Anything else is blocked, including tools that exist.
- write_paths  write_file may only target paths matching one of these patterns.
- read_deny    read_file and list_files may not target paths matching these patterns,
               in any letter case. The check covers the path asked for and, when the
               dispatcher passes the workspace, where that path really lands (a symlink
               to .env is still .env).

Paths must be relative and stay inside the workspace; anything else is blocked.
Patterns use fnmatch, where * matches any characters, including "/".
"""

from __future__ import annotations

import fnmatch
import json
import posixpath
from dataclasses import dataclass, field
from pathlib import Path

PATH_TOOLS_READ = ("read_file", "list_files")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


@dataclass
class Permissions:
    allow: list[str]
    write_paths: list[str] = field(default_factory=list)
    read_deny: list[str] = field(default_factory=list)
    source: str = "(in code)"

    @classmethod
    def load(cls, path: str | Path) -> "Permissions":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            allow=list(data.get("allow", [])),
            write_paths=list(data.get("write_paths", [])),
            read_deny=list(data.get("read_deny", [])),
            source=Path(path).name,
        )

    def check(self, name: str, args: dict, workspace: Path | None = None) -> Decision:
        if name not in self.allow:
            return Decision(False, f"tool {name!r} is not on the allowlist in {self.source}")
        if name == "write_file":
            where = _normalise(args.get("path", ""))
            if where is None:
                return Decision(False, f"write_file path {args.get('path')!r} leaves the workspace")
            if not any(fnmatch.fnmatchcase(where, pattern) for pattern in self.write_paths):
                return Decision(False, f"write_file may not touch {where!r} (write_paths in {self.source})")
        if name in PATH_TOOLS_READ:
            raw = args.get("path", ".") or "."
            where = _normalise(raw)
            if where is None:
                return Decision(False, f"{name} path {raw!r} must be relative and inside the workspace")
            landed = _landing(workspace, where) if workspace is not None else None
            for target in filter(None, (where, landed)):
                if _matches(target, self.read_deny):
                    via = "" if target == where else f", which leads to {target!r}"
                    return Decision(False, f"{name} may not read {where!r}{via} (read_deny in {self.source})")
        return Decision(True, "allowed")


def _normalise(path: str) -> str | None:
    """The path as the rules see it: forward slashes, no "./" or "a/../". None if it escapes.

    Without this, "app/../../secret.txt" would match the pattern "app/*".
    """
    if not isinstance(path, str) or not path.strip():
        return None
    clean = posixpath.normpath(path.replace("\\", "/"))
    if clean.startswith("/") or clean == ".." or clean.startswith("../") or ":" in clean.split("/")[0]:
        return None
    return clean


def _landing(workspace: Path, where: str) -> str | None:
    """Where `where` really points, relative to the workspace (symlinks followed)."""
    root = Path(workspace).resolve()
    target = (root / where).resolve()
    return target.relative_to(root).as_posix() if target.is_relative_to(root) else None


def _matches(path: str, patterns: list[str]) -> bool:
    """A deny match ignores letter case: on macOS and Windows, .ENV and .env are one file."""
    path = path.lower()
    name = posixpath.basename(path)
    return any(fnmatch.fnmatchcase(path, p.lower()) or fnmatch.fnmatchcase(name, p.lower()) for p in patterns)


if __name__ == "__main__":
    # Probe a rules file by hand:  python permissions.py permissions.json write_file app/main.py
    import sys
    if len(sys.argv) != 4:
        sys.exit("usage: python permissions.py RULES.json TOOL PATH")
    rules, tool, path = sys.argv[1:]
    decision = Permissions.load(rules).check(tool, {"path": path})
    print("allowed" if decision.allowed else "BLOCKED: " + decision.reason)
