# Lab 5 · Tests That Know the Answer

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence packet at the end (one per pair)

In the lecture you saw code and tests agree on a wrong answer at 22:00:00, a property test
shrink a double cancel to three steps, and mutants measure how much a suite would notice.
Today you do all three on the kit, then take the habits to your own product.

Agents are allowed in this lab. If one helps you, say where. One rule for today: **the
expected values in your tests come from `docs/requirements.md`**, whoever types them. If you
ask an agent for tests, give it the requirements and check every expected value against them.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell** where they
differ. Use one or the other; don't mix them. Replace `COURSE` with the folder where you keep
the course repository.

---

## Part 0 · Set up (10 min)

You need Python 3.11 or newer and git.

**macOS / Linux**
```bash
cp -R COURSE/lectures/05-independent-tests/lab-kit ~/afterhours-lab5
cd ~/afterhours-lab5
git init -q
git add -A
git commit -qm "kit"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # expect: 16 passed
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\05-independent-tests\lab-kit $HOME\afterhours-lab5
cd $HOME\afterhours-lab5
git init -q
git add -A
git commit -qm "kit"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                 # expect: 16 passed
```

If `git commit` asks who you are, run `git config user.name "Your Name"` and
`git config user.email "you@example.com"` once, then commit again.

- [ ] `16 passed`
- [ ] You have opened `docs/requirements.md` and read R1 to R6. This page is your oracle today.

## Part A · The kit (65 min)

### A1 · Measure what you were given (5 min)

Before changing anything, measure the suite that came with the kit:

```
python mutants.py --tests tests
```

It takes a few seconds. Each mutant is applied on its own to a fresh copy of the folder; your
files are never touched.

1. Mutation score of the given suite: ____ of ____
2. Which mutants survived? ______________________
3. Pick one survivor and, **without opening any test file**, guess why the given tests miss it.

### A2 · The door, from R4 (20 min)

