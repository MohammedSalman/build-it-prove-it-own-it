# Lab 10 kit · Many hands, one system

Everything for Lab 10, Part A. It is self-contained: you need Python 3.11 or newer and
git 2.38 or newer (`git --version`), nothing from earlier weeks.

| Path | What it is |
|---|---|
| `repo.bundle` | The AfterHours team repository as a single file: `main` plus two feature branches. Clone it (below) |
| `integration/test_integration_programme.py` | The integration test you finish in A3 |
| `integration/test_start_time_contract.py` | The contract tests you finish in A4 |
| `templates/contract.md` | A one-page integration contract, for A4 and for your team in Part B |
| `tools/schedule.py` | A tiny model: tasks, hours and dependencies in; critical path and finish time for 1 to 5 workers out |

## The story in the repository

The team is fictional and the time bug was **planted on purpose** for teaching. The code is
real and every branch runs.

- `main`: AfterHours after Week 1, plus a rule that bookings close when the event starts,
  and two task cards in `docs/tasks/` for work the team ran in parallel.
- `feature/utc-storage` (Ana, with a coding agent): stores and serves start times in UTC.
- `feature/local-display` (Ben, with a coding agent): a programme grouped by night, in
  festival time, with a "Started" mark.

Both branches start from the same `main` commit, and both are green on their own.

**Time is fixed on purpose.** The festival (9 to 11 October 2026) is on UTC+2, written as a
constant in `app/festival.py`. The app reads the time only through `app/clock.py`: tests
replace it with the `fixed_clock` fixture, and the running app uses a **demo clock**
(Friday 9 October 2026, 19:00 festival time) unless you set `AFTERHOURS_CLOCK=system`. So
everything in this lab gives the same result on every computer, in every time zone, on any
date.

## Set up (about 5 minutes)

Replace `COURSE` with the folder where you keep the course repository. One virtual
environment, made next to the repository, serves every worktree: all branches pin the same
packages. Use one shell or the other; don't mix them.

**macOS / Linux**
```bash
cp -R COURSE/lectures/10-many-hands/lab-kit ~/w10-kit
cd ~/w10-kit
python3 -m venv .venv
source .venv/bin/activate
git clone repo.bundle afterhours
pip install -r afterhours/requirements.txt
cd afterhours
git log --oneline --graph --all          # main and the two feature branches
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\10-many-hands\lab-kit $HOME\w10-kit
cd $HOME\w10-kit
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
git clone repo.bundle afterhours
pip install -r afterhours\requirements.txt
cd afterhours
git log --oneline --graph --all
```

If a later `git merge` stops with *Please tell me who you are*, set your name once:
`git config --global user.name "Your Name"` and
`git config --global user.email "you@example.com"`.

## Worktrees: one repository, several working folders

A **worktree** is an extra working folder attached to the same repository. Each worktree
has its own branch checked out and its own files, but they all share one history. That is
how several agents (or people) can work on one machine without editing each other's files.

The git commands are the same in bash and PowerShell. Forward slashes work in both. Run
them inside `afterhours`:

```
git worktree add ../ah-utc feature/utc-storage
git worktree add ../ah-display feature/local-display
git worktree add -b integration ../ah-merge main
git worktree list
```

You now have four folders side by side:

```
w10-kit/
  .venv/          the one environment
  afterhours/     main
  ah-utc/         feature/utc-storage    (Ana's work)
  ah-display/     feature/local-display  (Ben's work)
  ah-merge/       integration            (where the two meet)
```

Work in a worktree by going into its folder: `cd ../ah-utc`, then run the usual commands.
Keep the environment activated in every terminal you open (the `source` or `Activate.ps1`
line above, with the path `~/w10-kit/.venv` or `$HOME\w10-kit\.venv`).

## Useful commands

| What | Command (same in bash and PowerShell unless shown) |
|---|---|
| Tests of the folder you are in | `python -m pytest -q` |
| The programme, as the page shows it, no server needed | `python scripts/show_programme.py` (on a branch that has it) |
| Where do two branches start from? | `git merge-base feature/utc-storage feature/local-display` |
| Would they conflict? (changes nothing) | `git merge-tree --write-tree feature/utc-storage feature/local-display` |
| Merge a branch into the folder's branch | `git merge --no-ff --no-edit feature/utc-storage` |
| The history as a picture | `git log --oneline --graph --all` |
| What one branch changed | `git diff main feature/local-display --stat` |
| Run the app from one worktree | `uvicorn app.main:app --port 8003` (one port per worktree: 8001, 8002, 8003) |
| The real clock instead of the demo clock | bash: `AFTERHOURS_CLOCK=system uvicorn app.main:app` · PowerShell: `$env:AFTERHOURS_CLOCK="system"; uvicorn app.main:app` |

Each worktree keeps its own `afterhours.db` (created where you start the app), so two apps
in two worktrees never share data. Delete that file to start over with fresh seed data.

`git merge-tree --write-tree` prints one tree id when the branches merge cleanly and lists
the conflicting files when they don't. It needs git 2.38 or newer; skip it if yours is
older.

## When git says no

- **`fatal: 'feature/utc-storage' is already used by worktree at …`** (older git: *is
  already checked out at*). A branch can be checked out in only one worktree at a time. Go to
  the folder that has it, or make a new branch with `-b`.
- **`contains modified or untracked files, use --force to delete it`** when removing a
  worktree: commit or delete your new files first. Ignored files (`.venv`, `afterhours.db`,
  `__pycache__`) don't count.

## Clean up (after the lab)

From inside `afterhours`:

```
git worktree remove ../ah-utc
git worktree remove ../ah-display
git worktree remove ../ah-merge
git worktree prune
```

Removing a worktree deletes its folder, not its branch or its commits.
