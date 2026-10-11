# Lab 2 · One Request, Two Waitlists

**Time:** 2 hours · **Work in:** pairs for Part A, your team for Part B · **Hand in:** the
evidence listed at the end (one per pair, plus your team's two documents)

In the lecture you saw two coding agents turn the same one-line request into two different
waitlists, and skip the same big decision. Today you pin down what each one does, write
acceptance examples that tell them apart, decide a policy, and write your own team's scope
agreement.

Agents are allowed in this lab. If one helps you, say where. You own every claim you hand in.
One caution for Part A: if you ask an agent to write your examples, it will read the code and
write examples that describe what the code already does. The point of an example is to say
what the code **should** do.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Use one or
the other; don't mix them.

---

## Part 0 · Set up (10 min)

You need Python 3.11 or newer. Replace `COURSE` with the folder where you keep the course
repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/02-specify-the-promise/lab-kit ~/afterhours-lab2
cd ~/afterhours-lab2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\02-specify-the-promise\lab-kit $HOME\afterhours-lab2
cd $HOME\afterhours-lab2
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
```

Then, in either shell (the commands are the same), run each app's own tests inside its
folder, and the examples against all three:

```
cd base
python -m pytest -q                 # expect: 8 passed
cd ../waitlist-agent-a
python -m pytest -q                 # expect: 23 passed
cd ../waitlist-agent-b
python -m pytest -q                 # expect: 21 passed
cd ..
python scripts/compare.py           # expect the table below
```

```
example                                                      base      agent A   agent B
1 someone with a place cannot also wait for one              fail      PASS      fail
2 joining twice tells you that you were already on the list  fail      fail      PASS
```

- [ ] Three test suites green: 8, 23, 21
- [ ] `compare.py` prints the table above

The kit's `README.md` explains every folder. Read the two `PROVENANCE.md` files before Part A:
they say exactly who produced each folder, from what, and what was changed afterwards
(nothing, apart from the notes).

## Part A · The kit exercise (70 min)

### A1 · Meet the two waitlists (15 min)

Start both apps, each in its own terminal with the environment activated:

```
cd waitlist-agent-a
uvicorn app.main:app --port 8001
```
```
cd waitlist-agent-b
uvicorn app.main:app --port 8002
```

Open http://127.0.0.1:8001 and http://127.0.0.1:8002 side by side. Do the same three things
in both, and write down exactly what each page says.

1. Type **Sam**. Press **Join waitlist** on the Maker Workshop (it is seeded full). Then press
   it again.
2. Type **Maya**. Press **Reserve** on the escape room (one place left). Then press **Join
   waitlist** on the escape room, still as Maya.
3. Read each app's `CHANGES.diff`. Find the one function that decides whether someone may
   join. Which file and which line?

| | Agent A (port 8001) | Agent B (port 8002) |
|---|---|---|
| Sam, first press | | |
| Sam, second press | | |
| Maya joins after reserving | | |
| Function that decides, file:line | | |

Stop both servers (Ctrl+C) when you are done. To start again with fresh data, delete
`afterhours.db` in that app's folder.

### A2 · The divergence table (15 min)

For each question, find what each app does: read the code, try the page, or send a request.
In the last column, say whether the one-line request decided it.

| # | Question the request left open | Agent A | Agent B | Decided by the request? |
|---|---|---|---|---|
| 1 | Can you join while places remain? | | | |
| 2 | In what order do people wait? | | | |
| 3 | Who gets a place that frees up? | | | |
| 4 | Is anyone told when a place frees up? | | | |
| 5 | Is anything paid, and when? | | | |
| 6 | The same name joins twice | | | |
| 7 | Someone who already has a place joins | | | |
| 8 | "Sam", " Sam " and "sam" | | | |
| 9 | You get a place: are you still waiting? | | | |
| 10 | The event has already started | | | |
| 11 | Did the agent change anything else? | | | |
| 12 | What did its final report say about open decisions? | | | |

Hint for row 3: neither app can free a place, because nobody can cancel yet. The examples file
has a helper, `free_a_place(event)`, that deletes one reservation row to stand in for a
cancellation. You will use it in A3.

### A3 · Examples that pin a decision (30 min)

Open `tests/test_waitlist_examples.py`. Read the two given examples and the helpers above them.
Then add **three** examples of your own, using the template at the bottom of the file:

- **(a) One more example that splits the agents.** Pick a row of your divergence table where A
  and B differ, decide what AfterHours *should* do, and write it down.
- **(b) The freed place.** Write your pair's policy from the lecture (0:12) as an example: a
  place frees up (`free_a_place`) while Sam is waiting and Lee is not. What must happen?
- **(c) A decision nobody made.** Pick row 9 or row 10 of your table and decide it. (Row 4,
  telling people, needs a way to send messages that neither app has; leave it for Part B.)

Each example needs a docstring in Given / When / Then with names and numbers, one action in
the *When*, and assertions that check the *Then*. Run:

```
python scripts/compare.py --why
```

Copy the final table into your notes. Then answer:

1. Does every one of your examples fail on `base`? If one passes there, what is it testing?
2. Which of your examples fail on both agents? For each: is that a bug in both, or a decision
   nobody had made?
3. Pick one example that passes on one agent. Could a reasonable team have decided the
   opposite? What would they have written instead?

### A4 · Who wins? (10 min)

```
python scripts/who_wins.py
```

The policies in this script were written by the course staff; only "open to all" is what the
agents' apps really do. The people are made up.

1. Change one setting and run it again: `--kept 1`, `--offer-minutes 120`, or `--seed 3`.
   Whose outcome changed, and why?
2. Choose the freed-place policy you would ship for AfterHours. Write its rules table: at least
   four rows (*situation → outcome*), including what happens when the event starts. Name who
   it helps and who it hurts.

### Optional extension · Check a claim (15 min)

Agent B's report says: *"A test has four people join at once and checks they get positions 1
to 4. When I temporarily weakened that step, the test failed."* Make a scratch copy of
`waitlist-agent-b/`, remove the `BEGIN IMMEDIATE` in `app/waitlist.py` (and its `COMMIT`), and
run `python -m pytest -q tests/test_waitlist.py` ten times. Which test fails, and how often?
Does the evidence match the claim? Delete the scratch copy afterwards.

## Part B · Your team's product (25 min)

Work in your team's own AfterHours repository (set up in Lab 1, Part 6). Pick the next
feature your team will build (a waitlist is fine; so is anything else on your festival's list).

1. **Scope agreement.** Copy `templates/scope-agreement.md` from the kit to `docs/scope.md` and
   fill it in. One page. One named owner. At least two **Out** items and two **Open
   questions**, each with a person and a date.
2. **Five acceptance examples.** Copy `templates/examples.md` to `docs/examples.md`. Write five
   examples in Given / When / Then, with names and numbers. At least one is a **usability**
   criterion (who, what task, how fast, pass mark) and one is an **accessibility** criterion
   (which assistive technology, what they must hear or reach, the WCAG 2.2 criterion it ties
   to).
3. **Checks.** Each example names its check. Turn at least one functional example into an
   automated test now. Usability and accessibility criteria are checked by a person following
   written steps: write the steps. The remaining automated tests are built in Week 5.
4. Tick the two Week 2 items of the product checklist (`plan/product-checklist.md` in the
   course repository) in your `docs/checklist.md` (started in Lab 1, Part 6) and link each one
   to its evidence.

**Homework (about 2 hours, before Week 3): two real interviews.** Use
`templates/interview-guide.md`. Interview two people who could use your festival, not your
teammates. Ask about the past. Write up each on one page in `docs/interviews/` with labels,
not names. Then update the **Problem** and **Open questions** of your scope agreement with
what you learned.

---

### Hand in

One per pair (Part A):
1. The A1 table and the A2 divergence table
2. Your `tests/test_waitlist_examples.py` and the final `compare.py --why` table, with your
   answers to the three A3 questions
3. The A4 answers: what changed and why; your rules table, with who it helps and hurts

One per team (Part B):
4. Links to `docs/scope.md` and `docs/examples.md` in your repository, and to the automated test
5. By Week 3: `docs/interviews/` with two one-page write-ups

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 2, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 2 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Divergence table | Every cell checked by running or reading, not guessed; the request column says "no" where it should; notices A's change to reservations | Cells copied from the reports, or rows left blank |
| Examples | Three new examples, each one decision, Given / When / Then with names and numbers; all fail on `base`; (b) uses `free_a_place` and states what happens to everyone involved under the chosen policy (who gets the place, and who is refused, if anyone) | Examples that describe the current code; vague names ("a user"); pass on `base` |
| Reasoning | Separates "bug in both" from "decision nobody made"; says what the opposite decision would look like | Treats every failure as a bug |
| Policy | Rules table covers the start time and every boundary the chosen policy has (for a timed offer: an offer running out, twice in a row; for a lottery: when the draw happens and who is in it); names who it hurts | Picks a policy without saying who loses; leaves out a boundary the policy has |
| Scope agreement | One page, named owner, real Out items, open questions with person and date, usability and accessibility criteria that can be checked | Owner missing or "the team"; criteria like "easy to use" |
