# Lab 13 kit · AfterHours, mid-migration

This kit is self-contained. It does not need your code from earlier weeks.

AfterHours sells **day tickets**: one festival day each, scanned at the gate. The
organisers want **festival passes** that cover two or three days. That changes the
tickets table while the gates are open, so for a while two versions of the app run on
one database:

- `v1/` is the version running today. It knows only `tickets.day`.
- `v2/` sells passes too. It runs next to v1 during the migration, then alone.

Your job in Part A: photograph what v1 does, write the backfill that moves the data,
rehearse the whole migration with both versions writing, and remove a flag that should
have gone a year ago. The plan is in `docs/migration-plan.md`; the rules are in
`docs/requirements.md`.

## What is in the kit

| Path | What it is |
|---|---|
| `v1/`, `v2/` | The two versions. In real life these are two tags of one repository; here they sit side by side so you can run both |
| `migrations/expand.sql` | Step 1: add `first_day`, `last_day` |
| `migrations/backfill.py` | Step 2: **the skeleton you complete** (part A3) |
| `migrations/contract.py` | Step 3: drop `day`, with a guard that refuses if anything is wrong |
| `migrations/steps.py`, `migrations/meaning.py` | The log, the checks, the guards; what the data means |
| `migrate.py` | Runs the steps one at a time on a database |
| `scripts/make_production_db.py` | Makes a copy of "production": a v1 database with 600 tickets |
| `scripts/rehearse.py` | The whole migration, with v1 and v2 writing throughout, then a meaning check |
| `tests/characterization/` | Photographs of v1. Each runs four times: v1 and v2 on every shape of the table |
| `tests/v2/`, `tests/migration/`, `tests/flags/` | v2's new behaviour; the steps; the stale flag |
| `docs/` | Requirements (T1 to T6, M1, M2) and the migration plan |

## Set up (Part 0)

You need Python 3.11 or newer and git. Replace `COURSE` with the folder where you keep the
course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/13-change-without-forgetting/lab-kit ~/afterhours-lab13
cd ~/afterhours-lab13
git init -q
git add -A
git commit -qm "kit, as handed out"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests/characterization   # expect: 88 passed
python -m pytest -q tests/v2                 # expect: 17 passed
python -m pytest -q tests/migration          # expect: 8 failed, 19 passed (the backfill is yours)
python -m pytest -q tests/flags              # expect: 2 failed, 1 passed (the stale flag is yours)
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\13-change-without-forgetting\lab-kit $HOME\afterhours-lab13
cd $HOME\afterhours-lab13
git init -q
git add -A
git commit -qm "kit, as handed out"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q tests/characterization   # expect: 88 passed
python -m pytest -q tests/v2                 # expect: 17 passed
python -m pytest -q tests/migration          # expect: 8 failed, 19 passed (the backfill is yours)
python -m pytest -q tests/flags              # expect: 2 failed, 1 passed (the stale flag is yours)
```

If `git commit` asks who you are, run `git config user.name "Your Name"` and
`git config user.email "you@example.com"` once, then commit again.

## The migration by hand, on a copy of production

The same commands on both systems (in PowerShell too).

```
python scripts/make_production_db.py --db prod.db
python migrate.py --db prod.db meaning --save before.json
python migrate.py --db prod.db expand
python migrate.py --db prod.db status
python migrate.py --db prod.db backfill          # "complete the backfill" until part A3
python migrate.py --db prod.db verify
python migrate.py --db prod.db contract          # refused: v1 is still live
python migrate.py --db prod.db retire v1
python migrate.py --db prod.db contract
python migrate.py --db prod.db meaning --compare before.json
```

To start again, delete `prod.db` (and `prod.db-wal`, `prod.db-shm` if they exist).

## The rehearsal

```
python scripts/rehearse.py            # one run
python scripts/rehearse.py --runs 3   # three runs, different writes each time
```

Both apps run inside the script on one database file, so no ports are needed. It prints
each step, what the guards refused, and at the end compares what every ticket means with
a record of every write the apps confirmed. The counts differ a little from run to run,
because the backfill runs in its own thread and the writes land between its batches at
slightly different moments. PASS or FAIL must not differ.

## See both versions live (optional)

Two terminals, both in the kit folder with the environment activated.

**macOS / Linux**
```bash
AFTERHOURS_DB=prod.db uvicorn v1.main:app --port 8001     # terminal 1
AFTERHOURS_DB=prod.db uvicorn v2.main:app --port 8002     # terminal 2 (after expand)
```

**Windows PowerShell**
```powershell
$env:AFTERHOURS_DB = "prod.db"; uvicorn v1.main:app --port 8001     # terminal 1
$env:AFTERHOURS_DB = "prod.db"; uvicorn v2.main:app --port 8002     # terminal 2 (after expand)
```

Open http://127.0.0.1:8001/docs and http://127.0.0.1:8002/docs. Sell a ticket on one and
read it on the other. v2 refuses to start until `expand` has run. Add
`AFTERHOURS_NOW=2026-10-09T18:00` (PowerShell: `$env:AFTERHOURS_NOW = "2026-10-09T18:00"`)
to pin the clock to Friday evening. Stop both servers with Ctrl+C when you are done.

## If something goes wrong

- `ModuleNotFoundError: v1` or `migrations`: run commands from the kit folder, not from `tests/`.
- A characterization test fails after your change: you changed behaviour. Read the
  assertion. Do not edit the test.
- `REFUSED`: a guard is telling you a step is out of order. Read its reasons.
- `database is locked`: a server is still running on `prod.db`. Stop it.
- Start over at any time: `git stash` or `git checkout -- .` returns to your last commit.
