# AfterHours, mid-migration: notes for coding agents (and new teammates)

Two versions of one app share one SQLite database while the tickets table changes shape.
Read `docs/migration-plan.md` before changing anything under `v1/`, `v2/` or `migrations/`.

## Commands
- Set up: `python -m venv .venv`, activate it, then `pip install -r requirements.txt`
- All tests: `python -m pytest -q` (one folder at a time: see `pytest.ini`)
- A copy of production: `python scripts/make_production_db.py --db prod.db`
- The migration, one step at a time: `python migrate.py --db prod.db status` (then `expand`,
  `backfill`, `verify`, `retire v1`, `flag`, `contract`, `meaning`)
- The whole migration rehearsed with both apps writing: `python scripts/rehearse.py --runs 3`

## Map
- `v1/`: the version running today (day tickets). It retires during the migration.
- `v2/`: day tickets and festival passes. Runs next to v1, then alone.
- `migrations/`: `expand.sql`, `backfill.py`, `contract.py`, `steps.py` (log, checks,
  guards), `meaning.py` (what the data means, from any shape of the table)
- `tests/characterization/`: photographs of v1's behaviour, run against v1 AND v2
- `tests/v2/`, `tests/migration/`, `tests/flags/`: new behaviour, the steps, the stale flag
- `docs/requirements.md` (T1 to T6, M1, M2), `docs/migration-plan.md`

## Rules
- A characterization test records what v1 does, not what it should do. Never edit one to
  make a change pass. If a photograph shows a bug, say so; fixing it is a separate change
  with its own tests, after the migration.
- During the migration window v1 and v2 must give the same answer to the same request.
- Never change a guard in `migrations/` to get past it. If a guard refuses, it says why.
- Never reuse a flag's name for a new meaning. A new behaviour gets a new flag.
- Time comes from the app's clock (`clock.now()`), never `datetime.now()`.
- One SQLite connection per request. Never share a connection between threads.
- When you claim something works, show the command you ran and its output.
