"""Pins TODAY's cancellation rule: people may cancel any time before the event starts.

These tests must stay green while you extract the seam (Part A, step 2): a refactor
changes no behaviour. They are EXPECTED to fail when you switch to the 24-hour rule
(step 3), because they describe the rule you are replacing.

When that happens, delete this folder in the same commit as the rule change, and say
so in the commit message. Don't edit these tests to make them pass.
"""

from ..conftest import ESCAPE_ROOM, book, my_bookings


def test_old_rule_cancelling_an_hour_before_the_start_is_allowed(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T19:00")
    assert client.post(f"/api/reservations/{maya['id']}/cancel").status_code == 200


def test_old_rule_my_bookings_an_hour_before_the_start(client, set_now):
    book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T19:00")
    [row] = my_bookings(client, "Maya")
    assert row["can_cancel"] is True
    assert row["cancel_until"] == "2026-10-09T20:00"


def test_old_rule_confirmation_shows_the_start_as_the_deadline(client):
    maya = book(client, ESCAPE_ROOM, "Maya")
    assert maya["cancel_until"] == "2026-10-09T20:00"


def test_old_rule_refusal_message(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T20:15")
    res = client.post(f"/api/reservations/{maya['id']}/cancel")
    assert res.json()["detail"] == "This event has already started"
