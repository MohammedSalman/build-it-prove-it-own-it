# Lab 6 · One Tap, One Place

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence packet at the end (one per pair)

In the lecture, Maya pressed *Reserve* once on bad Wi-Fi and ended up with two places. Today
you reproduce that, give the database the rule "one confirmed place per person per event",
make the reservation request safe to retry with an idempotency key, and prove all of it with
tests and repeated runs. (Safe to retry means: repeats never make a second reservation; a
repeat of an attempt that booked gets that booking's answer; a repeat of an attempt that was
refused is simply tried again. If no request ever gets through, nothing can book the place;
that part depends on the network coming back.) Then you plan the
same change for your team's product.

Agents are allowed in this lab. If one helps you, say where. You own every claim you hand in.
The tests are the judge: **do not edit a provided test to make it pass.** If you think a test
is wrong, write down why and ask.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Use one or the
other; don't mix them. Replace `COURSE` with the folder where you keep the course repository.

| Part | What | Time |
|---|---|---|
| 0 | Set up | 10 min |
| A | The kit exercise: A1 see it, A2 one active place, A3 safe retries, A4 prove it | 70 min |
| B | Your team's product | 25 min |
| C | Evidence packet and hand-in | 10 min |
| Extensions | Optional: release payment holds, a transitions table, a waitlist design | after the lab |

---

## Part 0 · Set up (10 min)

**macOS / Linux**
```bash
cp -R COURSE/lectures/06-state-and-concurrency/lab-kit ~/afterhours-lab6
cd ~/afterhours-lab6
git init -q && git add -A && git commit -qm "Lab 6 kit"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # expect: 10 failed, 18 passed
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\06-state-and-concurrency\lab-kit $HOME\afterhours-lab6
cd $HOME\afterhours-lab6
git init -q; git add -A; git commit -qm "Lab 6 kit"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                 # expect: 10 failed, 18 passed
```

The 10 failing tests are today's tasks: 3 in `tests/test_active_unique.py` and 7 in
`tests/test_retries.py`. The 18 passing tests include Week 1's concurrency test,
`tests/test_concurrency.py`. It must still pass at the end.

You will use **two terminals**. Terminal 1 runs the app; terminal 2 runs the checks. In
**each** terminal, `cd` into `afterhours-lab6` and activate the environment.

- [ ] `10 failed, 18 passed`
- [ ] You have read `README.md` and `AGENTS.md` in the kit (5 minutes; they list the promises)

---

## Part A · The kit exercise (70 min)

### A1 · See the duplicate (10 min)

Terminal 1, start the app on a fresh database:

```bash
rm -f afterhours.db afterhours.db-wal afterhours.db-shm
uvicorn app.main:app
```
```powershell
Remove-Item afterhours.db* -ErrorAction SilentlyContinue
uvicorn app.main:app
```

Terminal 2 (the same command in both shells):

```
python scripts/flaky_client.py
```

1. What is the summary line? ______ (expected on the kit: `3 x DUPLICATE`)
2. Copy the six server log lines of **one** trial from terminal 1.
3. On paper, draw that trial as a timeline with four lanes (phone, Wi-Fi link, server,
   database), time downward, like Fig 6.2. Mark the moment the reservation was committed and
   the moment the answer was lost. Photograph it for your packet.
4. The lecture listed three things that can be behind "no answer". Which one happened here,
   and how does the log prove it?
5. The phone sent an `Idempotency-Key`. Find the line in `app/main.py` that reads it, and the
   place in `app/reservations.py` where it is ignored.

### A2 · One active place per person (15 min)

The rule: *a person holds at most one confirmed place per event.* It is about data, so the
database should enforce it.

1. In `app/schema.sql`, at the `TODO (Lab 6, Task A2)` comment, add a **partial unique
   index** on `reservations (event_id, attendee)` that covers only confirmed rows. (Lecture
   section 4 shows the shape. The SQLite page is https://www.sqlite.org/partialindex.html.)
2. In `app/reservations.py`, at the `TODO (Task A2)` comment: when the `INSERT` raises
   `sqlite3.IntegrityError`, raise `AlreadyReserved(event_id)` instead. (`main.py` already
   turns `AlreadyReserved` into HTTP 409.) You will need `import sqlite3` at the top.
3. Run the four uniqueness tests:
   ```
   python -m pytest -q tests/test_active_unique.py      # expect: 4 passed
   ```
4. Restart the app **on a fresh database** (stop it, delete `afterhours.db*`, start it
   again), then run `python scripts/flaky_client.py` again.
   - What does the summary say now? ______ (expected: `3 x CONFUSED`)
   - Look at the log: how many times was Maya's payment authorised in one trial? ______
   - In one sentence: why is one place not yet the right result for Maya?
5. `test_cancel_then_rebook_is_allowed` already passed before your change. What wrong version
   of the index would make it fail? Try it, watch it fail, and put the correct index back.

If the app refuses to start with *"The data in afterhours.db already breaks a rule in
schema.sql"*, that is SQLite refusing to add a rule that the saved data (the duplicates from
A1) already breaks. Delete the database files and start again.

