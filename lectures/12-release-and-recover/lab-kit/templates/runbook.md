# Runbook: <product name>

A runbook is written for a tired teammate at 21:00 on festival night, who did not build
this and has no agent to ask. Every step is a command to copy and a result to compare.
Keep it in the repository (`docs/runbook.md`) and change it in the same pull request as
the thing it describes.

**Owner:** <name> · **Last rehearsed:** <date>, see `docs/rehearsals/` · **Last changed:** <date>

## Before you start

- Where things run: <URLs, ports, which machine or service>
- Where the data lives: <database file or service, and where backups go>
- Who to tell, and how: <team channel; who decides on rollback or restore>
- What "working" means: <the SLI and its target, and how to measure it now>

## 1. Deploy a release

**When:** <e.g. a merged release, never on festival night after 18:00>

| # | Do | Expect | If not |
|---|---|---|---|
| 1 | <command> | <what you should see> | <stop, and do what> |
| 2 | | | |

**Stop conditions:** stop and roll back if <the SLI below X for Y minutes, a gate fails, ...>.

## 2. Roll back

**When:** <a release made things worse and did not change the data in a way the older
release cannot read>

| # | Do | Expect | If not |
|---|---|---|---|
| 1 | | | |

**Rollback is not safe when:** <e.g. the release removed or renamed a column; then roll
forward or restore, and say who decides>

## 3. Restore from a backup

**When:** <data is lost or damaged>. **First:** <stop writes, or tell people what will be
lost>. **Never** restore over production before the restore passed its checks in a
separate instance.

| # | Do | Expect | If not |
|---|---|---|---|
| 1 | | | |

**Our targets:** RPO <how much data we accept to lose> · RTO <how long we accept to be
down>. **Measured in the last rehearsal:** data-loss window <...>, restore time <...>.

## Known gaps

- <things this runbook does not cover yet>
