from .conftest import event_by_title

ESCAPE_ROOM = "Escape Room: The Locked Lab"   # seeded with 39 of 40 places taken
WORKSHOP = "Maker Workshop: Solder Your Own Badge"  # seeded full


def test_lists_the_festival_programme(client):
    events = client.get("/api/events").json()
    assert len(events) == 16
    assert {"title", "venue", "starts_at", "ends_at", "capacity", "reserved", "places_left",
            "step_free", "description"} <= events[0].keys()


def test_reserving_a_place_returns_the_reservation(client):
    event = event_by_title(client, ESCAPE_ROOM)
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Maya"})
    assert res.status_code == 201
    assert res.json()["attendee"] == "Maya"
    assert res.json()["event_id"] == event["id"]


def test_a_reservation_uses_up_a_place(client):
    event = event_by_title(client, ESCAPE_ROOM)
    client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Maya"})
    after = client.get(f"/api/events/{event['id']}").json()
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
    assert first.status_code == 201
    assert second.status_code == 409
    assert client.get(f"/api/events/{event['id']}").json()["reserved"] == 40


def test_unknown_event_is_404(client):
    res = client.post("/api/events/9999/reservations", json={"attendee": "Maya"})
    assert res.status_code == 404


def test_a_name_is_required(client):
    event = event_by_title(client, ESCAPE_ROOM)
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": ""})
    assert res.status_code == 422
