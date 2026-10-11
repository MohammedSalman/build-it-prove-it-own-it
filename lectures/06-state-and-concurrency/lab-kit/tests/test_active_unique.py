"""Task A2: one ACTIVE place per person per event, enforced by the database.

Three of these tests fail on the kit. They pass once schema.sql has a partial unique index
on confirmed reservations and reserve() turns the IntegrityError it causes into
AlreadyReserved. (The tests make fresh databases; delete your own afterhours.db* files after
changing schema.sql before you run the app again.)
"""

import sqlite3

import pytest

from app import db, reservations

from .conftest import event_by_title, reserve_via_api, rows_for
from .helpers import at_the_same_time, hold_everyone_at_payment

BOARD_GAMES = "Board Game Night"   # seeded with 23 of 60 places taken


def test_one_person_cannot_hold_two_active_places_at_one_event(client):
    event = event_by_title(client, BOARD_GAMES)

    first = reserve_via_api(client, event, "Maya")     # two separate attempts, no keys
    second = reserve_via_api(client, event, "Maya")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "You already have a place at this event"
    assert rows_for(event, "Maya") == 1


def test_cancel_then_rebook_is_allowed(client):
    """This already passes on the kit. It stops a unique index that also counts cancelled rows."""
    event = event_by_title(client, BOARD_GAMES)
    first = reserve_via_api(client, event, "Maya").json()
    client.post(f"/api/reservations/{first['id']}/cancel")

    again = reserve_via_api(client, event, "Maya")

    assert again.status_code == 201
    assert again.json()["id"] != first["id"]           # a new reservation, not an un-cancel
    assert rows_for(event, "Maya", "confirmed") == 1
    assert rows_for(event, "Maya", "cancelled") == 1


def test_two_tabs_at_the_same_moment_still_give_one_place(client, monkeypatch):
    """Maya presses Reserve in two browser tabs at once: two attempts, two different keys."""
    event = event_by_title(client, BOARD_GAMES)
    gate = hold_everyone_at_payment(monkeypatch, people=2)  # both check before either saves

    outcomes = at_the_same_time(
        lambda tab: reservations.reserve(event["id"], "Maya", client_id="maya-laptop", key=tab),
        ["tab-1", "tab-2"],
    )

    assert gate.all_arrived, "the two tabs did not meet at the payment gate: order not forced"
    places = [r for r in outcomes.values() if isinstance(r, dict)]
    refused = [r for r in outcomes.values() if isinstance(r, reservations.AlreadyReserved)]
    assert len(places) == 1, outcomes
    assert len(refused) == 1, outcomes
    assert rows_for(event, "Maya") == 1


def test_the_database_itself_refuses_a_second_active_place(client):
    """Even code that skips reserve() cannot store the duplicate."""
    event = event_by_title(client, BOARD_GAMES)
    insert = "INSERT INTO reservations (event_id, attendee) VALUES (?, 'Maya')"
    conn = db.connect()
    try:
        conn.execute(insert, (event["id"],))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insert, (event["id"],))
        # A cancelled reservation is not active, so it does not count.
        conn.execute(
            "INSERT INTO reservations (event_id, attendee, status, cancelled_at)"
            " VALUES (?, 'Maya', 'cancelled', '2026-10-01T10:00:00Z')",
            (event["id"],),
        )
    finally:
        conn.close()
