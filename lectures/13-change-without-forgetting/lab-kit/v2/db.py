"""Database access for AfterHours v2.

Every request opens its own SQLite connection and closes it when done.
Connections are never shared between threads.

v2 runs on two shapes of the tickets table:
  expanded    day + first_day + last_day   (during the migration window, next to v1)
  contracted  first_day + last_day         (after v1 is retired and `day` is dropped)
It refuses to start on the v1 shape (no first_day): run `python migrate.py expand` first.
"""

import os
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
DEFAULT_DB = "afterhours.db"

# The same synthetic festival as v1, so a fresh v2 database means the same thing.
SEED_EVENTS = [
    # (title, venue, starts_at, capacity, already_reserved)
    ("Escape Room: The Locked Lab", "Engineering Building, Room 2.14", "2026-10-09T20:00", 40, 39),
    ("Silent Disco on the Quad", "Main Quad", "2026-10-09T21:30", 150, 112),
    ("Board Game Night", "Student Union, Hall B", "2026-10-10T18:00", 60, 23),
    ("Maker Workshop: Solder Your Own Badge", "Makerspace", "2026-10-10T14:00", 12, 12),
    ("Open Mic", "Campus Cafe", "2026-10-11T19:00", 80, 41),
]

SEED_TICKETS = [
    ("Maya", "2026-10-09"),
    ("Sam", "2026-10-10"),
    ("Lee", "2026-10-11"),
    ("Ada", "2026-10-09"),
    ("Tom", "2026-10-10"),
]

SEED_FLAGS = [
    # (name, enabled, note, changed_at)
    ("wristband_mode", 0,
     "Festival 2025: the scanners failed on night one, so volunteers checked paper "
     "wristbands by eye and let every ticket in. Switched off after the festival.",
     "2025-10-11T09:12"),
]

DAY_CODES = {"2026-10-09": "FRI", "2026-10-10": "SAT", "2026-10-11": "SUN"}


class SchemaTooOld(RuntimeError):
    pass


def db_path() -> str:
    return os.environ.get("AFTERHOURS_DB", DEFAULT_DB)


def connect(path: str | None = None) -> sqlite3.Connection:
    """Open a fresh connection in autocommit mode (we write BEGIN ... COMMIT ourselves)."""
    conn = sqlite3.connect(path or db_path(), isolation_level=None, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def query_one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Run a query, return the first row, and release the statement immediately."""
    cur = conn.execute(sql, params)
    try:
        return cur.fetchone()
    finally:
        cur.close()


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def has_day_column(conn: sqlite3.Connection) -> bool:
    """True while the old column `day` still exists (from expand until contract)."""
    return "day" in columns(conn, "tickets")


def init_db(path: str | None = None, seed: bool = True) -> None:
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA.read_text())
        if not {"first_day", "last_day"} <= columns(conn, "tickets"):
            raise SchemaTooOld(
                "v2 needs the expanded tickets table (first_day, last_day). "
                "Run `python migrate.py expand` on this database first."
            )
        already_seeded = query_one(conn, "SELECT COUNT(*) AS n FROM events")["n"] > 0
        if seed and not already_seeded:
            _seed(conn)
    finally:
        conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    legacy = has_day_column(conn)
    conn.execute("BEGIN")
    for title, venue, starts_at, capacity, reserved in SEED_EVENTS:
        cur = conn.execute(
            "INSERT INTO events (title, venue, starts_at, capacity) VALUES (?, ?, ?, ?)",
            (title, venue, starts_at, capacity),
        )
        conn.executemany(
            "INSERT INTO reservations (event_id, attendee) VALUES (?, ?)",
            [(cur.lastrowid, f"guest-{i:03d}") for i in range(1, reserved + 1)],
        )
    for holder, day in SEED_TICKETS:
        if legacy:
            cur = conn.execute(
                "INSERT INTO tickets (holder, day, first_day, last_day, code) VALUES (?, ?, ?, ?, ?)",
                (holder, day, day, day, f"new-{holder}"),
            )
        else:
            cur = conn.execute(
                "INSERT INTO tickets (holder, first_day, last_day, code) VALUES (?, ?, ?, ?)",
                (holder, day, day, f"new-{holder}"),
            )
        conn.execute(
            "UPDATE tickets SET code = ? WHERE id = ?",
            (f"{DAY_CODES[day]}-{cur.lastrowid:04d}", cur.lastrowid),
        )
    conn.executemany(
        "INSERT OR IGNORE INTO flags (name, enabled, note, changed_at) VALUES (?, ?, ?, ?)", SEED_FLAGS
    )
    conn.execute("COMMIT")
