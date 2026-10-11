# Handover checklist

**Who fills it in:** the owning team, before Lab 14 (about 1.5 to 2 hours; most items were built
during the term and only need a link). **Who uses it next:** the receiving team, to find their
way in and to write their handover feedback. **Where it goes:** `docs/handover.md` in your
repository, so it travels with the code.

Every row needs **evidence a stranger can check**: a link to a file, a test, a CI run, or a
command with its output. "We did this" is not evidence. If an item does not apply to your
product, write why. If it is missing, say so: a gap you name is a known risk, and a gap you
hide is a surprise for the next team.

This completes the Week 14 line of the product checklist (`plan/product-checklist.md`):
*handover package complete; another team completed the maintenance challenge*.

Status: **yes** (evidence linked) · **partly** (say what is missing) · **no** (say why).

---

## Before you fill it in: the clean-clone rehearsal (20 minutes)

The README is the first thing a stranger runs. Run it the way they will: a fresh folder, a
fresh environment, and only the README open. Someone who did not write the README should
type the commands.

**macOS / Linux**
```bash
cd "$(mktemp -d)"
git clone YOUR-REPOSITORY-URL handover-rehearsal && cd handover-rehearsal
# now follow your README, exactly as written, and nothing else
```

**Windows PowerShell**
```powershell
$dir = Join-Path $env:TEMP "handover-rehearsal"; New-Item -ItemType Directory $dir | Out-Null; Set-Location $dir
git clone YOUR-REPOSITORY-URL .
# now follow your README, exactly as written, and nothing else
```

Write down the date, the operating system, the time it took to reach *tests pass* and *app
runs*, and every place the README was wrong, missing a step, or needed knowledge from your
head. Fix the README, then rehearse again.

---

## A · Run it (the receiving team's first hour)

| # | Item | Came from | Status | Evidence | Checked by, date |
|---|---|---|---|---|---|
| A1 | The README takes a stranger from `git clone` to passing tests and a running app, with commands for bash **and** PowerShell, the Python version, and the expected output (for example `15 passed`) | Weeks 1, 3 | | Clean-clone rehearsal: date, OS, minutes | |
| A2 | Dependencies are pinned. Direct ones in `requirements.txt`; better, the full set (for example `pip freeze > constraints.txt`) | Week 8 | | File link | |
| A3 | CI runs the tests on every push and pull request, and `main` is green now | Weeks 1, 3 | | CI run link | |
| A4 | Test and seed data are made up: no real people's names, emails or phone numbers anywhere in the repository | Weeks 3, 8 | | Where the seed data lives | |
| A5 | No secrets in the repository or its history | Week 8 | | Secret-scan command and output | |

## B · Understand it

| # | Item | Came from | Status | Evidence | Checked by, date |
|---|---|---|---|---|---|
| B1 | `AGENTS.md` states commands, a map, the rules, and the product's promises | Week 3 | | `AGENTS.md` | |
| B2 | A reading path: which files to read first, in what order, and what each teaches | Week 14 | | README section | |
| B3 | Module map: the decision each module hides and its interface | Week 4 | | `docs/modules.md` | |
| B4 | Every promise is written down next to the test that protects it | Weeks 2, 5 | | `docs/examples.md`, test names | |

## C · Change it safely

| # | Item | Came from | Status | Evidence | Checked by, date |
|---|---|---|---|---|---|
| C1 | Decisions a newcomer would question are recorded as ADRs, each with a rejected alternative | Week 4 | | `docs/adr/` | |
| C2 | How to change the database schema, written down and working: migrations, how they are applied, how they are verified | Week 13 | | Runbook section, migration files | |
| C3 | Contracts for shared decisions (formats, fields, endpoints), with producer and consumer tests | Week 10 | | `docs/contracts/` | |
| C4 | Tests derived from requirements; the concurrency test; retry and uniqueness tests; ownership tests; a mutation-score baseline | Weeks 1, 5, 6, 8 | | Test files, `docs/quality.md` | |
| C5 | How a change gets in: branch protection, required review with the checklist | Weeks 3, 7 | | Settings screenshot, PR history | |

