# AfterHours — starter

The running project for *Build It. Prove It. Own It.* A small platform for a student-run
campus festival: browse events, reserve one of a limited number of places.

It looks finished. The page is polished and every test passes. Lecture 1 is about why that
is not the same as "it works".

## Set up (once)

You need Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run it

```bash
uvicorn app.main:app
```

Open http://127.0.0.1:8000, type a name, and reserve a place. The escape room starts with
**one place left**.

The app creates `afterhours.db` next to where you run it. Delete that file to start over
with fresh seed data.

Full events show **Join waitlist**. Enter your name to join and see your position.
Waitlist entries persist across restarts, do not use a place, and do not authorize
payment. Joining again with the same name returns the same entry and position.
Names are trimmed and case-sensitive; as with reservations, there are no accounts.
People with an existing reservation cannot join that event's waitlist.

`POST /api/events/{event_id}/waitlist` accepts `{"attendee": "Maya"}` and returns
HTTP 201 with `id`, `event_id`, `attendee`, and a one-based `position` (including on
retries). Positions follow the order entries are saved. Unknown events return 404;
events with available places and attendees already reserved return 409. Invalid
names return 422. Event responses include the `waitlisted` count.

Startup adds the waitlist table to existing databases without resetting data.
This version records the queue only; it does not offer cancellation, notifications,
or automatic promotion into reservations.

## Test it

```bash
python -m pytest -q
```

## Race it

With the app running in one terminal, run this in a second one:

```bash
python scripts/race.py
```

It creates events with one place, has Maya and Sam press "Reserve" at the same instant,
and checks the promise *confirmed reservations ≤ capacity*. Try `--trials 30`,
`--people Maya,Sam,Lee`, or `--capacity 2`.

Watch the first terminal while it runs. The app logs each step of each reservation with a
millisecond timestamp, which is enough to draw the timeline of what happened.

`python scripts/rush.py` asks a different question: when 20 people book 20 *different*
events at once, how long do they wait, and does everyone get a place?

To test concurrency inside pytest, use `tests/helpers.py` (see its docstring).

## Settings (environment variables)

| Variable | Default | What it does |
|---|---|---|
| `AFTERHOURS_DB` | `afterhours.db` | Path to the SQLite file |
| `AFTERHOURS_PAYMENT_DELAY` | `0.3` | Seconds the simulated payment check takes. Nothing is ever charged |
| `AFTERHOURS_CLASSROOM_GATE` | `0` | Set to `2` for live demos: the first request waits (up to 3 s) at the payment step for a second one, so the two always overlap |

## Map

```
app/
  main.py           HTTP routes
  reservations.py   the reservation rule
  waitlist.py       joining full events' waitlists
  db.py             connections, schema, seed data
  payments.py       payment simulation
  schema.sql        tables
  static/index.html the web page
tests/              the (green) test suite, plus helpers.py for concurrency tests
scripts/race.py     the concurrency check: does the last place go to one person?
scripts/rush.py     the load check: do many people at once all get an answer?
AGENTS.md           instructions for coding agents and new teammates
.github/workflows/  CI: runs the tests on every push
```
