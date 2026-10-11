# AfterHours · Lab 6 kit: retries and state

The festival app from Lecture 1, with Patch B applied, plus three things that are new this week:

- **Cancelling.** A reservation is `confirmed` or `cancelled`. `POST /api/reservations/{id}/cancel`
  moves it from one to the other. Only confirmed reservations use up a place.
- **Retries.** The page now sends each reservation request once more when no answer arrives. It
  sends an `Idempotency-Key` header (a new key for each press of *Reserve*, the same key on the
  retry) and a `Client-Id` header (one per browser). **The server does not use them to
  recognise a retry**, so a retried booking is booked again.
- **`scripts/flaky_client.py`**, which loses the server's answer *after* the server has saved
  the reservation, then retries, and counts the places.

Your job in Lab 6: however often one press of *Reserve* is repeated, it makes at most one
reservation, and a repeat of a booked attempt gets that booking's answer. The tasks are
in `lectures/06-state-and-concurrency/lab-06.md`.

## Set up (once)

You need Python 3.11 or newer.

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows PowerShell**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
```

## Run it

```
uvicorn app.main:app
```

Open http://127.0.0.1:8000, type a name, and reserve a place. The app creates `afterhours.db`
next to where you run it. To start over with fresh seed data, stop the app and delete the
database files:

- macOS / Linux: `rm -f afterhours.db afterhours.db-wal afterhours.db-shm`
- PowerShell: `Remove-Item afterhours.db* -ErrorAction SilentlyContinue`

**After you change `app/schema.sql`, always start over this way.** SQLite will not add a
rule (such as a unique index) to a database whose data already breaks it; the app then stops
with a message that says so.

## Lose an answer (with the app running, in a second terminal)

```
python scripts/flaky_client.py                # 3 trials: the first answer of each is lost
python scripts/flaky_client.py --impatient    # the phone resends after 0.1 s instead
python scripts/flaky_client.py --no-key       # an older page that sends no key
```

Each trial books a fresh event with 5 places for Maya. The script prints a timeline for each
trial and a verdict: `DUPLICATE` (one press, two places), `CONFUSED` (one place, but the phone
was told something other than its reservation number), or `ok`. It exits with status 0 only
when every trial is `ok`.

Watch the first terminal while it runs. Each log line shows who, which key (first 4
characters), and what happened, with a millisecond timestamp.

## Test it

```
python -m pytest -q
```

On the kit as handed out, **10 tests fail on purpose**: they are the lab's tasks
(`tests/test_active_unique.py` and `tests/test_retries.py`). The other 18 pass, including
Week 1's concurrency test (`tests/test_concurrency.py`), which must keep passing.

To test concurrency inside pytest, use `tests/helpers.py` (see its docstring).

## Other checks from Week 1

`python scripts/race.py` (does the last place go to exactly one person?) and
`python scripts/rush.py` (do 20 people booking 20 events all get a quick answer?) still work.

## Settings (environment variables)

| Variable | Default | What it does |
|---|---|---|
| `AFTERHOURS_DB` | `afterhours.db` | Path to the SQLite file |
| `AFTERHOURS_PAYMENT_DELAY` | `0.3` | Seconds the simulated payment takes. Nothing is ever charged |
| `AFTERHOURS_CLASSROOM_GATE` | `0` | Set to `2` for live demos only: the first request waits (up to 3 s) at the payment step for a second one |

Setting a variable for one run: `AFTERHOURS_PAYMENT_DELAY=0 uvicorn app.main:app` in bash;
`$env:AFTERHOURS_PAYMENT_DELAY = "0"; uvicorn app.main:app` in PowerShell (it then stays set
in that window until you close it or run `Remove-Item Env:AFTERHOURS_PAYMENT_DELAY`).

## Map

```
app/
  main.py            HTTP routes (reads the Idempotency-Key and Client-Id headers)
  reservations.py    reserve() and cancel(): the state machine and the reservation rule
  idempotency.py     helpers to fingerprint, find, replay and save an attempt's answer,
                     and to remember refused attempts
  db.py              connections, schema, seed data
  payments.py        payment simulation: holds that can be released
  schema.sql         tables and constraints
  static/index.html  the web page (one key per press, one automatic retry, cancel buttons)
tests/               the test suite; helpers.py for concurrency tests
scripts/
  flaky_client.py    lose an answer after the server commits, retry, count the places
  race.py            the Week 1 concurrency check
  rush.py            the Week 1 load check
AGENTS.md            instructions for coding agents and new teammates
```
