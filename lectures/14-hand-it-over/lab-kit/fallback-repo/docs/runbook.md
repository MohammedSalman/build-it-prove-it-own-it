# Runbook

How to run, check, change, back up, restore and release AfterHours, and what to do when
something is wrong. Every command here is run by `tests/test_runbook.py` or was run by hand
before the handover; if one fails for you, that is a bug in this runbook: fix it or record it
in `docs/known-risks.md`.

Commands are shown once; they are the same in bash and PowerShell unless a PowerShell line is
given. Run them from the repository folder with the virtual environment activated.

## 1. Start, stop, and is it healthy?

```
uvicorn app.main:app                         # this machine only, port 8000
uvicorn app.main:app --host 0.0.0.0          # reachable from phones on the same network
```

Stop with Ctrl+C. The app is healthy when `http://127.0.0.1:8000/api/events` answers 200
with a JSON list of events. A browser or `curl` works; in PowerShell:
`Invoke-RestMethod http://127.0.0.1:8000/api/events`.

There is no separate health endpoint. Adding one is a reasonable first change.

## 2. Reset local data (your laptop only)

Stop the app, delete `afterhours.db`, `afterhours.db-wal` and `afterhours.db-shm`, start it
again: it seeds five events.

```
rm -f afterhours.db afterhours.db-wal afterhours.db-shm                       # bash
Remove-Item afterhours.db* -ErrorAction SilentlyContinue                       # PowerShell
```

**Never** do this on the machine that runs the festival. It deletes every reservation.

## 3. Change the database schema

Read `docs/adr/0002-schema-changes-are-numbered-migrations.md` first. In short:

1. Add a file `app/migrations/NNNN-what-it-does.sql` (next free number). Expand only: add a
   table, or add a column **with a default**:
   `ALTER TABLE events ADD COLUMN note TEXT NOT NULL DEFAULT '';`
2. Never edit `app/schema.sql`. `CREATE TABLE IF NOT EXISTS` skips a table that already
   exists, so a change to a table there reaches new databases and the tests, and never the
   festival's database. A new statement added there, such as an index, would reach it, but
   nothing records it in `schema_migrations`. Put every schema change in a numbered
   migration, so it is recorded and applied once, in one transaction.
3. Run the tests. Every test starts from a fresh database that goes through all migrations.
4. Rehearse on a copy of real data before release:
   ```
   python scripts/backup.py rehearsal/copy.db
   python scripts/migrate.py --status rehearsal/copy.db     # your file shows as PENDING
   python scripts/migrate.py rehearsal/copy.db              # applied: NNNN-what-it-does.sql
   python scripts/check_data.py rehearsal/copy.db           # OK, and the same counts as before
   ```
5. If a migration fails, the app refuses to start and **nothing** was applied (all pending
   migrations run in one transaction). Fix the file, then start again.

## 4. Back up, restore, and check

**Back up** (safe while the app is running):
```
python scripts/backup.py backups/afterhours-2026-10-09-1900.db
python scripts/check_data.py backups/afterhours-2026-10-09-1900.db
```
`backup.py` uses SQLite's online backup API. Do not copy `afterhours.db` with `cp` or
`Copy-Item` while the app runs: recent changes can still be in `afterhours.db-wal`.
A backup never overwrites an existing file; give each one a new name.

**Restore** (the app must be stopped):
1. Stop the app.
2. Move the damaged files aside instead of deleting them:
   `afterhours.db`, `afterhours.db-wal`, `afterhours.db-shm` → a folder named after the time.
3. Copy the backup to `afterhours.db`.
4. `python scripts/check_data.py afterhours.db` must print `OK`, with the counts you
   expect.
5. Start the app, and check it is healthy (section 1).

Everything written after the backup was taken is lost. Say how much, and to whom, in the
incident note.

**Check** any database at any time: `python scripts/check_data.py [file]`. It checks SQLite's
integrity, that every reservation belongs to an event, and the promise (confirmed ≤ capacity)
for every event. Exit code 0 means all hold.

## 5. Release a new version

1. CI is green on the commit you will release.
2. If the release contains a migration: rehearse it on a copy (section 3, step 4).
3. Take a backup and check it (section 4). Write its file name down: it is your way back.
4. Stop the app, update the code (`git pull`), `pip install -r requirements.txt`, start it.
   Pending migrations apply at startup.
5. Check it is healthy (section 1) and run `python scripts/check_data.py`.
6. **Roll back** if a check fails: stop, check out the previous version, start it. After an
   expand-only migration the old code runs on the new schema (it ignores the new column), so
   no data is lost. First read the ADR of the change you are rolling back: if the new version
   wrote rows the old one does not understand, say what that means for users before you roll
   back. Restore the backup only if the data itself is wrong, and accept losing what was
   written since.

## 6. When something is wrong

| You see | Likely cause | Do this |
|---|---|---|
| `pip install` fails | Python older than 3.11, or the environment is not activated | `python --version`; activate `.venv` |
| Fewer than 15 tests pass on a fresh clone | Something in your setup differs | Run `python -m pytest -q -x` and read the first failure; do not change tests to make them pass |
| `address already in use` | Another app is on port 8000 | `uvicorn app.main:app --port 8001` |
| `no such column` after changing the schema | `schema.sql` was edited instead of adding a migration | Undo the edit; add a migration (section 3) |
| App will not start: `migration file name must look like…` | A badly named file in `app/migrations/` | Rename it to `NNNN-words.sql` |
| App will not start: a SQL error during migration | The new migration fails on this database | Nothing was applied. Fix the migration; rehearse on a copy |
| A reservation answers 500 after about 5 s | A request waited more than 5 s for SQLite's write lock | Known risk KR-4. Look for a long-running write; restart if stuck |
| `check_data.py` prints `FAIL … reservations for … places` | The promise is broken in the data | Stop taking reservations for that event; find how (logs have timestamps); restore only if you cannot correct it |

## 7. Logs

The app logs each reservation step to the terminal with a millisecond timestamp:
`checked`, `payment authorised`, `re-checked … too late`, `reservation #N saved`. The lines
contain the attendee's name, which is personal data (known risk KR-5): do not paste them into
public issues or chats; replace names with the reservation number.
