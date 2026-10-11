# Migration plan: day tickets → festival passes

**Owner:** the release steward. **Status:** planned. **Promise:** requirement M1 in
`requirements.md`: every ticket admits the same holder on exactly the same days before
and after, including tickets sold or moved during the migration.

## Why it can't be one step

v1 stores one day per ticket in `tickets.day`. Passes (T5) need a range. The obvious
change, renaming `day` to `first_day` and adding `last_day`, breaks every v1 server the
moment it runs. And the gates are open all weekend (M2): servers are replaced one at a
time, so for a while v1 and v2 both run against **one** database. This is the
*migration window*. Every step below keeps both working until v1 is gone.

## The three shapes of the tickets table

| Shape | Columns | Who can run on it |
|---|---|---|
| v1 | `day` | v1 |
| expanded | `day`, `first_day`, `last_day` (new ones may be NULL) | v1 **and** v2 |
| contracted | `first_day`, `last_day` (both NOT NULL, `first_day <= last_day`) | v2 |

## The steps

| # | Step | Command | Live apps | Check before moving on |
|---|---|---|---|---|
| 0 | Today | | v1 | `python migrate.py meaning --save before.json` |
| 1 | **Expand**: add `first_day`, `last_day` | `migrate.py expand` | v1 | v1's tests pass on the expanded table |
| 2 | Deploy v2 next to v1 (the window opens) | start v2 servers | v1 + v2 | v2's tests pass on the expanded table |
| 3 | **Migrate**: backfill while both write | `migrate.py backfill` | v1 + v2 | `migrate.py verify` (it will not stay at zero while v1 writes) |
| 4 | Retire v1: stop every v1 server, **then** record it | `migrate.py retire v1` | v2 | no v1 server left (check each one) |
| 5 | Catch up: backfill again, then verify | `migrate.py backfill`, `migrate.py verify` | v2 | all three checks are 0 |
| 6 | Passes on sale | `migrate.py flag multi_day_passes on` | v2 | refused until v1 is recorded as retired (T6) |
| 7 | **Contract**: drop `day` | `migrate.py contract` | v2 | refused unless v1 is retired and all checks are 0 |
| 8 | Compare meaning | `migrate.py meaning --compare before.json` | v2 | tickets that existed before still mean the same (see below) |

`scripts/rehearse.py` runs steps 0 to 8 on a copy of production with both apps writing
throughout, and compares the final meaning with a record of every confirmed write.

## The compatibility strategy (supplied)

v2 follows two rules while the old column exists (see the top of `v2/tickets.py`):

- **WRITE.** Every ticket v2 writes has `day`, `first_day` and `last_day`. For a day
  ticket all three are the same day. For a pass, `day` is its first day.
- **READ.** For a day ticket, `day` is the truth. v1 writes only `day`: its new tickets
  have no `first_day` yet, and it may move a ticket after the backfill has copied it.
  A pass (`first_day < last_day`) exists only in the new columns.

After the contract step `day` is gone, and v2 reads and writes only the new columns. The
same v2 code does both: it looks at the table's columns on each request.

| During the window | writes | reads |
|---|---|---|
| v1 | `day` only | `day` |
| v2 | `day`, `first_day`, `last_day` | `day` for day tickets; `first_day`..`last_day` for passes |
| backfill | `first_day`, `last_day` (copied from `day`) | `day` |

## The backfill (part A3: you write it)

`migrations/backfill.py`, rules B1 to B6:

- **B1** Afterwards every day ticket has `first_day = last_day = day`.
- **B2** Passes are v2's own rows. Never touch them.
- **B3** Safe to run again: a second run right after the first changes nothing.
- **B4** Catches up: a ticket v1 moved after an earlier run is fixed by the next run.
- **B5** At most `batch_size` rows per transaction: SQLite has one write lock for the
  whole database, and the gates are selling and moving tickets while you copy. (Scans only
  read; in WAL mode, which the apps use, readers carry on while a writer works.)
- **B6** Copy inside the database (`UPDATE … SET first_day = day …`), not by reading
  `day` into Python and writing it back later.

## The verification queries

The contract step runs these inside its own transaction and refuses unless all are 0:

```sql
-- missing: tickets with no first_day or last_day
SELECT COUNT(*) FROM tickets WHERE first_day IS NULL OR last_day IS NULL;
-- disagree: day tickets whose new columns no longer match day (moved by v1 after the copy)
SELECT COUNT(*) FROM tickets WHERE first_day = last_day AND first_day <> day;
-- backwards: tickets that end before they start
SELECT COUNT(*) FROM tickets WHERE first_day > last_day;
```

It also refuses unless `migration_log` records `retire-v1`.

## Comparing meaning, not bytes

The v1 table and the contracted table have different columns, so their rows, and any
checksum of them, always differ. What must not differ is what each ticket **means**: who
it admits, on which days. `migrations/meaning.py` reads that from any shape, using the
READ rule above. `meaning --compare` reports every ticket whose meaning changed. It reads
only the tickets table, so it assumes `wristband_mode` is off: with that flag on, the gate
lets every ticket in on any day, and the comparison would not show it.

On a real migration, tickets are sold and moved during the window, so "the same as
before" is not the right expectation for them. The rehearsal keeps a record of every write
the apps confirmed, and compares against that.

## What the guards do not cover

- `retire v1` is a record that a person makes. The contract step trusts it. Check each
  server before you run it.
- A v1 server started by mistake after the contract fails on its first ticket write
  (HTTP 500: there is no `day` column). Loud, which is better than silently wrong.
- Every step before 6 can be undone by going back to v1 alone: v1 ignores the new
  columns. After step 6 that no longer works (v1 would turn pass holders away), and after
  step 7 the old column is gone, so v1 can't run at all. Going back from there needs a
  reverse migration that rebuilds `day` (possible while no passes exist), a repair
  forward, or a restore (Week 12) that also handles every write made since the backup.
  This kit supplies none of them. That is why those steps come last and have guards.

## Afterwards (not part of this lab)

Once passes are permanent: remove the WRITE/READ-rule code from v2, then the
`multi_day_passes` flag. Once v1 is gone: delete the `wristband_mode` row.
