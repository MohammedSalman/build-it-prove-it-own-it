"""Reserving and cancelling places at an event.

A reservation moves through a small state machine:

               reserve                cancel
    (nothing) ────────▶ confirmed ────────▶ cancelled ──┐
                                                ▲        │ cancel again: nothing changes
                                                └────────┘
    Forbidden: cancelled ──▶ confirmed. To come back, book again (a new reservation).

Only confirmed reservations use up a place.
"""

import logging

from . import db, idempotency, payments
from .idempotency import KeyReused  # noqa: F401  (re-exported: main.py turns it into HTTP 422)

log = logging.getLogger("afterhours")


class EventNotFound(Exception):
    pass


class SoldOut(Exception):
    pass


class AlreadyReserved(Exception):
    """The attendee already holds a confirmed place at this event."""


class ReservationNotFound(Exception):
    pass


# The only status change the app ever makes. cancel() enforces it in its UPDATE.
TRANSITIONS = {("confirmed", "cancelled")}


def _tag(attendee: str, key: str | None) -> str:
    """Log prefix: [Maya] or, when the request carries an idempotency key, [Maya · key 5b1f]."""
    return f"[{attendee} · key {key[:4]}]" if key else f"[{attendee}]"


def places_taken(conn, event_id: int) -> int:
    return db.query_one(
        conn,
        "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ? AND status = 'confirmed'",
        (event_id,),
    )["n"]


def reserve(event_id: int, attendee: str, client_id: str | None = None,
            key: str | None = None) -> dict:
    """Reserve one place at an event for `attendee`.

    client_id and key identify one reservation *attempt*: they come from the Client-Id and
    Idempotency-Key headers, and the page sends the same pair on every retry of an attempt.
    Both are optional; a request without a key is handled as a new attempt.

    Returns the reservation. Raises EventNotFound, SoldOut, AlreadyReserved or KeyReused.
    """
    tag = _tag(attendee, key)
    request_hash = idempotency.fingerprint(event_id, attendee)  # noqa: F841  (for Task A3)
    conn = db.connect()
    try:
        # TODO (Task A3, step 1): if this client has sent this key before, find(...) returns
        # its row and replay(...) gives the answer to send again: return it, without checking,
        # paying or saving. replay() returns None when that attempt was refused before; then
        # carry on as if nothing were stored.

        event = db.query_one(conn, "SELECT id, capacity FROM events WHERE id = ?", (event_id,))
        if event is None:
            raise EventNotFound(event_id)

        taken = places_taken(conn, event_id)
        log.info("%s checked: %d of %d places taken", tag, taken, event["capacity"])
        if taken >= event["capacity"]:
            # TODO (Task A3, step 2): before answering "full", look the key up once more.
            # Another send of this same attempt may have just booked the last place; if
            # replay(...) gives an answer, return it instead.
            raise SoldOut(event_id)

        hold = payments.authorize(attendee)
        log.info("%s payment authorised (%s, simulated, nothing charged)", tag, hold)

        # Patch B (Week 1): the first check was only a hint. Decide again, and write, inside
        # one transaction. BEGIN IMMEDIATE takes SQLite's write lock, so a second request
        # waits here until the first has committed, then sees the updated count.
        conn.execute("BEGIN IMMEDIATE")
        try:
            # TODO (Task A3, step 3): look the key up again here. Another send with the
            # same key may have booked while this one was paying. If replay(...) gives an
            # answer, end the transaction and return it.

            taken = places_taken(conn, event_id)
            if taken >= event["capacity"]:
                log.info("%s re-checked: %d of %d taken, too late", tag, taken, event["capacity"])
                raise SoldOut(event_id)

            # TODO (Task A2): once the unique index exists, a second confirmed place for the
            # same person makes this INSERT raise sqlite3.IntegrityError. Turn that into
            # AlreadyReserved(event_id).
            cur = conn.execute(
                "INSERT INTO reservations (event_id, attendee) VALUES (?, ?)", (event_id, attendee)
            )
            reservation = {"id": cur.lastrowid, "event_id": event_id, "attendee": attendee,
                           "status": "confirmed"}

            # TODO (Task A3, step 4): store the answer with idempotency.save(...) here,
            # inside this transaction, before COMMIT.

            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        log.info("%s reservation #%d saved", tag, reservation["id"])
        return reservation
    finally:
        conn.close()


def cancel(reservation_id: int) -> dict:
    """confirmed -> cancelled. Cancelling a cancelled reservation changes nothing.

    The WHERE clause is the transition guard. Checking the state and changing it happen
    in ONE statement, so there is no gap between check and act for another request to
    slip into.
    """
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE reservations"
            " SET status = 'cancelled', cancelled_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
            " WHERE id = ? AND status = 'confirmed'",
            (reservation_id,),
        )
        row = db.query_one(
            conn, "SELECT id, event_id, attendee, status FROM reservations WHERE id = ?",
            (reservation_id,),
        )
        if row is None:
            raise ReservationNotFound(reservation_id)
        if cur.rowcount == 1:
            log.info("[%s] reservation #%d cancelled", row["attendee"], reservation_id)
        else:
            log.info("[%s] reservation #%d was already cancelled: nothing to do",
                     row["attendee"], reservation_id)
        return dict(row)
    finally:
        conn.close()
