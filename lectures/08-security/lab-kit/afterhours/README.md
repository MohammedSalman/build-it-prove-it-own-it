# AfterHours · Week 8 kit

The festival app with sign-in added. People sign in, reserve places, see their own
reservations, and cancel them. Organisers can add events and read the door list.

**This version contains planted security defects for Lab 8.** The tests are not all green
on purpose. Do not deploy it.

## Set up and run

You need Python 3.11 or newer. The lab sheet has the full commands for bash and PowerShell.

```bash
pip install -r requirements.txt
python -m pytest -q              # on the kit: 1 failed, 20 passed, 1 skipped
uvicorn app.main:app             # then open http://127.0.0.1:8000
```

The app creates `afterhours.db` where you run it. Delete that file (and `afterhours.db-wal`,
`afterhours.db-shm`) to start again from the seed data. The escape room starts with one
place left, and the first new reservation gets number 228.

## Demo accounts

Local demo accounts, so you can play every part. Real passwords never appear in code.

| Name | Role | Password |
|---|---|---|
| Maya | student | `copper-kettle` |
| Sam | student | `violet-harbour` |
| Lee | student | `quiet-lantern` |
| Olu | organiser | `north-gate` |

The seeded `guest-001` … `guest-112` accounts hold earlier bookings and cannot sign in.

## The API

| Request | Who may send it |
|---|---|
| `POST /api/login` `{"name", "password"}` → `{"token", "name", "role"}` | anyone |
| `GET /api/events`, `GET /api/events/{id}` | anyone |
| `POST /api/events` | organisers |
| `GET /api/events/{id}/attendees` (the door list) | organisers |
| `POST /api/events/{id}/reservations` | signed in; the reservation is in your name |
| `GET /api/me`, `GET /api/me/reservations` | signed in |
| `DELETE /api/reservations/{id}` | signed in (who else? that is the lab) |
| `POST /api/logout` | signed in |

Signed-in requests carry the token: `Authorization: Bearer <token>`.
`python scripts/client.py --as Sam GET /api/me/reservations` sends one request as a demo
user; run it without arguments for help.

## Scripts

| Script | What it does |
|---|---|
| `scripts/client.py` | Send one request, as a stranger or as a demo account |
| `scripts/provenance.py` | Every installed dependency: version, licence, where it came from, why it is here |
| `scripts/secret_scan.py` | A small, readable scanner for secrets and personal data (`--history` for git history) |

## Settings (environment variables)

| Variable | Default | What it does |
|---|---|---|
| `AFTERHOURS_DB` | `afterhours.db` | Path to the SQLite file |
| `AFTERHOURS_PAYMENT_DELAY` | `0.3` | Seconds the simulated payment check takes. Nothing is ever charged |

## Map

```
app/
  main.py           HTTP routes
  auth.py           sign-in, tokens, current_user(), require_organiser()
  passwords.py      password hashing (scrypt, salted)
  reservations.py   reserve, cancel, my reservations
  db.py             connections, schema, seed data, demo accounts
  payments.py       payment simulation
  schema.sql        tables
  static/index.html the web page
inbox/              event submissions from student organisers (untrusted text)
exports/            an attendee export someone left here (see the lab)
tests/              test_basics, test_auth, test_access (adversarial), test_concurrency
scripts/            client.py, provenance.py, secret_scan.py
AGENTS.md           instructions for coding agents and new teammates
```
