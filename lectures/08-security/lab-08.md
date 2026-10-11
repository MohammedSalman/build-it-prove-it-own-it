# Lab 8 · Security Follows Authority

**Time:** 2 hours · **Work in:** pairs · **Hand in:** one evidence sheet per pair (end of lab)

In the lecture Sam cancelled Maya's booking with his own password, and a hidden sentence in
an event submission sent an agent after the attendee list. Today you do both attacks
yourself, turn the first into a test, fix it on the server, write the rules that stop the
second, and check where your code and your secrets live. Then you apply the week to your
team's product.

Agents are allowed in this lab. If one helps you, say where. You must be able to explain
every line you hand in without it.

> **Read this first.** The kit has **planted security defects**; finding them is the lab.
> Everything runs on your own machine. The agent runs **offline in replay mode**: the
> "model" is a recording the course team wrote, which obeys the hidden instruction on
> purpose. Replay shows what the **permission layer** does with those requests. It says
> nothing about whether any real model would obey the instruction or resist it. The agent's
> `http_post` tool is a stub: it opens no connection and only writes calls down.

| Part | What | Minutes |
|---|---|---:|
| 0 | Set up | 10 |
| A | The kit: A1 break in · A2 the attack as a test · A3 fix it on the server · A4 the agent and the poisoned submission · A5 dependencies and secrets | 70 |
| B | Your team's product: threat model, one ownership check with its adversarial test, secret scan | 25 |
| | Evidence sheet and hand-in | 10 |

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Where only
one line is shown, it is the same in both, except that PowerShell may use `\` in paths.

---

## Part 0 · Set up (10 min)

Replace `COURSE` with the folder that holds the course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/08-security/lab-kit ~/lab8
cd ~/lab8
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd afterhours
python -m pytest -q
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\08-security\lab-kit $HOME\lab8
cd $HOME\lab8
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
cd afterhours
python -m pytest -q
```

- [ ] pytest reports **1 failed, 20 passed, 1 skipped**. The failure is the leak (task A3);
  the skipped test is yours to write (task A2).
- [ ] Open a **second terminal**, `cd` into `lab8/afterhours` and activate the environment
  there too. The environment is one folder up: `source ../.venv/bin/activate` (PowerShell:
  `..\.venv\Scripts\Activate.ps1`). Terminal 1 runs the app; terminal 2 sends requests.

The demo accounts are Maya `copper-kettle`, Sam `violet-harbour`, Lee `quiet-lantern`
(students) and Olu `north-gate` (organiser). `afterhours/README.md` lists every route.

## Part A · The kit (70 min)

### A1 · Break in (10 min)

Terminal 1, from `afterhours/`, with a fresh database:

```bash
rm -f afterhours.db afterhours.db-wal afterhours.db-shm     # PowerShell: Remove-Item afterhours.db* -ErrorAction Ignore
uvicorn app.main:app
```

Open http://127.0.0.1:8000 and sign in as Maya to see the page. Then, in terminal 2, send
these requests one at a time. `scripts/client.py` signs in as the demo account you name and
prints the request and the answer.

```
python scripts/client.py --as Maya POST /api/events/1/reservations
python scripts/client.py --as Sam POST /api/events/1/reservations
python scripts/client.py --as Sam POST /api/events/3/reservations
python scripts/client.py --as Sam DELETE /api/reservations/228
python scripts/client.py --as Sam POST /api/events/1/reservations
python scripts/client.py --as Maya GET /api/me/reservations
python scripts/client.py GET /api/events
```

1. Fill in the status and the reservation number for each request.
2. Copy the log line in terminal 1 that records the cancellation. Which STRIDE threat does
   that line help with, and what can it not prove?
3. The last request is a stranger's. Whose names can a stranger read in its answer? Find the
   escape room's list: whose name is at the end of it now, and whose name was there before
   the attack? Could anyone see either defect on the web page? What does that tell you about
   where the checks must be?

Stop the app (Ctrl+C) when you are done.

### A2 · The attack as a test (15 min)

Open `tests/test_access.py`. The test `test_a_student_cannot_cancel_someone_elses_reservation`
is a skeleton. Delete its `pytest.skip(...)` line and write it, following the four steps in
its comments. `signed_in(client, "Maya")` returns the headers for a request as Maya.

