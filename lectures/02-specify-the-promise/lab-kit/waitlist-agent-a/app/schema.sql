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

CREATE TABLE IF NOT EXISTS waitlist (
    id         INTEGER PRIMARY KEY,
    event_id   INTEGER NOT NULL REFERENCES events(id),
    attendee   TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (event_id, attendee)
);
