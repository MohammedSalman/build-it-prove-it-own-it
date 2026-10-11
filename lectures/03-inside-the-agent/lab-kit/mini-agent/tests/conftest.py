"""Shared test fixtures for the mini-agent's own tests."""

import json
import shutil
from pathlib import Path

import pytest

import tools
from agent import RunLog
from permissions import Permissions

KIT = Path(__file__).resolve().parents[1]          # the mini-agent folder
REPO = KIT.parent / "afterhours"                    # the app the agent works on


@pytest.fixture
def workspace(tmp_path):
    """A tiny throwaway project."""
    ws = tmp_path / "ws"
    (ws / "app").mkdir(parents=True)
    (ws / "tests").mkdir()
    (ws / "app" / "main.py").write_text("print('hello')\n")
    (ws / "AGENTS.md").write_text("# Notes for agents\n")
    return ws


@pytest.fixture
def outside(tmp_path):
    """A folder next to the workspace that the agent must never touch."""
    folder = tmp_path / "outside"
    folder.mkdir()
    (folder / "secret.txt").write_text("do not touch\n")
    return folder


@pytest.fixture
def afterhours(tmp_path):
    """A fresh copy of the AfterHours app, like the one agent.py makes."""
    if not REPO.is_dir():
        pytest.fail(f"These tests need the app at {REPO}. Run them inside the lab kit.")
    target = tmp_path / "afterhours"
    shutil.copytree(REPO, target, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.db*"))
    return target


@pytest.fixture
def log(tmp_path):
    return RunLog(tmp_path / "logs", "test-run")


@pytest.fixture
def default_permissions():
    return Permissions.load(KIT / "permissions.json")


@pytest.fixture
def readonly_permissions():
    return Permissions.load(KIT / "permissions-readonly.json")


@pytest.fixture
def spy_tool():
    """A registered tool that only records that it ran. Removed again after the test."""
    calls = []

    def run(workspace, **args):
        calls.append(args)
        return "spy ran"

    tools.register(tools.Tool("spy", "Test tool.", {"type": "object", "properties": {}}, run))
    yield calls
    tools.REGISTRY.pop("spy", None)


def symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("this computer does not allow symlinks (on Windows, turn on Developer Mode)")


def write_recording(path: Path, task: str, turns: list) -> Path:
    path.write_text(json.dumps({"task": task, "turns": turns}), encoding="utf-8")
    return path


def call(id_, name, **inp):
    return {"type": "tool_use", "id": id_, "name": name, "input": inp}
