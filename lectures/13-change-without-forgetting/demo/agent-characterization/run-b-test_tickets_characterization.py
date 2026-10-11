"""Observed v1 API behavior, including quirks that differ from requirements.

Only feature-flag setup touches the database: there is no public flag API.
Ticket creation, reads, changes, and scans all go through the HTTP API.
"""

import pytest

from v1 import db


DAYS = [
    ("2026-10-09", "FRI", "Friday 9 October"),
    ("2026-10-10", "SAT", "Saturday 10 October"),
    ("2026-10-11", "SUN", "Sunday 11 October"),
]


def buy(client, day="2026-10-09", holder="Maya"):
    response = client.post("/api/tickets", json={"holder": holder, "day": day})
    assert response.status_code == 201, response.text
    return response.json()


def read(client, ticket):
    response = client.get(f"/api/tickets/{ticket['id']}")
    assert response.status_code == 200, response.text
    return response.json()


def change(client, ticket, day):
    return client.post(
        f"/api/tickets/{ticket['id']}/change-day", json={"day": day}
    )


def scan(client, code):
    return client.post("/api/gate/scan", json={"code": code})


def assert_admitted(response, ticket):
    assert response.status_code == 200, response.text
    assert response.json() == {
        "admitted": True, "holder": ticket["holder"], "code": ticket["code"]
    }


@pytest.mark.parametrize("day,prefix,label", DAYS)
def test_sell_and_read_each_festival_day(client, day, prefix, label):
    ticket = buy(client, day, "  Zoë O'Neil  ")
    assert isinstance(ticket["id"], int)
    assert ticket["id"] > 0
    assert ticket == {
        "id": ticket["id"],
        "holder": "  Zoë O'Neil  ",
        "day": day,
        "code": f"{prefix}-{ticket['id']:04d}",
    }
    assert read(client, ticket) == ticket


def test_read_existing_seeded_ticket(client):
    response = client.get("/api/tickets/1")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1, "holder": "Maya", "day": "2026-10-09", "code": "FRI-0001"
    }


def test_same_holder_can_buy_multiple_tickets_with_distinct_codes(client):
    tickets = [buy(client, day) for day in ("2026-10-09", "2026-10-09", "2026-10-10")]
    assert len({ticket["id"] for ticket in tickets}) == 3
    assert len({ticket["code"] for ticket in tickets}) == 3
    for ticket in tickets:
        assert read(client, ticket) == ticket


@pytest.mark.parametrize("now", [
    "2026-10-09T00:00:00", "2026-10-09T18:00:00", "2026-10-12T12:00:00"
])
def test_sales_are_allowed_even_when_ticket_day_has_started_or_passed(client, clock, now):
    clock.set(now)
    ticket = buy(client)
    assert read(client, ticket) == ticket


@pytest.mark.parametrize("day", [
    "2026-10-08", "2026-10-12", "2025-10-09", "2026-10-9",
    "2026-10-09T00:00:00", "not-a-date", "",
])
def test_invalid_sale_day_is_422(client, day):
    response = client.post("/api/tickets", json={"holder": "Maya", "day": day})
    assert response.status_code == 422
    assert response.json() == {"detail": f"Not a festival day: {day}"}
    # A refused sale does not consume the next ticket ID (five tickets are seeded).
    assert buy(client)["id"] == 6


