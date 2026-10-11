"""What the ticket data MEANS, read from any shape of the tickets table.

    meaning(conn) -> {ticket id: (holder, code, (days it admits on, ...))}

"Days it admits on" are the days the ticket's data entitles its holder to. That is what
the migration must keep. The v1 table and the contracted table have different columns, so
their bytes, and any checksum of their rows, always differ. Their meaning must not.

This reads only the tickets table, never the flags. It assumes wristband_mode is off: with
that flag on, the gate admits every ticket on any day, and meaning() does not show it.

The rule for reading is the same one v2 uses (v2/tickets.py, the READ rule): while the
old column `day` exists, it is the truth for day tickets; passes live only in
first_day and last_day.
"""

import json
import sqlite3
from pathlib import Path

FESTIVAL_DAYS = ("2026-10-09", "2026-10-10", "2026-10-11")


def admitted_days(first: str, last: str) -> tuple[str, ...]:
    return tuple(day for day in FESTIVAL_DAYS if first <= day <= last)


def meaning(conn: sqlite3.Connection) -> dict[int, tuple]:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(tickets)")}
    has_day = "day" in cols
    has_range = {"first_day", "last_day"} <= cols
    wanted = ["id", "holder", "code"] + (["day"] if has_day else []) + (
        ["first_day", "last_day"] if has_range else [])
    result = {}
    for row in conn.execute(f"SELECT {', '.join(wanted)} FROM tickets ORDER BY id").fetchall():
        first = row["first_day"] if has_range else None
        last = row["last_day"] if has_range else None
        if has_day and (first is None or last is None or first == last):
            days = (row["day"],)
        else:
            days = admitted_days(first, last)
        result[row["id"]] = (row["holder"], row["code"], days)
    return result


def differences(expected: dict, actual: dict, limit: int = 10) -> list[str]:
    """Human-readable differences, at most `limit` of them."""
    found = []
    for ticket_id in sorted(set(expected) | set(actual)):
        if ticket_id not in actual:
            found.append(f"ticket {ticket_id} {expected[ticket_id][:2]} is missing")
        elif ticket_id not in expected:
            found.append(f"ticket {ticket_id} {actual[ticket_id][:2]} was not expected")
        elif expected[ticket_id] != actual[ticket_id]:
            holder, code, days = expected[ticket_id]
            found.append(f"ticket {ticket_id} ({holder}, {code}): expected days {list(days)}, "
                         f"found {list(actual[ticket_id][2])}"
                         + ("" if actual[ticket_id][:2] == (holder, code) else f", found {actual[ticket_id][:2]}"))
    return found[:limit] + ([f"... and {len(found) - limit} more"] if len(found) > limit else [])


def save(m: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps({str(k): [v[0], v[1], list(v[2])] for k, v in m.items()}, indent=0))


def load(path: str | Path) -> dict:
    raw = json.loads(Path(path).read_text())
    return {int(k): (v[0], v[1], tuple(v[2])) for k, v in raw.items()}
