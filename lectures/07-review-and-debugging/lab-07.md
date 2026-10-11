# Lab 7 · One Incident, Reviewed and Debugged

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence packet at the end (one per
pair, plus one practice-defence note each)

In the lecture you met pull request #14, "Waitlist + email confirmations", and the incident
that followed it: bookings still answer `201 Created`, but confirmations stopped arriving.
Today you work the same incident from both ends. First you review the PR the way it should
have been reviewed. Then you debug the incident with a hypothesis log, find the commit that
changed the behaviour with `git bisect`, and fix it with a test that would have caught it.

The PR, the incident and the people are fictional and the problems were **planted on
purpose**. The code is real: every commit in the history runs.

Agents are allowed in Parts A1–A4 and B. If one helps you, say where. **Part A5 (the
practice defence) is unaided.** You own every claim you hand in.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Use one or
the other; don't mix them. Where only one command is shown, it is the same in both.

| Part | What | Minutes |
|---|---|---:|
| 0 | Set up | 10 |
| A1 | Review PR #14 with the checklist | 25 |
| A2 | Debug the incident: hypothesis log | 15 |
| A3 | Narrow it down: `git bisect run` | 10 |
| A4 | Fix it, with a test that fails first | 15 |
| A5 | Practice defence (5 minutes each) | 10 |
| B | Your team's product: cross-team review, request ids | 25 |
| | Evidence packet and hand-in | 10 |

---

## Part 0 · Set up (10 min)

Follow **Set up** in `COURSE/lectures/07-review-and-debugging/lab-kit/README.md`. You will
end in the folder `w7-kit/afterhours` with the environment active, and two results:

- [ ] `python -m pytest -q` → `27 passed`. CI is green.
- [ ] `python ../incident/check_confirmation.py` (PowerShell: `..\incident\...`) prints
      `BAD` and exits with code 1. The incident is real in this repository.

Open a **second terminal** now, `cd` into `w7-kit/afterhours` and activate the environment
there too (`source .venv/bin/activate` or `.venv\Scripts\Activate.ps1`). Terminal 1 runs
the app; terminal 2 runs everything else.

## Part A1 · Review PR #14 (25 min)

You are the reviewer Sam should have been. Use `../review-checklist.md` from the top. (The kit's files sit one folder up from the
repository, in `w7-kit`.)

1. **Before the code (5 min).** Read `../pr/PR-14.md`. List its claims. Then look at
   the shape of the change:
   ```
   git diff --stat 4ac8467 b7675a2
   git diff --stat 4ac8467 b7675a2 -- tests/
   git diff --diff-filter=D --name-only 4ac8467 b7675a2
   ```
2. **Risk-ordered reading (15 min).** Read the hunks in the checklist's order, not file by
   file. The whole diff is in `../pr/pr-14.diff`, or `git diff 4ac8467 b7675a2 -- app/`
   for one area. You may run anything. For example, checking that a library function exists
   takes one line (here for `json.loads`; use it on any call you doubt):
   ```
   python -c "import json; print(hasattr(json, 'loads'))"
   ```
3. **Decide (5 min).** Approve, approve with comments, or request changes.

Record **at least five findings**. The lecture named six kinds of problem hidden in this PR;
find where each one is, plus anything else you can defend.

| # | file:line | What you see | Why it matters (who is hurt, how) | What you ask for | Severity: blocker · major · minor |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |

Decision and the findings that block it: ______________________________________________

Use line numbers from the files at the PR's last commit (`git show b7675a2:app/notify.py`
shows a file at that commit), or from `pr-14.diff`. Say which.

## Part A2 · Debug the incident: hypothesis log (15 min)

Read `../incident/INCIDENT.md`. Copy `../hypothesis-log.md` and fill it in as
you go. Write each hypothesis and its prediction **before** you run the experiment.

1. Write the symptom with explicit starting conditions (Given / When / Expected / Actual).
2. Write **at least four** hypotheses. Cover different places on the request's path: the
   booking itself, the outbox, the code that writes to it, the delivery after it.
3. Run experiments that rule hypotheses out. At least one must be **discriminating**: a
   single experiment whose result is different for the two hypotheses still standing.

Things you can observe (you choose which, and in what order):

