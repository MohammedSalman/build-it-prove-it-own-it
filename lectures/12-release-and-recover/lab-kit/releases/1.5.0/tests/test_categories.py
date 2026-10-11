from .conftest import event_by_title


def test_every_event_has_a_category(client):
    events = client.get("/api/events").json()
    assert all(e["category"] in {"games", "music", "film", "maker", "other"} for e in events)


def test_the_programme_can_be_filtered_by_category(client):
    games = client.get("/api/events", params={"category": "games"}).json()
    assert {e["title"] for e in games} == {"Escape Room: The Locked Lab", "Board Game Night"}


def test_a_new_event_keeps_its_category(client):
    res = client.post("/api/events", json={
        "title": "Film Club: Metropolis", "venue": "Lecture Theatre 1",
        "starts_at": "2026-10-10T20:00", "capacity": 90, "category": "film",
    })
    assert res.status_code == 201
    assert event_by_title(client, "Film Club: Metropolis")["category"] == "film"
