# AfterHours · Lab 5 kit: tests that know the answer

The Week 1 app (with Patch B and the concurrency test), plus two new features:

- **Cancelling** a reservation gives its place back.
- **Door check-in**: the volunteer at the door checks each person in on a tablet.

Both features came with tests, and every test passes. Lecture 5 is about why that is not
enough. **This kit contains planted defects.** They were put there on purpose so that you
can find them with tests derived from the requirements. They say nothing about any
particular model or tool.

The tests in `tests/test_checkin.py` and `tests/test_cancel.py` play the part of tests an
agent wrote from its own code. We wrote them to show that pattern. Treat them as given, not
as truth.

## Set up (once)

You need Python 3.11 or newer. Use **one** of these blocks.

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # expect: 16 passed
```

**Windows PowerShell**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                 # expect: 16 passed
```

## The three instruments

| Command | What it asks |
|---|---|
| `python -m pytest -q` | Do the tests in `tests/` pass? |
| `python -m pytest -q properties` | Does the app agree with a small reference model over hundreds of random sequences of reserve and cancel? |
| `python mutants.py` | If we plant a small mistake, do the tests notice? (`--tests tests` to measure only `tests/`) |

The commands are the same in bash and PowerShell. `mutants.py` never changes your files: it
copies this folder to a temporary directory for every mutant.

## Where the expected answers come from

`docs/requirements.md` (R1 to R6) is the team's written promise. Tests should come from it,
not from reading the code and writing down what it does.

## The API

| Request | Answer |
|---|---|
| `GET /api/events` | The programme, with `reserved` (counted) and `places_left` (a stored counter) |
| `POST /api/events/{id}/reservations` `{"attendee": "Maya"}` | 201 reservation · 409 full · 404 no such event |
| `GET /api/reservations/{id}` | The reservation, its `status` and `checked_in_at` |
| `POST /api/reservations/{id}/cancel` | 200 cancelled reservation · 404 |
| `POST /api/reservations/{id}/check-in` | 200 with `checked_in_at` · 409 with the reason · 404 |

Check-in uses the app's clock (`app/clock.py`). The running app uses the real time. Tests use
a `FixedClock` through the `clock` fixture in `tests/conftest.py`:

```python
def test_something_at_the_door(client, clock):
    clock.set("2026-10-09T21:59:59")
    ...
```

## Map

```
docs/requirements.md   what we promised (R1 to R6)
app/
  main.py              HTTP routes; create_app(clock=...)
  reservations.py      reserve, cancel
  checkin.py           the door: door_is_open() and check_in()
  clock.py             SystemClock (real time) and FixedClock (tests)
  db.py, schema.sql    connections, tables, seed data
  payments.py          payment simulation (never charges anything)
tests/                 the test suite (green), helpers.py for concurrency tests
properties/            property tests: model.py is the reference model
mutants.py             test the tests; mutants.toml lists the mutants
scripts/               race.py and rush.py from Week 1 (need the app running)
```

## Run the app (optional)

```bash
uvicorn app.main:app
```

Open http://127.0.0.1:8000. The app creates `afterhours.db` where you run it; delete that
file to start again from the seed data.
