"""The schema-change procedure from docs/adr/0002: numbered migrations, applied at startup.

These tests use a temporary migrations folder, so they do not depend on which real
migrations exist in app/migrations/.
"""

import sqlite3

import pytest

from app import db


def columns(path, table="events"):
    conn = db.connect(str(path))
    try:
        return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
    finally:
        conn.close()


def every_row(path):
    """Every original field of every event and reservation, to compare before and after."""
    conn = db.connect(str(path))
    try:
        return (
            [tuple(r) for r in conn.execute(
                "SELECT id, title, venue, starts_at, capacity FROM events ORDER BY id")],
            [tuple(r) for r in conn.execute(
                "SELECT id, event_id, attendee, created_at FROM reservations ORDER BY id")],
        )
    finally:
        conn.close()


def applied(path):
    conn = db.connect(str(path))
    try:
        return [r[0] for r in conn.execute("SELECT name FROM schema_migrations ORDER BY name")]
    finally:
        conn.close()


def test_a_migration_reaches_a_database_that_already_exists(tmp_path, monkeypatch):
    folder = tmp_path / "migrations"
    folder.mkdir()
    monkeypatch.setattr(db, "MIGRATIONS", folder)
    database = tmp_path / "in-use.db"
    db.init_db(str(database))                      # the database the festival already has
    before = every_row(database)

    (folder / "0001-add-note.sql").write_text(
        "-- an expand step; this comment has a semicolon; it is ignored\n"
        "ALTER TABLE events ADD COLUMN note TEXT NOT NULL DEFAULT 'none; yet'; "
        "CREATE TABLE door_counts (event_id INTEGER, counted INTEGER);\n"
    )
    assert db.init_db(str(database)) == ["0001-add-note.sql"]   # the next start of the app

    assert "note" in columns(database)
    assert "event_id" in columns(database, "door_counts")      # two statements on one line
    assert every_row(database) == before                       # every original field unchanged
    assert db.init_db(str(database)) == []                     # applied once, never again


def test_a_bad_migration_changes_nothing(tmp_path, monkeypatch):
    folder = tmp_path / "migrations"
    folder.mkdir()
    monkeypatch.setattr(db, "MIGRATIONS", folder)
    database = tmp_path / "in-use.db"
    db.init_db(str(database))
    before = every_row(database)

    # 1. A statement fails: the whole batch is rolled back, including the good file.
    (folder / "0001-add-note.sql").write_text("ALTER TABLE events ADD COLUMN note TEXT;\n")
    (folder / "0002-broken.sql").write_text("ALTER TABLE no_such_table ADD COLUMN x TEXT;\n")
    with pytest.raises(sqlite3.OperationalError):
        db.init_db(str(database))
    assert "note" not in columns(database)
    assert applied(database) == []

    # 2. A file tries to commit on its own: refused before anything runs.
    (folder / "0002-broken.sql").write_text(
        "ALTER TABLE events ADD COLUMN x TEXT;\nCOMMIT;\nNOT VALID SQL;\n"
    )
    with pytest.raises(ValueError, match="COMMIT is not allowed"):
        db.init_db(str(database))
    assert "note" not in columns(database) and "x" not in columns(database)
    assert applied(database) == []
    assert every_row(database) == before


def test_a_badly_named_migration_stops_startup(tmp_path, monkeypatch):
    folder = tmp_path / "migrations"
    folder.mkdir()
    monkeypatch.setattr(db, "MIGRATIONS", folder)
    (folder / "add note.sql").write_text("ALTER TABLE events ADD COLUMN note TEXT;\n")
    with pytest.raises(ValueError, match="0001-add-thing.sql"):
        db.init_db(str(tmp_path / "x.db"))
