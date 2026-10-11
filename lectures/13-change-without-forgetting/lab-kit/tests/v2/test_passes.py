"""New behaviour in v2: multi-day festival passes (requirement T5).

These run on the expanded and the contracted database (see conftest.py). They switch
the multi_day_passes flag directly in the database; the guard that stops it going on
while v1 is live is tested in tests/migration/test_guards.py.
"""

from ..helpers import FRI, SAT, SUN, switch_flag


def sell(client, first, last, holder="Mei"):
    return client.post("/api/passes", json={"holder": holder, "first_day": first, "last_day": last})


def test_passes_are_not_on_sale_while_the_flag_is_off(client):
    assert sell(client, FRI, SUN).status_code == 404


def test_a_pass_covers_its_days(client):
    switch_flag(client.db, "multi_day_passes", True)
    res = sell(client, FRI, SUN)
    assert res.status_code == 201
    body = res.json()
    assert body["first_day"] == FRI and body["last_day"] == SUN
    assert body["day"] is None                      # a pass has no single day
    assert body["code"] == f"PASS-{body['id']:04d}"
    assert client.get(f"/api/tickets/{body['id']}").json() == body


def test_the_gate_admits_a_pass_on_each_of_its_days_only(client, clock):
    switch_flag(client.db, "multi_day_passes", True)
    code = sell(client, SAT, SUN).json()["code"]
    answers = {}
    for moment in ("2026-10-09T18:00:00", "2026-10-10T18:00:00", "2026-10-11T18:00:00"):
        clock.set(moment)
        answers[moment[:10]] = client.post("/api/gate/scan", json={"code": code}).status_code
    assert answers == {FRI: 409, SAT: 200, SUN: 200}
    clock.set("2026-10-09T18:00:00")
    assert client.post("/api/gate/scan", json={"code": code}).json()["detail"] == \
        "This pass is for Saturday 10 October to Sunday 11 October."


def test_a_pass_cannot_change_days(client):
    switch_flag(client.db, "multi_day_passes", True)
    ticket_id = sell(client, FRI, SAT).json()["id"]
    res = client.post(f"/api/tickets/{ticket_id}/change-day", json={"day": SUN})
    assert res.status_code == 409
    assert res.json()["detail"] == "A festival pass can't change days."


def test_a_pass_needs_two_or_more_festival_days_in_order(client):
    switch_flag(client.db, "multi_day_passes", True)
    assert sell(client, SAT, SAT).status_code == 422          # one day: that's a day ticket
    assert sell(client, SUN, FRI).status_code == 422          # backwards
    assert sell(client, FRI, "2026-10-12").status_code == 422  # not a festival day
