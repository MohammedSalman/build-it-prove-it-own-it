from .conftest import event_by_title, signed_in

ESCAPE_ROOM = "Escape Room: The Locked Lab"   # seeded with 39 of 40 places taken
WORKSHOP = "Maker Workshop: Solder Your Own Badge"  # seeded full


def test_lists_the_festival_programme(client):
    events = client.get("/api/events").json()
    assert len(events) == 5
    assert {"title", "venue", "starts_at", "capacity", "reserved", "places_left"} <= events[0].keys()


def test_reserving_a_place_returns_the_reservation(client):
    event = event_by_title(client, ESCAPE_ROOM)
    res = client.post(f"/api/events/{event['id']}/reservations", headers=signed_in(client, "Maya"))
    assert res.status_code == 201
    assert res.json()["attendee"] == "Maya"
    assert res.json()["event_id"] == event["id"]


def test_a_reservation_uses_up_a_place(client):
    event = event_by_title(client, ESCAPE_ROOM)
    client.post(f"/api/events/{event['id']}/reservations", headers=signed_in(client, "Maya"))
    after = client.get(f"/api/events/{event['id']}").json()
    assert after["reserved"] == 40
    assert after["places_left"] == 0


def test_a_full_event_turns_people_away(client):
    event = event_by_title(client, WORKSHOP)
    res = client.post(f"/api/events/{event['id']}/reservations", headers=signed_in(client, "Sam"))
    assert res.status_code == 409


def test_the_last_place_goes_to_whoever_asks_first(client):
    event = event_by_title(client, ESCAPE_ROOM)
    first = client.post(f"/api/events/{event['id']}/reservations", headers=signed_in(client, "Maya"))
    second = client.post(f"/api/events/{event['id']}/reservations", headers=signed_in(client, "Sam"))
    assert first.status_code == 201
    assert second.status_code == 409
    assert client.get(f"/api/events/{event['id']}").json()["reserved"] == 40


def test_unknown_event_is_404(client):
    res = client.post("/api/events/9999/reservations", headers=signed_in(client, "Maya"))
    assert res.status_code == 404


def test_cancelling_your_own_reservation_frees_the_place(client):
    event = event_by_title(client, ESCAPE_ROOM)
    maya = signed_in(client, "Maya")
    booking = client.post(f"/api/events/{event['id']}/reservations", headers=maya).json()
    assert client.delete(f"/api/reservations/{booking['id']}", headers=maya).status_code == 204
    assert client.get(f"/api/events/{event['id']}").json()["places_left"] == 1
    assert client.get("/api/me/reservations", headers=maya).json() == []
