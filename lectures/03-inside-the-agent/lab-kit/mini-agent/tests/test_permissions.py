"""The permission layer and the dispatcher (supplied, not a lab task). These pass on the kit.

They show that a request for a forbidden action is blocked in code, logged, and never runs,
whether it comes from a recording or from a live model: both go through dispatch().
"""

import json
import sys

import pytest

import agent
import tools
from agent import Limits, RunLog, dispatch, run, snapshot
from conftest import KIT, call, symlink_or_skip, write_recording
from models import ReplayModel
from permissions import Permissions


def test_a_tool_that_is_not_allowed_is_blocked_logged_and_never_runs(workspace, log, spy_tool):
    rules = Permissions(allow=["list_files"], source="test rules")
    result = dispatch(call("t1", "spy"), workspace, rules, log)
    assert result["is_error"] is True
    assert result["content"].startswith("BLOCKED by the permission layer")
    assert spy_tool == []                                  # the function never ran
    assert [b["tool"] for b in log.blocked] == ["spy"]
    lines = (log.log_dir / "blocked.jsonl").read_text().splitlines()
    assert json.loads(lines[-1])["tool"] == "spy"


def test_the_same_tool_runs_when_the_rules_allow_it(workspace, log, spy_tool):
    rules = Permissions(allow=["spy"])
    result = dispatch(call("t1", "spy"), workspace, rules, log)
    assert result == {"type": "tool_result", "tool_use_id": "t1", "content": "spy ran", "is_error": False}
    assert len(spy_tool) == 1
    assert log.blocked == []


def test_a_tool_that_does_not_exist_is_blocked(workspace, log, default_permissions):
    result = dispatch(call("t1", "run_shell", command="rm -rf app"), workspace, default_permissions, log)
    assert result["is_error"] and "not on the allowlist" in result["content"]
    assert (workspace / "app" / "main.py").exists()


def test_writing_outside_the_allowed_paths_is_blocked(workspace, log, default_permissions):
    for path in ["AGENTS.md", ".github/workflows/ci.yml", "app/../../outside/x.txt", "/etc/hosts"]:
        result = dispatch(call("t", "write_file", path=path, content="x"), workspace, default_permissions, log)
        assert result["is_error"] and result["content"].startswith("BLOCKED"), path
    assert (workspace / "AGENTS.md").read_text() == "# Notes for agents\n"
    assert not (workspace / ".github").exists()
    assert len(log.blocked) == 4


def test_the_model_is_only_told_about_the_allowed_tools(workspace, tmp_path, readonly_permissions):
    seen = {}

    class Recorder(ReplayModel):
        def next(self, system, messages, tool_defs):
            seen["tools"] = [t["name"] for t in tool_defs]
            return super().next(system, messages, tool_defs)

    rec = write_recording(tmp_path / "r.json", "hi", [{"stop_reason": "end_turn", "content": [{"type": "text", "text": "ok"}]}])
    run("hi", Recorder(rec), workspace, readonly_permissions, Limits(), RunLog(tmp_path, "t"))
    assert seen["tools"] == ["list_files", "read_file", "run_tests"]


def test_a_secret_file_is_never_read_into_the_context(workspace, tmp_path, default_permissions):
    (workspace / ".env").write_text("ANTHROPIC_API_KEY=sk-test-not-real-123\n")
    turns = [
        {"stop_reason": "tool_use", "content": [call("t1", "read_file", path=".env")]},
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "done"}]},
    ]
    model = ReplayModel(write_recording(tmp_path / "r.json", "read the env", turns))
    log = RunLog(tmp_path, "t")
    outcome = run("read the env", model, workspace, default_permissions, Limits(), log)
    assert "sk-test-not-real-123" not in json.dumps(outcome.messages)
    assert [b["tool"] for b in log.blocked] == ["read_file"]


def test_a_secret_file_cannot_be_read_by_absolute_path_or_in_capitals(workspace, log, default_permissions):
    (workspace / ".env").write_text("ANTHROPIC_API_KEY=sk-test-not-real-789\n")
    for path in [str(workspace / ".env"), ".ENV", "app/../.env"]:
        result = dispatch(call("t", "read_file", path=path), workspace, default_permissions, log)
        assert result["content"].startswith("BLOCKED"), path
        assert "sk-test" not in result["content"]


def test_a_secret_file_cannot_be_read_through_a_symlink(workspace, log, default_permissions):
    (workspace / ".env").write_text("ANTHROPIC_API_KEY=sk-test-not-real-789\n")
    symlink_or_skip(workspace / "app" / "notes.txt", workspace / ".env")     # an innocent name
    result = dispatch(call("t", "read_file", path="app/notes.txt"), workspace, default_permissions, log)
    assert result["content"].startswith("BLOCKED") and "leads to '.env'" in result["content"]
    assert "sk-test" not in result["content"]


