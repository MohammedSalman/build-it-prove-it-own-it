"""Database access for AfterHours.

Every request opens its own SQLite connection and closes it when done.
Connections are never shared between threads.
"""

import os
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
DEFAULT_DB = "afterhours.db"

# Synthetic festival programme (festival local time).
SEED_EVENTS = [
    # (title, venue, starts_at, ends_at, capacity, confirmed, cancelled)
    ("Escape Room: The Locked Lab", "Engineering Building, Room 2.14",
     "2026-10-09T20:00", "2026-10-09T21:30", 40, 39, 0),
    ("Silent Disco on the Quad", "Main Quad",
     "2026-10-09T21:30", "2026-10-09T23:30", 150, 112, 4),
    ("Board Game Night", "Student Union, Hall B",
     "2026-10-10T18:00", "2026-10-10T22:00", 60, 23, 2),
    ("Maker Workshop: Solder Your Own Badge", "Makerspace",
     "2026-10-10T14:00", "2026-10-10T16:00", 12, 12, 1),
    ("Open Mic", "Campus Cafe",
     "2026-10-11T19:00", "2026-10-11T21:00", 80, 41, 0),
]


def db_path() -> str:
    return os.environ.get("AFTERHOURS_DB", DEFAULT_DB)


def connect(path: str | None = None) -> sqlite3.Connection:
    """Open a fresh connection in autocommit mode.

    isolation_level=None means Python does not open transactions for us:
    every statement commits on its own unless we write BEGIN ... COMMIT.
    """
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


def init_db(path: str | None = None, seed: bool = True) -> None:
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA.read_text())
        already_seeded = query_one(conn, "SELECT COUNT(*) AS n FROM events")["n"] > 0
        if seed and not already_seeded:
            _seed(conn)
    finally:
        conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    conn.execute("BEGIN")
    for title, venue, starts_at, ends_at, capacity, confirmed, cancelled in SEED_EVENTS:
        cur = conn.execute(
            "INSERT INTO events (title, venue, starts_at, ends_at, capacity) VALUES (?, ?, ?, ?, ?)",
            (title, venue, starts_at, ends_at, capacity),
        )
        conn.executemany(
            "INSERT INTO reservations (event_id, attendee) VALUES (?, ?)",
            [(cur.lastrowid, f"guest-{i:03d}") for i in range(1, confirmed + 1)],
        )
        conn.executemany(
            "INSERT INTO reservations (event_id, attendee, status, cancelled_at)"
            " VALUES (?, ?, 'cancelled', '2026-10-01T10:00:00')",
            [(cur.lastrowid, f"guest-x{i:02d}") for i in range(1, cancelled + 1)],
        )
    conn.execute("COMMIT")
