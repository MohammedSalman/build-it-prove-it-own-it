# Festival demo day: format and rubric

**What it assesses:** the team product and releases component, **40%** of the course mark
(course plan §6), whose evidence is "acceptance demos, user observations, reliability checks,
successful handover". Demo day is where that evidence is shown and judged together. It draws
on the whole term's record (the product checklist), not only on what works on the day.

**When:** after the maintenance challenge closes. Graded defences are a separate slot, never
during demo day.

---

## 1. The format: a festival fair

Each team has a station: a laptop, its product running, and its repository open. Assessors
visit each station for a **10-minute slot**. Between slots, other students walk round as
festival-goers and try the products. They are users, not markers.

| Minutes | What the team does | What the assessor does |
|---:|---|---|
| 0–1 | Names the festival, the product's main promise, and the product checklist status | Opens the team's `docs/handover.md` |
| 1–5 | **Acceptance demo.** The assessor picks two examples from the team's published `docs/examples.md`, one of them the usability or accessibility criterion. The team runs each live, says "given / when / then" out loud, and shows the check that proves it (a test, a keyboard pass) | Watches the "then" happen, and the check |
| 5–7 | **Reliability check.** The team runs one reliability check live (the concurrency check, the retry test, or a restore onto a copy with the application-level checks) and shows the others' latest evidence | Asks "what would make this fail?" |
| 7–8 | **User observations.** One finding from a usability session, and what changed because of it (before and after) | |
| 8–10 | **Handover.** What the receiving team's log and feedback said, what the team fixed since, and the state of the drop-in pull request. Then questions | Reads the receiving team's first-run report or log |

Assessors write notes for 3 minutes after each slot. Budget: **13 assessor-minutes per team**
(for 30 teams, 6.5 hours per assessor if one assessor sees every team; with two assessors
per station for moderation, double it; with stations split between assessor pairs, divide).

**If the live demo fails,** the team says so, shows its recorded evidence (the CI run, a test
output, a recording made that week) and explains what went wrong. Judge the evidence and the
explanation, not the stage luck. A failure handled with evidence can still earn strong marks.

## 2. The rubric

The course plan fixes the component at 40% and names its four kinds of evidence; it does not
split the weight between them. This rubric scores each kind 0 to 4 and weights them equally
(mark = total ÷ 16 × 40). If your course splits the weight differently, publish that before the
swap.

| Score | **Acceptance demos** | **User observations** | **Reliability checks** | **Successful handover** |
|---|---|---|---|---|
| **4** | Both sampled examples run live exactly as published, each with the check that proves it; the accessibility or usability criterion is shown with its procedure | Unaided sessions ran; a specific finding changed the product; before and after shown | A live check passes and the team can say what it would catch; every reliability item on the product checklist has current evidence (concurrency, retries, restore rehearsal, performance baseline) | The receiving team ran the product within the first-run budget and made the change from the repository alone; the questions in their log were answered by the repository or honestly recorded as known risks; the team acted on the feedback |
| **3** | Both run, with a small gap in the check or a published example slightly out of date | Sessions ran and a finding was acted on, but the link between them is thin | Live check passes; one item's evidence is stale or thin | Ran within budget; a few logged questions had no answer in the repository |
| **2** | One runs as published; the other only partly, or without its check | Sessions ran but nothing changed, or findings are generic | Evidence exists but was not rerun this term, or the check cannot fail | Ran only after workarounds, or the change needed guesses about things the repository should have said |
| **1** | Demos do not match the published examples | Only the team's own opinions | Claims without evidence | The receiving team could not run it (a failure the instructor traced to the repository), with no first-run report acted on |
| **0** | Nothing demonstrable | None | None | No handover took place |

Notes for assessors:

- **Published requirements only.** Sample from the team's own published examples. Do not
  judge features nobody asked for, and do not check anything that was never written down.
- **The handover is judged from the log, not only the outcome.** A strong receiving team can
  succeed on a weak handover, and a struggling one can fail on a good one. Read their log:
  did the repository answer the questions they had? Where it did not, did the team know
  (a known risk, an open question)?
- **Never graded:** lines of code, commit counts, prompt length, how much the team used agents,
  chat logs, slide design.
- **Accessibility of the day:** the product is shown on a screen large enough to read, the
  accessibility criterion is demonstrated live (keyboard, or a screen reader the team brings),
  and a team member who prefers not to present speaks through the evidence instead.

## 3. What each team brings

- The product running from the tagged `defence` commit (or later, if the receiving team's
  pull request was merged after review).
- `docs/handover.md` (the handover checklist, filled in).
- The receiving team's challenge log and handover feedback, and your response to it.
- The product checklist with every item's evidence link, Weeks 1 to 14.
