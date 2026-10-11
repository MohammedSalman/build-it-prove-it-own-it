"""Characterization tests: cancelling, for the cases the 24-hour rule does NOT change.

Cancelling days ahead is allowed under both the old and the new rule. Cancelling at or
after the start is refused under both. The cases in between (less than 24 hours before
the start) are what the policy change is about: see tests/old_rule and tests/new_rule.
"""

from ..conftest import ESCAPE_ROOM, book, event_by_title, my_bookings


def test_cancelling_days_ahead_is_allowed(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-06T20:00")                              # three days before the start
    res = client.post(f"/api/reservations/{maya['id']}/cancel")
    assert res.status_code == 200
    assert res.json() == {"id": maya["id"], "event_id": maya["event_id"],
                          "attendee": "Maya", "status": "cancelled"}


def test_cancelling_just_over_24_hours_ahead_is_allowed(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-08T19:59")                              # 24 h 1 min before the start
    assert client.post(f"/api/reservations/{maya['id']}/cancel").status_code == 200


def test_cancelling_at_the_start_is_refused(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T20:00")
    assert client.post(f"/api/reservations/{maya['id']}/cancel").status_code == 409
    assert my_bookings(client, "Maya")[0]["status"] == "confirmed"


def test_cancelling_after_the_start_is_refused(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T20:45")
    assert client.post(f"/api/reservations/{maya['id']}/cancel").status_code == 409
    assert event_by_title(client, ESCAPE_ROOM)["places_left"] == 0


def test_cancelling_twice_is_refused(client):
    maya = book(client, ESCAPE_ROOM, "Maya")
    client.post(f"/api/reservations/{maya['id']}/cancel")
    res = client.post(f"/api/reservations/{maya['id']}/cancel")
    assert res.status_code == 409
    assert res.json()["detail"] == "This reservation is already cancelled"
    assert event_by_title(client, ESCAPE_ROOM)["places_left"] == 1


def test_unknown_reservation_is_404(client):
    assert client.post("/api/reservations/99999/cancel").status_code == 404


def test_cancel_then_book_again(client):
    maya = book(client, ESCAPE_ROOM, "Maya")
    client.post(f"/api/reservations/{maya['id']}/cancel")
    again = book(client, ESCAPE_ROOM, "Maya")
    assert again["id"] != maya["id"]