| What | How |
|---|---|
| Run the app | terminal 1: `uvicorn app.main:app` (`../README.md` shows how to set the log level) |
| Make one booking and get its request id | terminal 2: `python ../incident/book.py` |
| Did the booking happen? | open http://127.0.0.1:8000/api/events/3 in a browser |
| What is in the outbox? | `python scripts/outbox.py` |
| What does the log say about one request? | search terminal 1's output for the request id |
| Does one function work on its own? | `python -c "from app import notify; ..."` |
| What changed, and when? | `git log --oneline v0.2..HEAD`, `git log -p -- app/notify.py` |

Stop the app (Ctrl+C) when you are done. Before Part A3, `git status` must show no changed
files: `git stash` any edits you made while experimenting.

## Part A3 · Narrow it down: `git bisect run` (10 min)

You know a good revision (`v0.2`, checked by hand on Monday) and a bad one (`HEAD`). You
have a check that tells them apart and exits 0 or 1. That is everything `git bisect`
needs.

First check the check, at both ends, by hand. It must say `BAD` at `HEAD` (you saw that in
Part 0) and `GOOD` at `v0.2`:

```
git switch --detach v0.2
python ../incident/check_confirmation.py       # expect: GOOD, exit code 0
git switch main
```

Bisect trusts your command completely. If the check cannot run (for example a typo in the
script's path), Python exits with an error code that git counts as "bad" at every step,
and bisect confidently names the first commit after `v0.2`. That answer would be wrong.

```
git log --oneline v0.2..HEAD                   # how many candidate commits?
git bisect start HEAD v0.2
git bisect run python ../incident/check_confirmation.py
git bisect log > ../bisect-log.txt
git bisect reset
```

(Forward slashes work in PowerShell here too. If `git bisect run` fails on Windows, bisect
by hand as the kit README describes.)

1. Before you run it: how many candidate commits are there, and how many checks do you
   expect bisect to need? ______
2. How many checks did it run? ______ The first bad commit (**full hash**): ______________
3. `git show <that hash>`: which line in that commit is the cause? ______________
4. Bisect found where the behaviour changed. It did not find why nobody noticed. Name the
   earlier commit that made this failure **silent**, and the one that made CI **blind** to
   it: ______________
5. Which of your A1 findings would have stopped this incident before it shipped? ______

## Part A4 · Fix it, with a test that fails first (15 min)

Work on a branch: `git switch -c fix/confirmations`.

1. **The test first.** Bring back the end-to-end tests the PR deleted:
   ```
   git restore --source 4ac8467 -- tests/test_confirmations.py
   python -m pytest -q tests/test_confirmations.py       # expect failures: this is the incident
   ```
2. **The cause.** Fix the line bisect pointed you to. Run the whole suite and the check:
   ```
   python -m pytest -q
   python ../incident/check_confirmation.py
   ```
3. **The promise.** The team's rule in `AGENTS.md` is that every booking made through the
   API puts exactly one confirmation in the outbox. Logging the failure louder would make
   it visible, but a booking could still exist without its confirmation, so the promise
   would still be broken. Add this test to the end of `tests/test_confirmations.py`
   (and `import pytest` and `from app import notify, reservations` at the top):
   ```python
   def test_a_booking_whose_confirmation_cannot_be_queued_does_not_survive(client, monkeypatch):
       event = event_by_title(client, BOARD_GAMES)
       before = client.get(f"/api/events/{event['id']}").json()["reserved"]

       def broken(*args, **kwargs):
           raise RuntimeError("outbox unavailable")

       monkeypatch.setattr(notify, "queue_confirmation", broken)
       with pytest.raises(RuntimeError):
           reservations.reserve(event["id"], "Maya", "maya@example.org")
       assert client.get(f"/api/events/{event['id']}").json()["reserved"] == before
   ```
   Run it: it fails. Now, in `app/reservations.py`, queue the confirmation **inside** the
   booking's transaction again, before `COMMIT`, as the team's code did before the PR, and
   remove the `try`/`except` around it. Booking and confirmation are then saved together or
   not at all. Run the test again: it passes.
4. **Commit, then run everything** and keep the output for your packet:
   ```
   git add -A
   git commit -m "Queue confirmations in the booking transaction; restore the deleted tests"
   python -m pytest -q
   python ../incident/check_confirmation.py
   ```
   Commit before you make your hand-in diff: `git restore --source` created
   `tests/test_confirmations.py` as a new, untracked file, and `git diff main` leaves
   untracked files out.

- [ ] `tests/test_confirmations.py` failed before your fix and passes after it
- [ ] `python -m pytest -q` passes; the check prints `GOOD` and exits 0
- [ ] `git diff main --stat` lists `tests/test_confirmations.py`

## Part A5 · Practice defence (10 min: 5 minutes each)

A rehearsal for the graded defences later in the term. **Unaided:** no notes, no agent, no
running anything. The code may be open on the screen. One of you explains, the other
listens, times, and marks. Then swap.

**Student 1: the booking path.**
1. *Explain (3 min).* In your fixed version, how does `POST /api/events/3/reservations`
   become a row in the `outbox` table? Name the files and functions in order, and say where
   the transaction starts and ends.
2. *Predict (2 min).* Suppose the `INSERT INTO outbox` fails (for example, someone dropped
   the table). What does the client get? Does the booking exist afterwards? What does the
   log show?

**Student 2: the promotion path.**
1. *Explain (3 min).* How does `DELETE /api/reservations/{id}` give a place to the first
   person on the waitlist? Name the files and functions, and say what happens inside the
   transaction and what happens after it.
2. *Predict (2 min).* The Maker Workshop is full and nobody is waiting. Lee joins its
   waitlist, then one workshop reservation is cancelled. What does
   `GET /api/events/4` show for `reserved`, `places_left` and `waitlist`? Is anything
   added to the outbox?

**The listener marks** (one line each): path complete and in order · transaction boundary
named correctly · prediction stated with a reason. After both defences, check both
predictions: run the scenario, or read the code together, and write down whether each was
right. A wrong prediction that you then understand is a good outcome for a practice.

## Part B · Your team's product (25 min)

This connects the kit to your own AfterHours. It ticks the Week 7 item on the product
checklist: *every PR reviewed with the checklist; logs carry a request id.*

1. **Cross-team review (15 min).** Swap with another team. Review one recent pull request
   in their repository with the kit's `review-checklist.md`. Leave your findings as comments on the
   PR itself, each with a file and line. Receive theirs on one of yours. If your team has no
   open PR, review the most recent merged one.
2. **Request ids (10 min to start).** Give every request in your product an id, put it on
   every log line, and return it in an `X-Request-ID` header. The kit's commit `6c6f942`
   shows one way (`git show 6c6f942`). Paste one log sample where two lines share an id.
   *If it does not fit, finish at home (≈30 min).*

## Evidence packet and hand-in (10 min)

| | |
|---|---|
| **Review** | Your findings table and your decision (A1) |
| **Diagnosis** | Your hypothesis log, with the discriminating experiment marked (A2) |
| **Narrowing** | `bisect-log.txt`, the first bad commit's full hash, and your answers to A3 |
| **Fix** | `git diff main` of your committed branch; test output before and after (A4) |
| **Defence** | Each student: the path you explained, your prediction, whether it was right (A5) |
| **Product** | Link to the PR you reviewed with your comments; your log sample (B) |

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 7, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 7 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### Optional extensions

- Fix the other findings from A1 on your branch. Which ones need a decision from the team
  rather than a code change?
- Ask an AI reviewer to review `pr-14.diff`. Which of the six planted problems did it find?
  Which of its findings were wrong? Would you have approved on its word?
- Write a small CI step that fails when a pull request deletes a file under `tests/`. That
  turns the AGENTS.md rule "never delete a test" from a sign into a fence (Lecture 1, R7).

### How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Review | Five or more findings with file:line and a concrete request; deleted tests, the swallowed error and the missing function among them; a decision with named blockers | Findings without locations, "looks good" comments, or style points only |
| Diagnosis | Hypotheses written before experiments; each experiment could rule something out; one discriminating experiment named | A list of guesses, or experiments whose result could not change anything |
| Narrowing | Correct full hash; step count predicted and explained; the silent and blind commits named | Hash only, or a wrong good/bad range |
| Fix | Tests fail before and pass after, including the queue-failure test; confirmation back inside the transaction; the restored tests in the diff | Fix without a failing test, the `except` left as it was, or only louder logging |
| Defence | Path complete with the transaction boundary; prediction reasoned, then checked | Path read from the screen line by line; prediction not checked |
