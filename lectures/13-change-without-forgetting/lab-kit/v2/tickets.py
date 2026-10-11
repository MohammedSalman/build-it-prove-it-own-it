"""Tickets in v2: day tickets, and multi-day festival passes.

A ticket admits its holder on every festival day from first_day to last_day. A day
ticket has first_day == last_day; a pass covers two or three days.

v2 runs next to v1 during the migration window (docs/migration-plan.md). Two rules
make that safe:

  WRITE  While the old column `day` exists, v2 keeps it in step: every ticket v2 writes
         has day, first_day and last_day. (For a pass, day = first_day.)
  READ   While `day` exists, it is the truth for day tickets, because v1 still writes
         only `day`: v1's new tickets have no first_day yet, and v1 may move a ticket
         after the backfill has copied it. Passes exist only in the new columns.

The current time always comes from the app's clock (see clock.py).
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


class BadPass(ValueError):
    pass


class PassesNotOnSale(Exception):
    pass


class ChangeRefused(Exception):
    """The ticket exists, but it can't move to that day now."""


class GateRefused(Exception):
    """The ticket exists, but it doesn't admit anyone right now."""


def _starts(day: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), time(0, 0))


def _rollback(conn) -> None:
    if conn.in_transaction:
        conn.execute("ROLLBACK")


def days_of(row, legacy: bool) -> tuple[str, str]:
    """(first_day, last_day) that this ticket admits on, by the READ rule above."""
    first, last = row["first_day"], row["last_day"]
    if legacy and (first is None or last is None or first == last):
        return row["day"], row["day"]
    return first, last


def _select(conn, where: str, param) -> tuple:
    """One ticket row, and whether the old column `day` exists.

    One statement (SELECT *), so the row and the table's shape come from the same moment.
    Checking the shape first and reading afterwards would be check-then-act: the contract
    step could drop `day` in between, and the read would fail.
    """
    row = db.query_one(conn, f"SELECT * FROM tickets WHERE {where} = ?", (param,))
    return row, (row is not None and "day" in row.keys())


def _json(row, legacy: bool) -> dict:
    first, last = days_of(row, legacy)
    return {
        "id": row["id"],
        "holder": row["holder"],
        "day": first if first == last else None,   # v1 clients read `day`; a pass has none
        "code": row["code"],
        "first_day": first,
        "last_day": last,
    }


def _insert(conn, holder: str, first: str, last: str, prefix: str) -> tuple[int, str]:
    """Insert a ticket, keeping `day` in step while it exists (the WRITE rule).

    Called inside BEGIN IMMEDIATE: this connection holds the write lock, so the contract
    step, which needs the same lock, can't change the table between the check and the write.
    """
    if db.has_day_column(conn):
        cur = conn.execute(
            "INSERT INTO tickets (holder, day, first_day, last_day, code) VALUES (?, ?, ?, ?, ?)",
            (holder, first, first, last, f"new-{holder}"),
        )
    else:
        cur = conn.execute(
            "INSERT INTO tickets (holder, first_day, last_day, code) VALUES (?, ?, ?, ?)",
            (holder, first, last, f"new-{holder}"),
        )
    code = f"{prefix}-{cur.lastrowid:04d}"
    conn.execute("UPDATE tickets SET code = ? WHERE id = ?", (code, cur.lastrowid))
    return cur.lastrowid, code


def buy(holder: str, day: str) -> dict:
    """Sell a day ticket. Raises NotAFestivalDay."""
    if day not in DAY_CODES:
        raise NotAFestivalDay(day)
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            ticket_id, _ = _insert(conn, holder, day, day, DAY_CODES[day])
            row, legacy = _select(conn, "id", ticket_id)
            conn.execute("COMMIT")
        except BaseException:
            _rollback(conn)
            raise
        return _json(row, legacy)
    finally:
        conn.close()


def buy_pass(holder: str, first_day: str, last_day: str) -> dict:
    """Sell a festival pass for two or three consecutive days.

    Raises PassesNotOnSale (flag multi_day_passes is off), NotAFestivalDay, or BadPass.
    """
    conn = db.connect()
    try:
        if not flags.enabled(conn, "multi_day_passes"):
            raise PassesNotOnSale()
        for day in (first_day, last_day):
            if day not in DAY_CODES:
                raise NotAFestivalDay(day)
        if not first_day < last_day:
            raise BadPass("A pass covers at least two days: last_day must come after first_day.")
        conn.execute("BEGIN IMMEDIATE")
        try:
            ticket_id, _ = _insert(conn, holder, first_day, last_day, "PASS")
            row, legacy = _select(conn, "id", ticket_id)
            conn.execute("COMMIT")
        except BaseException:
            _rollback(conn)
            raise
        return _json(row, legacy)
    finally:
        conn.close()


def get(ticket_id: int) -> dict:
    conn = db.connect()
    try:
        row, legacy = _select(conn, "id", ticket_id)
    finally:
        conn.close()
    if row is None:
        raise TicketNotFound(ticket_id)
    return _json(row, legacy)


def change_day(ticket_id: int, new_day: str, now: datetime) -> dict:
    """Move a day ticket to another festival day. Passes can't move.

    Behaves exactly as v1 for day tickets: during the migration window a holder must
    get the same answer whichever server takes the request.
    Raises NotAFestivalDay, TicketNotFound, or ChangeRefused.
    """
    if new_day not in DAY_CODES:
        raise NotAFestivalDay(new_day)
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row, legacy = _select(conn, "id", ticket_id)
            if row is None:
                raise TicketNotFound(ticket_id)
            first, last = days_of(row, legacy)
            if first != last:
                raise ChangeRefused("A festival pass can't change days.")
            # A ticket can move until the day begins.
            if now >= _starts(new_day):
                raise ChangeRefused(f"Too late to move to {DAY_NAMES[new_day]}.")
            if legacy:
                conn.execute(
                    "UPDATE tickets SET day = ?, first_day = ?, last_day = ? WHERE id = ?",
                    (new_day, new_day, new_day, ticket_id),
                )
            else:
                conn.execute(
                    "UPDATE tickets SET first_day = ?, last_day = ? WHERE id = ?",
                    (new_day, new_day, ticket_id),
                )
            row, legacy = _select(conn, "id", ticket_id)
            conn.execute("COMMIT")
        except BaseException:
            _rollback(conn)
            raise
        return _json(row, legacy)
    finally:
        conn.close()


def scan(code: str, now: datetime) -> dict:
    """The gate scans a wristband code at time `now`.

    Returns who was admitted. Raises TicketNotFound or GateRefused.
    """
    conn = db.connect()
    try:
        row, legacy = _select(conn, "code", code)
        if row is None:
            raise TicketNotFound(code)
        if flags.enabled(conn, "wristband_mode"):
            # Festival 2025: the scanners failed on the first night, so volunteers checked
            # paper wristbands by eye and every ticket was let in.
            return {"admitted": True, "holder": row["holder"], "code": row["code"]}
        first, last = days_of(row, legacy)
        today = now.date().isoformat()
        if not first <= today <= last:
            if first == last:
                raise GateRefused(f"This ticket is for {DAY_NAMES[first]}.")
            raise GateRefused(f"This pass is for {DAY_NAMES[first]} to {DAY_NAMES[last]}.")
        return {"admitted": True, "holder": row["holder"], "code": row["code"]}
    finally:
        conn.close()
