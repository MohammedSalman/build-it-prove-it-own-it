"""Idempotency keys: remember the answer to each reservation attempt.

The page creates one key for each reservation attempt (a press of Reserve) and sends it,
unchanged, on every retry of that attempt, together with its Client-Id. The server stores,
per (client_id, key):

    request_hash   what the attempt asked for, as a fingerprint
    status_code    201 if the attempt booked a place; otherwise the refusal (404 or 409)
    response       the JSON body of that answer

Only bookings are replayed. A refused attempt ("the event is full") changed nothing, so a
retry of the same request is simply tried again, and may find a place that has freed up.
Either way the key stays bound to the request it was first used for: sent again for a
different request, it is refused (KeyReused, HTTP 422).

These helpers are complete. Deciding WHEN to call find(), replay() and save() is Lab 6,
Task A3 (see reservations.reserve). main.py already calls remember_refusal().
"""

import hashlib
import json
import sqlite3

from . import db

BOOKED = 201


class KeyReused(Exception):
    """The same client sent the same key for a different request."""


def fingerprint(event_id: int, attendee: str) -> str:
    """A short hash of what a reservation request asks for.

    Same event and same attendee -> same fingerprint. Anything else -> a different one.
    """
    payload = json.dumps({"event_id": event_id, "attendee": attendee}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def find(conn: sqlite3.Connection, client_id: str, key: str) -> sqlite3.Row | None:
    """The stored row for (client_id, key), or None if this key is new."""
    return db.query_one(
        conn,
        "SELECT request_hash, status_code, response FROM idempotency_keys"
        " WHERE client_id = ? AND key = ?",
        (client_id, key),
    )


def replay(stored: sqlite3.Row, request_hash: str) -> dict | None:
    """The answer to send again for a stored attempt.

    Returns the booking's answer, or None if the attempt was refused before (then carry on
    and try it again, as if nothing were stored). Raises KeyReused if the key was first used
    for a different request.
    """
    if stored["request_hash"] != request_hash:
        raise KeyReused("this Idempotency-Key was already used for a different request")
    if stored["status_code"] != BOOKED:
        return None
    return json.loads(stored["response"])


def save(conn: sqlite3.Connection, client_id: str, key: str, request_hash: str,
         status_code: int, response: dict) -> None:
    """Store a booking's answer.

    Call it inside the SAME transaction that creates the reservation, before COMMIT. If the
    attempt was refused before, its row is updated. An attempt can be booked only once: a
    second save for the same (client_id, key) raises sqlite3.IntegrityError, which rolls the
    whole transaction back, reservation included.
    """
    cur = conn.execute(
        "INSERT INTO idempotency_keys (client_id, key, request_hash, status_code, response)"
        " VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT (client_id, key) DO UPDATE"
        "   SET status_code = excluded.status_code, response = excluded.response"
        "   WHERE idempotency_keys.status_code <> 201"
        "     AND idempotency_keys.request_hash = excluded.request_hash",
        (client_id, key, request_hash, status_code, json.dumps(response)),
    )
    if cur.rowcount != 1:
        raise sqlite3.IntegrityError("this reservation attempt already has a stored booking")


def remember_refusal(client_id: str, key: str, request_hash: str, status_code: int,
                     detail: str) -> None:
    """Bind the key to this request after a refusal, so it cannot later be used for a
    different one. The refusal is not replayed.

    If the key is already bound (a booking, or another refusal that got here first), nothing
    is stored; and if it is bound to a DIFFERENT request, KeyReused is raised, so the caller
    answers 422 instead of the refusal. A binding never changes once stored, so checking
    after the insert is safe even when two refusals arrive at the same moment.

    Uses its own connection: a refusal booked nothing, so there is no transaction to share.
    """
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO idempotency_keys"
            " (client_id, key, request_hash, status_code, response) VALUES (?, ?, ?, ?, ?)",
            (client_id, key, request_hash, status_code, json.dumps({"detail": detail})),
        )
        if cur.rowcount == 0:
            stored = find(conn, client_id, key)
            if stored is not None and stored["request_hash"] != request_hash:
                raise KeyReused("this Idempotency-Key was already used for a different request")
    finally:
        conn.close()