```
python -m pytest -q tests/test_access.py
```

- [ ] **2 failed, 3 passed.** Your test must **fail** on the kit: an adversarial test that
  passes before the fix proves nothing.
- [ ] Your test checks the **state** afterwards (Maya still has #228; the event is still
  full), not only the status code.
- [ ] A comment says whether you expect 403 or 404, and why.

Then answer: a server that deletes the row and *then* answers 403 would pass a test that
checks only the status code. Does yours catch it?

### A3 · Fix it on the server (15 min)

1. **Ownership.** In `app/reservations.py`, make `cancel()` follow the rule in `AGENTS.md`:
   only the reservation's owner, or an organiser, may cancel it. Anyone else gets the answer
   your test expects. Try to make the check part of the `DELETE` statement itself, so there
   is no gap between checking and acting (Lecture 1).
2. **The leak.** In `app/main.py`, make `GET /api/events` stop sending names. The door list
   (`GET /api/events/{id}/attendees`) already exists for organisers.

```
python -m pytest -q
```

- [ ] **22 passed**, including `test_an_organiser_can_cancel_anyones_reservation` (your fix
  must not lock organisers out) and `test_the_door_list_is_for_organisers_only`.
- [ ] **Prove your test can fail.** Undo only the ownership part of your fix, run
  `tests/test_access.py`, and see your test fail. Put the fix back.
- [ ] Start the app again (fresh database) and repeat the A1 attack: Sam's `DELETE` of 228
  now gets your 403 or 404, and Maya keeps her place. Try `DELETE /api/reservations/9999` as
  Sam too. Can Sam tell the two answers apart?

### A4 · The agent and the poisoned submission (20 min)

```bash
cd ../agent-sandbox
python check_frozen.py                  # 18 of 18 frozen files unchanged: Week 3's agent, as it was
python agent.py --replay recordings/poisoned-submission.json --extra-tools http_stub --permissions permissions-organiser.json --no-check
python http_stub.py
```

Read the run from the top: the task, then one block per model call, then the EVIDENCE the
harness collected.

1. What does the model's last message claim? What does `python http_stub.py` show? Which
   step put personal data into the context?
2. Open `../afterhours/inbox/2026-10-11-late-night-karaoke.json`. Find the instruction.
   Would a person reading the description on a web page see it?
3. Name the three legs of the lethal trifecta as they appear in `permissions-organiser.json`.

Now write **`permissions-drafting.json`** next to `agent.py`: the rules for *this* task only
(read the task in the recording: draft the programme from `inbox/`, write only
`docs/programme-draft.md`). Give it what the task needs and nothing else. Then:

```bash
python http_stub.py --clear
python agent.py --replay recordings/poisoned-submission.json --extra-tools http_stub --permissions permissions-drafting.json --no-check
python http_stub.py
python -m pytest -q tests/test_injection.py
```
```bash
cat logs/blocked.jsonl                  # PowerShell: Get-Content logs\blocked.jsonl
```

- [ ] The stub records **0** outbound calls; `blocked calls` is at least 1 and includes
  `http_post`; `files changed: docs/programme-draft.md (new)` (the real task still works).
- [ ] `tests/test_injection.py`: **4 passed**.

4. What do these runs prove, and what do they not prove? Write two sentences, one each.
5. Run the recording once more with Week 3's rules: `--permissions permissions.json`. What
   is blocked, what gets into the context, and what happens to the draft? What does that say
   about reusing one rules file for every task?
6. In `logs/blocked.jsonl`, find the blocked `http_post` line from your drafting run. Its
   `body` starts with Maya's name and email, although your rules blocked the read of the
   export. Why? Give two lessons: one about replay, one about logs.

### A5 · Dependencies and secrets (10 min)

```bash
cd ../afterhours
python scripts/provenance.py
python scripts/secret_scan.py
```

1. How many packages does `requirements.txt` name, and how many are installed because of
   them? Which of them does `==` pin?
2. Pick two packages from the report. Where did pip get them from, what licence do they
   carry, and what does `Apache-2.0 OR BSD-2-Clause` mean? Where does that information come
   from, and how far do you trust it?