@pytest.mark.parametrize("ticket_id", [0, -1, 9999])
def test_read_unknown_ticket_is_404(client, ticket_id):
    response = client.get(f"/api/tickets/{ticket_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "No such ticket"}


@pytest.mark.parametrize("original,destination", [
    ("2026-10-09", "2026-10-10"),
    ("2026-10-11", "2026-10-09"),
    ("2026-10-09", "2026-10-09"),
])
def test_change_before_festival_preserves_identity_holder_and_code(client, clock, original, destination):
    clock.set("2026-10-08T12:00:00")
    ticket = buy(client, original)
    response = change(client, ticket, destination)
    assert response.status_code == 200
    expected = {**ticket, "day": destination}
    assert response.json() == expected
    assert read(client, ticket) == expected


@pytest.mark.parametrize("day,prefix,label", DAYS)
@pytest.mark.parametrize("offset,status", [
    ("before", 200), ("at", 409), ("after", 409)
])
def test_change_cutoff_is_destination_midnight(client, clock, day, prefix, label, offset, status):
    # Start from Sunday so Friday/Saturday cases also cover moving backwards.
    ticket = buy(client, "2026-10-11")
    previous_day = {"2026-10-09": "2026-10-08", "2026-10-10": "2026-10-09", "2026-10-11": "2026-10-10"}[day]
    clock.set({
        "before": f"{previous_day}T23:59:59.999999",
        "at": f"{day}T00:00:00",
        "after": f"{day}T00:00:00.000001",
    }[offset])
    response = change(client, ticket, day)
    assert response.status_code == status
    if status == 200:
        expected = {**ticket, "day": day}
        assert response.json() == expected
    else:
        expected = ticket
        assert response.json() == {"detail": f"Too late to move to {label}."}
    assert read(client, ticket) == expected


@pytest.mark.parametrize("now", [
    "2026-10-09T00:00:00", "2026-10-09T18:00:00", "2026-10-10T18:00:00"
])
def test_change_is_allowed_after_original_day_begins_or_ends(client, clock, now):
    # This is current behavior, despite T3 saying both days must still be ahead.
    ticket = buy(client)
    clock.set(now)
    response = change(client, ticket, "2026-10-11")
    assert response.status_code == 200
    assert response.json() == {**ticket, "day": "2026-10-11"}
    assert read(client, ticket) == response.json()


def test_same_day_change_is_refused_once_day_starts(client, clock):
    ticket = buy(client)
    clock.set("2026-10-09T00:00:00")
    response = change(client, ticket, ticket["day"])
    assert response.status_code == 409
    assert response.json() == {"detail": "Too late to move to Friday 9 October."}
    assert read(client, ticket) == ticket


@pytest.mark.parametrize("day", ["2026-10-12", "not-a-date", ""])
def test_invalid_change_leaves_ticket_unchanged_and_connection_usable(client, day):
    ticket = buy(client)
    response = change(client, ticket, day)
    assert response.status_code == 422
    assert response.json() == {"detail": f"Not a festival day: {day}"}
    assert read(client, ticket) == ticket
    assert change(client, ticket, "2026-10-10").status_code == 200


@pytest.mark.parametrize("day,status,detail", [
    ("2026-10-11", 404, "No such ticket"),
    ("not-a-date", 422, "Not a festival day: not-a-date"),
])
def test_change_error_precedence_for_missing_ticket(client, clock, day, status, detail):
    clock.set("2026-10-12T12:00:00")
    response = change(client, {"id": 9999}, day)
    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert buy(client)["holder"] == "Maya"


def test_refused_late_change_can_be_followed_by_valid_change(client, clock):
    ticket = buy(client, "2026-10-10")
    clock.set("2026-10-09T12:00:00")
    response = change(client, ticket, "2026-10-09")
    assert response.status_code == 409
    assert response.json() == {"detail": "Too late to move to Friday 9 October."}
    assert read(client, ticket) == ticket
    response = change(client, ticket, "2026-10-11")
    assert response.status_code == 200
    assert read(client, ticket) == {**ticket, "day": "2026-10-11"}


@pytest.mark.parametrize("day,prefix,label", DAYS)
@pytest.mark.parametrize("time", ["00:00:00", "12:00:00", "23:59:59.999999"])
def test_gate_admits_throughout_ticket_day_and_allows_repeat_scans(client, clock, day, prefix, label, time):
    ticket = buy(client, day)
    clock.set(f"{day}T{time}")
    for _ in range(2):
        assert_admitted(scan(client, ticket["code"]), ticket)
    assert read(client, ticket) == ticket


@pytest.mark.parametrize("day,prefix,label", DAYS)
@pytest.mark.parametrize("side", ["before", "after"])
def test_gate_refuses_immediately_outside_ticket_day(client, clock, day, prefix, label, side):
    adjacent_days = {
        "2026-10-09": ("2026-10-08", "2026-10-10"),
        "2026-10-10": ("2026-10-09", "2026-10-11"),
        "2026-10-11": ("2026-10-10", "2026-10-12"),
    }
    before, after = adjacent_days[day]
    ticket = buy(client, day)
    clock.set(f"{before}T23:59:59.999999" if side == "before" else f"{after}T00:00:00")
    response = scan(client, ticket["code"])
    assert response.status_code == 409
    assert response.json() == {"detail": f"This ticket is for {label}."}
    assert read(client, ticket) == ticket


def test_used_ticket_can_move_and_original_code_follows_new_day(client, clock):
    ticket = buy(client)
    clock.set("2026-10-09T18:00:00")
    assert_admitted(scan(client, ticket["code"]), ticket)
    response = change(client, ticket, "2026-10-10")
    assert response.status_code == 200
    assert response.json() == {**ticket, "day": "2026-10-10"}
    refused = scan(client, ticket["code"])
    assert refused.status_code == 409
    assert refused.json() == {"detail": "This ticket is for Saturday 10 October."}
    clock.set("2026-10-10T00:00:00")
    assert_admitted(scan(client, ticket["code"]), ticket)
    # Changing the printed prefix does not produce a replacement code.
    replacement = scan(client, f"SAT-{ticket['id']:04d}")
    assert replacement.status_code == 404
    assert replacement.json() == {"detail": "Unknown code"}


@pytest.mark.parametrize("code", ["NO-SUCH-CODE", "fri-0001", " FRI-0001", "FRI-0001 "])
def test_unknown_or_inexact_code_is_404(client, clock, code):
    clock.set("2026-10-09T12:00:00")
    response = scan(client, code)
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown code"}


@pytest.mark.parametrize("flag", [None, 0, 1])
@pytest.mark.parametrize("now", ["2026-10-08T12:00:00", "2026-10-10T12:00:00", "2026-10-12T12:00:00"])
def test_wristband_mode_bypasses_date_but_still_requires_known_code(client, clock, flag, now):
    ticket = buy(client)
    conn = db.connect()
    try:
        if flag is None:
            conn.execute("DELETE FROM flags WHERE name = 'wristband_mode'")
        else:
            conn.execute("UPDATE flags SET enabled = ? WHERE name = 'wristband_mode'", (flag,))
    finally:
        conn.close()
    clock.set(now)
    response = scan(client, ticket["code"])
    if flag == 1:
        assert_admitted(response, ticket)
    else:
        assert response.status_code == 409
        assert response.json() == {"detail": "This ticket is for Friday 9 October."}
    unknown = scan(client, "NO-SUCH-CODE")
    assert unknown.status_code == 404
    assert unknown.json() == {"detail": "Unknown code"}
    assert read(client, ticket) == ticket


@pytest.mark.parametrize("path,body,field", [
    ("/api/tickets", {"day": "2026-10-09"}, "holder"),
    ("/api/tickets", {"holder": "", "day": "2026-10-09"}, "holder"),
    ("/api/tickets", {"holder": "a" * 81, "day": "2026-10-09"}, "holder"),
    ("/api/tickets", {"holder": "Maya"}, "day"),
    ("/api/tickets/1/change-day", {}, "day"),
    ("/api/gate/scan", {}, "code"),
    ("/api/gate/scan", {"code": ""}, "code"),
    ("/api/gate/scan", {"code": "a" * 41}, "code"),
])
def test_request_field_validation(client, path, body, field):
    response = client.post(path, json=body)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


@pytest.mark.parametrize("holder", ["a" * 80, " "])
def test_holder_length_limit_and_whitespace_are_accepted(client, holder):
    ticket = buy(client, holder=holder)
    assert ticket["holder"] == holder
    assert read(client, ticket) == ticket


def test_maximum_length_unknown_scan_code_reaches_lookup(client):
    response = scan(client, "a" * 40)
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown code"}
