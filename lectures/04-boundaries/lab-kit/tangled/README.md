# AfterHours · the tangled version (Lab 4 kit)

AfterHours grew one prompt at a time: cancellation, then "My bookings", then door check-in
for volunteers. Every feature works and every characterization test passes. Where each
rule lives is another matter. Lab 4 is about that.

Setup and the lab steps are in `../README.md` (the kit README) and in `lab-04.md`.

## Run it

Pin the clock so the seeded festival (Fri 9 – Sun 11 Oct 2026) is in the future, whatever
today's date is.

macOS / Linux:
```bash
AFTERHOURS_NOW=2026-10-09T12:00 uvicorn app.main:app
```

Windows PowerShell:
```powershell
$env:AFTERHOURS_NOW = "2026-10-09T12:00"; uvicorn app.main:app
```

Open http://127.0.0.1:8000 (attendees: type a name, book, see "My bookings", cancel) and
http://127.0.0.1:8000/door (volunteers: pick an event, check people in). The app creates
`afterhours.db` where you run it; delete it to start over with fresh seed data.

## Test it

```bash
python -m pytest -q tests/characterization   # what the app does today: all pass
python -m pytest -q tests/old_rule            # today's cancellation rule: all pass
python -m pytest -q tests/new_rule            # the 24-hour rule: all FAIL until you build it
```

## Settings (environment variables)

| Variable | Default | What it does |
|---|---|---|
| `AFTERHOURS_DB` | `afterhours.db` | Path to the SQLite file |
| `AFTERHOURS_NOW` | *(real time)* | Pins the app's clock, e.g. `2026-10-09T12:00` (festival local time) |
| `AFTERHOURS_PAYMENT_DELAY` | `0.3` | Seconds the simulated payment takes. Nothing is ever charged |
| `AFTERHOURS_CLASSROOM_GATE` | `0` | Week 1 demo gate; leave it at `0` |

## Map

```
app/
  main.py           routes, and most of the logic
  reservations.py   reserving a place (Week 1)
  db.py, schema.sql connections, tables, seed data
  clock.py          the current time (AFTERHOURS_NOW pins it)
  payments.py       payment simulation
  static/           index.html (attendees), door.html (volunteers)
  policy.py         Lab 4 shell: the cancellation rule goes here
  catalog.py        Lab 4 shell (optional extension)
  checkin.py        Lab 4 shell (optional extension)
tests/
  characterization/ what the app does today (keep green)
  old_rule/         today's cancellation rule (retire with the change)
  new_rule/         the 24-hour rule (make these pass)
scripts/            race.py and rush.py from Week 1
docs/adr/           architecture decision records
```
