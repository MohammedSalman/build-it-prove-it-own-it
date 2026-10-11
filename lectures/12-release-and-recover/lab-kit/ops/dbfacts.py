"""Facts about a database file: what is in it, and a canonical logical dump of it.

A canonical logical dump is the database's schema and every row of every table, as
text, in a fixed order. Two databases with the same logical content give exactly the
same dump, whatever their file size, page layout or journal mode. Comparing dumps
answers "is this the same data?"; comparing file bytes does not.
"""

import hashlib
import json
import sqlite3
from pathlib import Path


def _open(path: Path) -> sqlite3.Connection:
    if not Path(path).exists():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _cell(value):
    return {"hex": value.hex()} if isinstance(value, bytes) else value


def canonical_dump(path: Path) -> str:
    conn = _open(path)
    try:
        lines = []
        objects = conn.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name").fetchall()
        for row in objects:
            # The CREATE statement exactly as SQLite stores it (json.dumps keeps it on one
            # line). Normalising whitespace here would also change string literals inside it.
            lines.append(f"{row['type']} {row['name']}: {json.dumps(row['sql'])}")
        for row in objects:
            if row["type"] != "table":
                continue
            name = row["name"]
            columns = [c["name"] for c in conn.execute(f'PRAGMA table_info("{name}")')]
            order = ", ".join(str(i + 1) for i in range(len(columns)))
            lines.append(f"rows {name} ({', '.join(columns)})")
            for values in conn.execute(f'SELECT * FROM "{name}" ORDER BY {order}'):
                lines.append(json.dumps([_cell(v) for v in values], ensure_ascii=True))
        return "".join(line + "\n" for line in lines)
    finally:
        conn.close()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def describe(path: Path) -> dict:
    """Row counts and the newest reservation, for the tables AfterHours has."""
    conn = _open(path)
    try:
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        facts = {"tables": len(tables), "events": 0, "reservations": 0, "newest_reservation": None}
        if "events" in tables:
            facts["events"] = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if "reservations" in tables:
            count, newest = conn.execute(
                "SELECT COUNT(*), MAX(created_at) FROM reservations").fetchone()
            facts["reservations"], facts["newest_reservation"] = count, newest
        return facts
    finally:
        conn.close()


def integrity(path: Path) -> str:
    conn = _open(path)
    try:
        return "; ".join(r[0] for r in conn.execute("PRAGMA integrity_check"))
    finally:
        conn.close()
