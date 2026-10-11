# Lab 1 · The Last Seat

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence packet at the end (one per pair)
· **Homework:** set up your team's own repository (about 45 minutes, before Lab 2)

In the lecture you saw two people get the last place at the same time, and three patches that
all kept the tests green. Today you reproduce the failure yourself, write the promise down as a
test, check an agent's claims, and decide which patch to ship, with evidence.

Agents are allowed in this lab. If one helps you, say where. You own every claim you hand in.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Use one or
the other; don't mix them.

---

## Part 0 · Set up (10 min)

You need Python 3.11 or newer and git. Replace `COURSE` with the folder where you keep the
course repository.

**macOS / Linux**
```bash
cp -R COURSE/starter/afterhours ~/afterhours-lab1
cd ~/afterhours-lab1
git init -q
git add -A
git commit -qm "starter"            # so you can apply and undo patches
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # expect: 7 passed
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\starter\afterhours $HOME\afterhours-lab1
cd $HOME\afterhours-lab1
git init -q
git add -A
git commit -qm "starter"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                 # expect: 7 passed
```

You will use **two terminals**. Terminal 1 runs the app; terminal 2 runs the checks. In
**each** terminal, `cd` into `afterhours-lab1` and activate the environment (the `source` or
`Activate.ps1` line above).

- [ ] Tests pass: `7 passed`
- [ ] Terminal 1: `uvicorn app.main:app`, then open http://127.0.0.1:8000 and reserve something

## Part 1 · Break it (20 min)

In terminal 2:

```
python scripts/race.py
```

1. How many of the 10 trials broke the promise? ______
2. Copy the six log lines of **one** trial from terminal 1 into your notes.
3. On paper, draw the race timeline for that trial: one lane per person, one for the database,
   time downward, the same shape as Fig 1.3. Mark each person's *gap* between check and save.
   Photograph it for your packet.
4. The agent-off drill from class: two places left, three people press at once. You wrote down
   a prediction. Now check it:
   ```
   python scripts/race.py --people Maya,Sam,Lee --capacity 2
   ```
   Was your prediction right? If not, what did you miss? ______

## Part 2 · Write the promise down (20 min)

1. Write the invariant in one line.
2. Write two acceptance examples in *Given / When / Then* form:
   - one where people book one after another (the tests already cover this), and
   - one where two people press at the same moment (nothing covers this).
3. Turn the second example into a test. The file `tests/helpers.py` does the hard part (the
   threads and the timing) for you. Read its docstring first. Then create
   `tests/test_concurrency.py` with this, and write the three assertions yourself:

   ```python
   from app import reservations

   from .conftest import event_by_title
   from .helpers import at_the_same_time, hold_everyone_at_payment

   ESCAPE_ROOM = "Escape Room: The Locked Lab"   # seeded with 39 of 40 places taken


   def test_the_last_place_goes_to_exactly_one_person(client, monkeypatch):
       event = event_by_title(client, ESCAPE_ROOM)
       hold_everyone_at_payment(monkeypatch, people=2)   # both check before either saves

       outcomes = at_the_same_time(
           lambda name: reservations.reserve(event["id"], name), ["Maya", "Sam"]
       )
       # outcomes looks like {"Maya": <what reserve returned or raised>, "Sam": ...}
       # A success returns a dict. A full event raises reservations.SoldOut.

       # TODO 1: exactly one person got a place
       # TODO 2: exactly one person was told the event is full (SoldOut)
       # TODO 3: the event now has exactly 40 reservations
       #         (hint: client.get(f"/api/events/{event['id']}").json()["reserved"])
   ```

   - [ ] `python -m pytest -q tests/test_concurrency.py` **fails** on the starter
   - [ ] Run it three times. It should fail every time. `hold_everyone_at_payment` is what
         makes it reliable. Write one sentence on why.

## Part 3 · Delegate an investigation (30 min)

Give a coding agent (Claude Code, Codex, Cursor, or another) this task on a **throwaway copy**
of your repo. If you have no agent access, use the saved answer in
`lectures/01-code-is-cheap/demo/agent-investigation.md`.

