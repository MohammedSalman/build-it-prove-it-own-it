# Lab 2 kit: one request, two waitlists

Two coding agents got the same one-line request, *"Add a waitlist to AfterHours: when an
event is full, people can join a waitlist."*, on identical copies of AfterHours. This kit
holds both real results, the app they started from, and the tools to compare them with
acceptance examples.

| Path | What |
|---|---|
| `base/` | AfterHours after Week 1, the starting point for both agents. No waitlist. `pytest`: 8 passed |
| `waitlist-agent-a/` | Agent A's result (Codex CLI, gpt-6-astra), verbatim. `pytest`: 23 passed. Read its `PROVENANCE.md` |
| `waitlist-agent-b/` | Agent B's result (a Claude Code subagent, Claude Opus 5.5), verbatim. `pytest`: 21 passed. Read its `PROVENANCE.md` |
| `tests/test_waitlist_examples.py` | Acceptance examples: two given, room for yours |
| `scripts/compare.py` | Runs the examples against all three apps and prints which pass where |
| `scripts/who_wins.py` | The same demand under different allocation policies. **The policies are authored by the course staff; neither agent built any of them** |
| `personas/persona-cards.md` | Four made-up personas for the discovery role-play |
| `templates/` | Scope agreement, acceptance examples, and interview guide |
| `requirements.txt` | Pinned packages; one environment serves all three apps |

Each app folder is a complete AfterHours: `app/`, `tests/`, `scripts/race.py`,
`scripts/rush.py`, its own README. In the two agent folders, `CHANGES.diff` shows exactly
what the agent changed.

## Set up (once, about 5 minutes)

You need Python 3.11 or newer. Replace `COURSE` with the folder where you keep the course
repository. Use one shell or the other; don't mix them.

**macOS / Linux**
```bash
cp -R COURSE/lectures/02-specify-the-promise/lab-kit ~/afterhours-lab2
cd ~/afterhours-lab2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\02-specify-the-promise\lab-kit $HOME\afterhours-lab2
cd $HOME\afterhours-lab2
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
```

## Check that all three apps work

The commands are the same in bash and PowerShell. Run each app's own tests **inside its
folder**:

```
cd base
python -m pytest -q                 # 8 passed
cd ../waitlist-agent-a
python -m pytest -q                 # 23 passed
cd ../waitlist-agent-b
python -m pytest -q                 # 21 passed
cd ..
```

Don't run `pytest` from the kit folder itself: it would find three apps with the same
package names and get confused.

## Run the acceptance examples against all three apps

```
python scripts/compare.py
```

It copies `tests/test_waitlist_examples.py` into a scratch copy of each app, runs it there,
and prints a table. Your app folders are not changed. With the two given examples you should
see:

```
example                                                      base      agent A   agent B
-----------------------------------------------------------------------------------------
1 someone with a place cannot also wait for one              fail      PASS      fail
2 joining twice tells you that you were already on the list  fail      fail      PASS
```

Add `--why` to see the reason for each failure. Every example fails on `base/`, which has no
waitlist at all. If one of yours passes there, it isn't testing the waitlist. If an example
can't run at all (a syntax error, a missing fixture), `compare.py` prints pytest's message,
leaves that example out of its summary, and exits with an error code: fix the example first.

## Who wins?

```
python scripts/who_wins.py
python scripts/who_wins.py --kept 1 --offer-minutes 120 --seed 3
```

Prints who gets the places under first come first served, a lottery, and a quota, and who
gets a place that frees up under four policies. Only one of those four, "open to all", is
what the agents' apps actually do. The people are made up.

## Try the two pages side by side (optional)

Two terminals, each with the environment activated:

```
cd waitlist-agent-a
uvicorn app.main:app --port 8001    # then open http://127.0.0.1:8001
```
```
cd waitlist-agent-b
uvicorn app.main:app --port 8002    # then open http://127.0.0.1:8002
```

The Maker Workshop is seeded full, so it shows **Join waitlist**. Each app keeps its data in
`afterhours.db` inside its own folder; stop the server and delete that file to start over.
Stop a server with Ctrl+C.
