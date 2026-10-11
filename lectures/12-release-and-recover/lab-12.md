# Lab 12 · Release and Recover

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence packet at the end (one per pair)

In the lecture, release 1.5.0 passed every gate the team had and broke the festival
programme. Today you run that Friday yourselves, on two environments on your laptop:
you ship the bad release, watch what visitors get, roll back, and then build the gate that
would have stopped it. In the second half you find out whether the team's backups can be
restored, and you prove a restore with checks a visitor and an owner would trust.

The releases, the team and the incident are fictional, and the problems were **planted on
purpose**: release 1.5.0's defect and the nightly backup job's defect. The code is real and
everything runs on your laptop. Nothing leaves it.

Agents are allowed in this lab. If one helps you, say where. You own every claim you hand
in. One warning: **do not ask an agent to fix `ops/nightly_backup.py` before Part A4 asks
you to test it.** Finding out what it does is the exercise.

Commands are the same in bash/zsh and PowerShell unless two versions are shown. Every
command runs from the kit folder, `w12-kit`.

| Part | What | Minutes |
|---|---|---:|
| 0 | Set up | 10 |
| A1 | Two environments | 10 |
| A2 | The Friday release | 15 |
| A3 | A gate that asks the visitor's question | 15 |
| A4 | Rehearse a restore | 25 |
| A5 | Ship the fix dark, then flip the flag | 5 |
| B | Your team's product: runbook and one rehearsal | 25 |
| | Evidence packet and hand-in | 10 |

---

## Part 0 · Set up (10 min)

Follow **Set up** in `COURSE/lectures/12-release-and-recover/lab-kit/README.md`. You end in
the folder `w12-kit` with the environment active.

- [ ] `python ops/status.py` lists staging, production and restore, all `not running`
- [ ] A **second terminal** is open in `w12-kit` with the environment active
      (`source .venv/bin/activate` or `.venv\Scripts\Activate.ps1`)

Terminal 1 will run the simulated visitors. Terminal 2 runs everything else.

## Part A1 · Two environments (10 min)

In terminal 2:

```
python ops/deploy.py production 1.4.0
python ops/deploy.py staging 1.4.0
python ops/deploy.py production 1.4.0
python ops/status.py
```

Open http://127.0.0.1:9210 (production) and http://127.0.0.1:9211 (staging) in a browser.
Book a place on production under your own name. The page footer names the release.

Now start the visitors in **terminal 1**, and leave them running until Part A5:

```
python ops/traffic.py production
```

1. The first command was refused. Which rule refused it, and where in `ops/deploy.py` is
   that rule? ______
2. `traffic.py` prints one line every 5 seconds. What does it show, and what does it say it
   cannot show yet? ______

## Part A2 · The Friday release (15 min)

1. **Read before you ship.** Read `releases/1.5.0/RELEASE.md`, and compare the schema with
   the release running now:

   **macOS / Linux**
   ```bash
   diff releases/1.4.0/app/schema.sql releases/1.5.0/app/schema.sql
   ```
   **Windows PowerShell**
   ```powershell
   Compare-Object (Get-Content releases\1.4.0\app\schema.sql) (Get-Content releases\1.5.0\app\schema.sql)
   ```
   **Write your prediction down before you deploy:** where does 1.5.0 stop, and what will
   terminal 1 show? ______
2. **Ship it** through the pipeline, as the team did (terminal 2). Note the clock time.
   ```
   python ops/deploy.py staging 1.5.0
   python ops/deploy.py production 1.5.0
   ```
3. **Look.** Watch terminal 1 for at least three lines. Reload http://127.0.0.1:9210: what
   does a visitor see? Read the end of the production server's log:

   **macOS / Linux:** `tail -n 20 envs/production/server.log`
   **PowerShell:** `Get-Content envs/production/server.log -Tail 20`
4. **Roll back** (terminal 2), and note the time. Watch terminal 1 until two lines in a row
   show no 500s.
   ```
   python ops/rollback.py production
   ```

A `none` among the answers is the second or so while one release stops and the next
starts: a single server cannot switch without a gap. Real systems run two copies and move
traffic between them.

Fill in, from your own terminals:

| | Clock time | What you saw |
|---|---|---|
| Production deploy of 1.5.0 finished | | |
| First 5-second window with 500s | | answers: |
| Rollback started / "Service restored" | | |
| First window with no 500s | | answers: |

5. Which requests failed and which kept working while 1.5.0 served? Why those? ______
6. The release's 12 tests passed. Why did they not catch this? ______
7. The `live` gate passed twice. What exactly does it check (read `ops/gates.py` and the
   `/healthz` route in `releases/1.5.0/app/main.py`)? ______
