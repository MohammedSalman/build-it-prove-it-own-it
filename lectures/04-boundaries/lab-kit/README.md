# Lab 4 kit · AfterHours, tangled

This kit is self-contained. It does not need your Week 1–3 code.

`tangled/` is a working AfterHours that grew one prompt at a time: cancellation, then
"My bookings", then door check-in for volunteers. Every feature works and every
characterization test passes. The cancellation rule, though, is written down in several
places, in several languages. Your job in Part A: move that rule behind one small
interface without changing behaviour, then change the rule.

## What is in the kit

| Path | What it is |
|---|---|
| `tangled/app/main.py` | Routes, with most of the logic and SQL inside them |
| `tangled/app/policy.py` | **Shell** for the core task: the interface is written, the body is yours |
| `tangled/app/catalog.py`, `tangled/app/checkin.py`, the end of `tangled/app/reservations.py` | **Shells** for the optional extension (the full split) |
| `tangled/tests/characterization/` | 33 tests that photograph what the app does today. Keep them green, always |
| `tangled/tests/old_rule/` | 4 tests that pin today's cancellation rule. Green now; retire them with the rule change |
| `tangled/tests/new_rule/` | 8 tests for the 24-hour rule. Red now; green when you are done |
| `tangled/docs/adr/0000-template.md` | The template for your architecture decision record |

## Set up (Part 0)

You need Python 3.11 or newer and git. Replace `COURSE` with the folder where you keep the
course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/04-boundaries/lab-kit/tangled ~/afterhours-lab4
cd ~/afterhours-lab4
git init -q
git add -A
git commit -qm "tangled kit, as handed out"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests/characterization   # expect: 33 passed
python -m pytest -q tests/old_rule            # expect: 4 passed
python -m pytest -q tests/new_rule            # expect: 8 failed (that is the target)
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\04-boundaries\lab-kit\tangled $HOME\afterhours-lab4
cd $HOME\afterhours-lab4
git init -q
git add -A
git commit -qm "tangled kit, as handed out"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q tests/characterization   # expect: 33 passed
python -m pytest -q tests/old_rule            # expect: 4 passed
python -m pytest -q tests/new_rule            # expect: 8 failed (that is the target)
```

## Run the app (optional, to see it)

The seeded festival runs Fri 9 – Sun 11 Oct 2026. Pin the app's clock so it behaves the same
whatever today's date is.

**macOS / Linux**
```bash
AFTERHOURS_NOW=2026-10-09T12:00 uvicorn app.main:app
```

**Windows PowerShell**
```powershell
$env:AFTERHOURS_NOW = "2026-10-09T12:00"
uvicorn app.main:app
```

Open http://127.0.0.1:8000, type a name, book the escape room, and look at *My bookings*.
Open http://127.0.0.1:8000/door for the volunteers' page. Stop the app with Ctrl+C. To see
the door open, restart with the clock at `2026-10-09T19:45`. (In PowerShell,
`Remove-Item Env:AFTERHOURS_NOW` unpins the clock again.)

## Search the code

**macOS / Linux**
```bash
grep -rn "starts_at" app
grep -rn -i "cancel" app AGENTS.md
```

**Windows PowerShell**
```powershell
Select-String -Path app\*.py, app\static\*.html -Pattern "starts_at"
Select-String -Path app\*.py, app\static\*.html, AGENTS.md -Pattern "cancel"
```

## The three test suites

| Suite | Kit as handed out | After your refactor (step A2) | After the rule change (step A3) |
|---|---|---|---|
| `tests/characterization` | 33 passed | 33 passed | 33 passed |
| `tests/old_rule` | 4 passed | 4 passed | 4 failed, then you delete the folder |
| `tests/new_rule` | 8 failed | 8 failed | 8 passed |

In this lab the refactor edits none of the supplied tests, and they stay green. That is
evidence the behaviour they cover did not change; read your diff for anything they don't
cover. The behaviour change then retires the tests that pinned the old behaviour, in the
same commit, where a reviewer can see it.

## If something goes wrong

- `ModuleNotFoundError: app`: run pytest from the `afterhours-lab4` folder, not from `tests/`.
- A characterization test fails after your refactor: your refactor changed behaviour. Read
  the assertion, then `git diff` to find where. Do not edit the test.
- Everything looks "closed" in the browser: you forgot to pin the clock (`AFTERHOURS_NOW`).
- Start over at any time: `git stash` or `git checkout -- .` returns to your last commit.
