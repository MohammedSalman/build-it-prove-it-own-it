# AfterHours: notes for coding agents (and new teammates)

AfterHours is a campus festival platform: events, limited places, reservations.
Python 3.11+, FastAPI, SQLite, pytest. One app, one database.

## Commands
- Set up: `python -m venv .venv`, activate it, then `pip install -r requirements.txt`
- Tests: `python -m pytest -q`
- Run the app: `uvicorn app.main:app` (then open http://127.0.0.1:8000)
- Concurrency check (app must be running): `python scripts/race.py`
- Load check (app must be running): `python scripts/rush.py`
- Lost-answer check (app must be running): `python scripts/flaky_client.py`

## Map
- `app/main.py`: HTTP routes
- `app/reservations.py`: reserve() and cancel(); the reservation state machine
- `app/idempotency.py`: storing and replaying the answer to a reservation attempt
- `app/db.py`: connections, schema, seed data
- `app/payments.py`: payment simulation (never charges anything)
- `app/static/index.html`: the whole web UI
- `tests/helpers.py`: helpers for tests where people act at the same time

## Promises that must always hold
- Confirmed reservations for an event ≤ its capacity.
- A person holds at most one confirmed place per event.
- One reservation attempt (one `Idempotency-Key` from one `Client-Id`) creates at most one
  reservation; every retry of a booked attempt gets the same answer; and once an attempt is
  booked or refused (404 or 409), its key stays bound to that request (another request with it
  gets HTTP 422).
- A reservation only ever changes from `confirmed` to `cancelled`. Never back.

## Rules
- One SQLite connection per request. Never share a connection between threads.
- Open the database only through `app.db.connect()`, also in scripts and migrations: it turns
  on foreign-key checks, which SQLite enforces only on connections that ask for them.
- Save an attempt's answer in the same transaction as the reservation it describes.
- A rule about requests at the same time needs a test with requests at the same time
  (`tests/helpers.py`). A sequential test cannot show it.
- Never weaken or delete a test to make it pass. If a test looks wrong, say so and stop.
- Say so before changing the database schema. After a schema change, delete `afterhours.db*`.
- When you claim something works, show the command you ran and its output.
