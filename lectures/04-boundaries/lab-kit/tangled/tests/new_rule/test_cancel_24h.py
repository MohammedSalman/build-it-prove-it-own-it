"""The intended change: cancellations close 24 hours before the event starts.

Spec (from the organisers, 2026-10-01):
  * A confirmed reservation can be cancelled while now < start - 24 hours.
  * From that moment on (including after the start) cancelling is refused with
    HTTP 409 and the detail "Cancellations close 24 hours before the event starts."
  * The confirmation and "My bookings" show that moment as cancel_until
    (ISO 8601, minutes, festival local time), and can_cancel is false from then on.

These tests FAIL on the kit as handed out. They pass once the new rule is in place.
Everything the change must NOT affect is covered by tests/characterization.
"""

from ..conftest import ESCAPE_ROOM, book, event_by_title, my_bookings

CLOSED = "Cancellations close 24 hours before the event starts."


def test_cancelling_23_hours_before_is_refused(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-08T21:00")                              # 23 h before the start
    res = client.post(f"/api/reservations/{maya['id']}/cancel")
    assert res.status_code == 409
    assert res.json()["detail"] == CLOSED
    assert my_bookings(client, "Maya")[0]["status"] == "confirmed"
    assert event_by_title(client, ESCAPE_ROOM)["places_left"] == 0


def test_cancelling_exactly_24_hours_before_is_refused(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-08T20:00")                              # the deadline itself
    assert client.post(f"/api/reservations/{maya['id']}/cancel").status_code == 409


def test_after_the_start_the_refusal_names_the_24_hour_rule(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T20:15")
    assert client.post(f"/api/reservations/{maya['id']}/cancel").json()["detail"] == CLOSED


def test_my_bookings_inside_the_last_24_hours(client, set_now):
    book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T19:00")
    [row] = my_bookings(client, "Maya")
    assert row["can_cancel"] is False
    assert row["cancel_until"] == "2026-10-08T20:00"


def test_confirmation_shows_the_24_hour_deadline(client):
    maya = book(client, ESCAPE_ROOM, "Maya")
    assert maya["cancel_until"] == "2026-10-08T20:00"
