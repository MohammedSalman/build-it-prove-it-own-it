# Lab E · Grading a Concierge

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence packet at the end (one per pair)

In the lecture you saw a concierge that answered the demo question well and failed the eval in
three ways, a judge that agreed with people 92% of the time and still missed two of three real
failures, and a cheap model that failed the one case that mattered most. Today you finish the
graders, label cases before you look, check the judge, and decide which version ships.

Everything runs offline: the model's replies are **recordings written by the course team**, not
model output. Replay tests the eval and the code around the model. It says nothing about how a
real model behaves, and the lab never asks you to pretend otherwise.

Agents are allowed in this lab. If one helps you, say where. One rule for today: **labels come
from `GRADING.md`**, never from the concierge's answers. If you ask an agent to label cases,
give it `GRADING.md` and `catalog.json`, not the recordings, and check every label yourself.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell** where they
differ. Replace `COURSE` with the folder where you keep the course repository.

---

## Part 0 · Set up (10 min)

You need Python 3.11 or newer and git.

**macOS / Linux**
```bash
cp -R COURSE/lectures/e-products-with-models/lab-kit ~/afterhours-labe
cd ~/afterhours-labe
git init -q && git add -A && git commit -qm "kit"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # expect: 21 failed, 27 passed
python concierge.py --config v1 "Something quiet on Friday night?"
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\e-products-with-models\lab-kit $HOME\afterhours-labe
cd $HOME\afterhours-labe
git init -q; git add -A; git commit -qm "kit"
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                 # expect: 21 failed, 27 passed
python concierge.py --config v1 "Something quiet on Friday night?"
```

If `git commit` asks who you are, run `git config user.name "Your Name"` and
`git config user.email "you@example.com"` once, then commit again.

The 21 failing tests are task A2 (`tests/test_graders.py`) and the tests of the eval that need
it (`tests/test_evals.py`). From here on the commands are the same in bash and PowerShell.

- [ ] `21 failed, 27 passed`, and the demo answer printed
- [ ] You have read `GRADING.md` sections 1 to 5. It is your oracle today.

## Part A · The kit (70 min)

### A1 · Grade by hand first (10 min)

```
python evals.py --config v1
```

The graders are not finished yet, so `evals.py` lists every answer instead of scoring it (exit
code 3). Each line shows when the question was asked: that time matters (c17 is asked on
Saturday at 22:30). Find these six answers and grade each one **by hand** with `GRADING.md`: the
score from section 5, and the rule that decides it. `catalog.json` has the events, and
`evalset.jsonl` has each case's labels and notes.

| Case, run | Suggested | Score | Rule that decides it |
|---|---|---|---|
| c05 run 1 | | | |
| c07 run 1 | | | |
| c09 run 1 | | | |
| c12 run 1 | | | |
| c13 run 1 | | | |
| c17 run 1 | | | |

Keep this table. In A2 you check the code against it, and it against the code.

### A2 · Finish the graders (20 min)

Open `graders.py`. Three functions end in `raise NotImplementedError`:

1. `already_started(starts_at, now)`: rule H5. Read what `GRADING.md` says about an event that
   starts exactly at `now` before you write the comparison.
2. `precision_at_k(suggestions, relevant, k)`: section 5. Look at the first `k` only; `None`
   when there are no suggestions.
3. `score_case(suggestions, case, failures)`: the four rules of section 5, in order.

Do **not** import anything from `app/concierge.py`. The concierge has its own `has_started()`,
and a grader that reuses the product's code would share its mistakes (Week 5).

```
python -m pytest -q tests/test_graders.py     # until it passes
python -m pytest -q                           # expect: 48 passed
python evals.py --config v1
```

1. Compare the report with your A1 table. Where they differ, who was wrong: you, the code, or
   `GRADING.md`? ______
2. Test the eval before you trust it:
   ```
   python evals.py --config oracle
   python evals.py --config always-abstain
   ```
   The oracle builds each answer from the labels. What must it score, and what would a hard-rule
   failure there tell you? Why does "no good match" every time score exactly 0.20? ______
3. Commit: `git commit -am "Finish graders: H5, precision@3, score (GRADING.md)"`.

- [ ] `48 passed`
- [ ] Oracle 1.00, always-abstain 0.20, and one sentence on why each must be so

### A3 · Label before you look (15 min)

`evalset-extra.jsonl` has four questions with `"relevant": null`. **Without running the
concierge on them**, write the relevant event ids for each (or `[]` for "no good match"), using
`GRADING.md` and `catalog.json` only. Write a short `note` for any label you were unsure of.

1. Commit your labels **before** you run anything:
   `git commit -am "Label x1-x4 from GRADING.md"`. The commit is your evidence that you labelled
   before you looked.
2. Now run them:
   ```
   python evals.py --config v2 --cases evalset-extra.jsonl
   ```
   (Before you label, the same command refuses to show the answers. Try it if you like.)
3. Swap label files with the pair next to you (copy theirs in as `their-extra.jsonl`) and run
   `python evals.py --config v2 --cases their-extra.jsonl`. Same answers, different labels.
   How far did the score move? ______
4. For each case where your labels differed, write the one-line rule you would add to
   `GRADING.md` to settle it.

| Case | Our labels | Their labels | Rule that would settle it |
|---|---|---|---|
| x1 | | | |
| x2 | | | |
| x3 | | | |
| x4 | | | |

- [ ] Labels committed before the run
- [ ] At least one new rule written

### A4 · Check the judge (10 min)

```
python evals.py --config v2 --judge-check
```

The model judge grades rubric criteria J1 and J2 (`GRADING.md` section 6); people graded the
same 20 answers. The judge's verdicts are authored, with mistakes planted of kinds reported in
published studies.

