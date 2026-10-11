# Lab 8 kit: Security Follows Authority

Two things to secure: a web app that decides who may do what, and a coding agent that
decides which tools may run. The lab sheet is `lectures/08-security/lab-08.md`.

**This kit contains planted security defects.** Finding and fixing them is the lab. Nothing
in it contacts the internet: the app runs on your own machine, the agent runs offline in
replay mode, and its `http_post` tool is a stub that only writes calls down.

```
lab-kit/
  README.md                  this file
  requirements.txt           pinned packages for everything in the kit
  threat-model-template.md   one page, for Part B
  afterhours/                the app with sign-in (tasks A1, A2, A3, A5)
    app/                     auth.py, reservations.py, main.py ... (planted defects inside)
    inbox/                   event submissions from student societies (one is poisoned)
    exports/                 an attendee export someone left in the repository
    tests/                   test_access.py holds the adversarial tests
    scripts/                 client.py, provenance.py, secret_scan.py
  agent-sandbox/             Week 3's mini-agent, frozen, plus Week 8's additions (task A4)
    FROZEN-COPY.md           what was copied from Week 3, when, and what Week 8 added
    http_stub.py             the http_post tool: records calls, sends nothing
    permissions-organiser.json   the kit's too-broad rules
    recordings/poisoned-submission.json   an authored run that obeys a hidden instruction
    tests/test_injection.py  what each rules file lets out
```

## Set up (about 5 minutes)

You need Python 3.11 or newer. Replace `COURSE` with the folder that holds the course
repository. Use the block for your system; don't mix them.

**macOS / Linux (bash or zsh)**
```bash
cp -R COURSE/lectures/08-security/lab-kit ~/lab8
cd ~/lab8
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd afterhours
python -m pytest -q                 # expect: 1 failed, 20 passed, 1 skipped (on purpose)
cd ../agent-sandbox
python check_frozen.py              # expect: 18 of 18 frozen files unchanged
cd ..
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\08-security\lab-kit $HOME\lab8
cd $HOME\lab8
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
cd afterhours
python -m pytest -q                 # expect: 1 failed, 20 passed, 1 skipped (on purpose)
cd ..\agent-sandbox
python check_frozen.py              # expect: 18 of 18 frozen files unchanged
cd ..
```

## The app (`afterhours/`)

```bash
cd afterhours
uvicorn app.main:app                                  # terminal 1; open http://127.0.0.1:8000
python scripts/client.py --as Sam GET /api/me/reservations      # terminal 2
```

Demo accounts: Maya `copper-kettle`, Sam `violet-harbour`, Lee `quiet-lantern` (students)
and Olu `north-gate` (organiser). `afterhours/README.md` lists every route and who may call
it. Delete `afterhours.db*` to start again from the seed data.

## The agent (`agent-sandbox/`)

The agent is Week 3's reference solution, copied unchanged (`FROZEN-COPY.md` has the
hashes; `python check_frozen.py` re-checks them). It works on a throwaway copy of
`../afterhours`, as in Week 3. Week 8 adds one tool without editing the agent, through
Week 3's `--extra-tools` option:

```bash
cd agent-sandbox
python agent.py --replay recordings/poisoned-submission.json --extra-tools http_stub --permissions permissions-organiser.json --no-check
python http_stub.py                      # how many calls would have left the machine
python -m pytest -q tests/test_injection.py
```

Every blocked request is appended to `logs/blocked.jsonl` (it appears after the first run
that blocks something; filter by `run`). Lab task A4 walks through the rest.

`python -m pytest -q` in `agent-sandbox/` also runs Week 3's own tests: 33 pass and 2 are
skipped, because they replay Week 3 recordings that only fit Week 3's app
(`FROZEN-COPY.md` explains; `pytest -rs` prints the reasons). On the unfinished kit the whole
run reports 2 failed, 35 passed, 2 skipped: the two failures are task A4.

## Read this before you trust it

- **The recording was written by the course team** in the shape of real API replies. It
  plays the worst case, a "model" that obeys the hidden instruction, and it plays its turns
  in order whatever the tools return. **It proves what the permission layer does with
  those requests. It proves nothing about whether any real model would obey the
  instruction, or resist it.**
- **The permission layer is a teaching model, not a security boundary** (Week 3). It
  controls only the requests that go through the agent's dispatcher. Real isolation is a
  container or operating-system sandbox, with no secrets and no network inside.
- **`http_post` is a stub.** It opens no connection. It appends each call to
  `agent-sandbox/logs/outbound.jsonl`, and `python http_stub.py` counts them.
- **The attendee export is synthetic**: made-up names at `example.org`, a domain reserved
  for examples. The payment key in `app/payments.py` is fake too. Treat them as real anyway;
  that is the exercise.