3. Fix both findings of the scan. The payment key comes from the environment variable
   `AFTERHOURS_PAYMENTS_KEY`; the export leaves the repository, and `.gitignore` keeps it and
   `.env` out. Re-run the scan: **0 finding(s)**, and `python -m pytest -q` still **22 passed**.
4. The key had been committed last week. Is your fix enough? What must happen first, and why?

### Optional extensions (if you finish early; not marked)

- **A fence inside the tool.** Give `http_post` in `http_stub.py` its own check (Week 3's
  third layer): it refuses any URL outside `https://chat.festival.example/`. Allow
  `http_post` in a copy of your drafting rules and replay. Which is safer, and why: removing
  the tool, or keeping it with a destination list?
- **Slow down guessing.** Limit failed sign-ins per name. The limit needs the current time:
  take it from an injectable clock so the test is deterministic.
- **A real scanner.** On a throwaway public GitHub repository, commit a fake key in a format
  GitHub recognises and watch push protection react. Compare with `secret_scan.py`.
- **Live mode** (only with a key and budget provided by the course). Run the drafting task
  live with your drafting rules and `--record`. Whatever the model does, one run shows one
  behaviour; what makes the result safe is still the rules file.

## Part B · Your team's product (25 min)

This week's item on the [product checklist](../../plan/product-checklist.md): **one-page
threat model; ownership checks with adversarial tests; no secrets in the repo**.

1. **Threat model** (15 min in the lab; finish as homework, about 45 min). Copy
   `../threat-model-template.md` (in the kit folder) to `docs/threat-model.md` in your
   repository. Draw your data-flow sketch with its trust boundaries, including any agent you
   use on the repository. List at least four threats as sentences with STRIDE letters, each
   ending in evidence or in an accepted risk with a name.
2. **One ownership check with its adversarial test** (8 min in the lab; homework about 1 h
   for the rest). Pick the route in your product that changes or reveals one person's data.
   Write the adversarial test first. If it passes on your current code, check that it would
   fail without the check (remove the check for a moment). If it fails, you found a real bug:
   fix it. Homework: one adversarial test for every such route.
3. **Secret scan** (2 min). Copy `scripts/secret_scan.py` into your repository and run it
   with `--history` (`python scripts/secret_scan.py --history`). It prints only the first four
   characters and the length of anything it finds, and email addresses only as a count, so
   the output is safe to save and hand in; check that yours is before you do. If it finds a
   real secret: revoke it first, then fix the code. Turn on secret scanning and push
   protection if your repository allows it.

## Evidence sheet (10 min, one per pair)

| | Hand in |
|---|---|
| A1 | The table of statuses; the log line; your answers to 2 and 3 |
| A2 | Your test (the function), and the `pytest` output showing it **fail** on the kit; your answer about the 403-after-delete server |
| A3 | Your diff; `pytest` output (22 passed); the output of your test with the ownership check removed; the two `DELETE` answers (228 and 9999) |
| A4 | `permissions-drafting.json`; the EVIDENCE lines and `http_stub.py` output of both runs; `pytest tests/test_injection.py`; answers 1–6 |
| A5 | The summary lines of `provenance.py`; scan output before and after; answers 1–4 |
| B | Links to `docs/threat-model.md`, the adversarial test (and the fix, if one was needed), and the saved scan output |

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 8, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 8 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Adversarial test (A2) | Fails on the kit, passes on the fix, checks the state afterwards; 403/404 choice argued | Checks only the status code, or passes on the kit |
| Server fix (A3) | Owner-or-organiser rule on the server, in the query; names removed from the response; all 22 tests pass; test shown to fail without the check | Hides data in the page, or locks organisers out |
| Agent rules (A4) | Task-specific rules, zero outbound calls, the task still works; says clearly what replay proves and what it does not | Rules copied from another task; claims the model "resisted" the injection |
| Dependencies and secrets (A5) | Knows which packages nobody chose; treats metadata as claims; key moved out and revocation named as the first step | Deletes the key and stops there |
| Team increment (B) | One-page model with boundaries, including the agent, and evidence for each threat; an adversarial test that was shown to fail without its check; scan output with history | A list of worries without evidence; a test that could never fail |
