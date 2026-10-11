# AfterHours: notes for coding agents (and new teammates)

AfterHours is a campus festival platform: events, limited places, reservations,
cancellations, and check-in at the door. Python 3.11+, FastAPI, SQLite, pytest, Hypothesis.
One app, one database.

## Commands
- Set up: `python -m venv .venv`, activate it, then `pip install -r requirements.txt`
- Tests: `python -m pytest -q`
- Property tests: `python -m pytest -q properties`
- Test the tests: `python mutants.py` (applies each mutant in `mutants.toml` to a fresh copy)
- Run the app: `uvicorn app.main:app` (then open http://127.0.0.1:8000)

## Map
- `docs/requirements.md`: what we promised. **Tests come from here.**
- `app/main.py`: HTTP routes · `app/reservations.py`: reserve, cancel · `app/checkin.py`: the door
- `app/clock.py`: the current time. App code never calls `datetime.now()` directly
- `app/db.py`: connections, schema, seed data · `app/payments.py`: payment simulation
- `tests/`: the test suite · `properties/`: property tests against a reference model

## Rules
- The promises that must always hold are in `docs/requirements.md` (R1 to R6).
- Derive expected values from `docs/requirements.md`, never from what the code currently does.
  If the requirements don't decide a case, stop and ask.
- Never weaken, skip, delete, or special-case a test to make it pass. If a test looks wrong,
  say so, quote the requirement, and stop. A human changes tests, in a separate commit that
  says why.
- Time-dependent code takes `now` from the clock, so tests can set it.
- One SQLite connection per request. Never share a connection between threads.
- When you claim something works, show the command you ran and its output.
