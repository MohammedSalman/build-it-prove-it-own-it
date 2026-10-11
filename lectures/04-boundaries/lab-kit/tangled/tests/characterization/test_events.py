"""Characterization tests: what the event listing does today.

These tests photograph current behaviour. They must stay green through every
step of Lab 4: the refactor, the policy change, and the optional split.
"""

from ..conftest import BOARD_GAMES, ESCAPE_ROOM, book, event_by_title


def test_lists_the_festival_programme_in_start_order(client):
    events = client.get("/api/events").json()
    assert [e["title"] for e in events] == [
        ESCAPE_ROOM,
        "Silent Disco on the Quad",
        "Maker Workshop: Solder Your Own Badge",
        BOARD_GAMES,
        "Open Mic",
    ]
    assert set(events[0]) == {
        "id", "title", "venue", "starts_at", "ends_at", "capacity",
        "reserved", "places_left", "booking_open",
    }


def test_reserved_counts_only_confirmed_places(client):
    games = event_by_title(client, BOARD_GAMES)      # seeded: 23 confirmed, 2 cancelled
    assert games["reserved"] == 23
    assert games["places_left"] == 37


def test_booking_is_open_until_the_event_starts(client, set_now):
    set_now("2026-10-09T19:59")
    assert event_by_title(client, ESCAPE_ROOM)["booking_open"] is True
    set_now("2026-10-09T20:00")
    assert event_by_title(client, ESCAPE_ROOM)["booking_open"] is False


def test_one_event_by_id(client):
    room = event_by_title(client, ESCAPE_ROOM)
    one = client.get(f"/api/events/{room['id']}").json()
    assert one == room


def test_unknown_event_is_404(client):
    assert client.get("/api/events/9999").status_code == 404


def test_create_event_takes_whole_minutes_and_defaults_to_two_hours(client):
    res = client.post("/api/events", json={
        "title": "Karaoke", "venue": "Bar", "starts_at": "2026-10-10T21:00", "capacity": 30,
    })
    assert res.status_code == 201
    assert res.json()["ends_at"] == "2026-10-10T23:00"
    for bad in ["2026-10-10T21:00:30", "2026-10-10 21:00", "tomorrow"]:
        res = client.post("/api/events", json={
            "title": "Karaoke", "venue": "Bar", "starts_at": bad, "capacity": 30,
        })
        assert res.status_code == 422, bad


def test_a_cancelled_place_is_free_again(client):
    maya = book(client, ESCAPE_ROOM, "Maya")                  # 40 of 40
    assert event_by_title(client, ESCAPE_ROOM)["places_left"] == 0
    client.post(f"/api/reservations/{maya['id']}/cancel")
    assert event_by_title(client, ESCAPE_ROOM)["places_left"] == 1
