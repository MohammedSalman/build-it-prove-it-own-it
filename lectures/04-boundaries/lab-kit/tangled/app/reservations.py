"""Reserving a place at an event."""

import logging

from . import db, payments

log = logging.getLogger("afterhours")


class EventNotFound(Exception):
    pass


class SoldOut(Exception):
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

        taken = db.query_one(
            conn,
            "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ? AND status = 'confirmed'",
            (event_id,),
        )["n"]
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
            taken = db.query_one(
                conn,
                "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ? AND status = 'confirmed'",
                (event_id,),
            )["n"]
            if taken >= event["capacity"]:
                log.info("[%s] re-checked: %d of %d taken, too late", attendee, taken, event["capacity"])
                raise SoldOut(event_id)
            cur = conn.execute(
                "INSERT INTO reservations (event_id, attendee) VALUES (?, ?)", (event_id, attendee)
            )
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        log.info("[%s] reservation #%d saved", attendee, cur.lastrowid)
        return {"id": cur.lastrowid, "event_id": event_id, "attendee": attendee}
    finally:
        conn.close()


# --- Lab 4, OPTIONAL extension: shells for the reservations module ------------------------
# After a full split, cancelling and "my bookings" would live here, next to reserve().
# Suggested interface; the route handlers in main.py would only translate HTTP.


class ReservationNotFound(Exception):
    pass


class CannotCancel(Exception):
    """Raised with a sentence the attendee can read."""


def cancel(reservation_id: int, now) -> dict:
    """Cancel a confirmed reservation. Raises ReservationNotFound or CannotCancel."""
    raise NotImplementedError("optional extension")


def my_reservations(attendee: str, now) -> list[dict]:
    """The attendee's reservations with status, can_cancel and cancel_until."""
    raise NotImplementedError("optional extension")
