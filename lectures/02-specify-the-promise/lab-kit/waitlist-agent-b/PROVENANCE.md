# Provenance: `waitlist-agent-b/`

This folder is AfterHours as it stood after Week 1, plus **one coding agent's real answer**
to a one-line request. Apart from the two files listed at the end, every file here is
exactly what the agent left. Nothing was fixed, tidied, or re-run through another tool.

| | |
|---|---|
| **Agent** | A fresh Claude Code subagent, model Claude Opus 5.5, with no context from other sessions |
| **Date** | 27 September 2026 |
| **Started from** | AfterHours after Week 1 (Week 1 starter + Patch B + the concurrency test; 8 tests passing), in its own git repository. Base commit `32e3832`, identical to `../base/` |
| **Given** | Only the request below. No task contract, no examples, no answers to questions: it ran without a human in the loop |
| **What it did** | Changed 7 files (268 lines added, 12 removed), added 13 tests, reported 21 passing tests and passing `race.py` and `rush.py` runs, and committed its own work |
| **Commit** | `0dba926` ("Add a waitlist for full events"), written by the agent. Its commit message is at the top of `CHANGES.diff` |

## The request (verbatim)

```
Add a waitlist to AfterHours: when an event is full, people can join a waitlist.

(A Python 3.11 environment with the project's dependencies is at <venv>; use <venv>/bin/python to run tests.)
```

The only change is the long local path of the Python environment, shortened to `<venv>`.
Agent A received the same text.

## Its final report (verbatim)

The full transcript of this run was not kept. Its final report was:

> People can now join a waitlist when an event is full. It's committed as `0dba926` ("Add a waitlist for full events"). All 21 tests pass (8 existing, 13 new), and `race.py` and `rush.py` still pass against a running server.
>
> **One thing to check first: it changes the database schema.** AGENTS.md says to say so before changing the schema. There was no way to ask mid-task, so I kept the change additive and am flagging it here. There's a new `waitlist` table (event, name, time joined) with one entry per name per event. The existing tables are unchanged. I started the app on a database made with the old schema: it added the new table on startup and nothing else was needed.
>
> **What people can do:**
> - **Join:** `POST /api/events/{id}/waitlist` with `{"attendee": name}`. The reply includes the person's position in line (1 = first). Joining again under the same name returns the same position (HTTP 200) rather than adding a second entry.
> - **Refusals:** an event that still has places answers 409 ("reserve one instead"). An unknown event gives 404 and an empty name gives 422, as reservations already do.
> - **Counts:** each event in the API now shows how many people are waiting (`waitlisted`).
> - **Web page:** a full event shows "Join waitlist" instead of a disabled Reserve button, and its card reads "Full · N on the waitlist". Joining shows your place in line. If someone misses the last place, the message now suggests the waitlist.
>
> **Decisions I made:**
> - **It can't break the capacity rule.** Being on the waitlist is not a reservation and never counts against capacity. Reserving works exactly as before.
> - **People joining at the same moment get different positions.** The "is it full?" check and the insert happen as one step. A test has four people join at once and checks they get positions 1 to 4. When I temporarily weakened that step, the test failed.
> - **The same name joining twice (even at once) is one entry.** Names are the only identity the app has.
> - **No payment when joining,** since no place is given.
> - **The full list of names isn't exposed,** only the count, to match how reservations work.
>
> **Not built, and the product owner should decide:** nobody ever moves from the waitlist into a place. The app has no way to cancel a reservation or raise capacity, so places never free up and the list is only a queue for now. Building that means choosing:
> - whether a freed place goes straight to the first person (and when they pay), or they get an offer with a time limit;
> - whether newcomers can take a freed place ahead of the waitlist;
> - how people are told.
>
> Other gaps:
> - There's no way to leave the waitlist or look up your position without joining again.
> - Name matching is exact, so "Maya" and "maya" count as different people.
> - Someone who already has a reservation can still join the waitlist.

## Files added by the course (not by the agent)

| File | What |
|---|---|
| `PROVENANCE.md` | This note |
| `CHANGES.diff` | `git show 0dba926`: exactly what the agent changed, with its commit message |

Run it: `python -m pytest -q` in this folder gives `21 passed`. `uvicorn app.main:app --port 8002`
serves the page at http://127.0.0.1:8002.
