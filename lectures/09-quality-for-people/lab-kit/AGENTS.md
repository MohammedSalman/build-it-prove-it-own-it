# AfterHours: notes for coding agents (and new teammates)

AfterHours is a campus festival platform: events, limited places, reservations.
Python 3.11+, FastAPI, SQLite, pytest. One app, one database.

## Commands
- Set up: `python -m venv .venv`, activate it, then `pip install -r requirements.txt`
- Tests: `python -m pytest -q`
- Run the app: `uvicorn app.main:app` (then open http://127.0.0.1:8000)
- Concurrency check (app must be running): `python scripts/race.py`
- Load check (app must be running): `python scripts/rush.py`
- What the database holds: `python scripts/who_booked.py [--name Maya]`

## Map
- `app/main.py`: HTTP routes
- `app/reservations.py`: the reservation rule
- `app/db.py`: connections, schema, seed data
- `app/payments.py`: payment simulation (never charges anything)
- `app/static/index.html`: the whole web UI
- `checklist.md`: the manual accessibility and usability procedures for the UI
- `tests/helpers.py`: helpers for tests where people act at the same time

## Rules
- The promise that must always hold: **confirmed reservations for an event ≤ its capacity.**
- One SQLite connection per request. Never share a connection between threads.
- Never weaken or delete a test to make it pass. If a test looks wrong, say so and stop.
- Say so before changing the database schema.
- When you claim something works, show the command you ran and its output.
- UI changes: `pytest` does not check the page. Say which procedure in `checklist.md` would
  confirm your change, and do not claim that a screen reader announces something unless a
  person has heard it.

This is the Week 1 version of this file plus the UI rule above. Your team's own AGENTS.md has grown since.
