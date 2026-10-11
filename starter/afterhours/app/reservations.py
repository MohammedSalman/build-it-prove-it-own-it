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
            conn, "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ?", (event_id,)
        )["n"]
        log.info("[%s] checked: %d of %d places taken", attendee, taken, event["capacity"])
        if taken >= event["capacity"]:
            raise SoldOut(event_id)

        payments.authorize(attendee)
        log.info("[%s] payment authorised (simulated, nothing charged)", attendee)

        cur = conn.execute(
            "INSERT INTO reservations (event_id, attendee) VALUES (?, ?)", (event_id, attendee)
        )
        log.info("[%s] reservation #%d saved", attendee, cur.lastrowid)
        return {"id": cur.lastrowid, "event_id": event_id, "attendee": attendee}
    finally:
        conn.close()