## D · Run it for real, and recover

| # | Item | Came from | Status | Evidence | Checked by, date |
|---|---|---|---|---|---|
| D1 | Runbook: start, health check, deploy, roll back, back up, restore | Week 12 | | `docs/runbook.md` | |
| D2 | A restore rehearsal, logged with its result and the application-level checks | Week 12 | | Rehearsal log | |
| D3 | Logs carry a request id, and the runbook says what the logs contain and where they go | Week 7 | | Log sample | |
| D4 | A performance budget for one page, with a measured baseline and the method | Week 11 | | `docs/performance.md` | |

## E · Know what is wrong

| # | Item | Came from | Status | Evidence | Checked by, date |
|---|---|---|---|---|---|
| E1 | Known risks: each says who it hurts, how you know, what limits it today, and what would fix it | Week 14 | | `docs/known-risks.md` | |
| E2 | Threat model | Week 8 | | `docs/threat-model.md` | |
| E3 | Open questions from the scope agreement, each still with an owner, or closed with the decision | Week 2 | | `docs/scope.md` | |

## F · Licences and provenance

| # | Item | Came from | Status | Evidence | Checked by, date |
|---|---|---|---|---|---|
| F1 | Every dependency, **including dependencies of dependencies**, with the licence it declares, the date and the command that produced the list. Anything whose licence is not declared, or that you do not recognise, checked by reading its licence file | Weeks 8, 14 | | `docs/licences.md` | |
| F2 | The project's own licence is stated, or "not chosen yet" is recorded as a known risk | Week 14 | | `LICENSE` or E1 | |
| F3 | Anything copied into the repository that is not a package (a code snippet from a web page, fonts, icons, images, data) says where it came from and under what licence, next to it or in `docs/licences.md` | Week 14 | | File links | |
| F4 | Meaningful help from agents is disclosed, as the course policy asks (in pull requests or commit messages). Chat logs are not needed and not wanted | All term | | PR examples | |

To produce F1, copy `scripts/licences.py` from the fallback repository
(`lectures/14-hand-it-over/lab-kit/fallback-repo/scripts/licences.py`) into your repository and
run it inside your environment: `python scripts/licences.py --out docs/licences.md`. It reads
what each installed package **declares**, which is a starting point, not proof.

## G · People

| # | Item | Came from | Status | Evidence | Checked by, date |
|---|---|---|---|---|---|
| G1 | Personal data inventory: which personal data the product stores (tables, fields, **logs**, backups), why each is needed, how long it is kept, and who can see it | Weeks 8, 14 | | `docs/privacy.md` or a README section | |
| G2 | The defaults are the minimum: nothing collected, logged or shown that the purpose does not need | Week 14 | | Where you checked (code, log sample, API response) | |
| G3 | Accessibility status: a recorded keyboard pass, and the known accessibility problems listed | Week 9 | | Keyboard pass record | |
| G4 | Usability findings and what you changed because of them | Week 9 | | Session notes | |

## H · The handover itself

| # | Item | Came from | Status | Evidence | Checked by, date |
|---|---|---|---|---|---|
| H1 | The receiving team can clone, open issues, push a branch and open a pull request, and can see CI | Week 14 | | Their names in repository settings | |
| H2 | The product checklist items for Weeks 1 to 13 are ticked, each with its evidence link | All term | | `docs/handover.md` links | |
| H3 | Everyone on the owning team knows the rule: no help of any kind until the challenge closes; afterwards we review their pull request with the Week 7 checklist | Week 14 | | Team names | |

---

## How the receiving team uses this list

Keep it open during your first hour. When you get stuck, look for the item that should have
answered your question. Your handover feedback (maintenance challenge, Appendix C) should
point at item numbers: "C2 was missing: we could not tell how the schema changes, and lost 40
minutes" is feedback the owning team can act on.

## What this list is not

It is not a points system and it is not marked line by line. It is the owning team's evidence
for the "successful handover" part of the team product mark, read together with the receiving
team's log. A short, honest list with real evidence beats a long one with empty links.
