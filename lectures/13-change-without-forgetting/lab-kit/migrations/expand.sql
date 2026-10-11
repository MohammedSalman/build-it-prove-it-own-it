-- Step 1 of 3: EXPAND.
--
-- Add the new columns next to the old one. Nothing is removed or renamed, so v1 keeps
-- working: it never names first_day or last_day, and its INSERTs leave them NULL.
-- v2 can start once this has run.
--
-- Run it with `python migrate.py expand` (which refuses to run it twice).

BEGIN IMMEDIATE;

ALTER TABLE tickets ADD COLUMN first_day TEXT;   -- NULL until v2 or the backfill fills it
ALTER TABLE tickets ADD COLUMN last_day  TEXT;

-- The migration's own record: which steps ran, and when.
CREATE TABLE IF NOT EXISTS migration_log (
    id      INTEGER PRIMARY KEY,
    step    TEXT NOT NULL,             -- expand · backfill · retire-v1 · contract
    note    TEXT NOT NULL DEFAULT '',
    done_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Passes go on sale later, with this flag (see docs/migration-plan.md, step 5).
INSERT OR IGNORE INTO flags (name, enabled, note, changed_at)
VALUES ('multi_day_passes', 0, 'Sell multi-day festival passes (v2 only). Remove once passes are permanent.',
        strftime('%Y-%m-%dT%H:%M', 'now'));

INSERT INTO migration_log (step, note) VALUES ('expand', 'added tickets.first_day, tickets.last_day');

COMMIT;
