import pytest

# Every characterization test runs four times: v1 on the database shapes v1 must work
# on, and v2 on the shapes v2 must work on. The two in the middle (v1-expanded,
# v2-expanded) are the migration window, when both versions are live.
SETUPS = [("v1", "old"), ("v1", "expanded"), ("v2", "expanded"), ("v2", "contracted")]


@pytest.fixture(params=SETUPS, ids=[f"{v}-{s}" for v, s in SETUPS])
def setup(request):
    return request.param
