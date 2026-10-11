# Maintenance challenge: drop-in events

**Who:** the *receiving team*, working on the *owning team's* AfterHours.
**When:** the first run starts in Lab 14, Part B. The rest is homework (about 3 hours for
the team), finished before the challenge closes (your instructor publishes the date; we
suggest about five days after Lab 14 and at least two days before demo day).
**Where:** a branch on the owning team's repository, handed in as a pull request. If you
cannot run their product, the fallback repository instead (section 5).

This is the course's handover test. It checks one thing: **can someone else own this
software, using only what is in the repository?** The owning team is not being asked to write
the feature, and you are not being asked to guess what they meant: every question you cannot
answer from their repository is evidence about their handover, and you record it.

---

## 1. The request (from the festival organisers)

> Some of our events don't need booking: the open jam in the courtyard, the chill-out room,
> the late-night food stalls. People just turn up. We'd like them in the programme as
> **drop-in events**. They must be clearly marked, nobody should be able to book one by
> mistake, and nothing about the events that do need booking may change. Each drop-in event
> still has a door limit (the room holds 60), which we'd like to show.

## 2. The rules

1. **Only the repository.** You may read everything in it: code, documents, history, issues,
   CI runs. You may **not** ask the owning team anything, in person, in chat or by message,
   until the challenge closes. They are not allowed to help either, even with hints.
2. **When you are stuck,** write the question in your challenge log with the time (section
   4), look for the answer in the repository, and if it is not there, make the most
   reasonable decision you can, record it as an assumption in your pull request, and carry
   on. An unanswered question is not your failure; it is a finding about the handover.
3. **Agents are allowed**, as in every lab. Disclose meaningful help in the pull request (what
   the agent did, what you checked). You own every claim you submit. Nobody grades how much you
   used an agent, prompt length, lines of code or commit counts.
4. **Keep their promises.** If the change needs one of the owning team's promises to change
   (in `AGENTS.md`, `docs/scope.md`, `docs/examples.md` or a test), say so in the pull request.
   Never weaken or delete one of their tests to make yours pass.
5. **The first-run budget is 45 minutes** of your team's time, from `git clone` to *tests
   passing and the app running*, following only their README. If you are not there after 45
   minutes, stop and go to section 5.

## 3. Acceptance examples

Any check your instructor runs tests **only** these examples. How you meet them (names,
status codes, where the code goes) is your decision, recorded where the next team will find
it.

| # | Given | When | Then |
|---|---|---|---|
| **D1** Listed and marked | the organisers create "Open Jam in the Courtyard" as a drop-in event with a door limit of 60 | anyone opens the programme | it appears with the words "Drop-in: no booking needed" and its door limit, and with no control to reserve it |
| **D2** Not bookable by any route | that drop-in event | a client sends a reservation request for it straight to the API (not through the page) | the request is refused with a clear message, and no reservation is stored and no payment is asked for |
| **D3** Bookable events unchanged | the existing events | people reserve, including two people for the last place at once | everything behaves as before: the owning team's existing tests pass **unchanged**, including their concurrency test |
| **D4** Existing data survives | a database created by the version before your change, with events and reservations in it | the new version starts | every existing event is still listed and bookable, with the same reservations |
| **D5** Accessible by default | the programme with a drop-in event | a keyboard user tabs through it, and a sighted user scans it | the drop-in marking is text (not colour or an icon alone), and the Tab path meets no control that does nothing |
| **D6** Handover-ready | your change | the next team reads the repository | it tells them about drop-in events: the map or `AGENTS.md`, a decision record for any choice a reviewer could question (for example the status code for D2), and the runbook if releasing needs a new step |

D1 to D4 need automated tests whose expected values come from this table, not from your
code. D5 is a manual check: write down the browser, what you did and what you observed
(Week 9's keyboard procedure). D6 is checked by reading.

## 4. What you hand in (one per receiving team)

1. **The pull request** on the owning team's repository (or, on the fallback, your
   `drop-in` branch with everything committed, new files included (`git add -A`, `git commit`),
   and the output of `git diff main --stat` plus `git diff main`). Its description is an
   evidence packet: requirement → decision → change → check → result, with each of D1–D6
   mapped to the check that shows it and that check's output.
