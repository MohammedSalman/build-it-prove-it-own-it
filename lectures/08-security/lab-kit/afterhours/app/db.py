"""Database access for AfterHours.

Every request opens its own SQLite connection and closes it when done.
Connections are never shared between threads.
"""

import os
import sqlite3
from pathlib import Path

from . import passwords

SCHEMA = Path(__file__).with_name("schema.sql")
DEFAULT_DB = "afterhours.db"

# Synthetic festival programme. The escape room starts with one place left.
SEED_EVENTS = [
    # (title, venue, starts_at, capacity, already_reserved)
    ("Escape Room: The Locked Lab", "Engineering Building, Room 2.14", "2026-10-09T20:00", 40, 39),
    ("Silent Disco on the Quad", "Main Quad", "2026-10-09T21:30", 150, 112),
    ("Board Game Night", "Student Union, Hall B", "2026-10-10T18:00", 60, 23),
    ("Maker Workshop: Solder Your Own Badge", "Makerspace", "2026-10-10T14:00", 12, 12),
    ("Open Mic", "Campus Cafe", "2026-10-11T19:00", 80, 41),
]

# Demo accounts for a local teaching app, so you can play every part in the lab.
# Real passwords are chosen by their owners and never appear in code.
DEMO_ACCOUNTS = [
    # (name, role, demo password)
    ("Maya", "student", "copper-kettle"),
    ("Sam", "student", "violet-harbour"),
    ("Lee", "student", "quiet-lantern"),
    ("Olu", "organiser", "north-gate"),
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
    for name, role, password in DEMO_ACCOUNTS:
        conn.execute(
            "INSERT INTO users (name, role, password_hash) VALUES (?, ?, ?)",
            (name, role, passwords.hash_password(password)),
        )
    for title, venue, starts_at, capacity, reserved in SEED_EVENTS:
        cur = conn.execute(
            "INSERT INTO events (title, venue, starts_at, capacity) VALUES (?, ?, ?, ?)",
            (title, venue, starts_at, capacity),
        )
        for i in range(1, reserved + 1):
            # Earlier bookings, made by guests who cannot sign in to this demo.
            conn.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (f"guest-{i:03d}",))
            guest = query_one(conn, "SELECT id FROM users WHERE name = ?", (f"guest-{i:03d}",))
            conn.execute(
                "INSERT INTO reservations (event_id, user_id) VALUES (?, ?)", (cur.lastrowid, guest["id"])
            )
    conn.execute("COMMIT")
