# Lab 13 · Change Without Forgetting

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence packet at the end (one per pair)

In the lecture you saw Knight's eighth server, photographed v1's change-day rule (bugs
included), ordered the steps of expand, migrate, contract, and watched a guard refuse a
contract that would have lost 29 tickets' moves. Today you do the migration yourself, on a
copy of production, with two versions of the app writing throughout.

Agents are allowed in this lab. If one helps you, say where. Two rules for today: **the
observed values in a characterization test come from running the code**, and **the labels
(promise or quirk) come from `docs/requirements.md`**. Never let either one decide the other.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell** where they
differ. Use one or the other; don't mix them. Replace `COURSE` with the folder where you
keep the course repository.

---

## Part 0 · Set up (10 min)

You need Python 3.11 or newer and git.

**macOS / Linux**
```bash
cp -R COURSE/lectures/13-change-without-forgetting/lab-kit ~/afterhours-lab13
cd ~/afterhours-lab13
git init -q
git add -A
git commit -qm "kit, as handed out"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests/characterization   # expect: 88 passed
python -m pytest -q tests/v2                 # expect: 17 passed
python -m pytest -q tests/migration          # expect: 8 failed, 19 passed
python -m pytest -q tests/flags              # expect: 2 failed, 1 passed
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\13-change-without-forgetting\lab-kit $HOME\afterhours-lab13
cd $HOME\afterhours-lab13
git init -q
git add -A
git commit -qm "kit, as handed out"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q tests/characterization   # expect: 88 passed
python -m pytest -q tests/v2                 # expect: 17 passed
python -m pytest -q tests/migration          # expect: 8 failed, 19 passed
python -m pytest -q tests/flags              # expect: 2 failed, 1 passed
```

If `git commit` asks who you are, run `git config user.name "Your Name"` and
`git config user.email "you@example.com"` once, then commit again.

- [ ] The four expected results above
- [ ] You have read `docs/requirements.md` (T1 to T6, M1, M2) and the step table in
      `docs/migration-plan.md`

Why 88? `tests/characterization` holds 22 photographs, and each runs four times: v1 on
the old table, v1 on the expanded table, v2 on the expanded table, v2 on the contracted
table (see `tests/characterization/conftest.py`). The failing tests are yours to fix in A3
and A5.

## Part A · The kit (70 min)

### A1 · Photograph change-day (15 min)

Open `tests/characterization/test_change_day_photos.py`. It has one row and five TODOs.

1. For each TODO, add a row with `None` as the observed status, and run
   ```
   python -m pytest -q tests/characterization/test_change_day_photos.py
   ```
   The failure message tells you what the app answered (`v1 answered 200: ...`). Copy the
   status into the row. Run again until all rows pass on all four setups. **Don't open
   `docs/requirements.md` while you do this.**
2. Now read T3 and fill in each row's `label`: `"promise: T3"` or `"QUIRK: ..."` with the
   sentence of T3 it contradicts. Leave every observed value as it is.
3. Answer in one or two sentences each:
   - Your quirk rows pass on v2 too. Why is that what we want **during** the migration?
   - Who decides whether the quirk is fixed, and when? What happens to the photograph then?

- [ ] Six rows, all passing on all four setups (24 test runs)
- [ ] Every row labelled; every quirk names the sentence of T3 it contradicts
- [ ] Commit: `git commit -am "A1: photograph change-day (observed values from v1; labels from T3)"`

**Optional (only if you finish early):** `COURSE/lectures/13-change-without-forgetting/demo/agent-characterization/`
holds characterization tests two agents wrote for v1. Find the test in each file that pins
the same quirk. How did each agent report it?

### A2 · Expand, and two versions on one table (10 min)

Work on a copy of "production": a v1 database with 600 tickets.

```
python scripts/make_production_db.py --db prod.db
python migrate.py --db prod.db meaning --save before.json
python migrate.py --db prod.db status
python migrate.py --db prod.db expand
python migrate.py --db prod.db status
python migrate.py --db prod.db verify
```

1. What did `expand` add, and what did it remove? Why does v1 keep working afterwards?
   (Look at the INSERT in `v1/tickets.py`.)
