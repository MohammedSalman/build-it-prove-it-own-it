"""Helpers for the tests.

Databases in three shapes
    build_database(path, shape) makes a fresh, seeded database in one of the shapes the
    migration passes through:
        "old"         a v1 database as it is today            (tickets.day)
        "expanded"    the same after migrations/expand.sql    (day + first_day + last_day;
                                                               the new columns still NULL)
        "contracted"  a fresh v2 database: the final shape    (first_day + last_day)

Apps
    app_client("v1" or "v2", clock) returns a TestClient for that version on the database
    named by AFTERHOURS_DB. Use it in a `with` block.

People acting at the same time (from Week 1)
    hold_everyone_at_payment(monkeypatch, payments_module)
        Makes each request wait at the payment step until the others arrive, so that
        everybody checks the count before anybody saves.
    at_the_same_time(action, names)
        Runs action(name) for every name, all starting together, and returns what
        happened to each person: the value action returned, or the exception it raised.
"""

import importlib
import sqlite3
import threading

from fastapi.testclient import TestClient

from migrations import steps

# The seed tickets, the same in every shape: holder -> (id, code, day)
SEED = {
    "Maya": (1, "FRI-0001", "2026-10-09"),
    "Sam": (2, "SAT-0002", "2026-10-10"),
    "Lee": (3, "SUN-0003", "2026-10-11"),
    "Ada": (4, "FRI-0004", "2026-10-09"),
    "Tom": (5, "SAT-0005", "2026-10-10"),
}
FRI, SAT, SUN = "2026-10-09", "2026-10-10", "2026-10-11"


def build_database(path, shape: str) -> str:
    path = str(path)
    if shape == "contracted":
        from v2 import db as v2_db
        v2_db.init_db(path)
        return path
    from v1 import db as v1_db
    v1_db.init_db(path)
    if shape == "expanded":
        conn = steps.connect(path)
        try:
            steps.expand(conn)
        finally:
            conn.close()
    elif shape != "old":
        raise ValueError(shape)
    return path


def use_database(tmp_path, monkeypatch, shape: str) -> str:
    """Build a database for this test and point both apps at it."""
    path = build_database(tmp_path / "afterhours.db", shape)
    monkeypatch.setenv("AFTERHOURS_DB", path)
    monkeypatch.setenv("AFTERHOURS_PAYMENT_DELAY", "0")
    return path


def app_client(version: str, clock, raise_server_exceptions: bool = True) -> TestClient:
    module = importlib.import_module(f"{version}.main")
    return TestClient(module.create_app(clock=clock), raise_server_exceptions=raise_server_exceptions)


def switch_flag(db_path: str, name: str, on: bool) -> None:
    """Flip a flag directly in the database (no guard): what a hurried admin might do."""
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        conn.execute(
            """INSERT INTO flags (name, enabled, changed_at) VALUES (?, ?, '2026-10-01T12:00')
               ON CONFLICT (name) DO UPDATE SET enabled = excluded.enabled""",
            (name, 1 if on else 0),
        )
    finally:
        conn.close()


def run_sql(db_path: str, *statements: str) -> None:
    """Change the database behind the apps' backs, as another version would."""
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        for sql in statements:
            conn.execute(sql)
    finally:
        conn.close()


def ticket_row(db_path: str, ticket_id: int) -> dict:
    conn = steps.connect(db_path)
    try:
        return dict(conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())
    finally:
        conn.close()


def hold_everyone_at_payment(monkeypatch, payments_module, people: int = 2, timeout: float = 2.0) -> None:
    gate = threading.Barrier(people)

    def authorize(attendee: str) -> None:
        try:
            gate.wait(timeout=timeout)
        except threading.BrokenBarrierError:
            pass  # the others could not get here (for example, they are waiting for a lock)

    monkeypatch.setattr(payments_module, "authorize", authorize)


def at_the_same_time(action, names: list[str]) -> dict:
    start_line = threading.Barrier(len(names))
    outcomes = {}

    def run(name):
        start_line.wait()
        try:
            outcomes[name] = action(name)
        except Exception as exc:
            outcomes[name] = exc

    threads = [threading.Thread(target=run, args=(name,)) for name in names]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return {name: outcomes.get(name, TimeoutError("no answer within 30 s")) for name in names}
