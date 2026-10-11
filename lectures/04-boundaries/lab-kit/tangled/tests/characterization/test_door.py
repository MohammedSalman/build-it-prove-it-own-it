"""Characterization tests: door check-in for volunteers.

The door opens 30 minutes before the start and closes when the event ends.
"""

from ..conftest import BOARD_GAMES, ESCAPE_ROOM, book, event_by_title


def door(client, title):
    return client.get(f"/api/events/{event_by_title(client, title)['id']}/door").json()


def test_door_list_shows_confirmed_people_only(client):
    maya = book(client, ESCAPE_ROOM, "Maya")
    sam = book(client, BOARD_GAMES, "Sam")
    client.post(f"/api/reservations/{sam['id']}/cancel")
    names = [p["attendee"] for p in door(client, ESCAPE_ROOM)["people"]]
    assert "Maya" in names and len(names) == 40
    assert "Sam" not in [p["attendee"] for p in door(client, BOARD_GAMES)["people"]]
    assert maya["id"] in [p["id"] for p in door(client, ESCAPE_ROOM)["people"]]


def test_check_in_opens_30_minutes_before_the_start(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T19:29")
    res = client.post(f"/api/reservations/{maya['id']}/check-in")
    assert res.status_code == 409
    assert res.json()["detail"] == "Check-in opens at 19:30"
    assert door(client, ESCAPE_ROOM)["door_open"] is False
    set_now("2026-10-09T19:30")
    assert door(client, ESCAPE_ROOM)["door_open"] is True
    res = client.post(f"/api/reservations/{maya['id']}/check-in")
    assert res.status_code == 200
    assert res.json()["checked_in_at"] == "2026-10-09T19:30:00"


def test_check_in_closes_when_the_event_ends(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T21:30")
    res = client.post(f"/api/reservations/{maya['id']}/check-in")
    assert res.status_code == 409
    assert res.json()["detail"] == "This event has ended"
    assert door(client, ESCAPE_ROOM)["door_open"] is False


def test_checking_in_twice_is_refused(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T19:45")
    client.post(f"/api/reservations/{maya['id']}/check-in")
    res = client.post(f"/api/reservations/{maya['id']}/check-in")
    assert res.status_code == 409
    assert res.json()["detail"] == "Already checked in at 19:45"
    assert door(client, ESCAPE_ROOM)["checked_in"] == 1


def test_a_cancelled_reservation_cannot_check_in(client, set_now):
    maya = book(client, ESCAPE_ROOM, "Maya")
    client.post(f"/api/reservations/{maya['id']}/cancel")
    set_now("2026-10-09T19:45")
    res = client.post(f"/api/reservations/{maya['id']}/check-in")
    assert res.status_code == 409
    assert res.json()["detail"] == "This reservation was cancelled"


def test_PINNED_QUIRK_door_expected_counts_cancelled_reservations(client):
    # Current behaviour, pinned as it is. It looks like a bug: the listing says 23
    # reserved, the door says 25 expected, because the door query forgot to leave out
    # cancelled reservations. A characterization test records what the code DOES.
    # Don't fix it inside a refactor. If you want to fix it, make that a separate,
    # intentional change: change this test in the same commit and say why.
    assert event_by_title(client, BOARD_GAMES)["reserved"] == 23
    assert door(client, BOARD_GAMES)["expected"] == 25
