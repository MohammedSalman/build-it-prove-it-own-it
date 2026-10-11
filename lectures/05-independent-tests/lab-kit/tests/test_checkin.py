# These tests came with the door check-in feature, written in the same session as the code,
# and they pass. For Lab 5 they play the part of tests an agent wrote from its own code.
# We wrote them to show that pattern (see the README): treat them as given, not as truth.

from .conftest import event_by_title, reserve

ESCAPE_ROOM = "Escape Room: The Locked Lab"   # Friday 9 October, 20:00 to 22:00


def check_in(client, booking):
    return client.post(f"/api/reservations/{booking['id']}/check-in")


def test_check_in_during_the_event(client, clock):
    booking = reserve(client, event_by_title(client, ESCAPE_ROOM))
    clock.set("2026-10-09T21:00:00")
    res = check_in(client, booking)
    assert res.status_code == 200
    assert res.json()["checked_in_at"] == "2026-10-09T21:00:00"


def test_check_in_before_the_door_opens_is_refused(client, clock):
    booking = reserve(client, event_by_title(client, ESCAPE_ROOM))
    clock.set("2026-10-09T19:00:00")
    assert check_in(client, booking).status_code == 409


def test_check_in_is_allowed_until_the_end_of_the_event(client, clock):
    booking = reserve(client, event_by_title(client, ESCAPE_ROOM))
    clock.set("2026-10-09T22:00:00")
    assert check_in(client, booking).status_code == 200


def test_check_in_after_the_event_is_refused(client, clock):
    booking = reserve(client, event_by_title(client, ESCAPE_ROOM))
    clock.set("2026-10-09T23:00:00")
    assert check_in(client, booking).status_code == 409


def test_checking_in_twice_is_refused(client, clock):
    booking = reserve(client, event_by_title(client, ESCAPE_ROOM))
    clock.set("2026-10-09T21:00:00")
    assert check_in(client, booking).status_code == 200
    assert check_in(client, booking).status_code == 409


def test_unknown_reservation_is_404(client):
    assert client.post("/api/reservations/9999/check-in").status_code == 404
