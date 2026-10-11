# AfterHours · Lab 11 kit: measure, find, fix, remeasure

The festival app from Lecture 1, with Patch B applied, and with **festival-scale data**. It is
fast with the five demo events. With ten festivals' worth of reservations in the database, the
page that shows how many places are left gets slow. Your job in Lab 11 is to find out how
slow, for whom, and why, fix the cause, and show the improvement with evidence. The tasks are
in `lectures/11-performance-and-economics/lab-11.md`.

New in this kit:

| Path | What it does |
|---|---|
| `scripts/seed_festival.py` | Builds a festival-scale database: 4,000 events, 1,000,000 reservations (synthetic, the same for everyone). `--scale demo` builds 10 events instead |
| `scripts/load.py` | Sends requests at a steady rate and reports achieved rate, errors, sample count, and p50/p95/p99 latency, over 3 runs |
| `scripts/explain.py` | Runs one request inside Python and shows every SQL statement it ran, SQLite's query plan, and the work SQLite did, in steps |
| `economics/effort.py` | Summarises producing, checking and integrating minutes from the labs' "One measurement", as pooled shares. File format: `plan/class-dataset.md` |
| `economics/effort-synthetic.csv` | A **synthetic** example dataset for `effort.py`. Invented, not collected: see `make_synthetic.py` |
| `economics/effort-template.csv` | A file for your own rows from Labs 1 to 10, in the same format |
| `worksheet.md` | The experiment worksheet you fill in during the lab |
| `GET /api/events?from=…&to=…` | The event list can now be limited to dates, so the page shows only this term's festival |
| `/?event=ID` | An event's own page, which refreshes its places left every 10 seconds |

Everything runs on your own machine. Nothing is sent anywhere.

## Set up (10 minutes)

You need Python 3.11 or newer. Replace `COURSE` with the folder where you keep the course
repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/11-performance-and-economics/lab-kit ~/afterhours-lab11
cd ~/afterhours-lab11
git init -q && git add -A && git commit -qm "Lab 11 kit"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                       # expect: 9 passed
python scripts/seed_festival.py           # expect: 4,000 events, 1,000,000 reservations
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\11-performance-and-economics\lab-kit $HOME\afterhours-lab11
cd $HOME\afterhours-lab11
git init -q; git add -A; git commit -qm "Lab 11 kit"
python -m venv .venv
.venv\Scripts\Activate.ps1                # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                       # expect: 9 passed
python scripts/seed_festival.py           # expect: 4,000 events, 1,000,000 reservations
```

The database file (`afterhours.db`, about 50 MB) is ignored by git.

Use **two terminals**, both in `afterhours-lab11` with the environment active. Terminal 1 runs
the app; terminal 2 runs everything else.

```
uvicorn app.main:app                      # terminal 1
```

Open http://127.0.0.1:8000 to see this term's festival. Click an event's name to open its
own page (for example http://127.0.0.1:8000/?event=3601). While it is open, the event page
asks for its places left every 10 seconds with `GET /api/events/{id}`: the request this lab
measures.

## Commands

| What | Command (bash and PowerShell alike) |
|---|---|
| What does one request do in the database? (no server needed) | `python scripts/explain.py` |
| The same for another request | `python scripts/explain.py /api/events/3700` |
| Measure: 20 requests per second, 10 s, 3 runs (app running) | `python scripts/load.py` |
| Measure at another rate | `python scripts/load.py --rate 200` |
| Sweep several rates to find the knee (2 to 3 minutes) | `python scripts/load.py --rates 10,20,40,80,160 --duration 5` |
| Keep the results in a CSV file | add `--csv results.csv --label before` |
| Your producing, checking and integrating minutes | `python economics/effort.py economics/effort-template.csv` |

**Start over with fresh data.** Stop the app first (Ctrl+C), then run
`python scripts/seed_festival.py` again. It deletes and rebuilds the database. To go back to
the five demo events instead, delete the database files and start the app:

- macOS / Linux: `rm -f afterhours.db afterhours.db-wal afterhours.db-shm`
- PowerShell: `Remove-Item afterhours.db* -ErrorAction SilentlyContinue`

**After you change `app/schema.sql`, restart the app.** The app runs `schema.sql` every time
it starts, and every statement in it says `IF NOT EXISTS`, so new tables or indexes are added
to your existing database at the next start. You do not need to seed again.

## Reading `load.py`'s output

```
run    target   achieved  requests  errors        p50        p95        p99        max
  1      20/s     20.0/s       200       0    32.3 ms    33.8 ms    35.0 ms    37.8 ms
```

- **target**: the rate at which `load.py` schedules requests: the demand. **achieved**:
  successful answers per second, counted until the last answer of the run came back. If
  achieved is well below target, the server cannot keep up.
- **requests**: how many requests the run scheduled and counted. The percentiles are over the
  successful ones (requests minus errors). A p99 needs well over 100 to mean much.
- **errors**: requests that did not end in a `200 OK` within 5 seconds of being due, listed by
  kind: `late` (answered, but too late), `not sent` (already 5 seconds overdue when one of
  `load.py`'s 50 connections came free, so it was dropped), or another HTTP status. Errors are
  left out of the percentiles, so a run with errors looks better than it was.
- **p50 / p95 / p99**: half, 95%, and 99% of the answers took this long or less. Latency is
  counted from the moment each request was due, so waiting behind other requests counts.

## Fair measurements

Your laptop is not a server, and it is doing other things. To make comparisons fair:

- Plug the laptop in, close what you can, and don't use it while `load.py` runs.
- Compare before and after on the **same machine, close together in time**, with the same
  command. Run each measurement three times (the default) and look at the spread.
- Write down what you ran: data size, rate, duration, the commit, the machine.
- Timing is evidence, not a test. Never put a timing limit in `pytest`: it will pass on one
  laptop and fail on another. Check the query plan in tests instead; that answer is the same
  everywhere.

## Settings (environment variables)

| Variable | Default | What it does |
|---|---|---|
| `AFTERHOURS_DB` | `afterhours.db` | Path to the SQLite file (also used by `seed_festival.py` and `explain.py`) |
| `AFTERHOURS_PAYMENT_DELAY` | `0.3` | Seconds the simulated payment takes. Nothing is ever charged |
| `AFTERHOURS_CLASSROOM_GATE` | `0` | Lecture 1's demo gate; leave it at 0 |

## Map

```
app/                 the app (unchanged from Lecture 1 + Patch B, except the date filter)
tests/               9 tests, all green
scripts/seed_festival.py   festival-scale data
scripts/load.py            load generator and latency report
scripts/explain.py         statements, query plans, and SQLite steps for one request
scripts/race.py, rush.py   Lecture 1's checks (still work)
economics/                 producing, checking and integrating analysis; the synthetic example data
worksheet.md               the experiment worksheet
```
