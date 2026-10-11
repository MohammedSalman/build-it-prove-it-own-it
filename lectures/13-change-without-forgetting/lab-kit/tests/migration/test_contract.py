"""Step 3, contract: runs only after v1 is retired and the data has caught up.

These tests fill the new columns with plain SQL, not with your backfill, so they pass on
the kit: they test the supplied contract step and its guard.
"""

import pytest

from migrations import steps
from migrations.contract import contract, problems

from ..helpers import build_database

FILL = "UPDATE tickets SET first_day = day, last_day = day"


@pytest.fixture
def conn(tmp_path):
    c = steps.connect(build_database(tmp_path / "m.db", "expanded"))
    yield c
    c.close()


def refused(conn) -> str:
    with pytest.raises(steps.StepRefused) as caught:
        contract(conn)
    assert steps.shape(conn) == "expanded", "a refused contract must change nothing"
    return " | ".join(caught.value.reasons)


def test_contract_is_refused_while_v1_is_live(conn):
    conn.execute(FILL)                                   # data complete, but v1 not retired
    assert "v1 is still live" in refused(conn)


def test_contract_is_refused_while_rows_have_no_new_columns(conn):
    steps.retire(conn, "v1")
    assert "5 tickets have no first_day/last_day" in refused(conn)


def test_contract_is_refused_while_a_day_ticket_disagrees_with_day(conn):
    conn.execute(FILL)
    conn.execute("UPDATE tickets SET day = '2026-10-10' WHERE id = 1")   # v1 moved Maya after the copy
    steps.retire(conn, "v1")
    assert "1 day tickets disagree with `day`" in refused(conn)


def test_contract_drops_day_and_keeps_everything_else(conn):
    conn.execute(FILL)
    steps.retire(conn, "v1")
    keep = "SELECT id, holder, first_day, last_day, code, created_at FROM tickets ORDER BY id"
    before = [tuple(r) for r in conn.execute(keep)]
    assert problems(conn) == []
    assert contract(conn) == 5
    assert steps.shape(conn) == "contracted"
    assert [tuple(r) for r in conn.execute(keep)] == before
    assert steps.steps_done(conn)[-1] == "contract"


def test_a_contracted_table_has_the_same_shape_as_a_fresh_v2_one(conn, tmp_path):
    conn.execute(FILL)
    steps.retire(conn, "v1")
    contract(conn)
    fresh = steps.connect(build_database(tmp_path / "fresh.db", "contracted"))
    try:
        def shape_of(c):
            cols = [tuple(r) for r in c.execute("SELECT name, type, \"notnull\", dflt_value, pk FROM pragma_table_info('tickets')")]
            unique = sorted(tuple(r2["name"] for r2 in c.execute(f"PRAGMA index_info('{r['name']}')"))
                            for r in c.execute("PRAGMA index_list('tickets')") if r["unique"])
            return cols, unique
        assert shape_of(conn) == shape_of(fresh)
    finally:
        fresh.close()


def test_contract_refuses_to_run_twice(conn):
    conn.execute(FILL)
    steps.retire(conn, "v1")
    contract(conn)
    with pytest.raises(steps.StepRefused, match="already contracted"):
        contract(conn)
