# Lab 14 · Hand It Over

**Time:** 2 hours · **Work in:** pairs for Part A, your whole team for Part B · **Hand in:**
the evidence at the end (Part A one per pair, Part B one per team) · **Homework:** the
maintenance challenge on your partner team's product (about 3 hours for the team)

Today you are on both sides of a handover. In Part A you receive a repository you have never
seen, the kit's **fallback repository**, and add the core of a feature to it using only what
is written there. In Part B you hand your own AfterHours to your partner team, and watch
them try to run it without helping.

**Before this lab** (set in the lecture, about 1.5 to 2 hours): your team has filled in
`lab-kit/handover-checklist.md` as `docs/handover.md` in your repository, done the
clean-clone rehearsal it describes, and given your partner team access to the repository
(item H1). Your instructor has paired the teams.

Agents are allowed, except in A1, which is agent-off. If one helps you, say where. You own every
claim you hand in.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Use one or
the other; don't mix them.

| Part | What | Minutes |
|---|---|---:|
| 0 | Set up the fallback repository, following only its README | 10 |
| A1 | Find your way before you change anything (agent-off) | 15 |
| A2 | Make the change: the core of the maintenance challenge | 40 |
| A3 | Score the handover you received | 15 |
| B | The swap: hand over, receive, observe | 30 |
| | Evidence and hand-in | 10 |

---

## Part 0 · Set up, as a newcomer (10 min)

