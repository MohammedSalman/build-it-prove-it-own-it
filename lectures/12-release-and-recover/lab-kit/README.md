# Lab 12 kit · Release and recover

Everything for Lab 12, Part A. It is self-contained: you need Python 3.11 or newer,
nothing from earlier weeks. Every tool uses the Python standard library, so the same
commands work on macOS, Linux and Windows.

Your laptop plays three machines. **Staging** and **production** are two copies of
AfterHours running side by side, each on its own port with its own database file. A third
one, **restore**, is used only to rehearse restoring a backup. Nothing leaves your laptop.

| Environment | Address | Database file |
|---|---|---|
| production | http://127.0.0.1:9210 | `envs/production/afterhours.db` |
| staging | http://127.0.0.1:9211 | `envs/staging/afterhours.db` |
| restore | http://127.0.0.1:9212 | `envs/restore/afterhours.db` |

If one of these ports is taken on your laptop, change it in `ops/pipeline.json`.

## What is in the kit

| Path | What it is |
|---|---|
| `releases/1.4.0/` | The release running at the start of festival week |
| `releases/1.5.0/` | Friday's release: event categories. Its tests pass. Read `RELEASE.md` |
| `releases/1.5.1/` | The same feature, done safely (you meet it in Part A5) |
| `flags/staging.json`, `flags/production.json` | The feature-flag file of each environment |
| `ops/pipeline.json` | The environments, the release gates, the SLO target |
| `ops/deploy.py` | Deploy a release: tests, promotion, switch, gates |
| `ops/rollback.py` | Put the previous good release back, and check it |
| `ops/status.py` | What runs where; `--history`; `--stop all` |
| `ops/traffic.py` | Simulated festival visitors, with the SLI measured every 5 seconds |
| `ops/sli.py` | The SLI as code: **you write `is_good()` in Part A3** |
| `ops/gates.py` | The `live` and `sli` gates that deploy and rollback run |
| `ops/backup.py` | Back up an environment with SQLite's online backup API |
| `ops/restore_check.py` | Restore a backup into the separate instance and check it: **you write two queries in Part A4** |
| `ops/restore.py` | Restore an environment for real, only from a backup that passes `restore_check.py`; keeps the database it replaces |
| `ops/dbfacts.py` | Row counts and the canonical logical dump used by backup and restore checks |
| `ops/nightly_backup.py` | The team's old nightly backup job. **Planted defect**, on purpose |
| `ops/tamper.py` | Make a damaged copy of a backup, to test your checks |
| `ops/tests/` | Tests for what you write in A3 and A4 |
| `templates/` | Runbook, rehearsal log and postmortem templates (Part B) |

The releases, the team and Friday's incident are fictional, and the problems were
**planted on purpose** for teaching. The code is real and every release runs.

## Set up (10 minutes)

Replace `COURSE` with the folder where you keep the course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/12-release-and-recover/lab-kit ~/w12-kit
cd ~/w12-kit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ops/status.py              # expect: three environments, all "not running"
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\12-release-and-recover\lab-kit $HOME\w12-kit
cd $HOME\w12-kit
python -m venv .venv
.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python ops/status.py              # expect: three environments, all "not running"
```

Open a **second terminal** in the same folder and activate the environment there too.
Terminal 1 runs the simulated visitors (`ops/traffic.py`) for most of the lab; terminal 2
runs everything else. Every command below is run from the kit folder, and is the same in
bash and PowerShell (forward slashes work in PowerShell).

## The commands

| What | Command |
|---|---|
| Deploy a release | `python ops/deploy.py staging 1.4.0` · `python ops/deploy.py production 1.4.0` |
| Roll back | `python ops/rollback.py production` (or `--to 1.4.0`) |
| What runs where | `python ops/status.py` · `python ops/status.py --history` |
| Simulated visitors | `python ops/traffic.py production` (Ctrl+C to stop) |
| Back up | `python ops/backup.py production` |
| Rehearse a restore | `python ops/restore_check.py backups/<file>.db` |
| Restore for real | `python ops/restore.py production backups/<file>.db --confirm production` |
| Tests for your code | `python -m pytest -q` (runs `ops/tests/`) |
| Stop every server | `python ops/status.py --stop all` |

Servers keep running after the command that started them returns, and after you close a
terminal. **Stop them all at the end:** `python ops/status.py --stop all`.

Each server writes its log to `envs/<environment>/server.log`.

### Start again from nothing

Stop the servers first, then delete the two folders the tools create.

**macOS / Linux**
```bash
python ops/status.py --stop all
rm -rf envs backups
```

**Windows PowerShell**
```powershell
python ops/status.py --stop all
Remove-Item -Recurse -Force envs, backups -ErrorAction SilentlyContinue
```

## How the pieces fit

`deploy.py staging 1.5.0` runs four steps and prints each one:

1. **tests**: the release's own test suite, in `releases/1.5.0/`;
2. **promotion**: for production only, the release's latest deploy to staging must have
   passed;
3. **switch**: stop the release running now, start the new one on the same port with the
   same database file;
4. **gates**: the checks listed under `"gates"` in `ops/pipeline.json`. The kit starts with
   `["live"]`: `GET /healthz` must answer 200. In Part A3 you add `"sli"`.

If a gate fails and `"auto_rollback"` is `true`, deploy puts back the last release that
passed its gates in that environment and checks it again. Every deploy and rollback is
recorded in `envs/<environment>/state.json` (`python ops/status.py --history` shows it).

A feature flag is read by the release that knows about it (1.5.1 reads
`event_categories`). The app re-reads its flag file on every request, so editing the file
takes effect at once, with no deploy.
