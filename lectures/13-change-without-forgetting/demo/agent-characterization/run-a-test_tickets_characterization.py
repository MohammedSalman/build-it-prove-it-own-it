"""Public ticket behavior before the pass migration, including v1's quirks.

Tickets are created and inspected through HTTP. Only feature-flag setup uses SQL,
because there is no flag-management API; it never touches the tickets schema.
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

import pytest


FRIDAY = "2026-10-09"
SATURDAY = "2026-10-10"
SUNDAY = "2026-10-11"
DAYS = [
    (FRIDAY, "FRI", "Friday 9 October"),
    (SATURDAY, "SAT", "Saturday 10 October"),
    (SUNDAY, "SUN", "Sunday 11 October"),
]
INVALID_DAYS = ["2026-10-08", "2026-10-12", "2026-02-30", "2026-10-9", "Friday", ""]


def buy(client, day=FRIDAY, holder="Maya"):
    response = client.post("/api/tickets", json={"holder": holder, "day": day})
    assert response.status_code == 201, response.text
    return response.json()


def assert_read(client, ticket):
    response = client.get(f"/api/tickets/{ticket['id']}")
    assert response.status_code == 200
    assert response.json() == ticket


def set_wristband_mode(value):
    with closing(sqlite3.connect(os.environ["AFTERHOURS_DB"])) as conn:
        if value is None:
            conn.execute("DELETE FROM flags WHERE name = 'wristband_mode'")
        else:
            conn.execute(
                "UPDATE flags SET enabled = ? WHERE name = 'wristband_mode'", (value,)
            )
        conn.commit()


@pytest.mark.parametrize("day,prefix,label", DAYS)
def test_sell_and_read_each_day_with_its_code(client, day, prefix, label):
    ticket = buy(client, day, "Zoë O'Neil")
    assert type(ticket["id"]) is int
    assert ticket["id"] > 0
    assert ticket == {
        "id": ticket["id"],
        "holder": "Zoë O'Neil",
        "day": day,
        "code": f"{prefix}-{ticket['id']:04d}",
    }
    assert_read(client, ticket)


def test_same_holder_can_buy_multiple_tickets_with_distinct_ids_and_codes(client):
    tickets = [buy(client), buy(client), buy(client, SATURDAY)]
    assert len({ticket["id"] for ticket in tickets}) == 3
    assert len({ticket["code"] for ticket in tickets}) == 3
    for ticket in tickets:
        assert_read(client, ticket)


@pytest.mark.parametrize("now", ["2026-10-09T00:00:00", "2026-10-12T12:00:00"])
def test_sales_are_allowed_even_after_the_ticket_day_begins(client, clock, now):
    clock.set(now)
    assert_read(client, buy(client))


@pytest.mark.parametrize("holder", [" ", "  Maya  ", "A" * 80])
def test_holder_is_preserved_without_trimming(client, holder):
    ticket = buy(client, holder=holder)
    assert ticket["holder"] == holder
    assert_read(client, ticket)


@pytest.mark.parametrize("day", INVALID_DAYS)
def test_sale_rejects_nonfestival_days(client, day):
    response = client.post("/api/tickets", json={"holder": "Maya", "day": day})
    assert response.status_code == 422
    assert response.json() == {"detail": f"Not a festival day: {day}"}


@pytest.mark.parametrize(
    "method,path,body,field",
    [
        ("POST", "/api/tickets", {"day": FRIDAY}, "holder"),
        ("POST", "/api/tickets", {"holder": "", "day": FRIDAY}, "holder"),
        ("POST", "/api/tickets", {"holder": "A" * 81, "day": FRIDAY}, "holder"),
        ("POST", "/api/tickets", {"holder": None, "day": FRIDAY}, "holder"),
        ("POST", "/api/tickets", {"holder": "Maya"}, "day"),
        ("POST", "/api/tickets", {"holder": "Maya", "day": None}, "day"),
        ("POST", "/api/tickets/1/change-day", {}, "day"),
        ("POST", "/api/tickets/1/change-day", {"day": None}, "day"),
        ("POST", "/api/gate/scan", {}, "code"),
        ("POST", "/api/gate/scan", {"code": ""}, "code"),
        ("POST", "/api/gate/scan", {"code": "X" * 41}, "code"),
        ("POST", "/api/gate/scan", {"code": None}, "code"),
        ("GET", "/api/tickets/not-an-id", None, "ticket_id"),
        ("POST", "/api/tickets/not-an-id/change-day", {"day": FRIDAY}, "ticket_id"),
    ],
)
def test_request_validation(client, method, path, body, field):
    response = client.request(method, path, json=body)
    assert response.status_code == 422
    location = "path" if field == "ticket_id" else "body"
    assert any(error["loc"] == [location, field] for error in response.json()["detail"])


def test_read_unknown_ticket(client):
    response = client.get("/api/tickets/999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "No such ticket"}


@pytest.mark.parametrize("day,prefix,label", DAYS)
@pytest.mark.parametrize("offset_us,status", [(-1, 200), (0, 409), (1, 409)])
def test_change_cutoff_is_exactly_destination_midnight(
    client, clock, day, prefix, label, offset_us, status
):
    original = buy(client, SUNDAY if day != SUNDAY else FRIDAY)
    clock.set(datetime.fromisoformat(day) + timedelta(microseconds=offset_us))
    response = client.post(
        f"/api/tickets/{original['id']}/change-day", json={"day": day}
    )
    assert response.status_code == status
    if status == 200:
        expected = {**original, "day": day}
        assert response.json() == expected
    else:
        expected = original
        assert response.json() == {"detail": f"Too late to move to {label}."}
    assert_read(client, expected)


@pytest.mark.parametrize("now,status", [("2026-10-08T23:59:59", 200), ("2026-10-09T00:00:00", 409)])
def test_same_day_change_uses_the_cutoff_too(client, clock, now, status):
    ticket = buy(client)
    clock.set(now)
    response = client.post(f"/api/tickets/{ticket['id']}/change-day", json={"day": FRIDAY})
    assert response.status_code == status
    assert response.json() == (
        ticket if status == 200 else {"detail": "Too late to move to Friday 9 October."}
    )
    assert_read(client, ticket)


@pytest.mark.parametrize("day", INVALID_DAYS)
def test_invalid_change_leaves_ticket_intact_and_allows_a_later_valid_change(client, day):
    ticket = buy(client)
    response = client.post(f"/api/tickets/{ticket['id']}/change-day", json={"day": day})
    assert response.status_code == 422
    assert response.json() == {"detail": f"Not a festival day: {day}"}
    assert_read(client, ticket)
    changed = client.post(f"/api/tickets/{ticket['id']}/change-day", json={"day": SATURDAY})
    assert changed.status_code == 200
    assert changed.json() == {**ticket, "day": SATURDAY}
    assert_read(client, changed.json())


@pytest.mark.parametrize(
    "day,status,detail",
    [(FRIDAY, 404, "No such ticket"), ("invalid", 422, "Not a festival day: invalid")],
)
def test_change_error_precedence_for_missing_ticket(client, clock, day, status, detail):
    # Invalid day wins over missing ticket; missing ticket wins over the cutoff.
    clock.set("2026-10-12T12:00:00")
    response = client.post("/api/tickets/999999/change-day", json={"day": day})
    assert response.status_code == status
    assert response.json() == {"detail": detail}


@pytest.mark.parametrize("day,prefix,label", DAYS)
@pytest.mark.parametrize("offset_us,admitted", [(-1, False), (0, True), (86_400_000_000 - 1, True), (86_400_000_000, False)])
def test_gate_admits_only_during_the_ticket_calendar_day(
    client, clock, day, prefix, label, offset_us, admitted
):
    ticket = buy(client, day)
    clock.set(datetime.fromisoformat(day) + timedelta(microseconds=offset_us))
    response = client.post("/api/gate/scan", json={"code": ticket["code"]})
    assert response.status_code == (200 if admitted else 409)
    assert response.json() == (
        {"admitted": True, "holder": ticket["holder"], "code": ticket["code"]}
        if admitted else {"detail": f"This ticket is for {label}."}
    )
    assert_read(client, ticket)


def test_scans_can_repeat_and_used_or_expired_tickets_can_move_to_a_future_day(client, clock):
    ticket = buy(client)
    admitted = {"admitted": True, "holder": ticket["holder"], "code": ticket["code"]}
    clock.set("2026-10-09T18:00:00")
    for _ in range(2):
        response = client.post("/api/gate/scan", json={"code": ticket["code"]})
        assert response.status_code == 200
        assert response.json() == admitted
    assert_read(client, ticket)

    # The current day has already started, but only the destination cutoff matters.
    changed = client.post(f"/api/tickets/{ticket['id']}/change-day", json={"day": SATURDAY})
    assert changed.status_code == 200
    assert changed.json() == {**ticket, "day": SATURDAY}
    assert_read(client, changed.json())
    refused = client.post("/api/gate/scan", json={"code": ticket["code"]})
    assert refused.status_code == 409
    assert refused.json() == {"detail": "This ticket is for Saturday 10 October."}

    clock.set("2026-10-10T18:00:00")
    response = client.post("/api/gate/scan", json={"code": ticket["code"]})
    assert response.status_code == 200
    assert response.json() == admitted  # Still the original FRI code.

    # A fully expired Friday ticket can move to Sunday, too.
    expired = buy(client)
    changed = client.post(f"/api/tickets/{expired['id']}/change-day", json={"day": SUNDAY})
    assert changed.status_code == 200
    assert changed.json() == {**expired, "day": SUNDAY}
    assert_read(client, changed.json())


@pytest.mark.parametrize("code_variant", ["unknown", "lowercase", "padded", "forty_characters"])
def test_gate_requires_an_exact_known_code(client, clock, code_variant):
    ticket = buy(client)
    clock.set("2026-10-09T18:00:00")
    code = {
        "unknown": "FRI-999999",
        "lowercase": ticket["code"].lower(),
        "padded": f" {ticket['code']} ",
        "forty_characters": "X" * 40,
    }[code_variant]
    response = client.post("/api/gate/scan", json={"code": code})
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown code"}


@pytest.mark.parametrize("flag", [None, 0, 1], ids=["absent", "disabled", "enabled"])
@pytest.mark.parametrize("now", ["2026-10-01T12:00:00", "2026-10-10T12:00:00", "2026-10-12T12:00:00"])
def test_wristband_mode_bypasses_dates_but_still_requires_a_known_code(client, clock, flag, now):
    ticket = buy(client)
    set_wristband_mode(flag)
    clock.set(now)
    response = client.post("/api/gate/scan", json={"code": ticket["code"]})
    assert response.status_code == (200 if flag else 409)
    assert response.json() == (
        {"admitted": True, "holder": ticket["holder"], "code": ticket["code"]}
        if flag else {"detail": "This ticket is for Friday 9 October."}
    )
    unknown = client.post("/api/gate/scan", json={"code": "unknown"})
    assert unknown.status_code == 404
    assert unknown.json() == {"detail": "Unknown code"}
    assert_read(client, ticket)