```
Goal:     Find out whether AfterHours can confirm more reservations for an event than its
          capacity, and why.
Context:  Small FastAPI + SQLite app. Read AGENTS.md first. The promise:
          confirmed reservations for an event <= its capacity.
Limits:   Investigate only. Do NOT modify any file. You may read files and run tests/scripts.
Deliver:  1. The code path of one reservation request, with file:line references.
          2. Every assumption that path makes (timing, users, database, network).
          3. Whether the promise can break, how, and your evidence. Say which claims you
             verified by running something and which you inferred from reading.
          4. The smallest repair you'd suggest (not applied), and what it would NOT fix.
Stop:     When you have evidence for 3, or if blocked (say what blocked you).
```

Fill in this table with **at least five** of its claims:

| The agent claimed | Its evidence (ran it / read it / none) | Your check | Status: verified · plausible · wrong · needs checking |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |

Then answer:
- Which of its claims did it verify by running something, and which did it only infer?
- Did it stay inside its limits? How do you know: did you check, or are you trusting it?
- Which limit was only an **instruction**, and which (if any) was **enforced**?

## Part 4 · Judge the patches (25 min)

The three patches from the lecture are in `COURSE/lectures/01-code-is-cheap/patch-cards/`.
For each one: apply it, **restart the app in terminal 1**, run the checks in terminal 2,
record the results, then undo it.

**macOS / Linux**
```bash
PATCHES="COURSE/lectures/01-code-is-cheap/patch-cards"
git apply "$PATCHES/patch-b-recheck-in-transaction.diff"
python -m pytest -q
python scripts/race.py
python scripts/rush.py
git checkout -- app                 # undo the patch (your new test file is kept)
```

**Windows PowerShell**
```powershell
$PATCHES = "COURSE\lectures\01-code-is-cheap\patch-cards"
git apply "$PATCHES\patch-b-recheck-in-transaction.diff"
python -m pytest -q
python scripts/race.py
python scripts/rush.py
git checkout -- app
```