2. `verify` says `missing: 600`. Read the READ rule at the top of `v2/tickets.py`. What
   day does a v2 gate use for one of those 600 tickets, and why is that right during the
   window?
3. Try the steps out of order and copy what the guards say:
   ```
   python migrate.py --db prod.db flag multi_day_passes on
   python migrate.py --db prod.db contract
   ```

- [ ] Answers to 1 to 3, with the two refusals copied in

### A3 · Write the backfill (25 min)

Open `migrations/backfill.py`. The rules B1 to B6 are in its docstring and in
`docs/migration-plan.md`; the three verification queries are in `migrations/steps.py`
(`CHECKS`). Complete the three TODOs.

```
python -m pytest -q tests/migration/test_backfill.py     # 6 tests: B1, B2, B3, B4 (x2), B5
python -m pytest -q tests/migration                      # expect: 27 passed when you are done
```

Then run it on your copy of production:

```
python migrate.py --db prod.db backfill
python migrate.py --db prod.db verify          # expect: all three checks 0, "ready"
python migrate.py --db prod.db backfill        # run it again: expect 0 rows
```

1. Paste the SQL condition that picks the rows your backfill changes. Point to the part
   that handles B4 and the part that keeps passes out (B2).
2. `test_b5_...` counts rows per transaction from outside your code. Why does the batch
   size matter on a festival Friday? (Think of Lecture 1's Patch C.)
3. B6 says to copy inside the database. The supplied tests don't check B6, so a
   reviewer has to read the code for it. Describe the gap that reading `day` into Python
   and writing it back later would open, and which later step would still save the data.

- [ ] `tests/migration`: 27 passed
- [ ] `verify` all zeros on `prod.db`; a second backfill changes 0 rows
- [ ] Commit: `git commit -am "A3: backfill (B1-B6)"`

### A4 · Rehearse the migration window (10 min)

```
python scripts/rehearse.py --runs 3
```

Each run copies production, then runs the whole plan while v1 and v2 sell and move tickets
through the real apps, with the backfill running in its own thread. It keeps a record of
every write the apps confirmed and compares the final meaning with it.

1. Paste the summary line and one run's steps 3 to 7.
2. In your run, which guard refused what, at which step, and why?
3. The counts differ between your three runs. Why? Why must PASS not differ?
4. Finish the migration by hand on `prod.db` and compare meaning with Part A2's snapshot:
   ```
   python migrate.py --db prod.db retire v1
   python migrate.py --db prod.db contract
   python migrate.py --db prod.db meaning --compare before.json
   ```
   Why does `--compare` show no differences here, when the rehearsal needed its own record
   of writes?

- [ ] `3 of 3 rehearsals passed`
- [ ] `no differences` on `prod.db`

**Optional:** run the naive backfill from the lecture, with the guard and then without it:
```
python scripts/rehearse.py --backfill "COURSE/lectures/13-change-without-forgetting/demo/naive_backfill.py:backfill"
python scripts/rehearse.py --backfill "COURSE/lectures/13-change-without-forgetting/demo/naive_backfill.py:backfill" --skip-guard
```
(PowerShell: the same, with backslashes, for example
`--backfill "C:\Users\you\course\lectures\13-change-without-forgetting\demo\naive_backfill.py:backfill"`.
Keep the quotes if the path has spaces. The script splits the function name off at the last
colon, so a drive letter is fine.)

### A5 · Retire a stale flag (10 min)

The `flags` table has a row `wristband_mode`, off since the 2025 festival.

1. Find every reader and every mention:
   ```bash
   grep -rn "wristband_mode" v1 v2 migrations scripts tests docs      # macOS / Linux
   ```
   ```powershell
   Get-ChildItem -Path v1,v2,migrations,scripts,tests,docs -Recurse -Include *.py,*.sql,*.md | Select-String "wristband_mode"
   ```
2. Check its value and history: `python migrate.py --db prod.db status`, and read the `note`
   in `v1/db.py`.
3. Remove the dead branch from **v2** only. v1 retires with its copy. Run:
   ```
   python -m pytest -q tests/flags             # expect: 3 passed
   python -m pytest -q tests/characterization  # expect: unchanged (108 passed with A1's six rows)
   ```
4. Answer:
   - The row can be deleted once no running version reads it. Have those conditions been
     met on your `prod.db`? What evidence would you need before deleting it in production?
   - A teammate proposes reusing the name for the passes switch, "since it's unused". Give
     two reasons against, one from Knight and one from this kit.

- [ ] `tests/flags`: 3 passed; characterization unchanged
- [ ] Commit: `git commit -am "A5: v2 no longer reads wristband_mode (off since Oct 2025)"`

## Part B · Your team's product (25 min)

Choose one schema change your product needs (or will soon): a split column, a rename, a
new required field, a one-to-many. Work in your team's own repository.

1. **Plan** it in `docs/migrations/0001-<name>.md`, using this outline (the kit's
   `docs/migration-plan.md` is a worked example):
   ```
   Requirement / promise that must survive (write it as M1 is written)
   Shapes of the table: old · expanded · contracted
   Steps: expand · deploy new version · backfill · retire old version · catch up and verify ·
          (switch on the new feature) · contract · compare meaning
   During the window: what each version reads and writes (a small table)
   Backfill rules: which rows, safe to re-run, catches up, batch size
   Verification queries: each counts rows that would be wrong after the contract
   Meaning: what the data means to the app, and how you compare it
   Guards: what each irreversible step refuses, and where the check runs
   Which steps can't be undone
   ```
2. **Photograph** the behaviour the change touches: at least three characterization tests,
   each labelled promise or quirk against your `docs/examples.md` or scope agreement.
3. **Expand**: write the expand migration and make your app write both shapes. Your existing
   tests must pass before and after the expand step.

**Homework (≈2 h, before Week 14):** the backfill (with a test for re-running and for
catching up), retiring the old reads, the contract step with a guard, and a meaning
comparison on a copy of your data. Commit the output of each step to
`docs/migrations/0001-<name>.md`.

Product checklist, Week 13: *One schema change done as expand → migrate → contract*
(evidence: migration files and their verification).

## Part C · Evidence packet and one measurement (10 min)

| | |
|---|---|
| **Requirement** (quote M1 and T6) | |
| **Decision** (the order of steps, the compatibility rules, and what you rejected) | |
| **Change** (commit hashes: A1, A3, A5) | |
| **Check** (commands and results: tests, `verify`, rehearsal 3 of 3, `meaning --compare`) | |
| **Result** (ready or not; what is still open: the T3 quirk, the `wristband_mode` row) | |

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 13, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 13 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

---

### Hand in (one per pair)
1. `test_change_day_photos.py` with six labelled rows, and your two A1 answers
2. The A2 answers with the two refusals
3. Your backfill's SQL condition and the three A3 answers
4. The rehearsal summary, one run's steps 3 to 7, the four A4 answers
5. The A5 search output, the diff, and your two answers
6. Part B: links to your migration plan, the three characterization tests, and the expand step
7. The evidence packet (each of you hands in your measurement row separately)

### How this is marked (studio practice, formative)
| | Strong | Developing |
|---|---|---|
| Photographs (A1) | Observed values from running the code; labels from T3 with the sentence quoted; quirks kept, reported, not fixed | Values taken from T3, or a quirk "fixed" in the test or the code |
| Backfill (A3) | All six tests pass; the condition covers NULL rows and moved rows and excludes passes; batches explained with the write lock | Passes the tests by accident (for example, only fills NULLs and B4 fails), or one big transaction |
| Rehearsal and order (A2, A4) | Names each refusal with its step and reason; explains why counts vary and PASS doesn't; explains why a simple before/after comparison works on a quiet copy only | Copies the output without explaining the guards |
| Flag (A5) | Every reader found; reader removed before the row; two concrete reasons not to reuse the name | Deletes the row first, or reuses the name |
| Part B | A plan with a read/write table for the window, verification queries, a meaning definition, and the irreversible steps named; tests pass around the expand step | A single migration that renames or drops in one step |
