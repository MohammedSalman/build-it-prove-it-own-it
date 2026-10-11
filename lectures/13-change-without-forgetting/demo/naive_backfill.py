"""A NAIVE backfill, for the in-class demonstration only (authored for the lecture).

It fills only rows with no first_day yet. It looks right, is safe to run again, and
passes a quick check on a quiet database. It misses a ticket that v1 moved after an
earlier run had already copied it (rule B4), so the new columns keep the old day.

    python scripts/rehearse.py --backfill ../demo/naive_backfill.py:backfill
    python scripts/rehearse.py --backfill ../demo/naive_backfill.py:backfill --skip-guard
"""

import sqlite3
from dataclasses import dataclass


@dataclass
class BackfillReport:
    rows: int = 0
    batches: int = 0


def backfill(conn: sqlite3.Connection, batch_size: int = 200) -> BackfillReport:
    report = BackfillReport()
    while True:
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(
                """UPDATE tickets SET first_day = day, last_day = day
                   WHERE id IN (SELECT id FROM tickets WHERE first_day IS NULL ORDER BY id LIMIT ?)""",
                (batch_size,),
            )
            changed = cur.rowcount
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        if changed == 0:
            return report
        report.rows += changed
        report.batches += 1