8. Was staging broken too? How could you have known before production? ______

## Part A3 · A gate that asks the visitor's question (15 min)

1. **Define the SLI.** Open `ops/sli.py`. Its docstring has the SLI as a table. Write
   `is_good()` so that it follows that table, then run its tests:
   ```
   python -m pytest -q ops/tests/test_sli.py          # expect: 10 passed
   ```
2. **Restart the visitors** in terminal 1 (Ctrl+C, then `python ops/traffic.py production`).
   The lines now show good, bad and the SLI.
3. **Put the SLI in the gate.** In `ops/pipeline.json`, change the gates line to:
   ```json
   "gates": ["live", "sli"],
   ```
4. **Try the Friday release again**, on staging (terminal 2):
   ```
   python ops/rollback.py staging            # staging back to 1.4.0, checked by both gates
   python ops/deploy.py staging 1.5.0        # expect: sli FAIL, then an automatic rollback
   python ops/deploy.py production 1.5.0     # expect: refused by the promotion rule
   python ops/status.py --history
   ```

- [ ] `test_sli.py`: 10 passed
- [ ] The staging deploy printed a `sli` line with `FAIL`, rolled back by itself, and staging
      serves 1.4.0
- [ ] Production refused 1.5.0, and nothing changed in terminal 1

5. The `sli` gate sends only `GET` requests, while your SLI also judges bookings. Why? ______
6. Write the stop condition that `ops/pipeline.json` now encodes, in one sentence. ______
7. `places_left >= 0` is part of *good*. Which earlier week's promise is that, and what
   kind of release would it catch that a status code would not? ______

## Part A4 · Rehearse a restore (25 min)

Leave the visitors running in terminal 1: they keep booking while you back up.

**Step 1 · The team's nightly job (5 min).** It has printed `Backup OK` every night since
Week 3. Run it, then restore its backup into the separate instance and check it. Use the
file name it prints:

```
python ops/nightly_backup.py
python ops/restore_check.py backups/nightly-YYYYMMDD.db
```

Read every line of the result. Two checks say `not written yet`; you write them in step 2.

1. Which checks passed? The restored site lists five events: where did they come from?
2. Look in the kit folder. A new file appeared that was not there before. Which one, how
   big is it, and what does that tell you about the defect in `ops/nightly_backup.py`?
   Describe the defect in one sentence. (Do not fix it now.) ______

**Step 2 · The owner's checks (8 min).** In `ops/restore_check.py`, write the two queries
`ORPHANS_SQL` and `OVER_CAPACITY_SQL`. Each must return one row per problem, and no rows
when the data keeps the promise. Then:

```
python -m pytest -q ops/tests/test_restore_check.py   # expect: 7 passed
python -m pytest -q                                   # expect: 21 passed
python ops/restore_check.py backups/nightly-YYYYMMDD.db
```

3. Your two new checks pass on the nightly backup. Is that good news? Which two checks
   still fail, and what does each of them know that yours do not? ______

**Step 3 · A real backup, while visitors book (5 min).**

```
python ops/backup.py production
python ops/restore_check.py backups/production-<the time it printed>.db
```

- [ ] `RESULT: PASS (6 of 6 checks passed)`

4. Copy the lines `Time to a checked restore` and `Data-loss window` into your packet.
   Your restore took well under a second. GitLab's took about 18 hours. Name two reasons
   the numbers are so different. ______

**Step 4 · Make each check fail on purpose (4 min).** A check you have never seen fail is
a check you cannot trust.

```
python ops/tamper.py backups/production-<time>.db --orphan
python ops/restore_check.py backups/production-<time>-orphan.db
python ops/tamper.py backups/production-<time>.db --oversell
python ops/restore_check.py backups/production-<time>-oversell.db
```

5. Which check failed each time? Which checks still passed on the damaged copies, and why
   is that correct? ______

**Step 5 · Put numbers on it (3 min).**

6. If backups ran only once a day, at 03:00, and production's disk failed right now, how
   much would be lost? ______ With hourly backups? ______
7. Write the team an RPO and an RTO for festival weekend, and say which of today's
   measurements supports each. ______

## Part A5 · Ship the fix dark, then flip the flag (5 min)

1. Read `releases/1.5.1/RELEASE.md`. Then, in terminal 2:
   ```
   python ops/deploy.py staging 1.5.1
   python ops/deploy.py production 1.5.1
   ```
   Staging's flag file (`flags/staging.json`) has `"event_categories": true`; production's
   has `false`. Open both sites: the category buttons appear on staging only.
