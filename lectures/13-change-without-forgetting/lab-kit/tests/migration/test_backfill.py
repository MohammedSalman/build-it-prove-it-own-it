"""Step 2, the backfill: rules B1 to B5 from migrations/backfill.py (Lab 13, part A3).

Each test builds an expanded database and writes rows the way v1 and v2 do, then runs
YOUR backfill. They all fail on the kit (NotImplementedError) until you complete it.
"""

import pytest

from migrations import steps
from migrations.backfill import backfill

from ..helpers import FRI, SAT, SUN, build_database


@pytest.fixture
def conn(tmp_path):
    c = steps.connect(build_database(tmp_path / "m.db", "expanded"))   # 5 v1 tickets, new columns NULL
    yield c
    c.close()


def v1_sells(conn, holder, day) -> int:
    """What v1 writes: only `day`."""
    cur = conn.execute("INSERT INTO tickets (holder, day, code) VALUES (?, ?, ?)", (holder, day, f"v1-{holder}"))
    return cur.lastrowid


def v1_moves(conn, ticket_id, day) -> None:
    conn.execute("UPDATE tickets SET day = ? WHERE id = ?", (day, ticket_id))


def v2_sells_pass(conn, holder, first, last) -> int:
    """What v2 writes for a pass: day = first_day."""
    cur = conn.execute("INSERT INTO tickets (holder, day, first_day, last_day, code) VALUES (?, ?, ?, ?, ?)",
                       (holder, first, first, last, f"pass-{holder}"))
    return cur.lastrowid


def days(conn, ticket_id):
    row = conn.execute("SELECT day, first_day, last_day FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return tuple(row)


def test_b1_every_day_ticket_ends_with_its_day_in_both_new_columns(conn):
    report = backfill(conn)
    assert report.rows == 5
    for day, first, last in conn.execute("SELECT day, first_day, last_day FROM tickets"):
        assert first == last == day
    assert steps.verify(conn) == {"missing": 0, "disagree": 0, "backwards": 0}


def test_b2_a_pass_is_left_alone(conn):
    mei = v2_sells_pass(conn, "Mei", FRI, SUN)
    backfill(conn)
    assert days(conn, mei) == (FRI, FRI, SUN)


def test_b3_a_second_run_changes_nothing(conn):
    backfill(conn)
    again = backfill(conn)
    assert (again.rows, again.batches) == (0, 0)


def test_b4_catches_up_with_a_ticket_v1_moved_after_an_earlier_run(conn):
    backfill(conn)
    v1_moves(conn, 1, SAT)                  # Maya: Friday -> Saturday, through a v1 server
    assert days(conn, 1) == (SAT, FRI, FRI)   # the new columns are stale now
    report = backfill(conn)
    assert report.rows == 1
    assert days(conn, 1) == (SAT, SAT, SAT)


def test_b4_catches_up_with_tickets_v1_sold_after_an_earlier_run(conn):
    backfill(conn)
    noor = v1_sells(conn, "Noor", SUN)
    assert backfill(conn).rows == 1
    assert days(conn, noor) == (SUN, SUN, SUN)


def test_b5_no_transaction_changes_more_than_batch_size_rows(conn):
    for i in range(445):
        v1_sells(conn, f"guest-{i}", FRI)           # 5 + 445 = 450 rows to fill
    changes_at_commit = []
    conn.set_trace_callback(
        lambda sql: changes_at_commit.append(conn.total_changes) if sql.strip().upper().startswith(("COMMIT", "END")) else None
    )
    start = conn.total_changes
    report = backfill(conn, batch_size=200)
    conn.set_trace_callback(None)
    per_transaction = [b - a for a, b in zip([start] + changes_at_commit, changes_at_commit)]
    assert sum(per_transaction) == 450
    assert max(per_transaction) <= 200, per_transaction
    assert (report.rows, report.batches) == (450, 3)
