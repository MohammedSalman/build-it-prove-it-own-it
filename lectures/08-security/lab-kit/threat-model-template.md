# Threat model: ______________________ (one page)

**Owner:** __________ · **Date:** __________ · **Covers:** which part of the product (for
example "sign-in, reservations and the door list"; not "everything")

Keep it to one page. A threat model is a list of decisions with evidence, not an essay.
Update it when you add a route, a role, a dependency, or an agent tool.

## 1. What are we protecting? (assets)

| Asset | Why it matters | Who may see it | Who may change it |
|---|---|---|---|
| e.g. reservations | a person's place at an event | its owner, organisers | its owner, organisers |
| | | | |
| | | | |

## 2. Who acts on the system? (actors)

Include people *and* software: a stranger, a signed-in user, an organiser, an admin, a
coding agent in your repository, the maintainers of your dependencies.

| Actor | What they can already do legitimately |
|---|---|
| | |
| | |

## 3. Where does data cross a trust boundary? (sketch and entry points)

Draw the boxes (browser, API, database, agent workspace, anything third-party) and a dashed
line wherever data crosses from something you do not control into something you do. Paste
a photo of the sketch here.

| Entry point (route, file, tool, dependency) | Who can reach it | What it trusts |
|---|---|---|
| | | |
| | | |

## 4. What could go wrong? (threats)

Write each threat as a sentence: **who** does **what** to **which asset** through **which
entry point**. Use STRIDE as a prompt list: **S**poofing, **T**ampering, **R**epudiation,
**I**nformation disclosure, **D**enial of service, **E**levation of privilege.

| # | Threat | STRIDE | Likelihood (L/M/H) | Impact (L/M/H) |
|---|---|---|---|---|
| T1 | | | | |
| T2 | | | | |
| T3 | | | | |
| T4 | | | | |

## 5. What stops it, and how do we know? (mitigations with evidence)

Evidence is something a stranger can check: a test name, a config file, a command and its
output. "We are careful" is not evidence.

| Threat | Mitigation | Evidence | Status (done / planned / accepted) |
|---|---|---|---|
| T1 | | | |
| T2 | | | |
| T3 | | | |
| T4 | | | |

## 6. What we accept for now, and who decided

| Risk we accept | Why (cost, time, likelihood) | Decided by | Revisit when |
|---|---|---|---|
| | | | |
