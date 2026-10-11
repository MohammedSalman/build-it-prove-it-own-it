"""The canonical logical dump (ops/dbfacts.py): same data, same dump; any change, a new dump."""

import sqlite3

from dbfacts import canonical_dump

TABLE = "CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT 'a b');"


def make(path, script, wal=False):
    conn = sqlite3.connect(path)
    if wal:
        conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(script)
    conn.close()
    return path


def test_the_same_rows_inserted_in_another_order_give_the_same_dump(tmp_path):
    a = make(tmp_path / "a.db", TABLE + "INSERT INTO t VALUES (1, 'Maya'); INSERT INTO t VALUES (2, 'Sam');")
    b = make(tmp_path / "b.db", TABLE + "INSERT INTO t VALUES (2, 'Sam'); INSERT INTO t VALUES (1, 'Maya');", wal=True)
    assert canonical_dump(a) == canonical_dump(b)


def test_one_changed_value_changes_the_dump(tmp_path):
    a = make(tmp_path / "a.db", TABLE + "INSERT INTO t VALUES (1, 'Maya');")
    b = make(tmp_path / "b.db", TABLE + "INSERT INTO t VALUES (1, 'Maia');")
    assert canonical_dump(a) != canonical_dump(b)


def test_a_changed_default_changes_the_dump_even_if_only_spaces_differ(tmp_path):
    a = make(tmp_path / "a.db", TABLE)
    b = make(tmp_path / "b.db", TABLE.replace("'a b'", "'a  b'"))
    assert canonical_dump(a) != canonical_dump(b)


def test_an_empty_database_has_an_empty_dump(tmp_path):
    sqlite3.connect(tmp_path / "empty.db").close()
    assert canonical_dump(tmp_path / "empty.db") == ""
