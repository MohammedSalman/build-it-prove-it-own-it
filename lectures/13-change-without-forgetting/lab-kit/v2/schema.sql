-- AfterHours v2 schema, for a NEW database only.
--
-- An existing v1 database gets the ticket columns through the migration instead
-- (migrations/expand.sql, then the backfill, then migrations/contract.py). After the
-- contract step, a migrated database has exactly this shape. A test checks that.
-- On an existing database every statement below is a no-op (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY,
    title     TEXT    NOT NULL,
    venue     TEXT    NOT NULL,
    starts_at TEXT    NOT NULL,          -- ISO 8601, festival local time
    capacity  INTEGER NOT NULL CHECK (capacity > 0)
);

CREATE TABLE IF NOT EXISTS reservations (
    id         INTEGER PRIMARY KEY,
    event_id   INTEGER NOT NULL REFERENCES events(id),
    attendee   TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id         INTEGER PRIMARY KEY,
    holder     TEXT    NOT NULL,
    first_day  TEXT    NOT NULL,         -- the first festival day it admits on
    last_day   TEXT    NOT NULL,         -- the last one; equal to first_day for a day ticket
    code       TEXT    NOT NULL UNIQUE,  -- printed on the wristband and scanned at the gate
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (first_day <= last_day)
);

CREATE TABLE IF NOT EXISTS flags (
    name       TEXT    PRIMARY KEY,
    enabled    INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    note       TEXT    NOT NULL DEFAULT '',
    changed_at TEXT    NOT NULL
);
