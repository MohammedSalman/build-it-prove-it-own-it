"""Week 8 addition (not part of the frozen copy). See FROZEN-COPY.md.

Two of Week 3's own tests replay Week 3 recordings that only fit Week 3's app. In this
kit the agent works on the Week 8 app next door (../afterhours), so they are skipped
here, with the reason printed. Both pass in Week 3's layout (verification.md, section 5).
"""

import pytest

WEEK3_APP_ONLY = {
    "tests/test_replay.py::test_the_add_name_check_replay_finishes_and_its_claims_hold":
        "Week 3 recording: it rewrites app/main.py with Week 3's version and expects Week 3's 10 tests",
    "tests/test_stopping.py::test_the_runaway_recording_is_stopped_by_the_step_limit":
        "Week 3 recording: it reads Week 3's smaller files; the Week 8 files reach the 60,000-token cap before step 12",
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        reason = WEEK3_APP_ONLY.get(item.nodeid)
        if reason:
            item.add_marker(pytest.mark.skip(reason=reason))
