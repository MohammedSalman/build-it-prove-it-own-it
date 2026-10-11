"""v2 during the migration window: the WRITE and READ rules in v2/tickets.py.

These run only on the expanded database, where `day` and the new columns both exist.
"""

import pytest

from migrations import steps
from migrations.contract import contract
from v2 import db as v2_db

from ..helpers import FRI, SAT, SEED, SUN, app_client, run_sql, switch_flag, ticket_row, use_database


@pytest.fixture(params=[("v2", "expanded")], ids=["v2-expanded"])
def setup(request):
    return request.param


def test_v2_writes_day_and_the_new_columns(client):
    ticket_id = client.post("/api/tickets", json={"holder": "Noor", "day": SAT}).json()["id"]
    row = ticket_row(client.db, ticket_id)
    assert (row["day"], row["first_day"], row["last_day"]) == (SAT, SAT, SAT)


def test_v2_keeps_all_three_in_step_when_a_ticket_moves(client):
    maya = SEED["Maya"][0]      # written by v1: first_day and last_day are still NULL
    assert client.post(f"/api/tickets/{maya}/change-day", json={"day": SUN}).status_code == 200
    row = ticket_row(client.db, maya)
    assert (row["day"], row["first_day"], row["last_day"]) == (SUN, SUN, SUN)


def test_a_pass_keeps_day_equal_to_its_first_day(client):
    switch_flag(client.db, "multi_day_passes", True)
    ticket_id = client.post("/api/passes", json={"holder": "Mei", "first_day": FRI,
                                                 "last_day": SUN}).json()["id"]
    row = ticket_row(client.db, ticket_id)
    assert (row["day"], row["first_day"], row["last_day"]) == (FRI, FRI, SUN)


def test_for_a_day_ticket_day_wins_over_stale_new_columns(client, clock):
    # The backfill copied Maya's Friday ticket; then a v1 server moved it to Saturday.
    # v1 changes only `day`, so the new columns still say Friday.
    maya, code, _ = SEED["Maya"]
    run_sql(client.db,
            "UPDATE tickets SET first_day = '2026-10-09', last_day = '2026-10-09' WHERE id = 1",  # backfill
            "UPDATE tickets SET day = '2026-10-10' WHERE id = 1")                                 # v1 moves it
    assert client.get(f"/api/tickets/{maya}").json()["day"] == SAT
    clock.set("2026-10-10T18:00:00")
    assert client.post("/api/gate/scan", json={"code": code}).status_code == 200
    clock.set("2026-10-09T18:00:00")
    assert client.post("/api/gate/scan", json={"code": code}).status_code == 409


def test_v2_refuses_to_start_on_a_database_that_was_not_expanded(tmp_path, monkeypatch, clock):
    use_database(tmp_path, monkeypatch, "old")
    with pytest.raises(RuntimeError, match="migrate.py expand"):
        with app_client("v2", clock):
            pass


class ContractLandsHere:
    """Wraps v2's connection: right after the first statement of the request, another
    connection runs the contract step. A deterministic way to put the contract in the
    middle of a request."""

    def __init__(self, conn, db_path, fired):
        self._conn, self._db_path, self._fired = conn, db_path, fired

    def execute(self, sql, *args):
        cur = self._conn.execute(sql, *args)
        if not self._fired:
            self._fired.append(sql)
            other = steps.connect(self._db_path)
            try:
                contract(other)
            finally:
                other.close()
        return cur

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.mark.parametrize("request_kind", ["read", "scan"])
def test_a_request_that_the_contract_step_interrupts_still_answers(client, clock, monkeypatch, request_kind):
    # Ready to contract: every row copied, v1 recorded as retired.
    run_sql(client.db, "UPDATE tickets SET first_day = day, last_day = day")
    conn = steps.connect(client.db)
    steps.retire(conn, "v1")
    conn.close()
    fired = []
    real_connect = v2_db.connect
    monkeypatch.setattr(v2_db, "connect", lambda path=None: ContractLandsHere(real_connect(path), client.db, fired))
    maya, code, _ = SEED["Maya"]
    clock.set("2026-10-09T18:00:00")
    if request_kind == "read":
        res = client.get(f"/api/tickets/{maya}")
    else:
        res = client.post("/api/gate/scan", json={"code": code})
    assert fired, "the contract step never ran"
    assert res.status_code == 200, res.text
    check = steps.connect(client.db)
    try:
        assert "day" not in steps.columns(check, "tickets")   # it really contracted
    finally:
        check.close()
