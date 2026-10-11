"""The order of the steps, enforced: passes go on sale only after v1 is retired."""

import pytest

from migrations import steps

from ..helpers import build_database


@pytest.fixture
def conn(tmp_path):
    c = steps.connect(build_database(tmp_path / "m.db", "expanded"))
    yield c
    c.close()


def flag(conn, name):
    return conn.execute("SELECT enabled FROM flags WHERE name = ?", (name,)).fetchone()["enabled"]


def test_passes_cannot_go_on_sale_while_v1_is_live(conn):
    with pytest.raises(steps.StepRefused, match="v1 is still live"):
        steps.set_flag(conn, "multi_day_passes", True)
    assert flag(conn, "multi_day_passes") == 0


def test_passes_can_go_on_sale_once_v1_is_retired(conn):
    steps.retire(conn, "v1")
    steps.set_flag(conn, "multi_day_passes", True)
    assert flag(conn, "multi_day_passes") == 1


def test_retiring_v1_needs_expand_first(tmp_path):
    c = steps.connect(build_database(tmp_path / "old.db", "old"))
    try:
        with pytest.raises(steps.StepRefused, match="expand has not run"):
            steps.retire(c, "v1")
    finally:
        c.close()


def test_on_a_fresh_v2_database_passes_can_go_on_sale(tmp_path):
    # A contracted table has no `day` column, so no v1 server can be running on it.
    c = steps.connect(build_database(tmp_path / "v2.db", "contracted"))
    try:
        steps.set_flag(c, "multi_day_passes", True)
        assert flag(c, "multi_day_passes") == 1
    finally:
        c.close()
