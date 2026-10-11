"""Lab 3, task A3: the stopping rule.

Some of these fail until you finish should_stop() in agent.py.
"""

from agent import Limits, RunLog, run, should_stop
from models import Reply, ReplayModel
from conftest import KIT, call

LIMITS = Limits(max_steps=12, cost_cap_tokens=60_000)


def reply(tool_calls: int) -> Reply:
    content = [{"type": "text", "text": "..."}] + [call(f"t{i}", "list_files") for i in range(tool_calls)]
    return Reply(content=content, stop_reason="tool_use" if tool_calls else "end_turn",
                 usage={"input_tokens": 0, "output_tokens": 0, "estimated": True})


def test_stops_when_the_model_asks_for_no_tools():
    assert should_stop(reply(0), steps=3, tokens_used=5_000, limits=LIMITS) == "done"


def test_keeps_going_while_there_is_work_and_budget():
    assert should_stop(reply(1), steps=3, tokens_used=5_000, limits=LIMITS) is None


def test_stops_at_the_step_limit():
    assert should_stop(reply(1), steps=12, tokens_used=5_000, limits=LIMITS) == "max_steps"


def test_stops_at_the_cost_cap():
    assert should_stop(reply(1), steps=3, tokens_used=60_000, limits=LIMITS) == "cost_cap"


def test_a_model_that_finishes_on_its_last_step_is_done():
    assert should_stop(reply(0), steps=12, tokens_used=60_000, limits=LIMITS) == "done"


def test_the_runaway_recording_is_stopped_by_the_step_limit(afterhours, tmp_path, default_permissions):
    model = ReplayModel(KIT / "recordings" / "runaway.json")
    outcome = run(model.task, model, afterhours, default_permissions, LIMITS, RunLog(tmp_path, "t"))
    assert outcome.reason == "max_steps"
    assert outcome.steps == 12


def test_with_more_steps_allowed_the_cost_cap_stops_it(afterhours, tmp_path, default_permissions):
    model = ReplayModel(KIT / "recordings" / "runaway.json")
    outcome = run(model.task, model, afterhours, default_permissions, Limits(max_steps=30, cost_cap_tokens=60_000),
                  RunLog(tmp_path, "t"))
    assert outcome.reason == "cost_cap"
    assert outcome.steps < 30
    assert outcome.tokens >= 60_000


def test_the_over_budget_turn_does_not_get_its_tools_run(afterhours, tmp_path, default_permissions):
    model = ReplayModel(KIT / "recordings" / "runaway.json")
    log = RunLog(tmp_path, "t")
    outcome = run(model.task, model, afterhours, default_permissions, Limits(max_steps=30, cost_cap_tokens=5_000), log)
    assert outcome.reason == "cost_cap"
    tool_events = [e for e in log.events if e["event"] == "tool"]
    assert len(tool_events) == outcome.steps - 1      # every turn but the last one ran its tool
