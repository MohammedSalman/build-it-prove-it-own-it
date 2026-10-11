# Lab 14 kit · Hand It Over

Documents for the handover, the defences and demo day, plus one runnable repository.

| File | For | What it is |
|---|---|---|
| `handover-checklist.md` | Your team, before Lab 14 | 32 items along the newcomer's path, each needing evidence a stranger can check. Copy it to `docs/handover.md` in your repository |
| `maintenance-challenge.md` | The receiving team | The drop-in events request, the rules ("only the repository"), acceptance examples D1 to D6, what to hand in, the fallback rule, and templates for the challenge log and the handover feedback |
| `fallback-repo/` | Part A of the lab; any receiving team that cannot run its partner's product | AfterHours after Week 1, handed over properly: README with a reading path, `AGENTS.md`, two decision records, runbook, known risks, licences, a migration procedure, and 15 tests |
| `defence/rubric.md` | Everyone, before the defences | Format, rubric, reassessment, accommodations, and the assessor-minutes budget |
| `defence/question-bank.md` | Everyone | The twelve question families the defences sample from. Public on purpose |
| `demo-day-rubric.md` | Your team, before demo day | The ten-minute format and the rubric for the team product component |

Everything here follows the course plan's assessment section (§6). None of these documents
adds a component or changes a weight.

## Set up the fallback repository

You need Python 3.11 or newer and git. Replace `COURSE` with the folder where you keep the
course repository. After the copy, the repository's own README takes over.

**macOS / Linux**
```bash
cp -R COURSE/lectures/14-hand-it-over/lab-kit/fallback-repo ~/afterhours-fallback
cd ~/afterhours-fallback
git init -q -b main && git add -A && git commit -qm "fallback repository, as handed over"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                  # expect: 15 passed
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\14-hand-it-over\lab-kit\fallback-repo $HOME\afterhours-fallback
cd $HOME\afterhours-fallback
git init -q -b main; git add -A; git commit -qm "fallback repository, as handed over"
python -m venv .venv
.venv\Scripts\Activate.ps1           # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                  # expect: 15 passed
```

If a receiving team uses the fallback for the whole challenge, push this repository to a new
repository of your own (GitHub or your course's server) so that the challenge can be handed in
as a pull request, or hand in a branch plus `git diff main`. Work on a branch
(`git switch -c drop-in`), never directly on `main`.

## List your own product's licences (handover item F1)

`fallback-repo/scripts/licences.py` uses only the standard library (plus `packaging`, which
pytest installs). Copy it into your own repository and run it inside your environment:

**macOS / Linux**
```bash
cp COURSE/lectures/14-hand-it-over/lab-kit/fallback-repo/scripts/licences.py scripts/
python scripts/licences.py --out docs/licences.md
```

**Windows PowerShell**
```powershell
Copy-Item COURSE\lectures\14-hand-it-over\lab-kit\fallback-repo\scripts\licences.py scripts\
python scripts/licences.py --out docs/licences.md
```

It reads your `requirements.txt` (and any file it includes with `-r`), follows the
dependencies of your dependencies as far as they are installed, including those behind extras
you asked for (such as `httpx2[http2]`), and writes what each package **declares** as its
licence. Lines it cannot follow (editable installs, bare URLs or paths) and packages that are
required but not installed are listed at the end: check those by hand. To keep your own
notes in that file, add the line `<!-- licences.py writes below this line -->` where the table
should go; the script keeps everything above it, and never overwrites a file that lacks it.
Anything marked "not declared: read the licence file" needs a person to read the licence.
