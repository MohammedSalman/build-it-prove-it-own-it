"""Feature flags, stored in the database so every running server sees the same value.

A flag that has no row is off.
"""

import sqlite3

from . import db


def enabled(conn: sqlite3.Connection, name: str) -> bool:
    row = db.query_one(conn, "SELECT enabled FROM flags WHERE name = ?", (name,))
    return bool(row and row["enabled"])