1. **Before you open `app/checkin.py`**, fill in this table from R4 and R5 only. Use the
   escape room (Friday 9 October, 20:00 to 22:00) and a second event with different times,
   the Silent Disco (Friday 9 October, 21:30 to 23:30). The second event matters: a "fix"
   that only special-cases 22:00:00 would pass every escape-room row.

   | Event | Which point | Time scanned | Expected (200 or 409) | Which sentence of R4 or R5 says so |
   |---|---|---|---|---|
   | Escape room | one second before opening | | | |
   | Escape room | the opening time | | | |
   | Escape room | one second before the end | | | |
   | Escape room | the end time | | | |
   | Silent Disco | one second before opening | | | |
   | Silent Disco | the opening time | | | |
   | Silent Disco | 22:00:00 (the escape room's end) | | | |
   | Silent Disco | one second before the end | | | |
   | Silent Disco | the end time | | | |

   Add rows if you think of other cases worth checking.

2. Turn the table into `tests/test_door_rules.py`. Start from this; the `clock` fixture sets
   the time the app sees.

   ```python
   import pytest

   from .conftest import event_by_title, reserve

   ESCAPE_ROOM = "Escape Room: The Locked Lab"   # Friday 9 October, 20:00 to 22:00
   SILENT_DISCO = "Silent Disco on the Quad"     # Friday 9 October, 21:30 to 23:30


   @pytest.mark.parametrize("title, scanned_at, expected", [
       (ESCAPE_ROOM, "2026-10-09T19:29:59", 409),   # one row per line of your table
       # TODO: the rest of your table
   ])
   def test_the_door_window_follows_r4(client, clock, title, scanned_at, expected):
       booking = reserve(client, event_by_title(client, title))
       clock.set(scanned_at)
       res = client.post(f"/api/reservations/{booking['id']}/check-in")
       assert res.status_code == expected
   ```

   Add one test for R5: a cancelled reservation cannot check in.

3. Run `python -m pytest -q`. Which of your rows fail? ______

4. Now open `app/checkin.py`, find the mistake, and fix it. Run the whole suite again. A test
   that came with the kit now fails. Which one, and which is right: that test or R4?

5. Correct that test so its expected value comes from R4, and add a comment that names the
   requirement. Commit the code fix and the test correction **separately**, each with a
   message that quotes R4. (This is the lecture's rule 3: nobody edits a test silently.)

   ```
   git add app/checkin.py
   git commit -m "Close check-in at the end time (R4: the end time is not inside the window)"
   git add tests/
   git commit -m "Tests from R4 and R5; expect 409 at 22:00:00 (R4), the old test was written from the code"
   ```

- [ ] Your door tests fail on the kit and pass after your fix
- [ ] The corrected given test cites R4

### A3 · Properties and a model (20 min)

1. Run the supplied property tests:
   ```
   python -m pytest -q properties
   ```
   Which property passed, which failed, and what was the shrunk failing case? Copy the
   `Failing test case:` lines into your notes.

2. Open `properties/model.py`. In two sentences: why did `test_capacity_is_never_exceeded`
   pass on an app with a real bug? (Hint: what does `reserve()` count, and what does the
   programme page show?)

3. Fix `cancel()` in `app/reservations.py`. Hint: which reservations hold a place? Run the
   properties again until both pass. Commit.

4. Write the property in `properties/test_cancel_twice.py` (R3: cancelling twice changes
   nothing). Complete TODO 1 to 3, then delete the `@pytest.mark.skip` line. Run
   `python -m pytest -q properties`.

5. A property that has never failed has not shown it can. Put the bug back **by hand**: in
   `cancel()`, change `if row["status"] == "confirmed":` (or whatever your fix checks) so
   that it is always true, run your property, see it fail, then undo with
   `git checkout -- app`. You have just run a mutant by hand.

- [ ] Both supplied properties pass after your fix
- [ ] Your idempotence property passes on the fix and fails with the bug put back

### A4 · Test the tests (20 min)

1. Run everything against the mutants:
   ```
   python mutants.py
   ```
   Mutation score now: ____ of ____ (it was ____ in A1).

2. For **every** mutant that still survives, either write a test from the requirements that
   catches it (quote the sentence), or argue in writing that it is equivalent: that it can
   never change anything anyone sees. Rerun `python mutants.py` to show the catch. (If you
   followed A2 and A3 closely, one or two will be left. If more survive, start with those.)

   | Mutant | Test that now catches it, or why it is equivalent | Requirement |
   |---|---|---|
   | | | |
   | | | |

   Stuck on M9? Read R6, then look at how `hold_everyone_at_payment` in `tests/helpers.py`
   replaces `payments.authorize` with `monkeypatch.setattr`. You can record calls the same way.

   `mutants.py` reports a raw score: it counts every mutant it could apply. If you argue that a
   survivor is equivalent, leave the raw score as it is and write an adjusted score next to it
   ("9 of 10 raw; 9 of 9 excluding M_, equivalent because …").

3. Write your own mutant. Create `my-mutants.toml` that puts the 22:00:00 bug back:

   ```toml
   [[mutant]]
   id = "BUG"
   file = "app/checkin.py"
   find = 'opens_at <= now < ends_at'
   replace = 'opens_at <= now <= ends_at'
   why = "The planted bug from the lecture."
   ```

   (If your fix looks different, copy your own line into `find`.) Run
   `python mutants.py --mutants my-mutants.toml`. Which test catches it? Would the suite you
   were given in Part 0 have caught it? Explain in one sentence what that says about mutation
   scores. You will reuse this file format in Part B.

- [ ] Score recorded before and after
- [ ] Every survivor dealt with, each tied to a requirement
- [ ] `my-mutants.toml` runs

## Part B · Your team's product (25 min)

Work in your team's own AfterHours repository.

1. **Requirement-derived tests.** For each of your five acceptance examples from Week 2
   (`docs/examples.md`), make sure there is a test whose expected value comes from the example
   or the scope agreement, and write the sentence it comes from in a comment. Wherever the
   requirement does not decide a case (a boundary, a second cancel, a retry), write the
   question in `docs/examples.md` for the product lead instead of guessing.
2. **A mutation baseline.** Copy `mutants.py` from the kit into your repository. Write a
   `mutants.toml` with at least five mutants of the code behind your acceptance examples:
   at least one boundary operator (`<` / `<=`), one dropped check, and one off-by-one. Run
   `python mutants.py --tests tests` and record in `docs/quality.md`: the date, the command,
   the raw score, and one line per survivor saying what you will do about it (write a test, or
   argue it is equivalent and give an adjusted score).
3. **The working rules.** Add the four working rules for tests from the lecture to your
   `AGENTS.md`.

Product checklist, Week 5: *Tests derived from requirements for every acceptance example;
mutation-score baseline recorded* (evidence: the test files and `docs/quality.md`).

**Optional extension** (only if the rest is done): run `python -m pytest -q properties` and
`python mutants.py --fail-under <your baseline>` in CI; add a `CODEOWNERS` file that names a
human owner for `tests/` (and for `CODEOWNERS` itself); rewrite the model property as a
Hypothesis state machine (see the Hypothesis docs on stateful testing), which Week 6 builds on.

## Part C · Evidence packet and one measurement (10 min)

| | |
|---|---|
| **Requirement** (quote R4 and R3) | |
| **Decision** (what you changed, and which test edits you made and why) | |
| **Change** (commit hashes) | |
| **Check** (the commands you ran and their results: failing before, passing after, scores) | |
| **Result** (ship / hold / condition; what is still open) | |

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 5, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 5 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

---

### Hand in (one per pair)
1. The mutation scores from A1 and A4, and your answer to A1 question 3
2. Your boundary table and `tests/test_door_rules.py`; the two commit messages from A2
3. The shrunk failing case, your two sentences from A3, and `properties/test_cancel_twice.py`
4. The survivor table from A4 and `my-mutants.toml` with your one-sentence answer
5. Part B: links to your requirement-derived tests and `docs/quality.md`
6. The evidence packet (each of you hands in your measurement row separately)

### How this is marked (studio practice, formative)
| | Strong | Developing |
|---|---|---|
| Boundary table | Both sides of both edges for both events, plus 22:00:00 at the Silent Disco; every expected value tied to a sentence of R4 or R5; written before reading the code | Times chosen from the code, only one side of an edge, or only one event |
| Test edits | The wrong given test corrected in its own commit, quoting R4 | Test changed silently, or changed to match the code |
| Properties | Explains why the capacity invariant passed (it counts rows; the page shows a stored counter); idempotence property fails with the bug put back | Property written but never seen to fail |
| Survivors | Each survivor either killed by a requirement-derived test or argued equivalent with a reason; M9 tied to R6 | Survivors listed without action, or "killed" by a test that copies the code's behaviour |
| Part B | Every acceptance example traced to a test; open questions written down; baseline score with date and command | Tests added without their source; score without the command |
