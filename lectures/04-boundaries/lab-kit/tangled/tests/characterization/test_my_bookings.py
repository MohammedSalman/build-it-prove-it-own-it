"""Characterization tests: the "My bookings" list."""

from ..conftest import BOARD_GAMES, ESCAPE_ROOM, book, my_bookings


def test_lists_only_that_persons_bookings_in_start_order(client):
    book(client, BOARD_GAMES, "Maya")
    book(client, ESCAPE_ROOM, "Maya")
    book(client, BOARD_GAMES, "Sam")
    rows = my_bookings(client, "Maya")
    assert [r["title"] for r in rows] == [ESCAPE_ROOM, BOARD_GAMES]
    assert set(rows[0]) == {"id", "event_id", "title", "venue", "starts_at", "status",
                            "cancel_until", "can_cancel"}


def test_a_booking_days_ahead_can_be_cancelled(client):
    book(client, ESCAPE_ROOM, "Maya")
    [row] = my_bookings(client, "Maya")
    assert row["status"] == "confirmed"
    assert row["can_cancel"] is True


def test_a_cancelled_booking_is_listed_but_cannot_be_cancelled_again(client):
    maya = book(client, ESCAPE_ROOM, "Maya")
    client.post(f"/api/reservations/{maya['id']}/cancel")
    [row] = my_bookings(client, "Maya")
    assert row["status"] == "cancelled"
    assert row["can_cancel"] is False


def test_after_the_start_a_booking_cannot_be_cancelled(client, set_now):
    book(client, ESCAPE_ROOM, "Maya")
    set_now("2026-10-09T20:00")
    assert my_bookings(client, "Maya")[0]["can_cancel"] is False


def test_nobody_has_no_bookings(client):
    assert my_bookings(client, "Nobody") == []