| Build | pytest (incl. your new test) | race.py | rush.py (slowest answer, anyone without a place?) |
|---|---|---|---|
| Starter | | | |
| Patch A · disable the button | | | |
| Patch B · re-check in a transaction | | | |
| Patch C · lock first (agent's) | | | |

Your timings will differ from the lecture's in the decimals. Look at the pattern.

Decide: **which patch would you ship, on what condition, and what does it still not fix?**
Name at least two things Patch B leaves for later.

## Part 5 · Evidence packet and one measurement (15 min)

Fill this in for your decision. This is what you hand in.

| | |
|---|---|
| **Requirement** | |
| **Decision** (and what you rejected, and why) | |
| **Change** (which patch or your own diff) | |
| **Check** (commands you ran and their results) | |
| **Result** (ship / hold / condition; open issues) | |

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 1, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 1 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

## Part 6 · Homework: your team's product (about 45 min, before Lab 2)

Everything so far happened in a throwaway copy, and Part 4 undid every patch. Your team's own
AfterHours starts now and grows all term: from Lab 2 on, every Part B works in it. Do this
once per team of four (both pairs together), before Lab 2. It ticks the two Week 1 rows of the
product checklist (`plan/product-checklist.md` in the course repository): *the last place goes
to exactly one person under concurrent requests* (evidence: the concurrency test in CI) and
*CI runs the tests on every push* (evidence: a CI badge or run link).

1. **Create the shared repository (5 min).** One of you creates an empty repository on GitHub
   (no README, licence or `.gitignore`: the starter has its own) and adds the other three as
   collaborators. Lab 3 protects its `main` branch; read its note on public and private
   repositories before you choose.
2. **Fill it: the starter, Patch B and your test (15 min).** Use one pair's
   `tests/test_concurrency.py`, one that fails on the starter and passes with Patch B (Part 4
   showed which). Replace `OWNER/REPO` with your repository.

   **macOS / Linux**
   ```bash
   cp -R COURSE/starter/afterhours ~/afterhours
   cd ~/afterhours
   git init -q
   git add -A
   git commit -qm "AfterHours starter"
   git branch -M main
   git apply COURSE/lectures/01-code-is-cheap/patch-cards/patch-b-recheck-in-transaction.diff
   cp ~/afterhours-lab1/tests/test_concurrency.py tests/
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m pytest -q                 # expect: 8 passed (run it three times)
   git add app/reservations.py tests/test_concurrency.py
   git commit -qm "Re-check the last place inside the write transaction (Patch B), with a concurrency test"
   git remote add origin https://github.com/OWNER/REPO.git
   git push -u origin main
   ```

   **Windows PowerShell**
   ```powershell
   Copy-Item -Recurse COURSE\starter\afterhours $HOME\afterhours
   cd $HOME\afterhours
   git init -q
   git add -A
   git commit -qm "AfterHours starter"
   git branch -M main
   git apply COURSE\lectures\01-code-is-cheap\patch-cards\patch-b-recheck-in-transaction.diff
   Copy-Item $HOME\afterhours-lab1\tests\test_concurrency.py tests\
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m pytest -q                 # expect: 8 passed (run it three times)
   git add app/reservations.py tests/test_concurrency.py
   git commit -qm "Re-check the last place inside the write transaction (Patch B), with a concurrency test"
   git remote add origin https://github.com/OWNER/REPO.git
   git push -u origin main
   ```

   If `git push` asks for a password, GitHub wants a personal access token or an SSH key
   instead: follow GitHub's guide to signing in from the command line.
3. **Watch CI go green (10 min).** The starter already has a workflow,
   `.github/workflows/ci.yml`: on every push it installs the requirements and runs
   `python -m pytest -q` in a job called `test`. Open the repository's **Actions** tab and
   find the run for your push. It must be green, and its log must show `8 passed`. If it is
   red, read the log, fix, commit and push again. (Optional: put the badge
   `![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)` in the README.)
4. **Record both Week 1 rows (10 min).** Create `docs/checklist.md`: copy the table from
   `plan/product-checklist.md`, tick the two Week 1 rows, and put links in their evidence
   cells: for the first, `tests/test_concurrency.py` on GitHub and the green run that ran it;
   for the second, the run link (or the badge). Commit and push. That push starts a second
   run, which must be green too. Later labs tick their rows in this file.
5. **Everyone gets a copy (5 min).** The other three clone it:
   `git clone https://github.com/OWNER/REPO.git ~/afterhours` (PowerShell:
   `git clone https://github.com/OWNER/REPO.git $HOME\afterhours`), create the environment as
   in Part 0, and run `python -m pytest -q` (`8 passed`). Lab 2's Part B works in this clone.

---

### Hand in (one per pair)
1. Photo of your race timeline (Part 1)
2. Invariant, two Given/When/Then examples, and `tests/test_concurrency.py` (Part 2)
3. The claims table and your three answers (Part 3)
4. The patch table and your decision (Part 4)
5. The evidence packet (Part 5). Each of you hands in your measurement row separately

### Hand in (one per team, before Lab 2)
6. Links to your repository, to the green CI run that ran `tests/test_concurrency.py`, and to
   `docs/checklist.md` with both Week 1 rows ticked (Part 6)

### How this is marked (studio practice, formative)
| | Strong | Developing |
|---|---|---|
| Timeline | Matches the log; both gaps marked | Shape right, gaps or timings missing |
| Test | Fails on starter, passes with B; the three assertions check winners, the refused person, and the final count | Asserts only one of the three, or passes on the starter |
| Claims | Each claim has your own check; instructions vs. enforcement identified | Claims copied without checks |
| Decision | Uses both race and rush evidence; names what B still misses | Picks B without evidence of C's cost |
| Team product | One shared repository with the starter, Patch B and the concurrency test; CI green on every push, its log shows `8 passed`; both Week 1 rows ticked with links a stranger can open | A piece missing (patch, test or checklist), CI red or never run, or evidence links that open nothing |
