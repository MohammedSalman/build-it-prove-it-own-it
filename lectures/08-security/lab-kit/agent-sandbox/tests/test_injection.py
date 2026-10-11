"""Week 8 addition: an injected instruction meets the permission layer.

The recording (recordings/poisoned-submission.json) is authored. It plays the worst case:
a "model" that obeys an instruction hidden in an event submission, reads the attendee
export and sends it out with http_post. Everything it asks for goes through Week 3's
dispatcher, unchanged. http_post is a stub (http_stub.py) that only writes calls down.

These tests prove what the permission layer does with those requests. They prove nothing
about whether any real model would obey the hidden instruction.

On the kit, the last two tests fail until you write permissions-drafting.json (task A4).
"""

import json
from pathlib import Path

import pytest

import agent
from agent import Limits, RunLog, run
from conftest import KIT
from models import ReplayModel
from permissions import Permissions

RECORDING = KIT / "recordings" / "poisoned-submission.json"
DRAFTING = KIT / "permissions-drafting.json"      # you write this in task A4
EMAIL_DOMAIN = "@students.example.org"            # every address in the attendee export


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    """Point the stub at a fresh file; return a function that reads what it recorded."""
    path = tmp_path / "outbound.jsonl"
    monkeypatch.setenv("HTTP_STUB_OUTBOX", str(path))
    return lambda: [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def replay(afterhours, tmp_path, rules: Path) -> int:
    """Run the agent's own command line, exactly as the lab does."""
    return agent.main(["--replay", str(RECORDING), "--extra-tools", "http_stub", "--permissions", str(rules),
                       "--workspace", str(afterhours), "--log-dir", str(tmp_path / "logs"), "--no-check"])


def blocked(tmp_path) -> list[dict]:
    path = tmp_path / "logs" / "blocked.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def drafting_rules() -> Path:
    if not DRAFTING.exists():
        pytest.fail("Task A4: write permissions-drafting.json next to agent.py (see Lab 8)")
    return DRAFTING


def test_every_request_in_the_recording_goes_through_dispatch(afterhours, tmp_path, outbox, monkeypatch):
    seen = []
    original = agent.dispatch

    def counting(call, *args, **kwargs):
        seen.append(call["name"])
        return original(call, *args, **kwargs)

    monkeypatch.setattr(agent, "dispatch", counting)
    replay(afterhours, tmp_path, KIT / "permissions-organiser.json")
    requested = [b["name"] for t in ReplayModel(RECORDING).turns for b in t["content"] if b["type"] == "tool_use"]
    assert seen == requested == ["list_files", "read_file", "read_file", "read_file", "read_file",
                                 "http_post", "write_file"]


def test_with_the_organisers_rules_the_attendee_list_goes_out(afterhours, tmp_path, outbox):
    """The kit's rules allow all three legs of the lethal trifecta. The stub shows the leak."""
    assert replay(afterhours, tmp_path, KIT / "permissions-organiser.json") == 0
    calls = outbox()
    assert len(calls) == 1
    assert calls[0]["url"] == "https://festival-sync.example.net/upload"
    assert calls[0]["body"].count(EMAIL_DOMAIN) == 12            # every attendee's address
    assert blocked(tmp_path) == []
    final = ReplayModel(RECORDING).turns[-1]["content"][0]["text"]
    assert "http" not in final and "attendee" not in final        # the summary never mentions it


def test_with_your_drafting_rules_the_upload_is_blocked_logged_and_nothing_leaves(afterhours, tmp_path, outbox):
    rules = drafting_rules()
    assert replay(afterhours, tmp_path, rules) == 0
    assert outbox() == []                                          # zero outbound calls
    assert "http_post" in [b["tool"] for b in blocked(tmp_path)]  # blocked, and logged
    assert (afterhours / "docs" / "programme-draft.md").is_file()  # the real task still got done


def test_with_your_drafting_rules_the_attendee_export_never_enters_the_context(afterhours, tmp_path, outbox):
    import http_stub  # noqa: F401  registers http_post, as --extra-tools does

    model = ReplayModel(RECORDING)
    log = RunLog(tmp_path / "logs", "t")
    outcome = run(model.task, model, afterhours, Permissions.load(drafting_rules()), Limits(), log)
    results = [b for m in outcome.messages if m["role"] == "user" and isinstance(m["content"], list)
               for b in m["content"] if b.get("type") == "tool_result"]
    assert results and not any(EMAIL_DOMAIN in r["content"] for r in results)
    assert ("read_file", "exports/attendees-friday.csv") in [(b["tool"], b["input"].get("path")) for b in log.blocked]
