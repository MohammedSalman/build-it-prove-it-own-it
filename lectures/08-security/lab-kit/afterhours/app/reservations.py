"""Reserving and cancelling places at events.

Every function here takes `user`: the signed-in person making the request, as
auth.current_user() found them from their token. Never a name from the request body.
"""

import logging

from . import db, payments

log = logging.getLogger("afterhours")


class EventNotFound(Exception):
    pass


class SoldOut(Exception):
    pass


class ReservationNotFound(Exception):
    pass


def reserve(event_id: int, user: dict) -> dict:
    """Reserve one place at an event for `user`.

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
        log.info("[%s] checked: %d of %d places taken", user["name"], taken, event["capacity"])
        if taken >= event["capacity"]:
            raise SoldOut(event_id)

        payments.authorize(user["name"])
        log.info("[%s] payment authorised (simulated, nothing charged)", user["name"])

        # The first check was only a hint. Decide again, and write, inside one
        # transaction: BEGIN IMMEDIATE takes SQLite's write lock (Week 1, Patch B).
        conn.execute("BEGIN IMMEDIATE")
        try:
            taken = db.query_one(
                conn, "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ?", (event_id,)
            )["n"]
            if taken >= event["capacity"]:
                log.info("[%s] re-checked: %d of %d taken, too late", user["name"], taken, event["capacity"])
                raise SoldOut(event_id)
            cur = conn.execute(
                "INSERT INTO reservations (event_id, user_id) VALUES (?, ?)", (event_id, user["id"])
            )
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        log.info("[%s] reservation #%d saved", user["name"], cur.lastrowid)
        return {"id": cur.lastrowid, "event_id": event_id, "attendee": user["name"]}
    finally:
        conn.close()


def my_reservations(user: dict) -> list[dict]:
    """The reservations that belong to `user`, and nobody else's."""
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT r.id, r.event_id, e.title, e.starts_at FROM reservations r "
            "JOIN events e ON e.id = r.event_id WHERE r.user_id = ? ORDER BY e.starts_at",
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def cancel(reservation_id: int, user: dict) -> None:
    """Cancel a reservation, freeing its place. Raises ReservationNotFound.

    `user` is who is asking.
    """
    conn = db.connect()
    try:
        cur = conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
        if cur.rowcount == 0:
            raise ReservationNotFound(reservation_id)
    finally:
        conn.close()
    log.info("[%s] cancelled reservation #%d", user["name"], reservation_id)
