# AfterHours product checklist

Each team's own AfterHours grows all term. The lab kits are isolated exercises; this
checklist is what connects them to the product. Part B of every lab ticks the items for that
week. Items stay ticked: a later change that breaks one un-ticks it until fixed.

Each team keeps its copy of this list in its repository as `docs/checklist.md` (set up in Lab 1,
Part 6). A release is **acceptable** when every item up to the current week is ticked and the evidence
column points at something a stranger can check (a test, a command, a document, a
recording).

| Week | Item | Evidence |
|---|---|---|
| 1 | The last place goes to exactly one person under concurrent requests | Concurrency test in CI |
| 1 | CI runs the tests on every push | CI badge or run link |
| 2 | One-page scope agreement signed off by the team | `docs/scope.md` |
| 2 | Five acceptance examples, including one usability and one accessibility criterion | `docs/examples.md` and at least one automated test (the rest arrive in Week 5) |
| 3 | AGENTS.md states commands, map, rules, and the product's promises | `AGENTS.md` |
| 3 | Three task contracts written for the next week's work | `docs/contracts/` |
| 4 | Module map; one ADR with a rejected alternative | `docs/modules.md`, `docs/adr/` |
| 5 | Tests derived from requirements for every acceptance example; mutation-score baseline recorded | Test files; `docs/quality.md` |
| 6 | Reservation requests are safe to retry (idempotency key); active reservations are unique | Retry and uniqueness tests |
| 7 | Every PR reviewed with the checklist; logs carry a request id | PR history; a log sample |
| 8 | One-page threat model; ownership checks with adversarial tests; no secrets in the repo | `docs/threat-model.md`; tests; secret scan output |
| 9 | One flow improved after an unaided usability session; keyboard-only booking works | Session notes; recorded keyboard pass |
| 10 | Two features built in parallel against a written contract; CI runs on the merged result | Contract file; CI run |
| 11 | Performance budget for one page with a measured baseline | `docs/performance.md` with numbers and method |
| 12 | Runbook for deploy, rollback, and restore; one restore rehearsal logged | `docs/runbook.md`; rehearsal log |
| 13 | One schema change done as expand → migrate → contract | Migration files and their verification |
| 14 | Handover package complete; another team completed the maintenance challenge | Handover checklist; the other team's PR |
| E (optional) | Any model-based feature has an eval set with labels, a stated k, an abstention rule and a budget gate | `evals/` and its latest report |
