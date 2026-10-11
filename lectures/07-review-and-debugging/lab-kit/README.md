# Lab 7 kit · One incident, reviewed and debugged

Everything for Lab 7, Part A. It is self-contained: you need Python 3.11 or newer and git,
nothing from earlier weeks.

| Path | What it is |
|---|---|
| `history.bundle` | The AfterHours team repository: 20 commits, Monday 5 to Thursday 8 October 2026. Clone it (below) |
| `pr/PR-14.md` | Pull request #14 as the reviewer saw it: description, checks, commits |
| `pr/pr-14.diff` | The PR's full diff ("Files changed"), 630 lines |
| `review-checklist.md` | The risk-ordered review checklist from the lecture |
| `incident/INCIDENT.md` | The incident report: confirmations stopped arriving |
| `incident/check_confirmation.py` | One booking, then look in the outbox. Exit code 0 good, 1 bad, 125 skip, for `git bisect run` |
| `incident/book.py` | Book a place on the running app and print the status and request id |
| `hypothesis-log.md` | Template for your hypothesis log |

The pull request, the incident and the people are fictional and the problems were
**planted on purpose** for teaching. The code is real and every commit runs.
Nothing is ever emailed: a "sent" message is a row in the `outbox` table.

## Set up (10 minutes)

Replace `COURSE` with the folder where you keep the course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/07-review-and-debugging/lab-kit ~/w7-kit
cd ~/w7-kit
git clone history.bundle afterhours
cd afterhours
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                         # expect: 27 passed
python ../incident/check_confirmation.py    # expect: BAD ... outbox holds 0 message(s)
echo $?                                     # expect: 1
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\07-review-and-debugging\lab-kit $HOME\w7-kit
cd $HOME\w7-kit
git clone history.bundle afterhours
cd afterhours
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                         # expect: 27 passed
python ..\incident\check_confirmation.py    # expect: BAD ... outbox holds 0 message(s)
$LASTEXITCODE                               # expect: 1
```

`requirements.txt` is the same in every commit, so this one environment works for the
whole history. The `.venv` folder and `afterhours.db` are ignored by git, so they survive
when git checks out other commits.

## Useful commands

| What | bash / zsh | PowerShell |
|---|---|---|
| Run the app | `uvicorn app.main:app` | same |
| Run it with every log line | `AFTERHOURS_LOG_LEVEL=DEBUG uvicorn app.main:app` | `$env:AFTERHOURS_LOG_LEVEL="DEBUG"; uvicorn app.main:app` |
| Start from fresh seed data (stop the app first) | `rm -f afterhours.db afterhours.db-wal afterhours.db-shm` | `Remove-Item afterhours.db* -ErrorAction SilentlyContinue` |
| Book one place (app running) | `python ../incident/book.py` | `python ..\incident\book.py` |
| What was "sent" | `python scripts/outbox.py` | same |
| The history | `git log --oneline --decorate` | same |
| The PR's change | `git diff 4ac8467 b7675a2 --stat` | same |
| One commit | `git show <hash>` | same |

To remove the log-level variable in PowerShell afterwards:
`Remove-Item Env:AFTERHOURS_LOG_LEVEL`.

## git bisect in one screen

Stop the app and make sure `git status` shows no changed files first (`git stash` any
experiments). Then, from the repository root:

```bash
git bisect start HEAD v0.2                              # bad first, then good
git bisect run python ../incident/check_confirmation.py
git bisect log                                          # save this for your hand-in
git bisect reset                                        # back to where you started
```

Use forward slashes in the `git bisect run` line on Windows too: git runs it through its
own shell. If `git bisect run` cannot find `python` on Windows, bisect by hand: run the
check at each commit git offers, then type `git bisect good` or `git bisect bad`.