### A3 · Safe retries (35 min)

Now make the retry get the *same answer*, without paying again. `app/idempotency.py` gives
you the helpers: `fingerprint(event_id, attendee)`, `find(conn, client_id, key)`,
`replay(stored, request_hash)` and `save(conn, client_id, key, request_hash, status_code,
response)`. Read the file first (3 minutes). The table `idempotency_keys` already exists, and
`main.py` already records refused attempts in it (`remember_refusal`), so that a key refused
once stays bound to its request. Only bookings are replayed: `replay()` returns `None` for an
attempt that was refused before, and then your code carries on as if nothing were stored.

Fill in the four `TODO (Task A3, …)` steps in `reserve()`:

| Step | Where | What it does | Rule |
|---|---|---|---|
| 1 | before the first check | if `key` is not `None` and `find()` returns a row, and `replay(...)` gives an answer, return it | 1, 2 |
| 2 | where the first check finds the event full | before raising `SoldOut`, look the key up again: this attempt's own resend may have taken the last place. If `replay(...)` gives an answer, return it | 3 |
| 3 | right after `BEGIN IMMEDIATE` | look the key up again; if `replay(...)` gives an answer now, `ROLLBACK` and return it | 3 |
| 4 | after the `INSERT`, before `COMMIT` | if `key` is not `None`, `save(...)` the answer with status 201 | 4 |

Hints:
- Always go through `replay()`, never read the stored response yourself: it raises
  `KeyReused` when the key was used for a different request, and two overlapping sends of
  one key can carry different requests. Let it propagate; `main.py` turns it into HTTP 422.
- Step 2 is the easiest to miss: an event can look full *because* this attempt already has
  the last place. One of the tests pauses a send right after its first look-up to force it.
- In step 3, end the transaction with `ROLLBACK` before you return. (The `finally:` block's
  `conn.close()` would roll it back anyway, but say what you mean; it also releases the write
  lock a moment sooner.)
- Call the helpers as `idempotency.save(...)`, not through `from .idempotency import save`.
  One test replaces `idempotency.save` with a version that fails, to prove rule 4.
- Requests without a key must keep working exactly as before.

Then the tests:

1. In `tests/test_retries.py`, `test_the_same_key_for_a_different_request_is_rejected` has
   its Given and When written. Write the Then (the status code, and that Sam holds no
   place), and delete the `pytest.fail(...)` line.
2. Below it, write one more test in the same style: **the same key sent for a different
   event** is rejected, and Maya gets no place at the second event. Use Open Mic.
3. Run until green:
   ```
   python -m pytest -q tests/test_retries.py        # expect: 12 passed
   ```

For each test in `tests/test_retries.py`, write one line in your packet: which rule it
checks, and what a wrong fix would look like that this test catches. (Four of them already
passed on the kit. Why are they there?)

### A4 · Prove it (10 min)

1. The whole suite, three times: `python -m pytest -q` (expect `29 passed` each time,
   including `tests/test_concurrency.py` from Week 1).
2. Restart the app on a fresh database. Then, three times: `python scripts/flaky_client.py`
   (expect `3 x ok` each time).
3. Three times: `python scripts/flaky_client.py --impatient`. Find the evidence in the server log
   that step 3 did the work: for one key, two `checked` lines and two payments, but only one
   `saved` line.
4. Three times: `python scripts/race.py`. Patch B must still keep the last-place promise.

A "run" is one invocation of the script; each run of `flaky_client.py` makes 3 trials and
each run of `race.py` makes 10.

| Check | Kit (from A1) | After A2 | After A3 |
|---|---|---|---|
| `pytest -q` (3 runs) | 10 failed, 18 passed | | |
| `flaky_client.py` (lost answer, 3 runs) | 3 × DUPLICATE | | |
| `flaky_client.py --impatient` (3 runs) | | | |
| `race.py` (3 runs) | | | |

---

## Part B · Your team's product (25 min)

Product checklist, Week 6: *reservation requests are safe to retry (idempotency key); active
reservations are unique.* Evidence: retry and uniqueness tests.

