# Lab 4 · One Seam, One Rule

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence list at the end (one per pair)

In the lecture, one sentence from the organisers ("cancellations close 24 hours before the
event") needed 8 edits in 3 files of the tangled app, and 2 lines in the modular one. Today
you do it the careful way on the tangled kit, in two commits:

1. **Make the change easy.** Move today's rule behind one small interface in
   `app/policy.py`, *without changing behaviour*. None of the supplied tests may change.
2. **Make the easy change.** Switch the rule to 24 hours, in that one module.

Then you record the decision as an ADR, practise explaining the code to your partner
without notes, and draw the module map of your own product.

Agents are allowed in this lab except where a step says **agent-off**. If one helps you,
say where. You own every claim you hand in.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Use one
or the other; don't mix them. Replace `COURSE` with the folder where you keep the course
repository.

| Part | What | Minutes |
|---|---|---:|
| 0 | Set up | 10 |
| A | The kit exercise: map, refactor, change, ADR, practice defence | 70 |
| B | Your team's product: module map and one ADR | 25 |
| | Evidence and hand-in | 10 |
| | *Optional extension, outside the 2 hours: the full three-module split* | |

---

## Part 0 · Set up (10 min)

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
python -m pytest -q tests/new_rule            # expect: 8 failed
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
python -m pytest -q tests/new_rule            # expect: 8 failed
```

The three test folders do different jobs. Read the docstring at the top of one file in each.

| Folder | What it pins | Now | After step A2 | After step A3 |
|---|---|---|---|---|
| `tests/characterization` | Behaviour that must not change today (bookings, the door, the cases both rules agree on) | 33 pass | 33 pass | 33 pass |
| `tests/old_rule` | Today's cancellation rule | 4 pass | 4 pass | 4 fail → you retire them |
| `tests/new_rule` | The 24-hour rule (the spec from the organisers) | 8 fail | 8 fail | 8 pass |

- [ ] The three results above match yours.
- [ ] Optional: run the app with the clock pinned (see the kit README) and cancel a booking in *My bookings*.

---

## Part A · The kit exercise (70 min)

### A1 · Map the rule (12 min) · agent-off for the first 8 minutes

Open `app/main.py`, `app/static/index.html` and `AGENTS.md`. Without an agent and without
search, find every place that states, checks or shows today's rule ("cancel any time before
the event starts"). Then use search to check you missed nothing:

**macOS / Linux**
```bash
grep -n -i "cancel\|starts_at" app/main.py app/static/index.html AGENTS.md
```
**Windows PowerShell**
```powershell
Select-String -Path app\main.py, app\static\index.html, AGENTS.md -Pattern "cancel", "starts_at"
```

| # | File:line | Language (Python, SQL, HTML, text, Markdown) | What it says or decides | Would a test catch a mistake here? Which? |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| … | | | | |

Then read `app/policy.py`. It is a **shell**: the interface and its conventions are
written, the body is yours. Answer in one sentence each:

- Which conventions does the docstring fix that the tangled code never wrote down?
- Why does the interface take `datetime` objects instead of the strings in the database?

### A2 · Make the change easy: extract the seam (25 min)

The rule must not change in this step. It is still "cancel any time before the start".

1. **Implement `policy.cancellation()` with today's rule.** The deadline is the start
   itself; the refusal reason is `"This event has already started"` (the message the app
   sends today). Keep the rule's facts as two named constants at the top of the module
   (how long before the start cancelling closes, and what people are told), so step A3
   is a change to data, not to logic. `timedelta(0)` is a valid notice period.
2. **Route every place from A1 through it.** In `app/main.py`:
   - the cancel route asks the policy and, when not allowed, answers 409 with
     `answer.reason`;
   - the reserve route sets `cancel_until` from `answer.deadline`, formatted exactly
     like `starts_at` (`deadline.isoformat(timespec="minutes")`, which gives
     `2026-10-09T20:00`);
   - the *My bookings* query stops deciding anything: select the rows, then compute
     `can_cancel` (confirmed **and** allowed) and `cancel_until` in Python for each row;
   - the comment above the cancellation routes stops restating the rule.

   In `app/static/index.html`, remove the sentence that states the rule and show each
   booking's `cancel_until` instead (the page already has a `when()` helper that
   formats a time). In `AGENTS.md`, replace the rule sentence with where the rule lives.
3. **Prove you changed no behaviour.**
   ```
   python -m pytest -q tests/characterization tests/old_rule   # expect: 37 passed
   python -m pytest -q tests/new_rule                          # expect: still 8 failed
   git diff --stat                                             # no file under tests/
   ```
   If a characterization or old-rule test fails, your refactor changed behaviour. Read
   the assertion, find the change with `git diff`, and fix the **code**. Never edit these
   tests in this step.
4. **Commit the refactor on its own.**
   ```
   git add -A
   git commit -m "refactor: move the cancellation rule into app/policy.py (no behaviour change)"
   ```

If you use an agent here, give it a contract you can check from the diff, for example:
*"Implement policy.cancellation() with today's rule and route every caller through it.
Do not change behaviour and do not edit any file under tests/. Keep the text format of
every existing API field. Show me the test runs."* Then check the diff yourself.

- [ ] 37 passed, 8 failed, and `git diff --stat HEAD~1 -- tests` prints nothing.

Passing tests are evidence, not proof: they only see what they check. Read your refactor
commit once (`git show HEAD`) and ask what it could change that no test looks at (a text
format, a message, what the page shows).

*Stretch, only if you finish A2 early:* after a booking, the page's toast promises "Free
cancellation until …" without asking. Under today's rule that is always true; under the
24-hour rule it will not be. Make the toast use `can_cancel` from *My bookings* (the page
already fetches it) instead of assuming. Keep the decision on the server; don't compare
times in the page.

### A3 · Make the easy change (8 min)

1. Change the rule **only in `app/policy.py`**: cancelling closes 24 hours before the
   start, and the reason becomes `"Cancellations close 24 hours before the event starts."`
2. Run all three suites.
   ```
   python -m pytest -q tests/characterization   # expect: 33 passed
   python -m pytest -q tests/new_rule            # expect: 8 passed
   python -m pytest -q tests/old_rule            # expect: 4 failed
   ```
   Read the four old-rule failures. Each should be a statement of the rule you just
   replaced. If a failure is anything else, stop and find out why before going on.
3. Retire the old-rule tests **in the same commit** as the change:
   ```
   git rm -r -q tests/old_rule
   git add -A
   git commit -m "feat: cancellations close 24 hours before the event (ADR 0001)" -m "Retires tests/old_rule: they pinned the rule this commit replaces."
   git show --stat HEAD
   ```
4. Write down what `git show --stat HEAD` lists. If anything outside `app/policy.py` and
   `tests/` had to change in this step, name it and say why: that is a place your seam
   missed in A2. (This is reported, not graded. We judge the change by the behaviour it
   keeps, not by a file count.)

- [ ] 41 passed in total: `python -m pytest -q`

### A4 · Write the ADR (13 min)

Copy `docs/adr/0000-template.md` to `docs/adr/0001-cancellation-rule.md` and fill it in.
One page is enough. It must contain:

- **Context:** the request, and your A1 count of where the rule lived.
- **Decision:** the interface, and the conventions a reader could get wrong (festival local
  time, the deadline is exclusive, the format of `cancel_until`).
- **At least one alternative you rejected**, with the reason. (For example: edit in place;
  a notice period per event in the database; an environment variable.)
- **Consequences:** at least one negative or neutral one. What change would this
  interface *not* absorb?
- **Decided by:** a named person from your pair.

Commit it (two commands, so they also work in Windows PowerShell 5.1):
```
git add docs/adr
git commit -m "docs: ADR 0001"
```

### A5 · Practice defence (12 min) · agent-off

Graded defences later in the course ask you to explain code you did not type, unaided,
and to predict a change. This is practice; nobody is graded. **Laptops closed for the
explainer.** The partner keeps the code open and ticks the checklist.

**Round 1 (5 min).** Student 1 explains: *Maya opened My bookings on Wednesday, when the
escape room still showed a Cancel button. She leaves the page open and taps Cancel on
Thursday at 21:00, 23 hours before the start, without reloading. Follow the request from
the button to the database and back. Which files and functions run, where is the decision
made, and what does she see?* Then
predicts: *The organisers change 24 hours to 48. Which files change, and which tests fail
before you update them?*

**Round 2 (5 min).** Student 2 explains: *Maya books the escape room at 12:00 on the
day before. Where does the `cancel_until` in her confirmation come from, and what does
it say?* Then predicts: *The organisers reword the refusal message. Which files change,
and which tests fail?*

**Check the predictions (2 min).** Make each predicted change for real, run the tests,
compare with the prediction, then undo it with `git checkout -- .`.

| Checklist (partner ticks) | Round 1 | Round 2 |
|---|---|---|
| Named the files and functions on the path, in order | | |
| Said where the rule is decided, and that nothing else decides it | | |
| Mentioned at least one convention at the boundary (local time, exclusive deadline, format) | | |
| Prediction: files that change | | |
| Prediction: tests that fail | | |
| Prediction matched the real run | | |

Write one sentence each: what was hard to explain without the code in front of you?

---

## Part B · Your team's product (25 min)

In your team's own AfterHours repository:

1. **Module map** in `docs/modules.md`. One row per module (or per file, if you have no
   modules yet):

   | Module | Decision it hides | Interface (functions or endpoints) | Used by | Likely changes |
   |---|---|---|---|---|

2. **One likely change.** Pick the decision in your product most likely to change this
   term. List every place it lives today (file:line), as in A1.
3. **One ADR** in `docs/adr/0001-….md` for how you will keep that decision in one place,
   with at least one rejected alternative. You do not have to make the code change today.
   If it is small, do it as two commits like Part A.

This ticks the Week 4 item on the product checklist: *module map; one ADR with a rejected
alternative* (`docs/modules.md`, `docs/adr/`).

---

## Evidence and hand-in (10 min)

One per pair:

1. The A1 table and your two answers.
2. `git log --oneline` of your kit repository, and `git show --stat` of the refactor and
   the rule-change commits.
3. The three test results after A2 and after A3 (copy the last line of each run).
4. Your ADR (`docs/adr/0001-cancellation-rule.md`).
5. The A5 checklist and your two sentences.
6. Links to your team's `docs/modules.md` and ADR (Part B).

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 4, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 4 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Map (A1) | All seven places plus the comment, with language and a test (or "none") for each | Only the Python places, or no view of which ones tests protect |
| Refactor (A2) | Separate commit; 37 passed, no test file changed; `cancel_until` keeps its format | Refactor and rule change mixed in one commit, or a test edited to pass |
| Change (A3) | Only `policy.py` and retired tests change; failures read and explained | Other files changed without explanation |
| ADR (A4) | Context with evidence, conventions stated, a real rejected alternative, a negative consequence, a named decider | A description of the code, or no alternative |
| Defence (A5) | Honest checklist; predictions tested against a real run | Checklist filled in without running the predictions |
| Product (B) | Each module names the decision it hides; the likely change is traced to file:line | A list of files with no decisions |

---

## Optional extension (outside the 2 hours): the full split

The kit also has shells for `app/catalog.py` and `app/checkin.py`, and for `cancel()` and
`my_reservations()` at the end of `app/reservations.py`. Move the rest of `main.py`'s
logic into them until `main.py` only translates HTTP: it reads the request, asks a
module, and turns the answer or the module's exception into a response.

- Keep all 33 characterization tests green, and edit none of them.
- Move the door window and "booking closes at the start" into `policy.py` too.
- `catalog` should own the only query that counts confirmed places.
- One characterization test is marked `PINNED_QUIRK`: the door page's "expected" count
  includes cancelled reservations. Keep it as it is during the split. If you then want
  to fix it, do that as a separate commit that changes that test on purpose, and write an
  ADR or a short note saying why.
- Write unit tests for `policy.py` that need no server and no database.

When you finish, count how many modules each of these hypothetical changes would touch:
(a) two places at every event are kept back for volunteers, so fewer can be booked;
(b) the door opens 45 minutes before the start; (c) we move from SQLite to PostgreSQL.
