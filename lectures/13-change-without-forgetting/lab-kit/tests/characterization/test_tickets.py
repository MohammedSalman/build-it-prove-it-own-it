"""Photographs of what v1 does with tickets today (characterization tests).

Every expected value in this file was OBSERVED by running v1. None was taken from
docs/requirements.md. The file runs against v1 and v2 on every shape of the database
each must work on (see conftest.py): during the migration window a holder must get the
same answer whichever server takes the request.

A photograph shows what is there, bugs included. It tells you when behaviour changes;
it cannot tell you whether the behaviour was right. That judgement is yours (part A1).
"""

import re

from ..helpers import FRI, SAT, SEED

MAYA_ID, MAYA_CODE, _ = SEED["Maya"]     # Friday ticket
SAM_ID, SAM_CODE, _ = SEED["Sam"]        # Saturday ticket


def fields(body: dict) -> dict:
    """The fields v1 returns. v2 adds more; the photograph covers v1's."""
    return {key: body[key] for key in ("id", "holder", "day", "code")}


# ---- selling and reading ---------------------------------------------------------------

def test_selling_a_day_ticket_returns_it(client):
    res = client.post("/api/tickets", json={"holder": "Noor", "day": SAT})
    assert res.status_code == 201
    body = res.json()
    assert fields(body) == {"id": 6, "holder": "Noor", "day": SAT, "code": "SAT-0006"}


def test_observed_code_format_is_day_then_ticket_number(client):
    # OBSERVED, NOT PROMISED: requirement T4 promises only that codes are unique.
    # Someone may depend on the format anyway (Hyrum's law); v2 keeps it for day tickets.
    codes = [client.post("/api/tickets", json={"holder": "Noor", "day": day}).json()["code"]
             for day in ("2026-10-09", "2026-10-10", "2026-10-11")]
    assert all(re.fullmatch(r"(FRI|SAT|SUN)-\d{4}", code) for code in codes), codes
    assert [code[:3] for code in codes] == ["FRI", "SAT", "SUN"]


def test_a_ticket_reads_back_the_same(client):
    res = client.get(f"/api/tickets/{MAYA_ID}")
    assert res.status_code == 200
    assert fields(res.json()) == {"id": MAYA_ID, "holder": "Maya", "day": FRI, "code": MAYA_CODE}


def test_a_day_outside_the_festival_is_refused(client):
    res = client.post("/api/tickets", json={"holder": "Noor", "day": "2026-10-12"})
    assert res.status_code == 422


def test_an_unknown_ticket_is_404(client):
    assert client.get("/api/tickets/9999").status_code == 404


# ---- the gate ----------------------------------------------------------------------------

def test_the_gate_admits_a_ticket_on_its_day(client, clock):
    clock.set("2026-10-09T18:00:00")
    res = client.post("/api/gate/scan", json={"code": MAYA_CODE})
    assert res.status_code == 200
    assert res.json() == {"admitted": True, "holder": "Maya", "code": MAYA_CODE}


def test_the_gate_refuses_a_ticket_on_another_day(client, clock):
    clock.set("2026-10-10T18:00:00")
    res = client.post("/api/gate/scan", json={"code": MAYA_CODE})
    assert res.status_code == 409
    assert res.json()["detail"] == "This ticket is for Friday 9 October."


def test_the_gate_day_runs_from_midnight_to_midnight(client, clock):
    answers = {}
    for moment in ("2026-10-08T23:59:59", "2026-10-09T00:00:00", "2026-10-09T23:59:59", "2026-10-10T00:00:00"):
        clock.set(moment)
        answers[moment] = client.post("/api/gate/scan", json={"code": MAYA_CODE}).status_code
    assert answers == {"2026-10-08T23:59:59": 409, "2026-10-09T00:00:00": 200,
                       "2026-10-09T23:59:59": 200, "2026-10-10T00:00:00": 409}


def test_an_unknown_code_is_404(client):
    assert client.post("/api/gate/scan", json={"code": "FRI-9999"}).status_code == 404


# ---- changing day ------------------------------------------------------------------------

def test_moving_a_ticket_before_the_festival(client):
    # Thursday 1 October (the default clock): every day is still ahead.
    res = client.post(f"/api/tickets/{MAYA_ID}/change-day", json={"day": SAT})
    assert res.status_code == 200
    assert fields(res.json()) == {"id": MAYA_ID, "holder": "Maya", "day": SAT, "code": MAYA_CODE}
    # OBSERVED: the code keeps its old prefix. Maya's Saturday ticket still says FRI.
    assert client.get(f"/api/tickets/{MAYA_ID}").json()["code"] == "FRI-0001"


def test_after_a_move_the_gate_follows_the_new_day(client, clock):
    client.post(f"/api/tickets/{MAYA_ID}/change-day", json={"day": SAT})
    clock.set("2026-10-09T18:00:00")
    assert client.post("/api/gate/scan", json={"code": MAYA_CODE}).status_code == 409
    clock.set("2026-10-10T18:00:00")
    assert client.post("/api/gate/scan", json={"code": MAYA_CODE}).status_code == 200


def test_moving_to_a_day_that_has_begun_is_refused(client, clock):
    clock.set("2026-10-09T18:00:00")    # Friday evening
    res = client.post(f"/api/tickets/{SAM_ID}/change-day", json={"day": FRI})
    assert res.status_code == 409
    assert res.json()["detail"] == "Too late to move to Friday 9 October."


def test_moving_to_a_day_outside_the_festival_is_refused(client):
    res = client.post(f"/api/tickets/{MAYA_ID}/change-day", json={"day": "2026-10-12"})
    assert res.status_code == 422
