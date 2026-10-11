"""Joining the waitlist for a full event.

A waitlist entry is not a reservation. It never counts towards capacity, so it cannot
break the promise "confirmed reservations <= capacity".
"""

import logging

from . import db
from .reservations import EventNotFound

log = logging.getLogger("afterhours")


class HasPlaces(Exception):
    """The event is not full, so there is nothing to wait for: reserve instead."""


def join(event_id: int, attendee: str) -> dict:
    """Put `attendee` on the waitlist of a full event.

    Returns the entry with the person's 1-based position in the queue, and whether it
    was newly created. Joining twice under the same name returns the existing entry
    (same place in the queue) instead of adding a second one.

    Raises EventNotFound, or HasPlaces if the event still has a free place.
    """
    conn = db.connect()
    try:
        # Check "is it full?" and write the entry in one transaction, so the answer
        # cannot change between the check and the insert, and two people joining at
        # once get distinct positions.
        conn.execute("BEGIN IMMEDIATE")
        try:
            event = db.query_one(conn, "SELECT id, capacity FROM events WHERE id = ?", (event_id,))
            if event is None:
                raise EventNotFound(event_id)

            taken = db.query_one(
                conn, "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ?", (event_id,)
            )["n"]
            if taken < event["capacity"]:
                raise HasPlaces(event_id)

            existing = db.query_one(
                conn, "SELECT id FROM waitlist WHERE event_id = ? AND attendee = ?",
                (event_id, attendee),
            )
            if existing is not None:
                entry_id, created = existing["id"], False
            else:
                cur = conn.execute(
                    "INSERT INTO waitlist (event_id, attendee) VALUES (?, ?)", (event_id, attendee)
                )
                entry_id, created = cur.lastrowid, True

            position = db.query_one(
                conn, "SELECT COUNT(*) AS n FROM waitlist WHERE event_id = ? AND id <= ?",
                (event_id, entry_id),
            )["n"]
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        log.info("[%s] %s waitlist #%d at position %d",
                 attendee, "joined" if created else "already on", entry_id, position)
        return {
            "id": entry_id,
            "event_id": event_id,
            "attendee": attendee,
            "position": position,
            "created": created,
        }
    finally:
        conn.close()
