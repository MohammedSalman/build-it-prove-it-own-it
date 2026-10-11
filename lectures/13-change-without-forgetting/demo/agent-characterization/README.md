# Saved agent output: an agent explains v1 and writes characterization tests (Lecture 13, section 5)

**What this is.** Two real runs of a coding agent, given the same task: explain what
`v1/tickets.py` does, then write characterization tests that pin down today's behaviour
before the passes migration. The only difference between the runs is what was in the
repository. Use it in the "Agents in maintenance" section; the chapter's table summarises it.

- **Agent:** Codex CLI `0.154.0-alpha.6.2`, model `gpt-6-astra`, reasoning effort high (from the
  course team's Codex configuration), `codex exec --skip-git-repo-check -s workspace-write`.
- **When:** 27 September 2026, both runs started within a minute of each other (about
  23:56 local time), one run per condition.
- **Threads:** run A `01a0e4a8-206c-7130-93e1-c2f6aa605d45`; run B `01a0e4a8-1f3e-7351-9208-1a0a840a82d5`.
- Each run worked in its own throwaway copy, a fresh git repository with one commit, and the
  pinned Python environment. Nothing was changed by hand afterwards.
- **Two runs are an anecdote.** Another run, model, or tool may behave differently. What the
  pair shows is what the input could and could not tell the agent.

## The two repositories

| | Run A | Run B |
|---|---|---|
| `v1/` (the kit's v1, with the planted change-day defect) | same | same |
| `tests/conftest.py` (`client` and `clock` fixtures), Week 1 event tests (7) | same | same |
| `README.md`, `AGENTS.md` (v1-era: commands, clock rule, never weaken a test) | same | same, plus one README line pointing to the requirements |
| `docs/requirements.md` (T1 to T4 only; nothing about passes) | **absent** | **present** |

## The task

Verbatim in [prompt.md](prompt.md) (`<repo>` and `<venv>` stand for the copy's path and the
pinned environment). It asked for an explanation of under 250 words, characterization tests in
`tests/test_tickets_characterization.py`, no changes under `v1/`, a passing pytest run, and
"anything that looked surprising".

## What happened

| | Run A: code only | Run B: code and requirements |
|---|---|---|
| Explanation | Correct on all four operations ([run-a-final-answer.md](run-a-final-answer.md)) | Correct ([run-b-final-answer.md](run-b-final-answer.md)) |
| Tests written | 15 test functions, 75 cases ([file](run-a-test_tickets_characterization.py)) | 21 test functions, 80 cases ([file](run-b-test_tickets_characterization.py)) |
| Its pytest run | `82 passed` (7 existing + 75) | `87 passed` (7 existing + 80) |
| Files outside the new test file | none (`git status`: one untracked file) | none |
| The planted defect (a ticket can move after its own day has begun) | Pinned as 200 in `test_scans_can_repeat_and_used_or_expired_tickets_can_move_to_a_future_day`. Summary: "Surprises: ... used or expired tickets can move to future days" | Pinned as 200 in `test_change_is_allowed_after_original_day_begins_or_ends`, with the comment `# This is current behavior, despite T3 saying both days must still be ahead.` Summary: "The main surprise: written requirement T3 says **both days must still be ahead**, but the code checks only the destination." |

Both agents did what a characterization test should do: photograph the behaviour, bug
included. Run A noticed the oddity without a requirement to name it; run B tied it to T3.
Neither could decide whether it was a bug, and neither was asked to.

## Checked afterwards: the agents' tests against v2

We ran each saved test file, unchanged, against the kit's apps (`solutions/check_package.py`
does this every time it runs):

| Test file | v1, v1 table | v2, expanded table | v2, contracted table | v2 with its two new response fields removed |
|---|---|---|---|---|
| Run A (75) | 75 passed | 62 passed, **13 failed** | 62 passed, **13 failed** | 75 passed |
| Run B (80) | 80 passed | 67 passed, **13 failed** | 67 passed, **13 failed** | 80 passed |

v2 answers these requests as v1 does and adds `first_day` and `last_day` to every ticket it
returns. The agents' tests compare whole response bodies with `==`, so every test that checks
a ticket body fails on v2. Removing the two fields from v2's responses makes every test pass,
so no other behaviour differs. After part A5 (v2 stops reading `wristband_mode`), 3 more tests
fail in each file, all of them photographs of the dead `wristband_mode` path: correct
failures, to be retired with the code.

## Files

- `prompt.md`: the task, verbatim, with the two paths replaced by placeholders
- `run-a-final-answer.md`, `run-b-final-answer.md`: the agents' final messages, verbatim
  (they contain the course team's scratch paths)
- `run-a-commands.md`, `run-b-commands.md`: every command and message in order, extracted
  from the JSON event stream (scratch paths shown as `<scratch>`, long outputs cut)
- `run-a-test_tickets_characterization.py`, `run-b-test_tickets_characterization.py`: the test
  files the agents wrote, unedited

## Reproduce

Copy `lab-kit/v1/` into a fresh folder with `tests/conftest.py` providing `client` and
`clock` (as in the lab kit), the Week 1 event tests, a README and an AGENTS.md; add
`docs/requirements.md` (T1 to T4) for run B; `git init` and commit; then run
`codex exec --skip-git-repo-check -s workspace-write -C <repo> - < prompt.md`. Results will
differ from run to run. Apply the same table to whatever it produces.
