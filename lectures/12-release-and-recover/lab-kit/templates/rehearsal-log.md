# Restore rehearsal: <date>

A rehearsal is a restore you do on purpose, before you need one, into a separate
instance, with the result checked. One file per rehearsal in `docs/rehearsals/`.

| | |
|---|---|
| **Who** | <names; who ran the commands, who checked> |
| **Backup used** | <file, when it was taken, how it was made> |
| **Restored into** | <the separate instance: where, which release> |
| **Commands** | <exact commands, copied from the runbook> |
| **Checks and results** | <each check: what it asks, PASS/FAIL, the numbers> |
| **Restore time (measured)** | <from start to a checked restore> |
| **Data-loss window** | <time between the backup and the moment of the (pretend) failure> |
| **Surprises** | <anything that did not match the runbook> |
| **Runbook changes** | <what you changed because of this rehearsal; link the commit> |
