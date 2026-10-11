"""Step 1, expand: add the new columns without disturbing anything v1 relies on."""

import pytest

from migrations import steps

from ..helpers import build_database


@pytest.fixture
def conn(tmp_path):
    c = steps.connect(build_database(tmp_path / "m.db", "old"))
    yield c
    c.close()


def test_expand_adds_two_empty_columns_and_changes_nothing_else(conn):
    before = [dict(r) for r in conn.execute("SELECT id, holder, day, code, created_at FROM tickets ORDER BY id")]
    steps.expand(conn)
    assert steps.shape(conn) == "expanded"
    after = [dict(r) for r in conn.execute("SELECT id, holder, day, code, created_at FROM tickets ORDER BY id")]
    assert after == before
    assert steps.verify(conn) == {"missing": len(before), "disagree": 0, "backwards": 0}
    assert steps.steps_done(conn) == ["expand"]


def test_expand_refuses_to_run_twice(conn):
    steps.expand(conn)
    with pytest.raises(steps.StepRefused, match="already expanded"):
        steps.expand(conn)


def test_expand_refuses_a_contracted_database(tmp_path):
    c = steps.connect(build_database(tmp_path / "v2.db", "contracted"))
    try:
        with pytest.raises(steps.StepRefused, match="already contracted"):
            steps.expand(c)
    finally:
        c.close()
