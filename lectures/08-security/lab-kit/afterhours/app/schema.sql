CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    role          TEXT    NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'organiser')),
    password_hash TEXT                               -- NULL: this account cannot sign in
);

-- One row per signed-in browser. We keep only a hash of each token, so a copy of the
-- database is not a copy of everyone's sign-in.
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

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
    user_id    INTEGER NOT NULL REFERENCES users(id),   -- who owns this reservation
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
