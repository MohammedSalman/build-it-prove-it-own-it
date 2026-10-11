# Provenance: `waitlist-agent-a/`

This folder is AfterHours as it stood after Week 1, plus **one coding agent's real answer**
to a one-line request. Apart from the three files listed at the end, every file here is
exactly what the agent left. Nothing was fixed, tidied, or re-run through another tool.

| | |
|---|---|
| **Agent** | Codex CLI 0.154.0-alpha.6.2, non-interactive (`codex exec`), model gpt-6-astra |
| **Date** | 27 September 2026 |
| **Started from** | AfterHours after Week 1 (Week 1 starter + Patch B + the concurrency test; 8 tests passing), in its own git repository. Base commit `32e3832`, identical to `../base/` |
| **Given** | Only the request below. No task contract, no examples, no answers to questions: it ran without a human in the loop |
| **What it did** | Read the code, changed 6 files (301 lines added, 23 removed), added 15 tests, ran `pytest` (23 passed), then tried to check the page in a browser (none was connected) |
| **Commit** | The agent left its work uncommitted. The course team committed it verbatim as `f4ad621` ("Agent A (Codex): implement 'Add a waitlist...' request, uncommitted work captured verbatim by course team") |

## The request (verbatim)

```
Add a waitlist to AfterHours: when an event is full, people can join a waitlist.

(A Python 3.11 environment with the project's dependencies is at <venv>; use <venv>/bin/python to run tests.)
```

The only change is the long local path of the Python environment, shortened to `<venv>`.
Agent B received the same text.

## Its final answer (verbatim)

> Added “Join waitlist” for full events, with persistent queue positions, duplicate prevention, and API support. Existing reservations and capacity limits are preserved. Automatic promotion isn’t included.
>
> Validation using your Python environment: `python -m pytest -q` → `23 passed in 0.32s`. JavaScript syntax check passed.
>
> Browser testing was unavailable because no browser is connected.

While it worked it also posted two progress messages. The one that states its plan:

> I’ll add an explicit “Join waitlist” button for full events and show each person their position. Joining will be free, repeated requests won’t create duplicates, and waitlist entries won’t count toward capacity.
>
> This requires a new `waitlist` table; startup will add it to existing databases while preserving reservations. There’s no cancellation flow yet, so automatic promotion is outside this change.

## Files added by the course (not by the agent)

| File | What |
|---|---|
| `PROVENANCE.md` | This note |
| `CHANGES.diff` | `git show f4ad621`: exactly what the agent changed, with the commit header |
| `agent-a-run.jsonl` | Codex's full event log (`--json`): every command it ran and every message it wrote. Only change: long local paths shortened to `<repo>`, `<venv>`, `<scratch>` and `~` |

Run it: `python -m pytest -q` in this folder gives `23 passed`. `uvicorn app.main:app --port 8001`
serves the page at http://127.0.0.1:8001.
