"""Checking people in at the door.

The door volunteer's tablet calls POST /api/reservations/{id}/check-in when someone
arrives. The time comes from the app's clock (see clock.py), never from datetime.now().
"""

from datetime import datetime, timedelta

from . import db
from .reservations import ReservationNotFound

OPENS_BEFORE_START = timedelta(minutes=30)


class CheckInRefused(Exception):
    """The reservation exists, but it cannot be checked in right now."""


def door_is_open(starts_at: datetime, ends_at: datetime, now: datetime) -> bool:
    """Check-in is open from 30 minutes before the start until the end of the event."""
    opens_at = starts_at - OPENS_BEFORE_START
    return opens_at <= now <= ends_at


def check_in(reservation_id: int, now: datetime) -> dict:
    """Check a reservation in at the door at time `now`.

    Returns the reservation with its check-in time.
    Raises ReservationNotFound, or CheckInRefused with a reason the volunteer can read out.
    """
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = db.query_one(
                conn,
                """SELECT r.id, r.attendee, r.status, r.checked_in_at, e.starts_at, e.ends_at
                   FROM reservations r JOIN events e ON e.id = r.event_id
                   WHERE r.id = ?""",
                (reservation_id,),
            )
            if row is None:
                raise ReservationNotFound(reservation_id)
            if row["status"] != "confirmed":
                raise CheckInRefused("This reservation was cancelled.")
            if row["checked_in_at"] is not None:
                raise CheckInRefused(f"Already checked in at {row['checked_in_at']}.")
            starts_at = datetime.fromisoformat(row["starts_at"])
            ends_at = datetime.fromisoformat(row["ends_at"])
            if not door_is_open(starts_at, ends_at, now):
                opens = (starts_at - OPENS_BEFORE_START).strftime("%H:%M")
                raise CheckInRefused(f"Check-in is closed. It runs from {opens} until {ends_at:%H:%M}.")
            checked_in_at = now.isoformat(timespec="seconds")
            conn.execute(
                "UPDATE reservations SET checked_in_at = ? WHERE id = ?", (checked_in_at, reservation_id)
            )
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"id": row["id"], "attendee": row["attendee"], "checked_in_at": checked_in_at}
    finally:
        conn.close()
