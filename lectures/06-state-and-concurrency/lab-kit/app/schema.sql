CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY,
    title     TEXT    NOT NULL,
    venue     TEXT    NOT NULL,
    starts_at TEXT    NOT NULL,          -- ISO 8601, festival local time
    capacity  INTEGER NOT NULL CHECK (capacity > 0)
);

-- A reservation is either confirmed or cancelled (see the state machine in reservations.py).
-- Cancelling keeps the row, so the history stays; only confirmed rows use up a place.
CREATE TABLE IF NOT EXISTS reservations (
    id           INTEGER PRIMARY KEY,
    event_id     INTEGER NOT NULL REFERENCES events(id),
    attendee     TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'confirmed'
                         CHECK (status IN ('confirmed', 'cancelled')),
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    cancelled_at TEXT,
    -- a cancelled reservation has a cancellation time, and a confirmed one has none
    CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL))
);

-- TODO (Lab 6, Task A2): one person may hold at most one ACTIVE (confirmed) place per event.
-- Add a partial unique index here. Cancelled rows must not count, so that someone who
-- cancels can book again.


-- Idempotency keys: the stored answer to each reservation attempt.
-- main.py already records refused attempts here; storing bookings is Lab 6, Task A3.
--   client_id     who is retrying: one browser or phone (sent as the Client-Id header)
--   key           one reservation attempt by that client (the Idempotency-Key header)
--   request_hash  a fingerprint of what the attempt asked for (event and attendee)
--   status_code   and response: 201 and the booking, or the refusal (refusals are not replayed)
CREATE TABLE IF NOT EXISTS idempotency_keys (
    client_id    TEXT    NOT NULL,
    key          TEXT    NOT NULL,
    request_hash TEXT    NOT NULL,
    status_code  INTEGER NOT NULL,
    response     TEXT    NOT NULL,
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (client_id, key)
);
