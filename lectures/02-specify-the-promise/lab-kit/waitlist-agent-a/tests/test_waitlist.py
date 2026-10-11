import sqlite3

import pytest

from app import db, payments
from app.main import create_app

from .conftest import event_by_title
from .helpers import at_the_same_time, hold_everyone_at_payment

WORKSHOP = "Maker Workshop: Solder Your Own Badge"
ESCAPE_ROOM = "Escape Room: The Locked Lab"


def join(client, event_id, attendee):
    return client.post(f"/api/events/{event_id}/waitlist", json={"attendee": attendee})


def test_join_full_event_without_payment_or_using_capacity(client, monkeypatch):
    def unexpected_payment(attendee):
        pytest.fail("Joining a waitlist must not authorize payment")

    monkeypatch.setattr(payments, "authorize", unexpected_payment)
    event = event_by_title(client, WORKSHOP)
    response = join(client, event["id"], "Maya")
    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"], "event_id": event["id"], "attendee": "Maya", "position": 1,
    }
    after = client.get(f"/api/events/{event['id']}").json()
    assert after["reserved"] == event["reserved"] == event["capacity"]
    assert after["places_left"] == 0
    assert after["waitlisted"] == 1
    assert event_by_title(client, WORKSHOP) == after


def test_positions_and_retries_survive_app_restart(client):
    event = event_by_title(client, WORKSHOP)
    first = join(client, event["id"], "Maya").json()
    second = join(client, event["id"], "Sam").json()
    assert [first["position"], second["position"]] == [1, 2]
    create_app()
    retry = join(client, event["id"], " Maya ")
    assert retry.status_code == 201
    assert retry.json() == first
    assert event_by_title(client, WORKSHOP)["waitlisted"] == 2


def test_cannot_join_before_event_is_full(client):
    event = event_by_title(client, ESCAPE_ROOM)
    response = join(client, event["id"], "Maya")
    assert response.status_code == 409
    assert "still available" in response.json()["detail"]
    assert event_by_title(client, ESCAPE_ROOM)["waitlisted"] == 0
    assert client.post(
        f"/api/events/{event['id']}/reservations", json={"attendee": "Sam"}
    ).status_code == 201
    assert join(client, event["id"], "Maya").status_code == 201


def test_unknown_event(client):
    assert join(client, 9999, "Maya").status_code == 404


@pytest.mark.parametrize("body", [{}, {"attendee": ""}, {"attendee": " \t "},
                                      {"attendee": "x" * 81}, {"attendee": None}])
def test_invalid_name(client, body):
    event = event_by_title(client, WORKSHOP)
    assert client.post(f"/api/events/{event['id']}/waitlist", json=body).status_code == 422
    assert event_by_title(client, WORKSHOP)["waitlisted"] == 0


def test_existing_reservation_cannot_join_waitlist(client):
    event = event_by_title(client, ESCAPE_ROOM)
    assert client.post(
        f"/api/events/{event['id']}/reservations", json={"attendee": " Maya "}
    ).status_code == 201
    response = join(client, event["id"], "Maya")
    assert response.status_code == 409
    assert "already have a reservation" in response.json()["detail"]
    assert event_by_title(client, ESCAPE_ROOM)["waitlisted"] == 0


def test_each_event_has_its_own_queue(client):
    workshop = event_by_title(client, WORKSHOP)
    escape = event_by_title(client, ESCAPE_ROOM)
    client.post(f"/api/events/{escape['id']}/reservations", json={"attendee": "Lee"})
    assert join(client, workshop["id"], "Maya").json()["position"] == 1
    assert join(client, workshop["id"], "Sam").json()["position"] == 2
    assert join(client, escape["id"], "Sam").json()["position"] == 1
    assert event_by_title(client, WORKSHOP)["waitlisted"] == 2
    assert event_by_title(client, ESCAPE_ROOM)["waitlisted"] == 1


def test_concurrent_joins_get_unique_positions(client):
    event = event_by_title(client, WORKSHOP)
    names = [f"Attendee {i}" for i in range(10)]
    outcomes = at_the_same_time(lambda name: join(client, event["id"], name), names)
    assert all(getattr(r, "status_code", None) == 201 for r in outcomes.values()), outcomes
    assert sorted(r.json()["position"] for r in outcomes.values()) == list(range(1, 11))
    assert len({r.json()["id"] for r in outcomes.values()}) == 10
    after = event_by_title(client, WORKSHOP)
    assert after["waitlisted"] == 10
    assert after["reserved"] == after["capacity"]


def test_concurrent_retries_save_one_entry(client):
    event = event_by_title(client, WORKSHOP)
    outcomes = at_the_same_time(
        lambda _: join(client, event["id"], "Maya"), [f"request {i}" for i in range(10)]
    )
    assert all(getattr(r, "status_code", None) == 201 for r in outcomes.values()), outcomes
    entries = [r.json() for r in outcomes.values()]
    assert all(entry == entries[0] for entry in entries)
    assert entries[0]["position"] == 1
    assert event_by_title(client, WORKSHOP)["waitlisted"] == 1


def test_last_seat_race_loser_can_explicitly_join_waitlist(client, monkeypatch):
    event = event_by_title(client, ESCAPE_ROOM)
    hold_everyone_at_payment(monkeypatch, people=2)

    def book_or_join(name):
        response = client.post(
            f"/api/events/{event['id']}/reservations", json={"attendee": name}
        )
        if response.status_code == 409:
            queued = join(client, event["id"], name)
            assert queued.status_code == 201
            return "waitlisted", queued.json()
        assert response.status_code == 201
        return "reserved", response.json()

    outcomes = at_the_same_time(book_or_join, ["Maya", "Sam"])
    assert all(isinstance(result, tuple) for result in outcomes.values()), outcomes
    assert sorted(result[0] for result in outcomes.values()) == ["reserved", "waitlisted"]
    after = event_by_title(client, ESCAPE_ROOM)
    assert after["reserved"] == after["capacity"]
    assert after["waitlisted"] == 1


def test_initialization_upgrades_existing_database_without_losing_data(tmp_path):
    path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(path)
    try:
        conn.executescript("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL, venue TEXT NOT NULL,
                starts_at TEXT NOT NULL, capacity INTEGER NOT NULL CHECK (capacity > 0)
            );
            CREATE TABLE reservations (
                id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id),
                attendee TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            INSERT INTO events VALUES (1, 'Legacy event', 'Quad', '2026-10-09T20:00', 1);
            INSERT INTO reservations (event_id, attendee) VALUES (1, 'Maya');
        """)
        before = conn.execute("SELECT * FROM reservations").fetchall()
        db.init_db(path)
        db.init_db(path)
        assert conn.execute("SELECT * FROM reservations").fetchall() == before
        assert conn.execute("SELECT title FROM events").fetchall() == [("Legacy event",)]
        assert conn.execute("SELECT COUNT(*) FROM waitlist").fetchone() == (0,)
    finally:
        conn.close()
