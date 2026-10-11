# AfterHours (fallback repository)

A small web app for a student-run campus festival: people browse the programme and reserve
one of a limited number of places at an event. Python 3.11+, FastAPI, SQLite, pytest. One
app, one database file, no external services.

This repository is written to be handed over. If you have just received it, this README is
your first hour: follow it from the top, and you should never need to ask the people who
wrote it.

**The promise this app keeps:** confirmed reservations for an event ≤ its capacity, even when
people press Reserve at the same moment. Everything else is secondary to that line.

**Status:** it works, for what it does, and the tests say which behaviours are checked. It
also has known gaps (anyone can book under any name, one person can hold two places, and
more). They are listed with evidence in [docs/known-risks.md](docs/known-risks.md). Read that
before you promise anything to a user.

---

## 1. Set up and check it works (about 10 minutes)

You need Python 3.11 or newer. Use **one** of the two blocks.

**macOS / Linux (bash or zsh)**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                  # expect: 15 passed
```

**Windows PowerShell**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1           # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                  # expect: 15 passed
```

If you do not see `15 passed`, stop and read [docs/runbook.md](docs/runbook.md), section 6
("When something is wrong").

## 2. Run it

```
uvicorn app.main:app
```

Open http://127.0.0.1:8000. The programme lists five events; the escape room has one place
left. Type a name and press **Reserve**. The terminal logs each step of the reservation with a
millisecond timestamp.

The app creates `afterhours.db` in the folder you start it from. To start again with fresh
data, stop the app and delete `afterhours.db`, `afterhours.db-wal` and `afterhours.db-shm`.
That deletes every reservation: fine on your laptop, never on the festival's machine (see the
runbook).

Two more checks, with the app running, in a second terminal (environment activated):

```
python scripts/race.py     # two people, one last place: expect "All 10 trials kept the promise"
python scripts/rush.py     # 20 people, 20 different events at once: expect "Everyone got a place."
```

## 3. Where to start reading

Read in this order. It takes about 30 minutes and it is the path from "it runs" to "I can
change it safely".

| # | Read | You learn |
|---|---|---|
| 1 | [AGENTS.md](AGENTS.md) | The commands, the map of the code, and the rules. Short on purpose: coding agents read it on every call, and so should you |
| 2 | `app/reservations.py` | The one rule that matters, `reserve()`, with comments on why it checks twice |
| 3 | `tests/test_concurrency.py` | How the promise is tested when two people act at once (`tests/helpers.py` does the timing) |
| 4 | [docs/adr/](docs/adr/) | Why the code is the way it is: two decisions, each with the alternatives we rejected |
| 5 | [docs/runbook.md](docs/runbook.md) | How to change the schema, back up, restore, release, and what to do when something breaks |
| 6 | [docs/known-risks.md](docs/known-risks.md) | What is not done or not safe yet, with evidence |
| 7 | [docs/licences.md](docs/licences.md) | What every dependency's licence says it allows |

## 4. Making a change

1. Start from the promise. Write down what must still be true after your change, and which
   test shows it.
2. Write or change the test first, from the requirement (not from your code).
3. If the change touches the database schema, add a migration in `app/migrations/`. Never
   edit `app/schema.sql`: a changed table there never reaches a database that already
   exists, and anything else added there runs outside the migration record
   ([ADR 0002](docs/adr/0002-schema-changes-are-numbered-migrations.md)).
4. Run `python -m pytest -q`. CI runs the same command on every push and pull request
   (`.github/workflows/ci.yml`).
5. Update the documents your change makes wrong, in the same pull request: this README,
   `AGENTS.md`, the runbook, a new ADR if you made a decision someone could question, and
   `docs/known-risks.md` if you closed or opened a risk.
6. In the pull request description, trace it: requirement → decision → change → check →
   result.

## 5. Map

```
app/
  main.py             HTTP routes and the JSON shapes
  reservations.py     reserve(): the capacity rule, checked twice (ADR 0001)
  db.py               connections, baseline schema + migrations (ADR 0002), seed data
  schema.sql          the baseline tables: never edit, add a migration instead
  migrations/         numbered schema changes, applied at startup (none yet)
  payments.py         payment simulation: sleeps ~0.3 s, never charges anything
  static/index.html   the whole web page (HTML, CSS and JavaScript in one file)
tests/
  test_basics.py       one request at a time: listing, reserving, full, unknown, validation
  test_concurrency.py  two people, one last place, at the same moment
  test_migrations.py   the schema-change procedure
  test_runbook.py      the runbook's commands: backup, data check, migration status
  helpers.py           threads and timing for concurrency tests
scripts/
  race.py rush.py      concurrency and load checks against a running app
  backup.py            safe copy of the database while the app runs
  check_data.py        does a database (or a restored copy) keep the promise?
  migrate.py           apply or list migrations on a copy, without starting the app
  licences.py          the licence every dependency declares
docs/                  runbook, decisions (adr/), known risks, licences
AGENTS.md              instructions for coding agents and new teammates
```

## 6. Settings (environment variables)

| Variable | Default | What it does |
|---|---|---|
| `AFTERHOURS_DB` | `afterhours.db` | Path to the SQLite file |
| `AFTERHOURS_PAYMENT_DELAY` | `0.3` | Seconds the simulated payment takes. Nothing is ever charged |
| `AFTERHOURS_CLASSROOM_GATE` | `0` | Demo only: `2` makes the first request wait (up to 3 s) at payment for a second one, so two requests always overlap. Leave it at 0 |

## 7. Licences

Every dependency and the licence it declares: [docs/licences.md](docs/licences.md)
(regenerate with `python scripts/licences.py --out docs/licences.md`). All are permissive
(MIT, BSD, Apache-2.0 or PSF). No licence has been chosen for this repository's own code
yet; that is known risk KR-8.

## 8. Where this code came from

The Week 1 starter of the course *Build It. Prove It. Own It.*, with Lecture 1's Patch B
(re-check inside a write transaction) and the Lab 1 concurrency test, plus the handover
documents, the migration procedure and the operations scripts added for Week 14. Don't take
its quality on trust: the tests and the commands in this README and the runbook are the
evidence, and you can run every one of them.
