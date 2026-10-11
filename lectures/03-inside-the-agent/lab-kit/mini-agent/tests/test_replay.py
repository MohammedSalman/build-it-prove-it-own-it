"""The whole harness, end to end, on the add-name-check recording.

This fails until write_file works (task A2): the recording's writes are refused, so its
final message ("10 passed") is not true. The evidence the harness collects shows that.
"""

import tools
from agent import Limits, RunLog, changes, run, snapshot
from conftest import KIT
from models import ReplayModel


def test_the_add_name_check_replay_finishes_and_its_claims_hold(afterhours, tmp_path, default_permissions):
    model = ReplayModel(KIT / "recordings" / "add-name-check.json")
    before = snapshot(afterhours)
    outcome = run(model.task, model, afterhours, default_permissions, Limits(), RunLog(tmp_path, "t"))
    assert outcome.reason == "done"
    assert outcome.steps == 7
    assert changes(before, snapshot(afterhours)) == ["tests/test_names.py (new)", "app/main.py (changed)"]
    # Do not trust the final message; run the tests ourselves.
    assert "10 passed" in tools.run_tests(afterhours)
