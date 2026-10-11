"""Step 3 of 3: CONTRACT. Drop the old column `day` and make the new columns required.

SQLite cannot make an existing column NOT NULL, so the table is rebuilt: create the new
table, copy every row, drop the old table, rename the new one (the procedure in
SQLite's ALTER TABLE documentation). All of it happens in one transaction.

The guard runs INSIDE that transaction, after BEGIN IMMEDIATE has taken SQLite's write
lock. Checking first and rebuilding later would be check-then-act (Lecture 1): a v1
write could land in between and be lost.
"""

import sqlite3

from .steps import StepRefused, log, shape, steps_done, verify

# Must match the tickets table in v2/schema.sql exactly (a test checks this).
NEW_TICKETS = """
CREATE TABLE tickets_new (
    id         INTEGER PRIMARY KEY,
    holder     TEXT    NOT NULL,
    first_day  TEXT    NOT NULL,
    last_day   TEXT    NOT NULL,
    code       TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (first_day <= last_day)
)
"""


def problems(conn: sqlite3.Connection) -> list[str]:
    """Every reason the contract step must not run yet. Empty means go."""
    current = shape(conn)
    if current == "contracted":
        return ["already contracted: the tickets table has no `day` column"]
    if current == "v1":
        return ["expand has not run: this is still the v1 tickets table"]
    reasons = []
    if "retire-v1" not in steps_done(conn):
        reasons.append(
            "v1 is still live (no 'retire-v1' in migration_log). v1 reads and writes `day`; "
            "dropping it would break every v1 server"
        )
    counts = verify(conn)
    if counts["missing"]:
        reasons.append(f"{counts['missing']} tickets have no first_day/last_day: run the backfill")
    if counts["disagree"]:
        reasons.append(
            f"{counts['disagree']} day tickets disagree with `day` (moved by v1 after the "
            "backfill copied them): run the backfill"
        )
    if counts["backwards"]:
        reasons.append(f"{counts['backwards']} tickets end before they start")
    return reasons


def contract(conn: sqlite3.Connection) -> int:
    """Rebuild the tickets table without `day`. Returns the number of tickets copied.

    Raises StepRefused (and changes nothing) if any problem is found.
    """
    conn.execute("BEGIN IMMEDIATE")   # take the write lock BEFORE checking
    try:
        reasons = problems(conn)
        if reasons:
            raise StepRefused("contract", reasons)
        copied = _rebuild(conn)
        log(conn, "contract", f"dropped tickets.day; {copied} tickets copied")
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return copied


def _rebuild(conn: sqlite3.Connection) -> int:
    conn.execute(NEW_TICKETS)
    cur = conn.execute(
        """INSERT INTO tickets_new (id, holder, first_day, last_day, code, created_at)
           SELECT id, holder, first_day, last_day, code, created_at FROM tickets"""
    )
    copied = cur.rowcount
    conn.execute("DROP TABLE tickets")
    conn.execute("ALTER TABLE tickets_new RENAME TO tickets")
    return copied