1. **State diagram (10 min).** Draw your core entity's state machine (a reservation, a
   ticket, a booking, whatever your festival calls it). Mark the guards, cross out the
   forbidden moves, and next to each rule write which layer enforces it: page, app or
   database. Commit it as `docs/states.md` (a photo or a Mermaid diagram is fine).
2. **Plan the retry change (15 min).** In your own product, decide and write down in
   `docs/states.md`: what one attempt is and where the client makes its key; where the
   answer is stored and which transaction stores it; which uniqueness rule your data needs and
   whether your database can express it as a partial unique index. Then start: port the
   uniqueness rule and its test first; it is the smaller change.

**Homework (about 1.5 hours), before Lab 7:** finish the idempotent endpoint in your product,
with at least one retry test (same key, same answer, one row) and one uniqueness test, both
running in CI.

---

## Part C · Evidence packet and hand-in (10 min)

| | |
|---|---|
| **Requirement** | One press of *Reserve* makes at most one reservation however often its request is repeated; a repeat of a booked attempt gets that booking's answer |
| **Decision** (and what you rejected, and why) | |
| **Change** (the files you changed) | |
| **Check** (commands and results, including three runs of each timing check) | |
| **Result** (ship / hold / condition; what is still open) | |

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 6, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 6 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### Hand in (one per pair)
1. The photo of your A1 timeline and your answers to A1 questions 4 and 5
2. Your A2 answers (the summary, the payment count, the sentence, the wrong index)
3. `git diff` of your changes to `app/` and `tests/`, and the one-line-per-test table from A3
4. The A4 table
5. Part B: `docs/states.md` from your product
6. The evidence packet (each of you hands in your measurement row separately)

### How this is marked (studio practice, formative)
| | Strong | Developing |
|---|---|---|
| Timeline | Commit shown before the lost answer; names which of the three cases happened, with the log line that proves it | Right shape; order of commit and loss unclear |
| Uniqueness | Partial index; explains why a full index breaks rebooking, and shows the failing test | Index works but no reason given for `WHERE status = 'confirmed'` |
| Retries | All four steps done; the new test is correct; each test mapped to its rule and to a wrong fix it catches | Tests pass, but rules 3 and 4 cannot be explained |
| Evidence | Three runs of each check in A4 (a run is one invocation of the script); Week 1's test still green; can explain `CONFUSED` versus `ok` | Single runs; Week 1's test not checked |
| Part B | Diagram with guards, forbidden moves and the enforcing layer; a clear key scope | Diagram without forbidden moves or enforcement |

---

## Optional extensions (after the lab; not marked)

**E1 · Give the money back (compensation).** In `reserve()`, whenever a request authorised a
payment but did not create a new reservation (full at the second check, `AlreadyReserved`, or
a resend answered by the first request in step 3), call `payments.release(hold)`. Write
tests with `payments.open_holds()`: the loser of the last place keeps no hold; a second
attempt for a place you already hold keeps no hold; a resend answered by the first request
keeps no hold. (`tests/helpers.py`'s gate replaces `authorize` with a version that places no
hold, so write a variant that calls the real one before waiting.)

**E2 · Let the database refuse forbidden moves.** Add a table of allowed status changes and
a `BEFORE UPDATE OF status` trigger that raises an error for any other change (SQLite's
`RAISE(ABORT, ...)`). Test that un-cancelling with a direct `UPDATE` fails, even one that
also clears `cancelled_at`.

**E3 · Design a waitlist (design only).** Draw the state machine for a waitlist (the
lecture's Fig 6.3 shows one possible design). Answer: who gets a freed place (look back at
Week 2's fairness policies), what happens to an offer nobody answers, which invariants must
hold (for example, confirmed + offered ≤ capacity), and which of them the database can
enforce.

## Troubleshooting

- **Port 8000 is busy.** Start the app with `uvicorn app.main:app --port 8001` and add
  `--url http://127.0.0.1:8001` to every script.
- **`flaky_client.py` says no server answered.** Start the app in terminal 1 first, in the
  same folder.
- **`--impatient` says it got an answer in time.** You started the app with
  `AFTERHOURS_PAYMENT_DELAY=0`. Restart it without that setting (the default is 0.3 s).
- **A test hangs for about 2 seconds, then fails with "order not forced".** The test could not
  create the order it needs: one request never reached the payment gate, or never looked the
  key up (for example because your step 1 raised an error, or skips `idempotency.find`). Read
  the outcomes printed in the assertion messages. On the untouched kit, the last-place test
  always takes these 2 seconds, because the kit's `reserve()` never looks keys up.
