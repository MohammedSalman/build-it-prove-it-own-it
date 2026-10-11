CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    title       TEXT    NOT NULL,
    venue       TEXT    NOT NULL,
    starts_at   TEXT    NOT NULL,          -- ISO 8601, festival local time
    ends_at     TEXT    NOT NULL,          -- ISO 8601, festival local time
    capacity    INTEGER NOT NULL CHECK (capacity > 0),
    -- A stored counter, so the programme page and the door tablet read one number
    -- instead of counting rows. reserve() and cancel() keep it up to date.
    places_left INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id            INTEGER PRIMARY KEY,
    event_id      INTEGER NOT NULL REFERENCES events(id),
    attendee      TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
    checked_in_at TEXT,                    -- festival local time; NULL until checked in at the door
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
