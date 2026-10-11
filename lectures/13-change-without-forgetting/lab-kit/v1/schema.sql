-- AfterHours v1 schema. Tickets are for one festival day each.

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
    day        TEXT    NOT NULL,         -- the festival day it is for, e.g. 2026-10-09
    code       TEXT    NOT NULL UNIQUE,  -- printed on the wristband and scanned at the gate
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS flags (
    name       TEXT    PRIMARY KEY,
    enabled    INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    note       TEXT    NOT NULL DEFAULT '',
    changed_at TEXT    NOT NULL
);
