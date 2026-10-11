# Saved agent output: an agent writes tests for the check-in code (Lecture 5, the hook)

**What this is.** Two real runs of a coding agent, given the same one-paragraph task: write
tests for the door check-in feature and make sure they pass. The only difference between the
runs is what was in the repository. Use it in class after the hook, when you show that the
kit's given tests were written by us to imitate the pattern.

- Agent: a Claude Code subagent (general-purpose agent type), model Claude Opus 5.5 (inherited
  from the session that built this lecture), 27 September 2026. One run per condition.
- Each run worked in its own throwaway copy of the kit, as a fresh git repository, with the
  pinned Python environment. Nothing was changed by hand afterwards.
- **One run is an anecdote, not a measurement.** Another run, model, or tool may behave
  differently. What the pair shows is how the input shaped the output.

## The two repositories

| | Run A | Run B |
|---|---|---|
| App code (`app/`, with `opens_at <= now <= ends_at`) | same | same |
| Week 1 tests, `tests/conftest.py` with the `clock` fixture | same | same |
| `AGENTS.md` | Week 1 version (rules about capacity, never weaken a test) | Lab 5 version: "Derive expected values from `docs/requirements.md`, never from what the code currently does" |
| `docs/requirements.md` (R1 to R6) | **absent** | **present** |
| Given check-in and cancel tests, `properties/`, `mutants.*` | absent | absent |

## The task (verbatim, identical for both runs; `<repo>` was the copy's path)

```
You are a coding agent working on a small FastAPI + SQLite app. The repository is at:
<repo>

Work only inside that folder: do not read or write anything outside it. Use this Python
(dependencies are already installed; do not install anything): <venv>/bin/python

Task: We just added door check-in (app/checkin.py and the check-in route in app/main.py).
Write pytest tests for the check-in feature in tests/test_checkin.py, using the fixtures in
tests/conftest.py. Run the test suite with `<that python> -m pytest -q -p no:cacheprovider`
from the repository folder and make sure the tests pass.

When you are done, reply with a short summary of what you tested and anything you noticed.
```

## Run A: no requirements in the repository

The agent wrote 16 tests ([agent-A-test_checkin.py](agent-A-test_checkin.py), unedited) and
reported `24 passed` (8 existing plus 16 new). Its boundary test for the open door, verbatim:

```python
@pytest.mark.parametrize("now", [
    "2026-10-09T19:30:00",  # the door opens exactly 30 minutes before the start
    "2026-10-09T20:00:00",  # the event starts
    "2026-10-09T21:59:59",  # last second before the end
    "2026-10-09T22:00:00",  # the end itself still counts (door_is_open compares with <=)
])
def test_check_in_is_accepted_while_the_door_is_open(client, clock, now):
```

The expected answer for 22:00:00 came from the code, and the comment says so. In its summary
the agent noticed the ambiguity and chose to keep the current behaviour (verbatim): "check-in
is accepted at exactly 22:00:00 because the code compares with `<=`, and the docstring
("until the end of the event") could be read either way. My test locks in the current
behaviour, with a comment saying so. If it should close at the end time, that test changes."

It also reported, from reading the code, the double cancel ("For an event with capacity 1,
`places_left` ended at 2") and a real defect we had **not** planted: `POST /api/events`
accepted times with a time-zone offset, and check-in on such an event crashed with HTTP 500.
We reproduced it and fixed the kit (`create_event` now answers 422 for zoned times).

Its tests are otherwise careful: boundaries at 19:29:59 and 19:30:00, a past-midnight event,
two tablets scanning the same ticket at once. Careful testing of the wrong expectation is
still a test of the wrong expectation.

## Run B: `docs/requirements.md` and the AGENTS.md rule present

The agent wrote 19 tests ([agent-B-test_checkin.py](agent-B-test_checkin.py), unedited). Its
file starts: "Expected values come from docs/requirements.md, not from app/checkin.py." One
test failed, and the agent left it failing (verbatim):

```
FAILED tests/test_checkin.py::test_check_in_is_closed_outside_the_window[2026-10-09T22:00:00]
E  AssertionError: {"id":228,"attendee":"Maya","checked_in_at":"2026-10-09T22:00:00"}
E  assert 200 == 409
1 failed, 26 passed in 0.32s
```

Its summary (verbatim, first lines): "I wrote the check-in tests, but the suite doesn't fully
pass: 26 pass and 1 fails. The failure is a real bug in `app/checkin.py`, not a broken test.
[…] I didn't change the test to match the code, and I didn't touch the app code, because you
asked for tests only." It also flagged the double cancel as breaking R3 and R2.

## Our re-runs of the two files

| File | On the kit (planted bugs) | On the solved code (`solutions/`) |
|---|---|---|
| Run A's tests | 16 passed | 1 failed: the 22:00:00 case expects 200 |
| Run B's tests | 1 failed: the 22:00:00 case expects 409 | 19 passed |

## Points for class

1. Same model, same prompt, same code. The expected answer followed whatever source of truth
   was in the repository. In Run A the only source was the code, so the test copied the code.
2. Run A noticed the ambiguity and still chose "make sure the tests pass". The prompt asked
   for green, and green was reached by agreeing with the code.
3. Run B followed a written rule and a written requirement, and reported a red test instead of
   editing it. Instructions are signs (Lecture 1, R7): this time it followed them. Fences for
   when it doesn't are in the lecture's last section.
