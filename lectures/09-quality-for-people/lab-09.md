# Lab 9 · Quality Is Experienced by People

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence at the end (one per pair)
· **Homework:** one unaided usability session with another team (about 1.5 hours)

The kit's page has six problems we planted on purpose. The backend is fine and every test
passes. Today you find the problems the way people meet them, with manual procedures on named
browser and screen-reader combinations, then fix the page and prove the fixes the same way.

**Green backend tests establish nothing about focus, announcements, contrast or what a person
believes happened.** `pytest` will say `9 passed` before and after your fixes. You will record
it, and you will not use it as evidence for anything on the page.

Agents are allowed. If one helps you, say where. You own every claim you hand in, and a claim
about what a screen reader says counts only if one of you heard it.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Use one or
the other; don't mix them.

---

## Part 0 · Set up (10 min)

You need Python 3.11 or newer and a supported browser (see the table in `checklist.md`). For
Part A2 one of you needs a screen reader: VoiceOver (built into macOS) or NVDA (free, Windows:
https://www.nvaccess.org/download; install it **before** the lab if you can). Replace `COURSE`
with the folder where you keep the course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/09-quality-for-people/lab-kit ~/afterhours-lab9
cd ~/afterhours-lab9
git init -q && git add -A && git commit -qm "kit"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # expect: 9 passed
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\09-quality-for-people\lab-kit $HOME\afterhours-lab9
cd $HOME\afterhours-lab9
git init -q; git add -A; git commit -qm "kit"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                 # expect: 9 passed
```

Use **two terminals**, both in `afterhours-lab9` with the environment activated. Terminal 1
runs the app; terminal 2 runs `who_booked.py` and `contrast.py`.

- [ ] `9 passed`
- [ ] Calibrated: Tab moves through the links of the course chapter with a visible ring
      (`checklist.md`, "Before you start")

## Part A · The kit (70 min)

### A1 · Feel it (10 min)

Do procedure **C4** in `checklist.md` (slow mode, one tap, then the impatient double tap on the
escape room, then on Board Game Night, then offline in Chrome).

Draw a two-lane timeline like Fig 9.1 for the escape-room double tap: **what the screen said**
and **what the database held**, with rough times. Mark the moment where they part.

### A2 · Audit (30 min)

Run the procedures in `checklist.md` and fill in its **findings table**:

- **C1** keyboard pass (Chrome or Firefox): about 10 min
- **C2** screen-reader pass (VoiceOver + Safari, or NVDA + Firefox): about 15 min. One of you
  operates, the other writes down the exact words from the caption panel or Speech Viewer.
- **C3** contrast: about 5 min for the time/venue line and the Reserve label; do the rest if
  you have time.

Aim for at least **six findings**. Each row names the procedure and the exact combination that
found it, with versions (for example "C2, NVDA + Firefox on Windows 11", plus the version
numbers from each program's About box), and what you observed.
"Contrast is low" is not a finding; "time/venue text #625b8a on #1f1a3d = 2.66:1, needs 4.5:1"
is.

### A3 · Fix, then re-check the same way (25 min)

Change `app/static/index.html`. You may ask an agent for help; then check its work with the
same procedures, not with its word. Work down this table: each fix is small, and each has a
**quick re-check**, a short slice of the procedure that found the problem, on the same
combination. Write what you observe in the last column of your findings table.

| Fix (core) | Quick re-check | Time |
|---|---|---|
| K1 Reserve becomes `<button type="button">` (reset its font and border in CSS) | C1 steps 1–3: Tab from the top; reserve Board Game Night with Enter | 2 min |
| K3 a visible focus ring (`:focus-visible { outline: … }`) | during the same Tab pass: can you see every stop? | 0 min |
| K2 a visible `<label for="attendee">` | C2 step 1 only: the field's exact words now | 1 min |
| K5 an empty `<p role="status">` in the HTML; write each result into it | C2 step 5: activate Reserve from the keyboard, stay still, listen | 2 min |
| K6 on press, change the button's own text at once and ignore further presses until the answer arrives | C4 steps 1–4 in slow mode, then `who_booked.py --name Maya` | 3 min |
| K4 the two text pairs (time/venue line, Reserve label) | `python scripts/contrast.py` on your new colours | 1 min |

Then run `python -m pytest -q`: it still says `9 passed`. Write one sentence on why that
proves nothing about any fix above.

**Optional extension** (if you finish early; worth doing for your portfolio):

- **K7.** After a keyboard reservation, press Tab once (C1 step 4). If you are back at the
  top of the page, find out why. Hint: after every reservation the page rebuilds all the event
  cards, including the button that had focus. Update the existing cards instead.
- The name field's border (1.4.11, needs 3:1 against the page).
- The offline and unknown-outcome messages from the lecture's state list.

### A4 · Compare with an agent (5 min)

Open `COURSE/lectures/09-quality-for-people/demo/agent-audit.md`: a real agent's audit of this
page, done by reading the code, with no browser. Answer:

1. Which of its claims did your manual procedures confirm?
2. Which of your findings did it miss, and why couldn't it see them?
3. What does it mean by "VERIFIED"? Is that the same as your evidence?

## Part B · Your team's AfterHours (25 min)

1. **Keyboard pass** (C1) on your own booking flow, in a supported browser. Record the stops
   and whether you can finish a booking. Fix one problem you find, and re-check.
2. **One state you hadn't designed.** Pick the unknown-outcome state (the request left, no
   answer came back) or the offline state. Decide what the button shows, what the message
   says, and what a screen reader hears. Implement it if it's small; otherwise write it as a
   task contract for next week.
3. **Plan the homework session** with another team: agree a time, write your three tasks
   (`usability/session-script.md`, step 1).

This ticks the Week 9 line of the product checklist once the homework is done: *one flow
improved after an unaided usability session; keyboard-only booking works* (evidence: session
notes; a recorded keyboard pass).

## Evidence and hand-in (10 min)

One per pair:

1. The screen-versus-database timeline from A1
2. The findings table, with the re-check column filled in (A2, A3)
3. `git diff` of your `index.html`
4. The `pytest` output, and your one sentence about what it does not show
5. Your answers to A4
6. Part B: the keyboard stops of your product, the state you designed, and your three tasks

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 9, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 9 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

## Homework · Unaided usability session (about 1.5 hours)

Follow `lab-kit/usability/session-script.md` with another team, on your own AfterHours: prepare
(20 min), run two 15-minute sessions and take part in two of theirs, then debrief (20 min) and
fix one flow. Hand in the two note sheets (`usability/note-sheet.md`), your problem list, and
the fix with how you re-checked it, before Lab 10.

## How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Findings | Six or more, each tied to a named procedure and combination, with observed detail (exact words, ratios, stops) | Problems listed from reading the code, no combination named |
| Belief vs state | Timeline shows the moment screen and database part, checked with `who_booked.py` | Describes the double tap without checking the database |
| Fixes | Each core fix re-checked with its quick re-check on the same combination; extension: finds and fixes the focus problem that appears once Reserve is a real button | Fixes backed only by `pytest` or by "looks right" |
| Honesty | Screen-reader claims come from what was heard; the agent's "verified" is questioned | Screen-reader output guessed from the code |
| Part B | Keyboard stops recorded; one state designed with button, message and announcement | Plan only |
