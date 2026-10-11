"""Database access for AfterHours.

Every request opens its own SQLite connection and closes it when done.
Connections are never shared between threads.

The schema has two parts (see docs/adr/0002-schema-changes-are-numbered-migrations.md):

  schema.sql        the baseline tables. Never edit it: CREATE TABLE IF NOT EXISTS
                    skips tables that already exist, so a changed table here never
                    reaches a database that is already in use.
  migrations/*.sql  every change since the baseline, applied in name order at startup,
                    all in one transaction, and recorded in the schema_migrations table.

Fresh databases (every test run) and existing ones go through the same migrations, so the
test suite exercises every migration on every run.
"""

import os
import re
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
MIGRATIONS = Path(__file__).with_name("migrations")
MIGRATION_NAME = re.compile(r"^\d{4}-[a-z0-9-]+\.sql$")
DEFAULT_DB = "afterhours.db"

# Synthetic festival programme. The escape room starts with one place left,
# which is what Lecture 1 is about.
SEED_EVENTS = [
    # (title, venue, starts_at, capacity, already_reserved)
    ("Escape Room: The Locked Lab", "Engineering Building, Room 2.14", "2026-10-09T20:00", 40, 39),
    ("Silent Disco on the Quad", "Main Quad", "2026-10-09T21:30", 150, 112),
    ("Board Game Night", "Student Union, Hall B", "2026-10-10T18:00", 60, 23),
    ("Maker Workshop: Solder Your Own Badge", "Makerspace", "2026-10-10T14:00", 12, 12),
    ("Open Mic", "Campus Cafe", "2026-10-11T19:00", 80, 41),
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


def init_db(path: str | None = None, seed: bool = True) -> list[str]:
    """Create the baseline tables, apply pending migrations, and seed an empty database.

    Returns the names of the migrations applied by this call (empty if none were pending).
    """
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA.read_text())
        applied = apply_migrations(conn)
        already_seeded = query_one(conn, "SELECT COUNT(*) AS n FROM events")["n"] > 0
        if seed and not already_seeded:
            _seed(conn)
        return applied
    finally:
        conn.close()


def migration_files(folder: Path | None = None) -> list[Path]:
    """The migration files, in the order they are applied (by name)."""
    folder = folder or MIGRATIONS
    files = sorted(p for p in folder.glob("*.sql"))
    for p in files:
        if not MIGRATION_NAME.match(p.name):
            raise ValueError(f"migration file name must look like 0001-add-thing.sql: {p.name}")
    return files


def apply_migrations(conn: sqlite3.Connection, folder: Path | None = None) -> list[str]:
    """Apply every migration not yet recorded in schema_migrations.

    All pending migrations run in one transaction under SQLite's write lock: either all of
    them are applied and recorded, or none is. Two processes starting at once cannot both
    apply the same migration, because the list of applied ones is read inside the lock.
    The runner owns that transaction, so a migration file may not contain BEGIN, COMMIT,
    ROLLBACK, SAVEPOINT or similar statements; every file is checked before anything runs.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))"
    )
    files = migration_files(folder)
    if not files:
        return []
    parsed = [(path, list(_statements(path.read_text(), path.name))) for path in files]
    applied_now = []
    conn.execute("BEGIN IMMEDIATE")
    try:
        done = {row["name"] for row in conn.execute("SELECT name FROM schema_migrations")}
        for path, statements in parsed:
            if path.name in done:
                continue
            for statement in statements:
                conn.execute(statement)
                if not conn.in_transaction:  # second line of defence; the check above should stop this
                    raise RuntimeError(f"{path.name} ended the migration transaction")
            conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (path.name,))
            applied_now.append(path.name)
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return applied_now


TRANSACTION_CONTROL = {"BEGIN", "COMMIT", "END", "ROLLBACK", "SAVEPOINT", "RELEASE",
                       "VACUUM", "ATTACH", "DETACH"}


def _without_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return re.sub(r"--[^\n]*", " ", sql)


def _statements(sql: str, name: str = "migration"):
    """Split a migration into complete SQL statements, and refuse transaction control.

    A statement ends at a semicolon that SQLite itself says completes it, so several
    statements may share a line, and semicolons inside strings or comments are fine.
    """
    statements, buffer = [], ""
    for piece in re.split(r"(;)", sql):
        buffer += piece
        if piece == ";" and sqlite3.complete_statement(buffer):
            if _without_comments(buffer).strip(" \t\r\n;"):
                statements.append(buffer.strip())
            buffer = ""
    if _without_comments(buffer).strip():
        raise ValueError(f"{name} ends with an incomplete statement (missing ';'?): {buffer.strip()[:60]!r}")
    for statement in statements:
        words = _without_comments(statement).split()
        first = words[0].rstrip(";").upper() if words else ""
        if first in TRANSACTION_CONTROL:
            raise ValueError(f"{name}: {first} is not allowed in a migration; "
                             "the app runs all pending migrations in one transaction itself")
    return statements


def _seed(conn: sqlite3.Connection) -> None:
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
    conn.execute("COMMIT")