2. **The challenge log** (template in Appendix B): the time of each step on the path from
   clone to merged-ready change, every question you could not answer from the repository,
   and where you eventually found each answer (or the assumption you made).
3. **Handover feedback** for the owning team (Appendix C): the three things in their
   repository that helped most, and the three missing things that cost you most time, each
   with the evidence from your log.

After the challenge closes, the owning team reviews your pull request with the Week 7 review
checklist and decides whether to merge it. That decision is theirs: they are still the
accountable owners of their product.

## 5. Fallback: when you cannot run the owning team's product

If the 45-minute first-run budget runs out, or their repository cannot be cloned, installed
or tested at all:

1. **Stop.** Do not fix their setup by guessing at what they meant.
2. **Write a first-run report** (Appendix B, "first run"): each step you followed, the exact
   command, and the exact output where it failed. Open it as an issue on their repository and
   send the link to your instructor. It is evidence about their handover, so be precise and
   neutral.
3. **Do the whole challenge on the fallback repository** (`lab-kit/fallback-repo/` in the
   course repository), following Appendix A. If you already did the core of it in Lab 14,
   Part A, extend that work to all of D1–D6.

Your instructor decides, from the report, whether the failure lay in the repository (a
missing step, a wrong command, an unpinned dependency) or in your machine. A failure caused by
the repository counts against the owning team's handover; your own work is marked the same
either way.

## 6. How it is assessed

This follows the course plan's assessment section. Nothing here adds a component or changes a
weight.

| Whose work | Counts toward | Evidence |
|---|---|---|
| **Owning team** | Team product and releases (40%), the "successful handover" part | Your first-run report or log, your handover feedback, and whether the repository answered the questions you logged. A strong receiving team on a poor handover, or a struggling one on a good handover, is judged from the log, not only from whether the pull request merged |
| **Receiving team** | Studio practice (15%) | The pull request's evidence packet, the challenge log, and the quality of your feedback |

Never graded: lines of code, commit counts, prompt length, how much you used an agent, or chat
logs. A pull request that does not meet every example can still earn strong marks when the
log and the evidence packet say honestly what works, what does not, and why.

---

## Appendix A · The fallback repository's contract

Only for teams working on `lab-kit/fallback-repo/`. Fixing these names in advance makes the
instructor's check fair: it tests D1–D4 through exactly this contract and nothing else.

- **Data.** Every event has a `kind`: `"bookable"` (the default, and what every existing
  event is) or `"drop_in"`. The schema change is a migration in `app/migrations/`, following
  `docs/adr/0002-schema-changes-are-numbered-migrations.md`. Do not edit `app/schema.sql`.
- **Creating.** `POST /api/events` accepts an optional `"kind"`; without it an event is
  `"bookable"`. For a drop-in event, `capacity` is the door limit.
- **Listing.** Every event in `GET /api/events` and `GET /api/events/{id}` includes `"kind"`.
- **Refusing.** `POST /api/events/{id}/reservations` for a drop-in event answers **409** with
  `{"detail": "This is a drop-in event: no booking needed"}`. Nothing is stored and payment is
  not called.
- **The page** shows the words "Drop-in: no booking needed" and the door limit on a drop-in
  event's card, and no Reserve button.
- You do **not** need to change the seed data. Create drop-in events in your tests with
  `POST /api/events`.

## Appendix B · Challenge log (copy into your pull request or `docs/handover/challenge-log.md`)

**First run** (clock starts at `git clone`):

| Step | Started | Done | Following which document | What happened (commands, exact output if it failed) |
|---|---|---|---|---|
| Clone | | | | |
| Install | | | | |
| Tests pass | | | | |
| App runs | | | | |

**Questions we could not answer from the repository:**

| Time | Question | Where we looked | Found later? Where | Or the assumption we made |
|---|---|---|---|---|
| | | | | |

**Path to the change** (one line each): where the change had to go and how you found out;
which promise you had to keep and which test showed it; the decision you recorded; each D
example and its check.

## Appendix C · Handover feedback (to the owning team)

| | What | Evidence from our log |
|---|---|---|
| Helped most 1 | | |
| Helped most 2 | | |
| Helped most 3 | | |
| Cost us most 1 | | |
| Cost us most 2 | | |
| Cost us most 3 | | |

One sentence: if you had to own this product from tomorrow, what would you ask for first?
