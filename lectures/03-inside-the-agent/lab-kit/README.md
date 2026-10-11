# Lab 3 kit: the mini-agent

A small coding agent you can read in one sitting: a model in a loop, with four tools, a
permission layer, and a stopping rule. By default it runs **offline in replay mode**: the
"model" is a recording, so you need no API key and no network. The lab sheet is
`lectures/03-inside-the-agent/lab-03.md`.

```
lab-kit/
  README.md                  this file
  requirements.txt           pinned packages (the Anthropic SDK is only used by live mode)
  task-contract-template.md  the contract card, to copy
  afterhours/                the app the agent works on (AfterHours after Week 1, 8 tests)
  mini-agent/
    agent.py                 the loop, the dispatcher, the stopping rule, the command line
    tools.py                 list_files, read_file, write_file, run_tests
    permissions.py           the permission layer
    models.py                replay model (default) and live model (optional)
    permissions.json         rules for a change task
    permissions-readonly.json  rules for an investigation during a code freeze
    recordings/              three recorded runs to replay
    tests/                   tests for the agent itself
```

## Set up (about 5 minutes)

You need Python 3.11 or newer. Replace `COURSE` with the folder that holds the course
repository. Use the block for your system; don't mix them.

**macOS / Linux (bash or zsh)**
```bash
cp -R COURSE/lectures/03-inside-the-agent/lab-kit ~/lab3
cd ~/lab3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd mini-agent
python -m pytest -q                 # expect: 18 failed, 17 passed (the failures are your tasks)
python agent.py --replay recordings/add-name-check.json
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\03-inside-the-agent\lab-kit $HOME\lab3
cd $HOME\lab3
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
cd mini-agent
python -m pytest -q                 # expect: 18 failed, 17 passed (the failures are your tasks)
python agent.py --replay recordings\add-name-check.json
```

Run every later command from the `mini-agent` folder with the environment active.

## What happens when you run it

`agent.py` copies `../afterhours` into a fresh throwaway folder in your system's temp
directory (it prints the path), and its file tools work only there. Your `afterhours` folder
is never written by them. (Tests that `run_tests` executes run as you, though; see below.) Each step it prints what the "model" said, which tools it asked for, and what came
back. At the end the harness collects its own evidence: it runs the tests in the workspace,
lists the files that changed, and counts the blocked calls. The full log goes to
`logs/<run>.jsonl`, and every blocked call is also appended to `logs/blocked.jsonl`.

| Command | Use it for |
|---|---|
| `python agent.py --replay recordings/add-name-check.json` | A small change task, end to end |
| `python agent.py --replay recordings/code-freeze.json --permissions permissions-readonly.json` | Requests the rules forbid |
| `python agent.py --replay recordings/runaway.json` | A run that never finishes on its own |
| `python agent.py --replay recordings/runaway.json --max-steps 30` | The same, with a looser step limit (limits work once task A3 is done) |
| `python -m pytest -q tests/test_write_file.py` | Task A2 |
| `python -m pytest -q tests/test_stopping.py` | Task A3 |
| `python permissions.py permissions.json write_file app/main.py` | Ask a rules file about one request (task A5) |
| `python agent.py --help` | All options (`--cost-cap`, `--permissions`, `--workspace` ...) |

## Your two tasks

1. **`safe_write_path()` in `tools.py`** (task A2). `write_file` must refuse absolute paths,
   `..`, symlinks and folders. The docstring states the rules; the tests check them.
2. **`should_stop()` in `agent.py`** (task A3). It already stops when the model asks for no
   tools. Add the cost cap and the step limit.

Everything else is supplied and already tested (the 17 passing tests).

On Windows, the four symlink tests are **skipped** unless your account may create symlinks
(turn on Developer Mode in Windows Settings). Then pytest reports 15 failed, 16 passed,
4 skipped on the unfinished kit. The symlink rules are still part of your task: a skipped
test is a check you did not get, not a check you passed.

## Read this before you trust it

- **The recordings were written by the course team** in the exact shape of real API replies.
  They are not model output. A replayed "model" plays its next turn whatever the tools
  returned, so it cannot notice a failed write or a blocked call. **Replay proves the harness
  works; it says nothing about how a real model behaves.**
- **The permission layer is a teaching model, not a security boundary.** It controls only
  the requests that go through this harness. `run_tests` runs code the model may have
  written, and that code can do anything your user account can do. Real isolation is a
  container or an operating-system sandbox, with no secrets and no network inside.
- Token counts in replay are **estimates** (characters ÷ 4), not measurements.

## Live mode (optional, costs money)

Only if your course provides an API key and a spending limit. Live mode sends the task and
every file the agent reads to Anthropic's API, and `run_tests` runs the model's code on your
computer, so use a throwaway machine or container and keep secrets out of the project.

```bash
export ANTHROPIC_API_KEY=...            # PowerShell: $env:ANTHROPIC_API_KEY = "..."
python agent.py --live --task-file my-contract.md --record recordings/my-run.json
python agent.py --replay recordings/my-run.json     # replay your own run, offline
```

The live model is `claude-opus-5` (configured September 2026; see `models.py`).
