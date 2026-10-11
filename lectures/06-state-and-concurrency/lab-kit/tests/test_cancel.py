"""Cancelling: the transition confirmed -> cancelled. Provided; these pass on the kit."""

import sqlite3

import pytest

from app import db

from .conftest import event_by_title, reserve_via_api

BOARD_GAMES = "Board Game Night"   # seeded with 23 of 60 places taken


def test_cancelling_frees_the_place(client):
    event = event_by_title(client, BOARD_GAMES)
    reservation = reserve_via_api(client, event, "Maya").json()

    res = client.post(f"/api/reservations/{reservation['id']}/cancel")

    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"
    assert client.get(f"/api/events/{event['id']}").json()["reserved"] == 23


def test_cancelling_twice_changes_nothing_more(client):
    event = event_by_title(client, BOARD_GAMES)
    reservation = reserve_via_api(client, event, "Maya").json()

    client.post(f"/api/reservations/{reservation['id']}/cancel")
    again = client.post(f"/api/reservations/{reservation['id']}/cancel")

    assert again.status_code == 200
    assert again.json()["status"] == "cancelled"
    assert client.get(f"/api/events/{event['id']}").json()["reserved"] == 23   # not 22


def test_cancelling_an_unknown_reservation_is_404(client):
    assert client.post("/api/reservations/9999/cancel").status_code == 404


def test_the_database_refuses_an_unknown_status(client):
    event = event_by_title(client, BOARD_GAMES)
    conn = db.connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO reservations (event_id, attendee, status) VALUES (?, 'Maya', 'maybe')",
                (event["id"],),
            )
    finally:
        conn.close()


def test_the_database_refuses_a_cancellation_without_a_time(client):
    event = event_by_title(client, BOARD_GAMES)
    reservation = reserve_via_api(client, event, "Maya").json()
    conn = db.connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?",
                         (reservation["id"],))
    finally:
        conn.close()
