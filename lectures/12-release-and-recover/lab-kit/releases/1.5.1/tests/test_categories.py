import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

from .conftest import event_by_title


@pytest.fixture
def categories_on(tmp_path, monkeypatch):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps({"event_categories": True}), encoding="utf-8")
    monkeypatch.setenv("AFTERHOURS_FLAGS", str(path))
    return path


def test_with_the_flag_off_the_api_looks_like_1_4(client, monkeypatch):
    monkeypatch.delenv("AFTERHOURS_FLAGS", raising=False)
    events = client.get("/api/events").json()
    assert all("category" not in e for e in events)
    assert len(client.get("/api/events", params={"category": "games"}).json()) == 5


def test_every_event_has_a_category(client, categories_on):
    events = client.get("/api/events").json()
    assert all(e["category"] in {"games", "music", "film", "maker", "other"} for e in events)


def test_the_programme_can_be_filtered_by_category(client, categories_on):
    games = client.get("/api/events", params={"category": "games"}).json()
    assert {e["title"] for e in games} == {"Escape Room: The Locked Lab", "Board Game Night"}


def test_a_new_event_keeps_its_category(client, categories_on):
    res = client.post("/api/events", json={
        "title": "Film Club: Metropolis", "venue": "Lecture Theatre 1",
        "starts_at": "2026-10-10T20:00", "capacity": 90, "category": "film",
    })
    assert res.status_code == 201
    assert event_by_title(client, "Film Club: Metropolis")["category"] == "film"


def test_the_flag_can_be_turned_off_again_without_a_restart(client, categories_on):
    assert "category" in client.get("/api/events").json()[0]
    categories_on.write_text(json.dumps({"event_categories": False, "note": "off"}), encoding="utf-8")
    assert "category" not in client.get("/api/events").json()[0]


# The 1.4.0 schema, exactly as a database created by 1.4.0 has it.
SCHEMA_1_4 = """
CREATE TABLE events (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, venue TEXT NOT NULL,
    starts_at TEXT NOT NULL, capacity INTEGER NOT NULL CHECK (capacity > 0)
);
CREATE TABLE reservations (
    id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id),
    attendee TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
INSERT INTO events (title, venue, starts_at, capacity)
    VALUES ('Quiz Night', 'Student Union', '2026-10-09T19:00', 50);
INSERT INTO reservations (event_id, attendee) VALUES (1, 'Maya');
"""


def test_a_database_created_by_1_4_keeps_working(tmp_path, monkeypatch, categories_on):
    """The test 1.5.0 never had: start this release on a database WITH HISTORY."""
    path = tmp_path / "from-1.4.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_1_4)
    conn.close()
    monkeypatch.setenv("AFTERHOURS_DB", str(path))
    monkeypatch.setenv("AFTERHOURS_PAYMENT_DELAY", "0")
    with TestClient(create_app()) as c:
        events = c.get("/api/events").json()
        assert [(e["title"], e["reserved"], e["category"]) for e in events] == [("Quiz Night", 1, "other")]
        assert c.post("/api/events/1/reservations", json={"attendee": "Sam"}).status_code == 201
