"""The whole migration with both versions writing, step by step (uses YOUR backfill).

A small, deterministic version of scripts/rehearse.py. Every write goes through the real
v1 or v2 app, and every confirmed write is recorded in `expected`. At the end the
contracted database must mean exactly what `expected` says.
"""

from migrations import steps
from migrations.backfill import backfill
from migrations.contract import contract
from migrations.meaning import admitted_days, differences, meaning
from scripts.make_production_db import make

from ..helpers import FRI, SAT, SUN, app_client, use_database


class Recorder:
    """Sends writes to an app and records what each confirmed write means."""

    def __init__(self, expected):
        self.expected = expected

    def buy(self, app, holder, day):
        res = app.post("/api/tickets", json={"holder": holder, "day": day})
        assert res.status_code == 201, res.text
        self.expected[res.json()["id"]] = (holder, res.json()["code"], (day,))
        return res.json()["id"]

    def move(self, app, ticket_id, day):
        res = app.post(f"/api/tickets/{ticket_id}/change-day", json={"day": day})
        assert res.status_code == 200, res.text
        holder, code, _ = self.expected[ticket_id]
        self.expected[ticket_id] = (holder, code, (day,))

    def sell_pass(self, app, holder, first, last):
        res = app.post("/api/passes", json={"holder": holder, "first_day": first, "last_day": last})
        assert res.status_code == 201, res.text
        self.expected[res.json()["id"]] = (holder, res.json()["code"], admitted_days(first, last))


def test_writes_from_both_versions_survive_backfill_and_contract(tmp_path, monkeypatch, clock):
    db = use_database(tmp_path, monkeypatch, "expanded")
    conn = steps.connect(db)
    record = Recorder(meaning(conn))
    with app_client("v1", clock) as v1, app_client("v2", clock) as v2:
        # The window opens. Both versions write before the backfill...
        noor = record.buy(v1, "Noor", FRI)          # v1: only `day`
        record.buy(v2, "Priya", SAT)                # v2: all three columns
        record.move(v1, 1, SUN)                     # Maya, a v1 row, moved by v1
        record.move(v2, 2, FRI)                     # Sam, a v1 row, moved by v2
        backfill(conn)
        # ...and after it.
        record.move(v1, 3, FRI)                     # Lee: copied, then moved by v1 (stale copy)
        record.buy(v1, "Kofi", SUN)                 # a v1 row the backfill never saw
        record.move(v2, noor, SAT)                  # a v1 row moved by v2
    # v1 is retired: its servers are stopped (the `with` block above), then it is recorded.
    steps.retire(conn, "v1")
    backfill(conn)                                  # the catch-up
    assert steps.verify(conn) == {"missing": 0, "disagree": 0, "backwards": 0}
    steps.set_flag(conn, "multi_day_passes", True)
    with app_client("v2", clock) as v2:
        record.sell_pass(v2, "Mei", FRI, SUN)
        contract(conn)
        record.buy(v2, "Omar", SUN)                 # v2 keeps working after the contract
        record.move(v2, 4, SAT)
    assert differences(record.expected, meaning(conn)) == []
    assert len(record.expected) == 10
    conn.close()


def test_a_quiet_production_copy_means_the_same_before_and_after(tmp_path):
    db = str(tmp_path / "prod.db")
    make(db, tickets=600, seed=13)
    conn = steps.connect(db)
    before = meaning(conn)
    steps.expand(conn)
    backfill(conn)
    steps.retire(conn, "v1")
    contract(conn)
    assert differences(before, meaning(conn)) == []
    assert len(before) == 600
    conn.close()
