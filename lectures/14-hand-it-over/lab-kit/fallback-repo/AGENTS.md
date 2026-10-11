# AfterHours: notes for coding agents and new teammates

AfterHours is a campus festival platform: events, limited places, reservations.
Python 3.11+, FastAPI, SQLite, pytest. One app, one database file. Start with README.md.

## Commands
- Set up: `python -m venv .venv`, activate it, `pip install -r requirements.txt`
- Tests: `python -m pytest -q` (expect `15 passed` before you change anything)
- Run: `uvicorn app.main:app`, then http://127.0.0.1:8000
- With the app running: `python scripts/race.py` (concurrency), `python scripts/rush.py` (load)
- Database: `python scripts/backup.py <new-file>`, `python scripts/check_data.py [file]`,
  `python scripts/migrate.py --status <file>`
- Licences: `python scripts/licences.py`

## Map
- `app/main.py`: HTTP routes and JSON shapes
- `app/reservations.py`: `reserve()`, the capacity rule
- `app/db.py`: connections, baseline schema plus migrations, seed data
- `app/migrations/`: numbered schema changes (read its README before adding one)
- `app/static/index.html`: the whole web page
- `tests/helpers.py`: threads and timing for tests where people act at the same time
- `docs/`: runbook, decisions (`adr/`), known risks, licences

## Promises (never break these; each has a test)
- Confirmed reservations for an event ≤ its capacity, also when people act at the same
  moment (`tests/test_concurrency.py`).
- A full event answers 409 and stores nothing (`tests/test_basics.py`).
- A database that already exists keeps all its data when the app is upgraded
  (`tests/test_migrations.py`).

## Rules
- One SQLite connection per request. Never share a connection between threads.
- Never weaken or delete a test to make it pass. If a test looks wrong, say so and stop.
- Never edit `app/schema.sql`. Schema changes are new files in `app/migrations/` (ADR 0002).
  Say so before adding one.
- Do not add personal data to logs or to test data. Tests use made-up names.
- Update README, this file, the runbook, `docs/known-risks.md` or `docs/adr/` in the same
  change when your change makes them wrong.
- When you claim something works, show the command you ran and its output.

## Where decisions are recorded
- `docs/adr/0001-recheck-inside-the-write-transaction.md`: why `reserve()` checks twice
- `docs/adr/0002-schema-changes-are-numbered-migrations.md`: how the schema changes
