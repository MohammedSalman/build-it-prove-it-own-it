# AfterHours: notes for coding agents (and new teammates)

AfterHours is a campus festival platform: events, limited places, reservations,
cancellations, and door check-in. Python 3.11+, FastAPI, SQLite, pytest. One app, one
database.

## Commands
- Set up: `python -m venv .venv`, activate it, then `pip install -r requirements.txt`
- Tests: `python -m pytest -q`
- Run the app: `uvicorn app.main:app` (then open http://127.0.0.1:8000 and http://127.0.0.1:8000/door)
- Pin the clock for manual testing: set `AFTERHOURS_NOW=2026-10-09T12:00` before starting the app
- Concurrency check (app must be running): `python scripts/race.py`

## Map
- `app/main.py`: HTTP routes, and most of the logic (events, cancelling, my bookings, door check-in)
- `app/reservations.py`: reserving a place (capacity check and save, in one transaction)
- `app/db.py`: connections, schema, seed data
- `app/clock.py`: the current time
- `app/payments.py`: payment simulation (never charges anything)
- `app/static/index.html`: the attendee page (events, my bookings)
- `app/static/door.html`: the door volunteers' page
- `tests/helpers.py`: helpers for tests where people act at the same time

## Festival rules
- Confirmed reservations for an event ≤ its capacity.
- Booking closes when the event starts.
- People can cancel any time before the event starts. A cancelled place is free again.
- Door check-in opens 30 minutes before the start and closes when the event ends.
- All times are festival local time.

## Rules for changes
- One SQLite connection per request. Never share a connection between threads.
- Get the time from `clock.now()`, never from `datetime.now()`, so tests can pin it.
- Never weaken or delete a test to make it pass. If a test looks wrong, say so and stop.
- Say so before changing the database schema.
- When you claim something works, show the command you ran and its output.

## Lab 4 scaffolding
- `app/policy.py`, `app/catalog.py`, `app/checkin.py`: module shells (not used by the app yet).
- `tests/characterization/`: what the app does today. Must stay green.
- `tests/old_rule/`: pins today's cancellation rule. `tests/new_rule/`: the 24-hour rule.
