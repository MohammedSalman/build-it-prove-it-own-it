# AfterHours: Week 9 lab kit ("Quality Is Experienced by People")

The same AfterHours as after Week 1 (Patch B applied, the concurrency test added), with one
difference: **the web page has planted usability and accessibility problems.** We put them
there on purpose so you can practise finding them. The backend is unchanged, and every test
passes:

```
python -m pytest -q          # 9 passed
```

That green run tells you nothing about whether a person can use the page. `tests/test_page.py`
passes on this broken page and would pass on a fixed one too. Your evidence this week comes
from **manual procedures**: a keyboard pass, a screen-reader pass, contrast measurements, and
watching people. They are in `checklist.md`.

## What's here

| Path | What |
|---|---|
| `app/static/index.html` | The page you audit and fix (the only file you need to change) |
| `checklist.md` | The manual procedures, the supported browser and screen-reader combinations, and a findings table |
| `usability/session-script.md` | Script for the unaided usability session (homework) |
| `usability/note-sheet.md` | Note sheet for the observer, one per participant |
| `scripts/who_booked.py` | Shows what the database holds: the system state, whatever the page said |
| `scripts/race.py`, `scripts/rush.py` | Week 1's concurrency and load checks (not needed this week) |
| `tests/` | The backend tests, plus `test_page.py` (the page is served; nothing more) |

## Set up (once)

You need Python 3.11 or newer. Replace `COURSE` with the folder where you keep the course
repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/09-quality-for-people/lab-kit ~/afterhours-lab9
cd ~/afterhours-lab9
git init -q && git add -A && git commit -qm "kit"      # so you can see and undo your changes
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                                      # expect: 9 passed
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\09-quality-for-people\lab-kit $HOME\afterhours-lab9
cd $HOME\afterhours-lab9
git init -q; git add -A; git commit -qm "kit"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                 # expect: 9 passed
```

## Run it

**Normal speed** (the simulated payment check takes 0.3 s):

```bash
uvicorn app.main:app                 # bash and PowerShell alike
```

**Slow payment day** (the payment check takes 3 s, as a busy real provider might):

```bash
AFTERHOURS_PAYMENT_DELAY=3 uvicorn app.main:app            # macOS / Linux
```
```powershell
$env:AFTERHOURS_PAYMENT_DELAY = "3"; uvicorn app.main:app  # PowerShell
Remove-Item Env:AFTERHOURS_PAYMENT_DELAY                    # afterwards, back to normal
```

Open http://127.0.0.1:8000. Stop the server with Ctrl+C. The app keeps its data in
`afterhours.db`; stop the server and delete `afterhours.db*` to start again from the seed data
(the escape room at 39 of 40).

## Compare what people are told with what is stored

```bash
python scripts/who_booked.py                 # places reserved per event
python scripts/who_booked.py --name Maya     # every reservation with "Maya" in the name
```

It reads the database directly, so it works whether or not the server is running.

## After you change the page

Reload the browser tab (the server sends the file fresh each time), then repeat the procedure
in `checklist.md` that found the problem. Run `python -m pytest -q` as well: it should still
say `9 passed`, and it still proves nothing about the page.