def test_a_request_that_does_not_fit_the_schema_never_reaches_the_tool(workspace, log):
    ran = []
    strict = tools.Tool("count", "Test tool.", {"type": "object", "properties": {"n": {"type": "integer"}},
                                               "required": ["n"], "additionalProperties": False},
                        lambda ws, **args: ran.append(args) or "counted")
    tools.register(strict)
    try:
        rules = Permissions(allow=["count"])
        for bad in [{}, {"n": "3"}, {"n": True}, {"n": 3, "extra": 1}, ["n", 3]]:
            result = dispatch({"id": "t", "name": "count", "input": bad}, workspace, rules, log)
            assert result["is_error"] and result["content"].startswith("bad request"), bad
        assert ran == []
        assert dispatch(call("t", "count", n=3), workspace, rules, log)["content"] == "counted"
    finally:
        tools.REGISTRY.pop("count", None)


def test_run_tests_does_not_hand_your_api_key_to_the_code_it_runs(workspace, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real-456")
    (workspace / "tests" / "test_env.py").write_text(
        "import os\n\ndef test_no_key():\n    assert 'ANTHROPIC_API_KEY' not in os.environ\n")
    output = tools.run_tests(workspace)
    assert output.startswith("exit code 0"), output


def test_every_replayed_request_goes_through_the_dispatcher(afterhours, tmp_path, readonly_permissions):
    """The code-freeze recording: two forbidden requests, both blocked, nothing changed."""
    model = ReplayModel(KIT / "recordings" / "code-freeze.json")
    requested = sum(len([b for b in t["content"] if b["type"] == "tool_use"]) for t in model.turns)
    before = snapshot(afterhours)
    log = RunLog(tmp_path / "logs", "t")
    outcome = run(model.task, model, afterhours, readonly_permissions, Limits(), log)
    handled = [e for e in log.events if e["event"] in ("tool", "blocked")]
    assert outcome.reason == "done"
    assert len(handled) == requested                          # one decision per request, none skipped
    assert [b["tool"] for b in log.blocked] == ["write_file", "run_shell"]
    assert snapshot(afterhours) == before                     # the code freeze held
    assert len((tmp_path / "logs" / "blocked.jsonl").read_text().splitlines()) == 2


def test_the_loop_hands_every_request_to_dispatch(afterhours, tmp_path, readonly_permissions, monkeypatch):
    """Counts the calls into dispatch(): one per recorded request, in order."""
    ran = []
    original = agent.dispatch

    def counting(*args, **kwargs):
        ran.append(args[0]["name"])
        return original(*args, **kwargs)

    monkeypatch.setattr(agent, "dispatch", counting)
    model = ReplayModel(KIT / "recordings" / "code-freeze.json")
    run(model.task, model, afterhours, readonly_permissions, Limits(), RunLog(tmp_path, "t"))
    assert ran == ["read_file", "read_file", "read_file", "write_file", "run_shell"]


STUB = '''
import json
from pathlib import Path

import tools

SENT = Path(__file__).with_name("sent.jsonl")


def notify(workspace, message):
    """A stand-in for a tool with side effects: it only records what it would have sent."""
    with open(SENT, "a", encoding="utf-8") as f:
        f.write(json.dumps({"message": message}) + "\\n")
    return "sent"


tools.register(tools.Tool(
    "notify", "Send a short message to the team (stub: records it locally).",
    {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
    notify,
))
'''


@pytest.fixture
def forget_notify():
    yield
    tools.REGISTRY.pop("notify", None)          # leave the registry as we found it
    sys.modules.pop("notify_stub", None)


def test_a_tool_added_with_extra_tools_still_obeys_the_rules(afterhours, tmp_path, monkeypatch, forget_notify):
    (tmp_path / "notify_stub.py").write_text(STUB, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    turns = [{"stop_reason": "tool_use", "content": [call("t1", "notify", message="hello")]},
             {"stop_reason": "end_turn", "content": [{"type": "text", "text": "ok"}]}]
    rec = write_recording(tmp_path / "r.json", "say hello", turns)
    common = ["--replay", str(rec), "--extra-tools", "notify_stub", "--workspace", str(afterhours),
              "--log-dir", str(tmp_path / "logs"), "--no-check"]

    assert agent.main(common) == 0                                  # default rules: notify is not allowed
    assert not (tmp_path / "sent.jsonl").exists()                   # the stub recorded nothing
    blocked = (tmp_path / "logs" / "blocked.jsonl").read_text().splitlines()
    assert [json.loads(line)["tool"] for line in blocked] == ["notify"]

    allow = tmp_path / "allow-notify.json"
    allow.write_text(json.dumps({"allow": ["notify"]}), encoding="utf-8")
    assert agent.main(common + ["--permissions", str(allow)]) == 0  # now it is allowed
    assert len((tmp_path / "sent.jsonl").read_text().splitlines()) == 1
