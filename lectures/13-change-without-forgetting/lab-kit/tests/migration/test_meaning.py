"""migrations/meaning.py: read what tickets mean from any shape of the table."""

import hashlib

import pytest

from migrations import steps
from migrations.contract import contract
from migrations.meaning import meaning

from ..helpers import FRI, SAT, SUN, build_database, run_sql


def meaning_of(path):
    conn = steps.connect(path)
    try:
        return meaning(conn)
    finally:
        conn.close()


def checksum_of_rows(path):
    conn = steps.connect(path)
    try:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
        return hashlib.sha256(repr([tuple(r) for r in rows]).encode()).hexdigest()
    finally:
        conn.close()


@pytest.mark.parametrize("shape", ["old", "expanded", "contracted"])
def test_the_seed_tickets_mean_the_same_in_every_shape(tmp_path, shape):
    m = meaning_of(build_database(tmp_path / "m.db", shape))
    assert m[1] == ("Maya", "FRI-0001", (FRI,))
    assert m[3] == ("Lee", "SUN-0003", (SUN,))
    assert len(m) == 5


def test_while_day_exists_it_decides_what_a_day_ticket_means(tmp_path):
    path = build_database(tmp_path / "m.db", "expanded")
    run_sql(path, "UPDATE tickets SET first_day = day, last_day = day",
            "UPDATE tickets SET day = '2026-10-10' WHERE id = 1")      # v1 moved Maya after the copy
    assert meaning_of(path)[1] == ("Maya", "FRI-0001", (SAT,))


def test_a_pass_means_every_day_in_its_range(tmp_path):
    path = build_database(tmp_path / "m.db", "expanded")
    run_sql(path, "INSERT INTO tickets (holder, day, first_day, last_day, code) "
                  "VALUES ('Mei', '2026-10-09', '2026-10-09', '2026-10-11', 'PASS-0006')")
    assert meaning_of(path)[6] == ("Mei", "PASS-0006", (FRI, SAT, SUN))


def test_a_checksum_of_the_rows_changes_even_when_the_meaning_does_not(tmp_path):
    path = build_database(tmp_path / "m.db", "expanded")
    before_meaning, before_sum = meaning_of(path), checksum_of_rows(path)
    run_sql(path, "UPDATE tickets SET first_day = day, last_day = day")
    conn = steps.connect(path)
    steps.retire(conn, "v1")
    contract(conn)
    conn.close()
    assert checksum_of_rows(path) != before_sum     # different columns, different bytes
    assert meaning_of(path) == before_meaning       # same people, same days
