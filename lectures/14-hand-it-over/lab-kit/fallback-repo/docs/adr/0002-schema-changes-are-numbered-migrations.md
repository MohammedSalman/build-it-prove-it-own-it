# 0002. Schema changes are numbered migrations, applied at startup

**Status:** accepted (Week 14, before the handover). **Owner:** the team's release steward.

## Context

The app used to create its tables from `app/schema.sql` with `CREATE TABLE IF NOT EXISTS`.
That statement skips a table that already exists. So if someone adds a column to
`schema.sql`, every new database gets it, including the fresh one each test creates, and
**the tests pass**, while a database that is already in use never gets it. We tried it: the
restarted app kept the old table, and the first query that used the new column failed with
`sqlite3.OperationalError: no such column`. A team that receives this repository would meet
that on its first schema change, on the festival's machine, after a green test run.

## Decision

- `app/schema.sql` is the baseline and is never edited again.
- Every schema change is a new file in `app/migrations/`, named `NNNN-what-it-does.sql`.
- At startup `app/db.py` applies every file not yet recorded in the `schema_migrations`
  table, in name order, **all in one transaction** under the write lock, and records each
  one. If any statement fails, none of them is applied and the app does not start. A file
  that contains its own `BEGIN`, `COMMIT` or `ROLLBACK` is refused before anything runs,
  because it could commit half a change.
- A fresh database goes through the same migrations as an old one. So the test suite applies
  every migration on every run, and `tests/test_migrations.py` checks the procedure itself
  (an existing database gets the change and keeps its data; a failing migration changes
  nothing).

## Alternatives we rejected

- **Edit `schema.sql` and delete the database.** Fine on a laptop. On the festival's
  machine it deletes every reservation.
- **A migration tool such as Alembic.** A good choice for a bigger schema. For two tables it
  adds a dependency, a second way to describe the schema, and a tool every new teammate must
  learn. Revisit if the schema grows past a handful of tables.
- **Apply migrations by hand with the sqlite3 shell.** Nothing records what was applied
  where, and nothing tests it.

## Consequences

- Upgrading is "back up, stop, start the new version" (`docs/runbook.md`, section 5).
- Only expand in one release: add tables, add columns with a default. Removing or renaming
  something that the running version still reads needs expand, migrate, contract over
  several releases.
- Rolling back the code after an expand-only migration is safe **for the data**: the old
  code ignores the new column and loses nothing. It is not automatically safe for
  **behaviour**: rows the new version wrote can mean something the old version does not
  understand (a new kind of event that the old code would treat like any other). Each
  change that adds meaning says in its own ADR whether rolling back is allowed.
- Rolling back the data means restoring the backup taken before the release, and losing what
  was written since.
