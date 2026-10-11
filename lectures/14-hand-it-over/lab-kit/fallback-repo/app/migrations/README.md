# Migrations

Every change to the database schema since the baseline (`app/schema.sql`) lives here, one
numbered file per change: `0001-add-something.sql`, `0002-…`. The app applies pending files
in name order when it starts, all in one transaction, and records each one in the
`schema_migrations` table. There are none yet.

Rules (the reasons are in `docs/adr/0002-schema-changes-are-numbered-migrations.md`):

- Never edit or rename a file that has been merged; add a new one.
- Name: four digits, a dash, lowercase words with dashes, `.sql`. Anything else stops the app
  at startup with a clear error.
- Each statement ends with a semicolon; several may share a line, and `--` comments are fine.
- No `BEGIN`, `COMMIT`, `ROLLBACK` or `SAVEPOINT`: the app runs all pending migrations in one
  transaction itself, and refuses to start if a file tries to manage its own.
- Only **expand** in one release (add a table, add a column with a default). Removing or
  renaming something that old code still reads is a separate, later release: expand,
  migrate, contract.
- Before a release, rehearse the migration on a backup copy: `docs/runbook.md`, section 3.

Adding a column with a default:

```sql
ALTER TABLE events ADD COLUMN note TEXT NOT NULL DEFAULT '';
```
