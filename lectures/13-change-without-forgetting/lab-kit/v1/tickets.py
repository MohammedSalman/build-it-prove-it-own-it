"""Day tickets: each ticket is for one festival day and is scanned at the gate.

The current time always comes from the app's clock (see clock.py), never from
datetime.now(). Days are ISO dates in festival local time, e.g. "2026-10-09".
"""

from datetime import date, datetime, time

from . import db, flags
from .db import DAY_CODES

DAY_NAMES = {"2026-10-09": "Friday 9 October", "2026-10-10": "Saturday 10 October",
             "2026-10-11": "Sunday 11 October"}


class TicketNotFound(Exception):
    pass


class NotAFestivalDay(ValueError):
    pass


class ChangeRefused(Exception):
    """The ticket exists, but it can't move to that day now."""


class GateRefused(Exception):
    """The ticket exists, but it doesn't admit anyone right now."""


def _starts(day: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), time(0, 0))


def _json(row) -> dict:
    return {"id": row["id"], "holder": row["holder"], "day": row["day"], "code": row["code"]}


def _rollback(conn) -> None:
    if conn.in_transaction:
        conn.execute("ROLLBACK")


def buy(holder: str, day: str) -> dict:
    """Sell a day ticket. Raises NotAFestivalDay."""
    if day not in DAY_CODES:
        raise NotAFestivalDay(day)
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(
                "INSERT INTO tickets (holder, day, code) VALUES (?, ?, ?)", (holder, day, f"new-{holder}")
            )
            code = f"{DAY_CODES[day]}-{cur.lastrowid:04d}"
            conn.execute("UPDATE tickets SET code = ? WHERE id = ?", (code, cur.lastrowid))
            conn.execute("COMMIT")
        except BaseException:
            _rollback(conn)
            raise
        return {"id": cur.lastrowid, "holder": holder, "day": day, "code": code}
    finally:
        conn.close()


def get(ticket_id: int) -> dict:
    conn = db.connect()
    try:
        row = db.query_one(conn, "SELECT id, holder, day, code FROM tickets WHERE id = ?", (ticket_id,))
    finally:
        conn.close()
    if row is None:
        raise TicketNotFound(ticket_id)
    return _json(row)


def change_day(ticket_id: int, new_day: str, now: datetime) -> dict:
    """Move a ticket to another festival day.

    Raises NotAFestivalDay, TicketNotFound, or ChangeRefused.
    """
    if new_day not in DAY_CODES:
        raise NotAFestivalDay(new_day)
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = db.query_one(conn, "SELECT id, holder, day, code FROM tickets WHERE id = ?", (ticket_id,))
            if row is None:
                raise TicketNotFound(ticket_id)
            # A ticket can move until the day begins.
            if now >= _starts(new_day):
                raise ChangeRefused(f"Too late to move to {DAY_NAMES[new_day]}.")
            conn.execute("UPDATE tickets SET day = ? WHERE id = ?", (new_day, ticket_id))
            conn.execute("COMMIT")
        except BaseException:
            _rollback(conn)
            raise
        return {"id": row["id"], "holder": row["holder"], "day": new_day, "code": row["code"]}
    finally:
        conn.close()


def scan(code: str, now: datetime) -> dict:
    """The gate scans a wristband code at time `now`.

    Returns who was admitted. Raises TicketNotFound or GateRefused.
    """
    conn = db.connect()
    try:
        row = db.query_one(conn, "SELECT id, holder, day, code FROM tickets WHERE code = ?", (code,))
        if row is None:
            raise TicketNotFound(code)
        if flags.enabled(conn, "wristband_mode"):
            # Festival 2025: the scanners failed on the first night, so volunteers checked
            # paper wristbands by eye and every ticket was let in.
            return {"admitted": True, "holder": row["holder"], "code": row["code"]}
        if row["day"] != now.date().isoformat():
            raise GateRefused(f"This ticket is for {DAY_NAMES[row['day']]}.")
        return {"admitted": True, "holder": row["holder"], "code": row["code"]}
    finally:
        conn.close()
