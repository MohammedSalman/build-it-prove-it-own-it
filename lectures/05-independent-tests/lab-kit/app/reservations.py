"""Reserving and cancelling places."""

import logging

from . import db, payments

log = logging.getLogger("afterhours")

# Only confirmed reservations take up a place.
CONFIRMED_COUNT = "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ? AND status = 'confirmed'"


class EventNotFound(Exception):
    pass


class SoldOut(Exception):
    pass


class ReservationNotFound(Exception):
    pass


def reserve(event_id: int, attendee: str) -> dict:
    """Reserve one place at an event for `attendee`.

    Returns the saved reservation. Raises EventNotFound or SoldOut.
    """
    conn = db.connect()
    try:
        event = db.query_one(conn, "SELECT id, capacity FROM events WHERE id = ?", (event_id,))
        if event is None:
            raise EventNotFound(event_id)

        taken = db.query_one(conn, CONFIRMED_COUNT, (event_id,))["n"]
        log.info("[%s] checked: %d of %d places taken", attendee, taken, event["capacity"])
        if taken >= event["capacity"]:
            raise SoldOut(event_id)

        payments.authorize(attendee)
        log.info("[%s] payment authorised (simulated, nothing charged)", attendee)

        # The first check was only a hint. Decide again, and write, inside one
        # transaction: BEGIN IMMEDIATE takes SQLite's write lock, so a second request
        # waits here until the first has committed, then sees the updated count.
        conn.execute("BEGIN IMMEDIATE")
        try:
            taken_now = db.query_one(conn, CONFIRMED_COUNT, (event_id,))["n"]
            if taken_now >= event["capacity"]:
                log.info("[%s] re-checked: %d of %d taken, too late", attendee, taken_now, event["capacity"])
                raise SoldOut(event_id)
            cur = conn.execute(
                "INSERT INTO reservations (event_id, attendee) VALUES (?, ?)", (event_id, attendee)
            )
            conn.execute("UPDATE events SET places_left = places_left - 1 WHERE id = ?", (event_id,))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        log.info("[%s] reservation #%d saved", attendee, cur.lastrowid)
        return {"id": cur.lastrowid, "event_id": event_id, "attendee": attendee, "status": "confirmed"}
    finally:
        conn.close()


def get(reservation_id: int) -> dict:
    """Look up one reservation. Raises ReservationNotFound."""
    conn = db.connect()
    try:
        row = db.query_one(
            conn,
            "SELECT id, event_id, attendee, status, checked_in_at FROM reservations WHERE id = ?",
            (reservation_id,),
        )
    finally:
        conn.close()
    if row is None:
        raise ReservationNotFound(reservation_id)
    return dict(row)


def cancel(reservation_id: int) -> dict:
    """Cancel a reservation and give its place back to the event.

    Returns the cancelled reservation. Raises ReservationNotFound.
    """
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = db.query_one(
                conn, "SELECT id, event_id, attendee FROM reservations WHERE id = ?", (reservation_id,)
            )
            if row is None:
                raise ReservationNotFound(reservation_id)
            conn.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (reservation_id,))
            conn.execute("UPDATE events SET places_left = places_left + 1 WHERE id = ?", (row["event_id"],))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        log.info("[%s] reservation #%d cancelled", row["attendee"], reservation_id)
        return {"id": row["id"], "event_id": row["event_id"], "attendee": row["attendee"], "status": "cancelled"}
    finally:
        conn.close()
