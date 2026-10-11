"""The mini-agent's tools: what the model may ask for, and what each request really does.

The model never runs a tool itself. It sends a request (a tool name and some JSON input);
agent.dispatch() checks the request against the permission layer and only then calls the
function registered here. Every tool gets the workspace folder as its first argument and
returns text, which goes back into the model's context.

To add a tool, write a function and register it (see the bottom of this file, or
README.md, "Adding a tool"). Registering a tool does not allow it: the permission file
decides that.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

RUN_TESTS_TIMEOUT = 60        # seconds; a hung test run is stopped, not waited for
LIST_LIMIT = 200              # at most this many paths from list_files
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


class ToolError(Exception):
    """The tool refused or failed. The message goes back to the model as an error result."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str          # the model reads this to decide when to use the tool
    input_schema: dict        # JSON Schema for the input the model must send
    run: Callable[..., str]   # run(workspace, **input) -> text for the model

    def schema(self) -> dict:
        """The tool definition as the model sees it."""
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}

    def check_input(self, args) -> str | None:
        """Does a request fit input_schema? None if it does, else what is wrong.

        The model sees the schema as a description. This check is what enforces it. It
        covers the parts of JSON Schema these tools use: required keys, value types, and
        "additionalProperties": false.
        """
        if not isinstance(args, dict):
            return "the input must be a JSON object"
        properties = self.input_schema.get("properties", {})
        for key in self.input_schema.get("required", []):
            if key not in args:
                return f"missing {key!r}"
        for key, value in args.items():
            if key not in properties:
                if self.input_schema.get("additionalProperties", True) is False:
                    return f"unexpected {key!r}"
                continue
            wanted = properties[key].get("type")
            if wanted and (not isinstance(value, JSON_TYPES[wanted])
                           or (wanted in ("integer", "number") and isinstance(value, bool))):
                return f"{key!r} must be {wanted}"
        return None


JSON_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
              "array": list, "object": dict}


REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    REGISTRY[tool.name] = tool
    return tool


# ---------------------------------------------------------------------------------------
# Paths. The model sends paths as text. Text from a model is untrusted input.

def resolve_for_reading(workspace: Path, path: str) -> Path:
    """Where a read of `path` really lands. Refuses anything that ends up outside the workspace.

    resolve() follows symlinks and removes "..", so a link or a "../" that points outside
    is caught here.
    """
    root = workspace.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ToolError(f"refused: {path!r} is outside the workspace")
    return target


def safe_write_path(workspace: Path, path: str) -> Path:
    """Where a write of `path` may go. Stricter than reading.

    Refuse (raise ToolError) when the path:
      - is empty,
      - is absolute (/etc/passwd, C:\\Users\\...),
      - contains a ".." part anywhere (../x, app/../../x),
      - goes through a symlink: any part of it that already exists and is a link,
        even a link that points somewhere inside the workspace,
      - is an existing directory.
    Otherwise return the absolute target path inside the workspace.

    Why refuse links that point inside? The permission layer checks the path the model
    asked for (say app/notes.py). If app/notes.py is a link to AGENTS.md, the write would
    land on AGENTS.md, a file the permission rules never allowed.
    """
    if not path or not path.strip():
        raise ToolError("refused: empty path")
    requested = Path(path)
    if requested.is_absolute() or requested.drive or requested.root:
        raise ToolError(f"refused: {path!r} is an absolute path; use a path inside the workspace")
    if ".." in requested.parts:
        raise ToolError(f"refused: {path!r} contains '..'")
    root = workspace.resolve()
    current = root
    for part in requested.parts:
        current = current / part
        if current.is_symlink():
            raise ToolError(f"refused: {path!r} goes through a symlink")
    if current.is_dir():
        raise ToolError(f"refused: {path!r} is a directory")
    if not current.resolve().is_relative_to(root):      # belt and braces
        raise ToolError(f"refused: {path!r} is outside the workspace")
    return current


# ---------------------------------------------------------------------------------------
# The four tools.

def list_files(workspace: Path, path: str = ".") -> str:
    start = resolve_for_reading(workspace, path)
    if not start.is_dir():
        raise ToolError(f"{path!r} is not a directory")
    root = workspace.resolve()
    found = []
    for dirpath, dirnames, filenames in os.walk(start):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if ".db" in name:
                continue
            found.append((Path(dirpath) / name).relative_to(root).as_posix())
    if len(found) > LIST_LIMIT:
        found = found[:LIST_LIMIT] + [f"... and {len(found) - LIST_LIMIT} more"]
    return "\n".join(found) or "(no files)"


def read_file(workspace: Path, path: str) -> str:
    target = resolve_for_reading(workspace, path)
    if not target.is_file():
        raise ToolError(f"{path!r} is not a file")
    return target.read_text(encoding="utf-8", errors="replace")


def write_file(workspace: Path, path: str, content: str) -> str:
    target = safe_write_path(workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} characters to {path}"


def _without_secrets(env: dict) -> dict:
    """A copy of the environment without anything that looks like a credential.

    The tests run code the agent may have written. That code must not find your API key.
    """
    words = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    return {k: v for k, v in env.items() if not any(w in k.upper() for w in words)}


def run_tests(workspace: Path, path: str = "") -> str:
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if path:
        resolve_for_reading(workspace, path)
        command.append(path)
    env = _without_secrets(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        done = subprocess.run(
            command, cwd=workspace.resolve(), env=env, capture_output=True, text=True,
            timeout=RUN_TESTS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"run_tests stopped after {RUN_TESTS_TIMEOUT} s (timeout)")
    lines = (done.stdout + done.stderr).strip().splitlines()
    tail = "\n".join(lines[-40:])
    return f"exit code {done.returncode}\n{tail}"


register(Tool(
    "list_files",
    "List the files in the project (or in one folder of it). Use this first to find your way around.",
    {"type": "object",
     "properties": {"path": {"type": "string", "description": "Folder relative to the project root. Default: the root."}},
     "additionalProperties": False},
    list_files,
))
register(Tool(
    "read_file",
    "Read one text file from the project. Read a file before you change it.",
    {"type": "object",
     "properties": {"path": {"type": "string", "description": "File path relative to the project root, e.g. app/main.py"}},
     "required": ["path"], "additionalProperties": False},
    read_file,
))
register(Tool(
    "write_file",
    "Create or replace one text file in the project with the full new content.",
    {"type": "object",
     "properties": {"path": {"type": "string", "description": "File path relative to the project root"},
                    "content": {"type": "string", "description": "The complete new content of the file"}},
     "required": ["path", "content"], "additionalProperties": False},
    write_file,
))
register(Tool(
    "run_tests",
    "Run the project's tests with pytest (all of them, or one file) and return the summary. "
    f"Stops after {RUN_TESTS_TIMEOUT} seconds.",
    {"type": "object",
     "properties": {"path": {"type": "string", "description": "Optional test file, e.g. tests/test_basics.py"}},
     "additionalProperties": False},
    run_tests,
))
