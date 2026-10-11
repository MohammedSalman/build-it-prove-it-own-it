"""Join a full event's waitlist without reserving or authorizing payment."""

from . import db
from .reservations import EventNotFound


class EventNotFull(Exception):
    pass


class AlreadyReserved(Exception):
    pass


def join(event_id: int, attendee: str) -> dict:
    """Return a stable entry and its position, ordered by insertion ID.

    Repeated joins by the same attendee return their existing entry. Serialize
    checks and insertion with reservations and other joins using SQLite's lock.
    """
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        event = db.query_one(conn, "SELECT capacity FROM events WHERE id = ?", (event_id,))
        if event is None:
            raise EventNotFound(event_id)
        if db.query_one(
            conn, "SELECT id FROM reservations WHERE event_id = ? AND attendee = ?",
            (event_id, attendee),
        ):
            raise AlreadyReserved(event_id)
        taken = db.query_one(
            conn, "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ?", (event_id,)
        )["n"]
        if taken < event["capacity"]:
            raise EventNotFull(event_id)

        conn.execute(
            "INSERT INTO waitlist (event_id, attendee) VALUES (?, ?) "
            "ON CONFLICT (event_id, attendee) DO NOTHING",
            (event_id, attendee),
        )
        entry = dict(db.query_one(
            conn, "SELECT id, event_id, attendee FROM waitlist WHERE event_id = ? AND attendee = ?",
            (event_id, attendee),
        ))
        entry["position"] = db.query_one(
            conn, "SELECT COUNT(*) AS n FROM waitlist WHERE event_id = ? AND id <= ?",
            (event_id, entry["id"]),
        )["n"]
        conn.execute("COMMIT")
        return entry
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
