# Lab 10 · Two Green Branches, One Red Main

**Time:** 2 hours · **Work in:** pairs for Part A, your team for Part B · **Hand in:** the
evidence listed at the end (one per pair, plus your team's contract)

In the lecture, two teammates each gave a task to a coding agent, in separate worktrees.
Both branches passed their tests, git merged them without a single conflict, and the
merged festival programme showed every event two hours early. Today you reproduce that,
write the integration test that catches it, write the contract that would have prevented
it, and repair the merge against that contract. Then you set up the same safety net for
your own team.

Agents are allowed in this lab. If one helps you, say where. You own every claim you hand
in. One caution for A3 and A4: a test written only from the code (by you or by an agent) is
likely to describe what the code does now, including the bug (Week 5). Give it the requirement
("what the organiser types is what the programme shows") and the contract's examples.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Git
commands are the same in both; forward slashes in paths work in both.

---

## Part 0 · Set up (10 min)

You need Python 3.11 or newer and git 2.38 or newer. Replace `COURSE` with the folder where
you keep the course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/10-many-hands/lab-kit ~/w10-kit
cd ~/w10-kit
python3 -m venv .venv
source .venv/bin/activate
git clone repo.bundle afterhours
pip install -r afterhours/requirements.txt
cd afterhours
git log --oneline --graph --all
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\10-many-hands\lab-kit $HOME\w10-kit
cd $HOME\w10-kit
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
git clone repo.bundle afterhours
pip install -r afterhours\requirements.txt
cd afterhours
git log --oneline --graph --all
```

- [ ] The graph shows `main` and two branches, `origin/feature/utc-storage` and
      `origin/feature/local-display`, each two commits ahead of `main`
- [ ] `python -m pytest -q` inside `afterhours` prints `10 passed`

The kit's `README.md` explains worktrees, every command you need, and what to do when git
says no. Keep it open.

## Part A · The kit exercise (70 min)

### A1 · Two green branches (10 min)

1. In `afterhours`, read `docs/tasks/README.md` and the two task cards next to it.
2. Make a worktree for each branch, plus one where they will meet:

   ```
   git worktree add ../ah-utc feature/utc-storage
   git worktree add ../ah-display feature/local-display
   git worktree add -b integration ../ah-merge main
   git worktree list
   ```

3. Run the tests in each feature worktree (`cd ../ah-utc`, then `python -m pytest -q`; the
   same in `../ah-display`). Expect `17 passed` and `14 passed`.
4. Back in `afterhours`, check that both branches start from the same commit, and ask git
   whether they would conflict:

   ```
   git merge-base feature/utc-storage feature/local-display
   git rev-parse main
   git merge-tree --write-tree feature/utc-storage feature/local-display
   ```

| | `feature/utc-storage` | `feature/local-display` |
|---|---|---|
| Tests (passed / failed) | | |
| Does it write `starts_at`, read it, or both? Which file and function? | | |
| What does its code assume `starts_at` means? Quote the comment or docstring | | |
| Does its task card say what `starts_at` means after the change? | | |

Does `merge-base` print the same hash as `main`? Does `merge-tree` report any conflict? ______

### A2 · One red main (10 min)

In the `ah-merge` worktree, merge both branches, run the tests, and print the programme:

```
cd ../ah-merge
git merge --no-ff --no-edit feature/utc-storage
git merge --no-ff --no-edit feature/local-display
python -m pytest -q
python scripts/show_programme.py
```

Then print the programme in `ah-display` too (`cd ../ah-display`, same script) and compare.

1. How many tests pass on the merged build? ______
2. What time does the merged programme show for the escape room, and what is its status at
   the demo clock's 19:00? What does `ah-display` show? ______
3. The escape room is marked *Started*. Does the server agree? Read the closing rule in
   `app/reservations.py` on the merged build and say what a booking at 19:00 would get.
   ______
4. Which of the two branches is wrong? Answer in two sentences. ______

*Optional, 3 minutes:* run the page from `ah-merge` with `uvicorn app.main:app --port 8003`
and open http://127.0.0.1:8003. Stop it with Ctrl+C.

### A3 · The integration test (15 min)

Copy `integration/test_integration_programme.py` from the kit into `ah-merge/tests/`.

**macOS / Linux**
```bash
cp ~/w10-kit/integration/test_integration_programme.py ~/w10-kit/ah-merge/tests/
```

**Windows PowerShell**
```powershell
Copy-Item $HOME\w10-kit\integration\test_integration_programme.py $HOME\w10-kit\ah-merge\tests\
```

Read it first. The clock is fixed at Friday 19:00 festival time with the `fixed_clock`
fixture, and the festival's zone is a constant. Then write the assertions for TODO 1 to 3,
and TODO 4 if you have time.

- [ ] In `ah-merge`: `python -m pytest -q tests/test_integration_programme.py` **fails**.
      Copy the first assertion error.
- [ ] Copy your finished test into `ah-display/tests/` and run it there. It **passes**.
      From `ah-merge`: bash `cp tests/test_integration_programme.py ../ah-display/tests/`,
      PowerShell `Copy-Item tests\test_integration_programme.py ..\ah-display\tests\`. Then
      `cd ../ah-display`, run `python -m pytest -q`, delete the copy again, and go back to
      `ah-merge`.
- [ ] One sentence: why does the same test pass on `feature/local-display` alone?
- [ ] One sentence: why can't it run on `feature/utc-storage` alone? What does that tell
      you about where an integration test has to run?

### A4 · Write the contract, then repair against it (30 min)

Work in `ah-merge`. First copy the contract template and the contract-test skeleton in:

**macOS / Linux**
```bash
cd ~/w10-kit/ah-merge
mkdir -p docs/contracts
cp ~/w10-kit/templates/contract.md docs/contracts/start-times.md
cp ~/w10-kit/integration/test_start_time_contract.py tests/
```

**Windows PowerShell**
```powershell
cd $HOME\w10-kit\ah-merge
New-Item -ItemType Directory -Force docs\contracts
Copy-Item $HOME\w10-kit\templates\contract.md docs\contracts\start-times.md
Copy-Item $HOME\w10-kit\integration\test_start_time_contract.py tests\
```

1. **The contract (10 min).** Fill in `docs/contracts/start-times.md` for `starts_at`. Keep both teammates'
   goals: storage in UTC, and times shown in festival time. Name one owner. Write the five
   rules so a stranger could check them, and at least three examples, including an event
   that starts at 01:00 on Saturday.
2. **The contract tests (8 min).** Open `tests/test_start_time_contract.py`. Put your
   contract's examples in `EXAMPLES` and finish TODO 3 and TODO 4. Run
   `python -m pytest -q tests/test_start_time_contract.py`. Which tests fail: the producer's
   (Ana's side) or the consumer's (Ben's side)? What does that tell you that the integration
   test did not? ______
3. **The repair (10 min).** Make `festival_start` in `app/programme.py` follow your
   contract. If your contract says only `app/festival.py` converts, add the conversion there
   (for example a `to_festival(text)` that uses the existing `parse_utc` and then
   `.astimezone(FESTIVAL_TZ)`) and call it from `festival_start`. Run all the tests. Some of Ben's own tests in `tests/test_programme.py`
   now fail. Why? Update them so they use start times in the contract's format, without
   weakening what they check. Run everything again until it is green.
4. **Commit** on the `integration` branch: `git add -A`, then
   `git commit -m "Start-time contract; the programme reads UTC"`.

- [ ] Before the repair, the consumer tests fail and the producer tests pass
- [ ] After the repair, `python -m pytest -q` is green, including your integration and
      contract tests (about 30 tests, depending on how many examples you wrote)
- [ ] `python scripts/show_programme.py` shows the escape room at 20:00, *upcoming*

### A5 · CI on the merged result (5 min)

On GitHub, each branch's pull request was green. By default, a GitHub Actions workflow
triggered by a pull request tests a merge of the branch into `main`, as `main` was when the
checks ran.

1. Ana's pull request merged first. When Ben's checks ran, which `main` did they test
   against? Were they still valid after Ana's merge? ______
2. Name one repository rule that would have made Ben's branch be tested against the `main`
   that already had Ana's change, and say what it costs. ______
3. *(bash or zsh only, optional)* In `ah-merge`, run the tests under two very different
   time zones: `TZ=Pacific/Kiritimati python -m pytest -q` and
   `TZ=America/Los_Angeles python -m pytest -q`. Same result? Which two design choices make
   that true? ______

### Optional extension · Contract first, with two agents (30 min or more)

Redo the week the other way round. From `afterhours`, make a new branch and worktree from
`main`, and commit your contract and its examples there **before** anyone codes. Then make
two worktrees from that commit, give each one's agent its task card plus one line:
*"Contract: docs/contracts/start-times.md. Convert only in app/festival.py. Test against
the contract's examples."* Merge both into a fresh integration branch and run your
integration and contract tests.

- Did the merge pass the first time? If not, which rule of the contract did an agent break,
  and would you change the contract or the code?
- Which task had to merge first, and why? (Hint: which one does the other need at run
  time?)

Also try `python ~/w10-kit/tools/schedule.py` (PowerShell: `python $HOME\w10-kit\tools\schedule.py`)
and compare its answer with the pairs exercise from class.

## Part B · Your team's product (25 min)

Work in your team's own AfterHours repository.

1. **Pick two features** you will build in parallel next (people, agents, or both). Draw
   their dependency graph on paper, or list the tasks in `tools/schedule.py`. Circle every
   **shared decision**: a field, a format, an endpoint, a rule both features rely on.
2. **Write the contract** for the most important shared decision: copy
   `templates/contract.md` to `docs/contracts/<name>.md`. One owner. At least three
   examples, one of them awkward. Name the producer test and the consumer test.
3. **Worktrees.** Create one worktree per feature. Each feature gets a task card (Week 3
   format) that points at the contract.
4. **CI on the merged result.** Check that your CI runs on pull requests, not only on
   pushes, and open one run's log to see which commit it tested (the checkout step prints
   it: the test merge, or your branch's own commit?). In your branch protection, require
   your test job as a status check. Then make sure a branch is tested against the latest
   `main` before it merges: turn on *Require branches to be up to date before merging*, or
   a merge queue if your repository offers one. Write down which you chose and why.
   A merge queue only runs your GitHub Actions workflow if the workflow is triggered by the
   `merge_group` event: add `merge_group:` next to `pull_request:` under `on:` in your CI file,
   or the queue waits for a check that never comes.
5. Start the Week 10 item of the product checklist (`plan/product-checklist.md` in the
   course repository): link the contract file now. Tick the item only after the homework,
   when both features have merged through CI, and link that CI run on the merged result.

**Homework (about 2 to 3 hours, before Week 11):** build both features in their worktrees,
merge them through CI, and add one integration test that crosses the two. Add a line to the
contract saying what, if anything, it missed.

---

### Hand in

One per pair (Part A):
1. The A1 table, with the `merge-base` and `merge-tree` answers
2. The A2 answers
3. Your `tests/test_integration_programme.py`, its failing output on `ah-merge` and its
   passing run on `ah-display`, and the two A3 sentences
4. `docs/contracts/start-times.md`, `tests/test_start_time_contract.py`, the output showing
   which side failed before the repair, your diff of `app/programme.py` and
   `tests/test_programme.py`, and the final `python -m pytest -q` line
5. The A5 answers

One per team (Part B):
6. A link to the contract, which rule you chose in step 4, and which commit your CI
   tested. By Week 11: the link to the CI run on the merged result of both features

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 10, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 10 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Diagnosis | Names the meaning of `starts_at` as the conflict; shows that each branch is right about the `main` it started from; quotes the task cards and the schema comment | Blames one branch, or blames git |
| Integration test | Fails on the merge and passes on `ah-display`; time fixed with `fixed_clock`, nothing from the host's clock or zone; checks the label **and** that the server accepts the booking | Passes on the merge; calls `datetime.now()`; only checks that the endpoint answers 200 |
| Contract | One named owner; rules a stranger could check; examples include the after-midnight case; both sides tested against the same examples; says which side failed first | No owner, or "the team"; examples only in prose; tests written from the code instead of from the examples |
| Repair | Small and in one place: the reader goes through the contract's conversion; Ben's tests updated to the contract's format and still check the boundary; everything green | Conversions sprinkled in several files; tests weakened or deleted to go green |
| CI | Explains why both pull requests were green and names a rule that tests each branch against the latest `main`, with its cost | "Run CI more often" |
