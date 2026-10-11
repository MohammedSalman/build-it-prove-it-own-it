"""Shared pieces of the migration: connections, the log, the checks, and two guards.

The migration code never imports v1 or v2. It talks to the database only, the way a
migration run by the release steward would.
"""

import os
import sqlite3
from pathlib import Path

EXPAND_SQL = Path(__file__).with_name("expand.sql")


class StepRefused(Exception):
    """A step's preconditions do not hold. Nothing was changed."""

    def __init__(self, step: str, reasons: list[str]):
        self.step = step
        self.reasons = reasons
        super().__init__(f"{step} refused: " + "; ".join(reasons))


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or os.environ.get("AFTERHOURS_DB", "afterhours.db"),
                           isolation_level=None, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def shape(conn: sqlite3.Connection) -> str:
    """Which shape the tickets table has: 'v1', 'expanded' or 'contracted'."""
    cols = columns(conn, "tickets")
    if not cols:
        raise StepRefused("read", ["this database has no tickets table"])
    has_day, has_range = "day" in cols, {"first_day", "last_day"} <= cols
    if has_day and has_range:
        return "expanded"
    if has_range:
        return "contracted"
    return "v1"


def steps_done(conn: sqlite3.Connection) -> list[str]:
    if not columns(conn, "migration_log"):
        return []
    return [row["step"] for row in conn.execute("SELECT step FROM migration_log ORDER BY id")]


def log(conn: sqlite3.Connection, step: str, note: str = "") -> None:
    conn.execute("INSERT INTO migration_log (step, note) VALUES (?, ?)", (step, note))


# The verification queries. Each counts rows that would be wrong after the contract step.
# They only make sense on the expanded shape, while `day` and the new columns both exist.
CHECKS = {
    "missing": (
        "tickets with no first_day or last_day (written by v1, or not backfilled yet)",
        "SELECT COUNT(*) AS n FROM tickets WHERE first_day IS NULL OR last_day IS NULL",
    ),
    "disagree": (
        "day tickets whose new columns disagree with `day` (moved by v1 after being copied)",
        "SELECT COUNT(*) AS n FROM tickets WHERE first_day = last_day AND first_day <> day",
    ),
    "backwards": (
        "tickets whose last_day comes before first_day",
        "SELECT COUNT(*) AS n FROM tickets WHERE first_day > last_day",
    ),
}


def count(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    """Run a COUNT(*) AS n query and release the statement at once."""
    cur = conn.execute(sql, params)
    try:
        return cur.fetchone()["n"]
    finally:
        cur.close()


def verify(conn: sqlite3.Connection) -> dict[str, int]:
    """Run the verification queries. All zeros means the new columns can take over."""
    if shape(conn) != "expanded":
        raise StepRefused("verify", [f"the tickets table is in the {shape(conn)} shape, not expanded"])
    return {name: count(conn, sql) for name, (_, sql) in CHECKS.items()}


def expand(conn: sqlite3.Connection) -> None:
    """Step 1: add first_day and last_day next to day."""
    current = shape(conn)
    if current != "v1":
        raise StepRefused("expand", [f"the tickets table is already {current}"])
    conn.executescript(EXPAND_SQL.read_text())


def retire(conn: sqlite3.Connection, version: str) -> None:
    """Record that every server running `version` has been stopped.

    This is a record, not a check: the release steward stops the v1 servers first,
    then runs this. The contract step trusts it.
    """
    if version != "v1":
        raise StepRefused("retire", ["only v1 can be retired in this migration"])
    done = steps_done(conn)
    if "expand" not in done:
        raise StepRefused("retire", ["expand has not run: v1 is the only version there is"])
    if "retire-v1" in done:
        raise StepRefused("retire", ["v1 is already recorded as retired"])
    log(conn, "retire-v1", "every v1 server stopped")


# A flag that must not go on before a step has run, and why.
FLAG_NEEDS = {
    "multi_day_passes": (
        "retire-v1",
        "v1 is still live, and v1 reads only `day`: it would let a pass holder in on the "
        "pass's first day and turn them away on the others",
    ),
}


def set_flag(conn: sqlite3.Connection, name: str, on: bool) -> None:
    if on and name in FLAG_NEEDS:
        needed, why = FLAG_NEEDS[name]
        # A contracted table has no `day`, so no v1 can be running on it (a fresh v2 install).
        if needed not in steps_done(conn) and shape(conn) != "contracted":
            raise StepRefused(f"flag {name} on", [why])
    conn.execute(
        """INSERT INTO flags (name, enabled, changed_at)
           VALUES (?, ?, strftime('%Y-%m-%dT%H:%M', 'now'))
           ON CONFLICT (name) DO UPDATE SET enabled = excluded.enabled, changed_at = excluded.changed_at""",
        (name, 1 if on else 0),
    )


def status(conn: sqlite3.Connection) -> dict:
    current = shape(conn)
    info = {
        "shape": current,
        "tickets": count(conn, "SELECT COUNT(*) AS n FROM tickets"),
        "steps": [dict(r) for r in conn.execute("SELECT step, done_at FROM migration_log ORDER BY id")]
        if columns(conn, "migration_log") else [],
        "flags": {r["name"]: bool(r["enabled"]) for r in conn.execute("SELECT name, enabled FROM flags")},
    }
    if current == "expanded":
        info["checks"] = verify(conn)
    return info
