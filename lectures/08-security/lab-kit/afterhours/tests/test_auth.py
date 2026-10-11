"""Authentication: who is asking? (Supplied. These pass on the kit.)"""

import sqlite3

from .conftest import PASSWORDS, event_by_title, signed_in

ESCAPE_ROOM = "Escape Room: The Locked Lab"


def test_signing_in_returns_a_token_and_who_you_are(client):
    res = client.post("/api/login", json={"name": "Maya", "password": PASSWORDS["Maya"]})
    assert res.status_code == 200
    assert res.json()["name"] == "Maya" and res.json()["role"] == "student"
    assert len(res.json()["token"]) >= 32


def test_a_wrong_password_and_an_unknown_name_get_the_same_answer(client):
    wrong = client.post("/api/login", json={"name": "Maya", "password": PASSWORDS["Sam"]})
    unknown = client.post("/api/login", json={"name": "Nobody", "password": "x"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_a_guest_account_cannot_sign_in(client):
    assert client.post("/api/login", json={"name": "guest-001", "password": ""}).status_code == 422
    assert client.post("/api/login", json={"name": "guest-001", "password": "x"}).status_code == 401


def test_reserving_needs_a_signed_in_user(client):
    event = event_by_title(client, ESCAPE_ROOM)
    assert client.post(f"/api/events/{event['id']}/reservations").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.post(f"/api/events/{event['id']}/reservations", headers=bad).status_code == 401


def test_the_name_on_a_reservation_comes_from_the_token_not_the_request(client):
    """Week 1's app took the name from the request body, so anyone could book as anyone."""
    event = event_by_title(client, ESCAPE_ROOM)
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Maya"},
                      headers=signed_in(client, "Sam"))
    assert res.status_code == 201
    assert res.json()["attendee"] == "Sam"


def test_my_reservations_shows_only_mine(client):
    event = event_by_title(client, ESCAPE_ROOM)
    maya, sam = signed_in(client, "Maya"), signed_in(client, "Sam")
    client.post(f"/api/events/{event['id']}/reservations", headers=maya)
    assert [r["title"] for r in client.get("/api/me/reservations", headers=maya).json()] == [ESCAPE_ROOM]
    assert client.get("/api/me/reservations", headers=sam).json() == []


def test_signing_out_ends_the_session(client):
    maya = signed_in(client, "Maya")
    assert client.get("/api/me", headers=maya).status_code == 200
    assert client.post("/api/logout", headers=maya).status_code == 204
    assert client.get("/api/me", headers=maya).status_code == 401


def test_the_database_keeps_no_passwords_and_no_tokens(client, tmp_path):
    token = signed_in(client, "Maya")["Authorization"].removeprefix("Bearer ")
    conn = sqlite3.connect(tmp_path / "test.db")
    dump = "\n".join(conn.iterdump())
    conn.close()
    assert token not in dump
    assert PASSWORDS["Maya"] not in dump


def test_only_organisers_can_add_events(client):
    new = {"title": "Pub Quiz", "venue": "Bar", "starts_at": "2026-10-11T20:00", "capacity": 30}
    assert client.post("/api/events", json=new).status_code == 401
    assert client.post("/api/events", json=new, headers=signed_in(client, "Sam")).status_code == 403
    assert client.post("/api/events", json=new, headers=signed_in(client, "Olu")).status_code == 201
