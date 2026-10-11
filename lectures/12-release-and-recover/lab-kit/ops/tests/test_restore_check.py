"""The two application-level checks from ops/restore_check.py (Part A4).

Each test builds a tiny database in a temporary folder, with the same tables as
AfterHours, and runs your query on it. No server is needed.
"""

import sqlite3

import pytest

import restore_check

SCHEMA = """
CREATE TABLE events (id INTEGER PRIMARY KEY, title TEXT NOT NULL, venue TEXT NOT NULL,
                     starts_at TEXT NOT NULL, capacity INTEGER NOT NULL CHECK (capacity > 0));
CREATE TABLE reservations (id INTEGER PRIMARY KEY,
                           event_id INTEGER NOT NULL REFERENCES events(id),
                           attendee TEXT NOT NULL,
                           created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')));
INSERT INTO events VALUES (1, 'Open Mic', 'Cafe', '2026-10-11T19:00', 2);
INSERT INTO events VALUES (2, 'Board Games', 'Hall B', '2026-10-10T18:00', 3);
INSERT INTO events VALUES (3, 'Quiet Room', 'Library', '2026-10-10T10:00', 5);
INSERT INTO reservations (event_id, attendee) VALUES (1, 'Maya'), (1, 'Sam'), (2, 'Lee');
"""


@pytest.fixture
def conn(tmp_path):
    connection = sqlite3.connect(tmp_path / "t.db")
    connection.executescript(SCHEMA)
    yield connection
    connection.close()


def orphans(conn):
    return restore_check.find_problems(conn, restore_check.ORPHANS_SQL, "ORPHANS_SQL")


def over_capacity(conn):
    return restore_check.find_problems(conn, restore_check.OVER_CAPACITY_SQL, "OVER_CAPACITY_SQL")


def test_clean_data_has_no_orphans(conn):
    assert orphans(conn) == []


def test_a_reservation_for_a_missing_event_is_one_orphan(conn):
    conn.execute("INSERT INTO reservations (event_id, attendee) VALUES (99, 'ghost')")
    assert len(orphans(conn)) == 1


def test_a_deleted_event_leaves_orphans_behind(conn):
    conn.execute("DELETE FROM events WHERE id = 1")   # foreign keys are off by default
    assert len(orphans(conn)) == 2


def test_clean_data_has_no_event_over_capacity(conn):
    assert over_capacity(conn) == []


def test_a_full_event_is_not_over_capacity(conn):
    conn.execute("INSERT INTO reservations (event_id, attendee) VALUES (2, 'Ana'), (2, 'Bo')")
    assert over_capacity(conn) == []


def test_one_reservation_too_many_is_found(conn):
    conn.execute("INSERT INTO reservations (event_id, attendee) VALUES (1, 'Ana')")
    assert len(over_capacity(conn)) == 1


def test_every_event_over_capacity_is_listed_once(conn):
    conn.executemany("INSERT INTO reservations (event_id, attendee) VALUES (?, ?)",
                     [(1, "x1"), (1, "x2"), (2, "y1"), (2, "y2"), (2, "y3")])
    assert len(over_capacity(conn)) == 2