**Start a timer now.** From this point until A1, use only the fallback repository's own
README. Replace `COURSE` with the folder where you keep the course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/14-hand-it-over/lab-kit/fallback-repo ~/afterhours-fallback
cd ~/afterhours-fallback
git init -q -b main && git add -A && git commit -qm "fallback repository, as handed over"
# now follow README.md, section 1, exactly as written
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\14-hand-it-over\lab-kit\fallback-repo $HOME\afterhours-fallback
cd $HOME\afterhours-fallback
git init -q -b main; git add -A; git commit -qm "fallback repository, as handed over"
# now follow README.md, section 1, exactly as written
```

- [ ] `python -m pytest -q` says `15 passed`. Time on the timer: ____ min
- [ ] In a second terminal (environment activated), `uvicorn app.main:app` runs and
      http://127.0.0.1:8000 shows five events. Stop it again with Ctrl+C.
- [ ] Every question you had, and whether the README answered it:

| Time | Question | Answered by (file, section) or "not answered" |
|---|---|---|
| | | |

## Part A · The handover test, on the fallback repository (70 min, pairs)

You are the receiving team. The organisers want **drop-in events** (the request and the
acceptance examples are in `lab-kit/maintenance-challenge.md`, sections 1 and 3). The fallback
repository's exact contract (field name, status code, message) is in that file's
**Appendix A**. Read those three parts now (3 minutes).

### A1 · Find your way before you change anything (15 min) · agent-off

Laptops open for reading only: no agent, no running anything, no search engine. The README's
full reading path (its section 3) takes about 30 minutes, so today read only this subset, in
this order (about 10 minutes): `AGENTS.md` (Promises and Map), `app/reservations.py`,
`app/migrations/README.md`, `docs/adr/0002-…`, and the table in `docs/known-risks.md`. Then
write your answers (about 5 minutes); you will check them in A2. If your team later falls back
to this repository for the whole challenge, read the full path first.

1. **The promises.** Which promises must still hold after your change? For each, name the test
   that protects it.
2. **The map.** List every file you expect to change or add for D1 to D4, and what changes in
   each. Which existing tests do you expect to have to change? (Your prediction; check it in
   A2.)
3. **The schema.** How does this repository change its database schema? What would happen if
   you added the column to `app/schema.sql` instead: what would the tests say, and what would
   the festival's existing database do? Where did you find the answer?
4. **The risks.** Name one known risk from `docs/known-risks.md` that your change must not make
   worse, and one it will add.

### A2 · Make the change (40 min)

Implement the core of the challenge on the fallback repository: **D1 at the API** (a drop-in
event can be created and is listed with its kind and door limit), **D2**, **D3** and **D4**,
following Appendix A, on a branch (`git switch -c drop-in`). Work the way the README's section 4 asks:

1. **Tests first.** Write tests for D1, D2 and D4 whose expected values come from the
   acceptance examples and Appendix A, not from your code. Run them and watch them fail.
2. **The migration.** Add the schema change as a numbered file in `app/migrations/`
   (`app/migrations/README.md` shows the form).
3. **The code**, until your new tests pass and `python -m pytest -q` shows every original test
   still passing, unchanged.
4. **Check your A1 predictions.** Which files did you actually change? Did any existing test
   need changing? Write down where your prediction was wrong, and why.

You may use an agent here. If you do, give it the same limits the challenge gives you (only
the repository; no editing existing tests), and check what it did against your A1 map.

- [ ] New tests failed before the change and pass after it
- [ ] `python -m pytest -q`: all passed; `git diff --stat main -- tests/test_basics.py tests/test_concurrency.py tests/test_migrations.py tests/test_runbook.py` prints nothing
- [ ] `app/schema.sql` is unchanged (`git diff --stat main -- app/schema.sql` prints nothing)

**Optional extension** (if you finish early; the full challenge needs these anyway):
D1 on the page (no Reserve button, the words "Drop-in: no booking needed" and the door
limit); D5 by keyboard (Tab through the programme in Chrome or Firefox; write down what you
observe); D6 (README test count, `AGENTS.md`, a decision record for the 409, known risks).

### A3 · Score the handover you received (15 min)

1. Go through `lab-kit/handover-checklist.md` for the **fallback repository**. For each item:
   yes, partly or no, with the evidence. Be strict. A good handover still has gaps. Did the
   fallback say so itself, or did you find a gap it does not mention?
2. Of everything that helped you in Part 0 and A1, which three things does **your own team's**
   repository not have yet? Write them as three issues for your team.

## Part B · The swap (30 min, whole team)

Your team splits in two: **two receivers** and **two observers**. (Teams of three: one
observer.)

1. **Hand over (5 min).** Check that the other team can clone your repository and open pull
   requests (checklist H1). Give them the link. From now until the challenge closes, nobody on
   your team helps them, answers a question or drops a hint.
2. **Receive and observe (20 min).**
   - **Receivers** start the maintenance challenge on the partner team's repository: start the
     first-run clock at `git clone` and fill in Appendix B of `maintenance-challenge.md` as you
     go. The 45-minute first-run budget starts now; you continue it at home.
   - **Observers** sit with the partner team's receivers while they work on **your**
     repository. Do not help, do not point, do not react. Write down every stall: the time,
     what they were looking for, and whether your repository had the answer. This is Week 9's
     usability session, with your repository as the interface.
3. **Swap notes (5 min).** Observers: turn your top three stalls into issues on your own
   repository, with the evidence ("12:04, looked for how to run the tests for 4 minutes;
   README says `pytest` but the package is not installed by `requirements.txt`"). Receivers:
   write down where you are on the first-run clock.

This lab starts the Week 14 line of the product checklist: *handover package complete; another
team completed the maintenance challenge* (evidence: the handover checklist; the other team's
pull request).

## Evidence and hand-in (10 min)

**One per pair (Part A):**
1. Your Part 0 time and questions table
2. Your A1 answers, and your A2 note on where each prediction was right or wrong
3. `git diff --stat main` and the `pytest` output from A2, and the change itself. Commit
   everything on your `drop-in` branch, new files included (`git add -A`, then
   `git commit -m "drop-in events"`), then `git diff main > a2.diff` (or push the branch)
4. Your A3 scoring of the fallback repository, and your three issues for your own team

**One per team (Part B):**
5. The observers' stall notes and the issues they opened
6. The receivers' first-run log so far

## Homework · The maintenance challenge (about 3 hours for the team)

Finish the challenge on your partner team's product, as `lab-kit/maintenance-challenge.md`
describes: the pull request with its evidence packet, the challenge log and the handover
feedback, before the challenge closes. **If their product will not run within the 45-minute
first-run budget,** stop, write the first-run report, and do the whole challenge on the
fallback repository instead (section 5 of the challenge). Your Part A work is your starting
point.

## How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| First run | Time recorded; every question logged with where the answer was, or that there was none | "It worked" with no record |
| Find your way (A1) | Promises with their tests; a file map; the schema question answered with its source; predictions written before A2 and checked after | Map written after the change, or copied from the code |
| The change (A2) | Tests first, expected values from the examples; D1 to D4 pass; original tests unchanged; schema changed by migration; wrong predictions explained | Tests written after, or derived from the code; `schema.sql` edited |
| Scoring (A3) | Strict and evidenced, including a gap the fallback does not mention; three concrete issues for your own team | Every item "yes"; issues too vague to act on |
| The swap (B) | Observers neutral and specific (times, what was sought, whether it existed); issues opened | Notes that coach or blame; no issues |