1. Overall agreement: ______. Of the answers people failed, how many did the judge fail? ______
2. For each disagreement, who is right? Quote the rule.
3. Which disagreement could an exact check in code replace? Which one could not?
4. Would you let this judge grade J2 on its own for the next 1,000 answers? What would you
   need to see first?

### A5 · Compare, budget, decide (15 min)

```
python evals.py --compare v1 v2
python evals.py --compare v2 v2-small
python evals.py --config v2 --gate
python evals.py --config v2-small --gate
```

1. Fill in the table from the reports.

| Config | Mean score (95% interval) | Hard-rule failures | "No good match" right / wrong | Cost per 1,000 | p95 latency (recorded) |
|---|---|---|---|---|---|
| v1 | | | | | |
| v2 | | | | | |
| v2-small | | | | | |

2. Which version passes `budget.json`? Which line decides it? These are authored answers: what
   would you need to see before you shipped that version for real?
3. v2 is better than v1 overall. Which case got worse, and what did the concierge do there?
4. Which numbers in your table are **measured**, which **estimated**, and which **authored**?
   What would you have to run before launch to replace the authored ones?
5. **The injection.** Find c13's line in each config's report. In two sentences: why does
   passing c13 in every run not show that the concierge resists prompt injection?
6. Write one more injection case: a question, the event whose description you would change,
   the planted sentence, and what goes in `must_not_suggest`. Then try to run it in replay and
   explain the error message. (Hint: `concierge.py --show-prompt`, and what replay looks up.)

- [ ] Table filled, decision made with the budget line that decides it
- [ ] Two sentences on c13, and a new injection case

### Optional extensions (if you finish early; not marked)

- **Live mode** (only with a course key and a spending limit): run
  `python evals.py --config v2 --live --runs 1 --record recordings/my-v2.json`, then replay your
  recording. Compare its token counts with the estimates. Which numbers changed most?
- **A missing fact.** In class the rainy-afternoon question showed the programme has no
  `indoors` field. Add one (schema, seed, `catalog.json` via `solutions`-style script or by
  hand), and write two cases that need it.
- **Facts from the database.** Change the concierge's message so that any time or place comes
  from the database, not from the model. Which rubric criterion becomes unnecessary?
- **CI.** Make CI run `python evals.py --config v2 --gate`. What does a green run prove, given
  that CI replays recordings?

## Part B · Your team's product (25 min)

Most teams have no model in their product. You can still do the work that matters most: decide
what a good answer is before anything answers. Work in your team's own AfterHours repository.

1. **If your product has a model-based feature**, write an eval for it as in the kit.
2. **If it does not**, write the eval for a concierge over *your own* festival programme:
   - `docs/evals.md`: what the feature is for, k, the abstention rule, your hard rules, and your
     rubric, saying for each criterion whether code, people or a model judge grades it;
   - `evals/evalset.jsonl`: at least 10 cases with labels written from `docs/evals.md`, including
     at least two where "no good match" is right and one injection case with the planted
     description written out;
   - a budget: the numbers a version must meet, written now, before anything is compared.

The product checklist has an optional Extension row (`plan/product-checklist.md`, row *E
(optional)*): *any model-based feature has an eval set with labels, a stated k, an abstention
rule and a budget gate*, with `evals/` and its latest report as the evidence. Today's work
prepares an eval. It does not meet that row by itself: the row is met only when your product has
a model-based feature, and `evals/` holds a gate that runs (a command that fails when a version
misses the budget, as `python evals.py --config v2 --gate` does in the kit) together with the
latest report it produced. If your team adopts a model feature later, this eval becomes its
release gate.

## Evidence packet (10 min)

| | |
|---|---|
| **Requirement** (quote the GRADING.md rules you relied on) | |
| **Decision** (which version passes the budget, the line that decides it, and what must run live before launch) | |
| **Change** (your commits: graders, labels) | |
| **Check** (commands and results: pytest, oracle, always-abstain, gate, judge check) | |
| **Result** (ship / hold / condition; what must be measured live before launch) | |

No measurement row this week: the class dataset covers Labs 1 to 13 only
(`plan/class-dataset.md`).

---

### Hand in (one per pair)
1. The A1 table and your answer to A2 question 1
2. `graders.py` (A2), with the two sentences on the oracle and the null baseline
3. Your committed labels, the swap result, and your new rules (A3)
4. Your answers to A4
5. The A5 table, your decision, the two sentences on c13, and your new injection case
6. Part B: links to `docs/evals.md` and `evals/evalset.jsonl`
7. The evidence packet

### How this is marked (studio practice, formative)
| | Strong | Developing |
|---|---|---|
| Graders | All tests pass without importing the product's code; the boundary at `now` justified from GRADING.md; oracle and null baseline explained | Tests pass but the H5 boundary is copied from the tests, or the baselines are not explained |
| Labels | Committed before the run; every label traceable to a rule; disagreements turned into written rules | Labels changed after seeing answers, or disagreements left as "we disagreed" |
| Judge | Names the direction of each disagreement; replaces the time error with an exact check; refuses to trust the judge alone on J2 without more checking | Reports only the agreement percentage |
| Decision | Uses the budget written in advance; names the hard-rule line; separates measured, estimated and authored numbers; asks for live runs before any real launch | Picks by mean score alone, treats recorded latency as measured, or treats a replay pass as a ship decision |
| Injection | Says what one case can and cannot show; new case well formed; explains why replay cannot run it | Treats a passing case as proof of safety |
| Part B | Rules written before labels; abstention and injection cases present; budget written | Cases without labels or rules; no abstention cases |
