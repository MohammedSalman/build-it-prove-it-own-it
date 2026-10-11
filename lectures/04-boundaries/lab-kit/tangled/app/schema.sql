CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY,
    title     TEXT    NOT NULL,
    venue     TEXT    NOT NULL,
    starts_at TEXT    NOT NULL,          -- ISO 8601, festival local time, e.g. 2026-10-09T20:00
    ends_at   TEXT    NOT NULL,          -- ISO 8601, festival local time (added for door check-in)
    capacity  INTEGER NOT NULL CHECK (capacity > 0)
);

CREATE TABLE IF NOT EXISTS reservations (
    id            INTEGER PRIMARY KEY,
    event_id      INTEGER NOT NULL REFERENCES events(id),
    attendee      TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    -- added for cancellation
    status        TEXT    NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
    cancelled_at  TEXT,                  -- festival local time
    -- added for door check-in
    checked_in_at TEXT                   -- festival local time
);
