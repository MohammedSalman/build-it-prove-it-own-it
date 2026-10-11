"""Characterization tests: reserving a place (Week 1 behaviour, plus the start-time rule)."""

from ..conftest import ESCAPE_ROOM, WORKSHOP, book, event_by_title


def test_reserving_a_place_returns_the_reservation(client):
    event = event_by_title(client, ESCAPE_ROOM)
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Maya"})
    assert res.status_code == 201
    body = res.json()
    assert body["attendee"] == "Maya"
    assert body["event_id"] == event["id"]
    assert set(body) == {"id", "event_id", "attendee", "cancel_until"}


def test_a_reservation_uses_up_a_place(client):
    book(client, ESCAPE_ROOM, "Maya")
    after = event_by_title(client, ESCAPE_ROOM)
    assert after["reserved"] == 40
    assert after["places_left"] == 0


def test_a_full_event_turns_people_away(client):
    event = event_by_title(client, WORKSHOP)
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Sam"})
    assert res.status_code == 409


def test_the_last_place_goes_to_whoever_asks_first(client):
    event = event_by_title(client, ESCAPE_ROOM)
    first = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Maya"})
    second = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Sam"})
    assert (first.status_code, second.status_code) == (201, 409)
    assert event_by_title(client, ESCAPE_ROOM)["reserved"] == 40


def test_no_booking_once_the_event_has_started(client, set_now):
    event = event_by_title(client, ESCAPE_ROOM)
    set_now("2026-10-09T20:00")
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Maya"})
    assert res.status_code == 409
    assert res.json()["detail"] == "This event has already started"


def test_unknown_event_is_404(client):
    res = client.post("/api/events/9999/reservations", json={"attendee": "Maya"})
    assert res.status_code == 404


def test_a_name_is_required(client):
    event = event_by_title(client, ESCAPE_ROOM)
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": ""})
    assert res.status_code == 422