2. **Release the feature in production without a deploy.** Set the flag to `true` in
   `flags/production.json` with your editor, or:

   **macOS / Linux**
   ```bash
   printf '{\n  "event_categories": true\n}\n' > flags/production.json
   ```
   **Windows PowerShell**
   ```powershell
   Set-Content -Path flags\production.json -Value '{ "event_categories": true }' -Encoding ascii
   ```
   Reload http://127.0.0.1:9210. Run `python ops/status.py`: is the pid the same as before?
3. Click **Games**. Why is the list empty, on production and on staging alike? (Hint: which
   category did the existing events get when 1.5.1 added the column? Filling in real values
   for old rows is a *backfill*, Week 13.) What would a fresh database, like the one the
   tests use, show? ______
4. Turn the flag off again (`false`) and reload.

Now stop the visitors in terminal 1 with **Ctrl+C** and copy their last two lines (the
totals and the error budget) into your packet. Then stop every server:

```
python ops/status.py --stop all
```

## Part B · Your team's product (25 min)

This ticks the Week 12 item on the product checklist: *runbook for deploy, rollback, and
restore; one restore rehearsal logged.*

1. **Runbook (15 min).** Copy `templates/runbook.md` into your product as
   `docs/runbook.md` and fill in deploy, roll back and restore **for your product**. Every
   step is a command to copy, what you expect to see, and what to do if you do not. Name the
   stop conditions, and say when rolling back is not safe.
2. **One rehearsal (10 min to start).** Back up your product's database and restore it into
   a separate instance: another folder, another port, another database file. Never restore
   over your real one. Check it: does it serve, do your invariants hold, is it the same
   data, is there any data at all. If your product uses SQLite: `ops/dbfacts.py` (the
   canonical dump) works on any SQLite file, your two queries work on any AfterHours schema,
   and `ops/backup.py` shows the three lines that call the backup API. Log it in
   `docs/rehearsals/<date>.md` from `templates/rehearsal-log.md`.
   *If the rehearsal does not fit, finish it at home (≈45 min); the runbook is due today.*

## Evidence packet and hand-in (10 min)

| | |
|---|---|
| **Release** | Your A2 table and answers 5 to 8 |
| **Gate** | Your `is_good()`; the `gates` line; the output of the staging deploy that failed the `sli` gate and rolled back; the refused production deploy (A3) |
| **Restore** | The nightly job's restore check and your one-sentence defect (A4 step 1); your two queries; the passing restore check of the real backup; the two damaged-copy results and your answer 5 |
| **Numbers** | The traffic totals and error budget line; restore time; data-loss window; your RPO and RTO with their evidence |
| **Flag** | Your answer to A5 question 3 |
| **Product** | Links to `docs/runbook.md` and your rehearsal log (B) |

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 12, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 12 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### Optional extensions

- **Restore production for real.** Read `ops/restore.py` first: what does it refuse to do,
  and what does it keep? Then `python ops/restore.py production backups/production-<time>.db
  --confirm production`, and compare `python ops/status.py --history` before and after. Which
  bookings did production lose?

- **Make the nightly job trustworthy.** Change `ops/nightly_backup.py` so it refuses to run
  when the database file does not exist, exits with a non-zero code, takes the path from
  `ops/pipeline.json`, and writes a manifest (or simply calls `backup()` from
  `ops/backup.py`). Show that `restore_check.py` passes on its output.
- **An automatic stop condition.** Write `ops/watch.py`: probe production like the `sli`
  gate every 5 seconds for 2 minutes after a deploy, and call `rollback()` from
  `ops/rollback.py` when two windows in a row are below the SLO.
- **Refresh staging from production.** Restore a production backup into staging with the
  backup API, then deploy 1.5.0 there. Explain why teams refresh staging from production,
  and what personal data that copies into staging.
- **A canary by flag.** Extend `releases/1.5.1/app/flags.py` so a flag can be on for a
  percentage of visitors (hash of the attendee name), and design the stop condition for it.

### How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Release | Prediction written before the deploy; the table filled from your own terminals; explains why tests and the `live` gate passed (fresh database, `SELECT 1`) | Table copied from the chapter, or "the tests were wrong" without saying what they could not see |
| Gate | `is_good()` passes its tests; the `sli` gate stops 1.5.0 in staging and production refuses it; stop condition stated precisely | Gate added but never seen failing; SLI judged by status code only |
| Restore | Explains why the nightly backup passes four checks and fails two; both queries correct and seen failing on damaged copies; restore time and data-loss window measured | Queries pass their tests but the point that a check for broken rows cannot see missing rows is missed |
| Numbers | RPO and RTO stated with the measurement behind each; GitLab comparison names data size and disk speed or practice | Targets with no evidence |
| Product | Runbook with commands, expected results and stop conditions; a rehearsal into a separate instance, logged | A runbook of intentions ("restore the backup"), or a restore over the real database |
