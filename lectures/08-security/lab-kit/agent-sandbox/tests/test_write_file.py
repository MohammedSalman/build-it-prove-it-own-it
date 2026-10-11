"""Lab 3, task A2: write_file may only write inside the workspace.

These fail until you implement safe_write_path() in tools.py.
"""

import pytest

import tools
from agent import dispatch
from conftest import call, symlink_or_skip
from permissions import Permissions
from tools import ToolError


def test_writes_a_new_file_inside_the_workspace(workspace):
    tools.write_file(workspace, "tests/test_new.py", "def test_ok():\n    assert True\n")
    assert (workspace / "tests" / "test_new.py").read_text() == "def test_ok():\n    assert True\n"


def test_creates_missing_folders(workspace):
    tools.write_file(workspace, "app/routes/events.py", "x = 1\n")
    assert (workspace / "app" / "routes" / "events.py").read_text() == "x = 1\n"


def test_replaces_an_existing_file(workspace):
    tools.write_file(workspace, "app/main.py", "print('bye')\n")
    assert (workspace / "app" / "main.py").read_text() == "print('bye')\n"


@pytest.mark.parametrize("path", [
    "../outside/secret.txt",               # straight out
    "app/../../outside/secret.txt",        # in, then out
    "",                                    # nothing
    "   ",                                 # nothing, with spaces
])
def test_refuses_paths_that_leave_the_workspace_or_are_empty(workspace, outside, path):
    with pytest.raises(ToolError):
        tools.write_file(workspace, path, "overwritten\n")
    assert (outside / "secret.txt").read_text() == "do not touch\n"


def test_refuses_an_absolute_path(workspace, outside):
    with pytest.raises(ToolError):
        tools.write_file(workspace, str(outside / "secret.txt"), "overwritten\n")
    assert (outside / "secret.txt").read_text() == "do not touch\n"


def test_refuses_a_path_through_a_linked_folder_that_points_outside(workspace, outside):
    symlink_or_skip(workspace / "app" / "data", outside)          # app/data -> ../outside
    with pytest.raises(ToolError):
        tools.write_file(workspace, "app/data/secret.txt", "overwritten\n")
    assert (outside / "secret.txt").read_text() == "do not touch\n"


def test_refuses_a_linked_file_even_when_it_points_inside(workspace):
    # app/notes.md is a link to AGENTS.md. The rules allow app/*, but not AGENTS.md.
    symlink_or_skip(workspace / "app" / "notes.md", workspace / "AGENTS.md")
    with pytest.raises(ToolError):
        tools.write_file(workspace, "app/notes.md", "overwritten\n")
    assert (workspace / "AGENTS.md").read_text() == "# Notes for agents\n"


def test_refuses_to_write_over_a_folder(workspace):
    with pytest.raises(ToolError):
        tools.write_file(workspace, "app", "overwritten\n")
    assert (workspace / "app").is_dir()


def test_a_link_escape_gets_past_the_rules_but_not_past_the_tool(workspace, outside, log):
    """Two layers: the permission rules allow app/*, so only the tool's own check stops this."""
    symlink_or_skip(workspace / "app" / "data", outside)
    rules = Permissions(allow=["write_file"], write_paths=["app/*"])
    result = dispatch(call("t1", "write_file", path="app/data/secret.txt", content="x"), workspace, rules, log)
    assert result["is_error"] is True
    assert "symlink" in result["content"]
    assert log.blocked == []                      # the permission layer said yes
    assert (outside / "secret.txt").read_text() == "do not touch\n"
