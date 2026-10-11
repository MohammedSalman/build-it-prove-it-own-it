"""Step 2 of 3: MIGRATE. Copy `day` into first_day and last_day. (Lab 13, part A3.)

The backfill runs while v1 and v2 are both live and writing. The rules
(docs/migration-plan.md, "The backfill"):

  B1  Afterwards every day ticket has first_day = last_day = day.
  B2  Festival passes (first_day < last_day) are v2's own rows. Never touch them.
  B3  Safe to run again: a second run right after the first changes nothing (rows == 0).
  B4  Catches up: a day ticket that v1 moved AFTER an earlier run (day changed, new
      columns stale) is fixed by the next run.
  B5  Small transactions: at most `batch_size` rows per transaction. SQLite has one write
      lock for the whole database, and sales and day changes wait for it while a
      transaction holds it (Lecture 1, Patch C). Scans only read, and carry on.
  B6  Copy inside the database (UPDATE ... SET first_day = day ...). Reading `day` into
      Python and writing it back later leaves a gap in which v1 can move the ticket.

The verification queries in migrations/steps.py (CHECKS) count exactly the rows this
function must fix. Run `python -m pytest -q tests/migration/test_backfill.py`.
"""

import sqlite3
from dataclasses import dataclass


@dataclass
class BackfillReport:
    rows: int = 0       # rows changed, in total
    batches: int = 0    # transactions that changed at least one row


def backfill(conn: sqlite3.Connection, batch_size: int = 200) -> BackfillReport:
    """Bring first_day and last_day in line with `day` for every day ticket that needs it."""
    report = BackfillReport()

    # TODO 1: Write the condition "this row needs the backfill" as SQL (B1, B2, B4).
    #         Hint: look at the "missing" and "disagree" checks in migrations/steps.py.
    #
    # TODO 2: Loop. In each pass: BEGIN IMMEDIATE, ONE UPDATE that changes at most
    #         batch_size rows that need it, COMMIT (B5, B6). SQLite's UPDATE has no LIMIT,
    #         so pick the ids in a subquery:
    #             UPDATE tickets SET ... WHERE id IN (SELECT id FROM tickets WHERE ... LIMIT ?)
    #         The cursor's .rowcount says how many rows the UPDATE changed.
    #         Stop when a pass changes nothing. Roll back if anything raises.
    #
    # TODO 3: Count rows and batches in `report` (B3: a second run returns rows == 0).

    raise NotImplementedError("Lab 13, part A3: complete the backfill in migrations/backfill.py")
