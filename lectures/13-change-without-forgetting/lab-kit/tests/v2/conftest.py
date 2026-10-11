import pytest

# v2's own tests run on both shapes v2 must work on: during the migration window
# (expanded) and after the contract step (contracted).
SETUPS = [("v2", "expanded"), ("v2", "contracted")]


@pytest.fixture(params=SETUPS, ids=[f"{v}-{s}" for v, s in SETUPS])
def setup(request):
    return request.param
