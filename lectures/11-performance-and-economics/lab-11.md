# Lab 11 · Measure, Find, Fix, Remeasure

**Time:** 2 hours · **Work in:** pairs · **Hand in:** the evidence packet at the end (one per
pair, plus one practice-defence note each)

In the lecture the festival page was fast with 10 events and slow with ten festivals of
data. Today you measure that yourself, find the cause without guessing, fix it with a change
that a test checks, and measure again. You finish with a claim about speed that a stranger
could check, and with a first performance budget for your own product.

The festival data is **synthetic**: made up by a script, the same for everyone. The slow
query is not planted for today; the schema has had it since Week 1. What we chose is a
database big enough for it to matter.

Agents are allowed in Parts A1–A4, A6 and B. If one helps you, say where. **Part A5 (the
practice defence) is unaided.** You own every claim you hand in.

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Where only
one command is shown, it is the same in both.

| Part | What | Minutes |
|---|---|---:|
| 0 | Set up | 10 |
| A1 | Baseline: how slow, for whom, at what load | 15 |
| A2 | Find the cause without a stopwatch | 15 |
| A3 | A test that fails first, then the fix | 10 |
| A4 | Remeasure and compare | 15 |
| A5 | Practice defence (5 minutes each) | 10 |
| A6 | Your own numbers: producing, checking, integrating | 5 |
| B | Your team's product: a performance budget and a baseline | 25 |
| | Evidence packet and hand-in | 10 |

**About timing on laptops.** Latency depends on your machine and on what else it is doing.
Keep the laptop plugged in, close what you can, and don't use it while `load.py` runs.
Your numbers will differ from your neighbours'. That is expected; compare your own before and
after, made on the same machine, close together in time.

---

## Part 0 · Set up (10 min)

Follow **Set up** in `COURSE/lectures/11-performance-and-economics/lab-kit/README.md`. You
end in the folder `afterhours-lab11` with the environment active, a first commit, and:

- [ ] `python -m pytest -q` → `9 passed`
- [ ] `python scripts/seed_festival.py` → `4,000 events, 1,000,000 reservations`, and this
      term's festival has event ids 3601 to 4000

Open a **second terminal**, `cd` into `afterhours-lab11` and activate the environment there
too (`source .venv/bin/activate` or `.venv\Scripts\Activate.ps1`). In terminal 1:

```
uvicorn app.main:app
```

Open http://127.0.0.1:8000. The page shows this term's festival. Notice how long it takes.
Then click an event's name. The event's own page (`/?event=3601` for the escape room) asks
the server for its places left every 10 seconds, with `GET /api/events/{id}`. That request is
the one you measure today.

## Part A1 · Baseline: how slow, for whom, at what load (15 min)

Open `worksheet.md` in your repository. Fill in **§1 before you measure**: who is waiting,
for what, and what you expect.

1. **A quiet moment.** In terminal 2:
   ```
   python scripts/load.py
   ```
   This sends the request an open event page makes, `GET /api/events/{id}`, for random events
   of this term's festival, 20 times a second for 10 seconds, three times. Copy all three runs into
   worksheet §3.
2. **The sweep.** Now raise the rate step by step. It takes two to three minutes; don't use
   the laptop meanwhile. Fill in worksheet §2 on paper while it runs.
   ```
   python scripts/load.py --rates 10,20,40,80,160 --duration 5 --csv results.csv --label before
   ```
   Copy the summary table into worksheet §3.
3. Answer in the worksheet:
   - Between which two rates is **the knee**, where p95 stops being flat and jumps?
   - Look at **achieved** and **errors** above the knee. What happened to the requests that
     did not come back in time?
   - At 8 pm we expect about 200 availability checks per second (2,000 students, one check
     every ten seconds each). What would a student see?

## Part A2 · Find the cause without a stopwatch (15 min)

A stopwatch tells you *that* it is slow. It rarely tells you *why*. Start with evidence that
gives the same answer on every machine.

1. **Hypotheses first.** In worksheet §4, write **at least three** hypotheses for why the
   availability check is slow, each with the result that would rule it out. Write them
   before you run anything below.
2. **What does the request do in the database?** This runs inside Python and needs no
   server; leave the app running.
   ```
   python scripts/explain.py
   ```
   Record: how many SQL statements, the query plan, the SQLite steps, the table sizes.
3. **A discriminating experiment.** Event 3604 (the Maker Workshop) has 12 reservations; event
   3607 (a club night) has several hundred. If the work depended on the size of the event,
   their step counts would differ a lot. Predict, then run:
   ```
   python scripts/explain.py /api/events/3604
   python scripts/explain.py /api/events/3607
   ```
4. **The same code at demo scale.** Build a small database next to the big one and look at
   the same request there (the app keeps using `afterhours.db`):
   ```
   python scripts/seed_festival.py --scale demo --db demo.db
   python scripts/explain.py --db demo.db /api/events/1
   ```
   Same plan? How many steps? Why did nobody notice this in Week 1?
5. **Booking uses the same kind of count.** Read `reserve()` in `app/reservations.py`: it
   counts an event's reservations twice. Look at the plan of that count:
   ```
   python scripts/explain.py --sql "SELECT COUNT(*) FROM reservations WHERE event_id = 3601"
   ```
6. In the worksheet: which hypotheses are ruled out, and by which line of evidence?

`SCAN r` means SQLite reads every row of `reservations` (alias `r`), one after another.
`SEARCH … USING … INDEX` means it jumps to the matching rows through an index. A step is
one instruction of SQLite's small internal machine: for the same data it is the same count
on every laptop.

## Part A3 · A test that fails first, then the fix (10 min)

A timing test would pass on a fast laptop and fail on a slow one. A plan test gives the same
answer however busy the machine is, and it catches the problem even on the tiny test
database: SQLite picks a plan from the query, the schema and, only after someone runs
`ANALYZE` (AfterHours never does), statistics about the data. So with the same SQLite version
the test database gets the festival's plan. Record your SQLite version in worksheet §2;
`explain.py` prints it.

1. Create `tests/test_query_plan.py` with this, and write the two assertions yourself:
   ```python
   from app import db
   from app.main import EVENT_SQL

   from .conftest import event_by_title

   ESCAPE_ROOM = "Escape Room: The Locked Lab"


   def plan(sql, params):
       """SQLite's plan as one string, e.g. 'SEARCH e USING ... | SCAN r LEFT-JOIN'."""
       conn = db.connect()
       try:
           rows = conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
       finally:
           conn.close()
       return " | ".join(row["detail"] for row in rows)


   def test_the_availability_check_uses_an_index(client):
       event = event_by_title(client, ESCAPE_ROOM)
       detail = plan(EVENT_SQL + " WHERE e.id = ? GROUP BY e.id", (event["id"],))
       # TODO 1: the plan must not scan the reservations table.
       #         (Newer SQLite prints "SCAN r"; older versions "SCAN TABLE reservations AS r".)
       # TODO 2: the plan must use an index to find this event's reservations.
   ```
   - [ ] `python -m pytest -q tests/test_query_plan.py` **fails**, and the message shows the plan
2. **The fix.** Add one statement at the end of `app/schema.sql` that creates an index on
   `reservations(event_id)`. Use `CREATE INDEX IF NOT EXISTS`, because the app runs this file
   every time it starts. Nothing else changes.
   - [ ] `python -m pytest -q` → `10 passed`
3. **Restart the app** in terminal 1 (Ctrl+C, then `uvicorn app.main:app`). At start-up it
   builds the index on your million rows; that takes a moment. Then:
   ```
   python scripts/explain.py
   python scripts/explain.py --sql "SELECT COUNT(*) FROM reservations WHERE event_id = 3601"
   ```
   Record the new plan and steps in worksheet §5.
4. Commit only the change and its test, so your diff shows exactly what you changed:
   ```
   git add app/schema.sql tests/test_query_plan.py
   git commit -m "Index reservations by event"
   ```

## Part A4 · Remeasure and compare (15 min)

Same machine, same data, same commands, as soon as you can after the baseline.

```
python scripts/load.py
python scripts/load.py --rates 10,20,40,80,160 --duration 5 --csv results.csv --label after
```

Fill in worksheet §6 and §7, then write the claim in §8. Two rules for the claim:

- **Evidence, not a gate.** Report what you measured, with its conditions. Don't write
  "it is fast now"; write the numbers, the rate, the runs, and the machine.
- **Say what you did not measure.** For example: booking under load, the festival list page,
  many people booking at once, another machine, a real network.

If you have time: the 8 pm rate on the fixed app, `python scripts/load.py --rate 200`.

## Part A5 · Practice defence (10 min: 5 minutes each)

A rehearsal for the graded defences later in the term. **Unaided:** no notes, no agent, no
running anything. The code may be open on the screen. One of you explains, the other listens,
times, and marks. Then swap.

**Student 1: the availability check.**
1. *Explain (3 min).* On the escape room's page (`/?event=3601`), how does the page's request
   `GET /api/events/3601` turn into the words "1 place left!", and how does the number stay
   current? Name the files and functions in order, the SQL it runs, and what SQLite does to
   answer it, before and after your index.
2. *Predict (2 min).* Your index is on `reservations(event_id)`. What is the plan, and roughly
   how many steps, for
   `SELECT COUNT(*) FROM reservations WHERE attendee = 'student-00042'`? Why?

**Student 2: the measurement.**
1. *Explain (3 min).* How does `load.py` get the p95 of one run? Say what counts as one
   sample, from which moment a latency is measured, and what happens to a request that has
   no answer after 5 seconds.
2. *Predict (2 min).* You run `python scripts/load.py --duration 2 --repeat 1`. How many
   requests does the run count, and which of them is its p99? What does that tell you about
   p99 from short runs?

**The listener marks** (one line each): path or method complete and in order · the key
mechanism named correctly (the plan; the moment latency starts) · prediction stated with a
reason. Then check both predictions together: run them (`explain.py --sql …`,
`load.py --duration 2 --repeat 1`) and write down whether each was right. A wrong prediction
that you then understand is a good outcome for a practice.

## Part A6 · Your own numbers: producing, checking, integrating (5 min)

Labs 1 to 10 each ended with "One measurement": your own minutes producing, checking and
integrating. Copy your rows into `economics/effort-template.csv` (your pseudonym in the
`student` column; delete the row of any lab you did not record). Today's lab is not in it yet:
you record your Lab 11 row at the end of the lab, with its homework, like every other lab. Then:

```
python economics/effort.py economics/effort-template.csv
```

Each lab has only your row, and the script never shows a lab with fewer than 5 rows, so it
hides every lab and prints one overall line instead: your pooled shares over all your rows. Answer in one sentence each: what share of your recorded lab time
was checking, and what share was integrating? Name one reason your own numbers could be wrong.
(If you kept no numbers, run `python economics/effort.py` on the **synthetic** example instead
and say what you would need to collect.)

## Part B · Your team's product (25 min)

This ticks the Week 11 item on the product checklist: *a performance budget for one page with
a measured baseline* (`docs/performance.md` with numbers and method).

1. **Pick one page** your users will wait on at your festival's busiest moment. Name the
   request behind it.
2. **Write the budget** in `docs/performance.md`: "p95 of `<request>` at most ___ ms at ___
   requests per second, with ___ rows of data", and one sentence on why (who waits, and what
   Week 9 said about how long people wait before they give up or tap again).
3. **Make the data realistic.** How many rows will your busiest table hold after a year?
   Adapt `scripts/seed_festival.py`, or write a smaller seeding script.
4. **Measure a baseline.** Copy `scripts/load.py` into your repository and run it against your
   page (`--path`, `--ids`), three runs. Record the command, data size, machine, commit and
   date with the numbers.
5. **Check the plan** of the request's main query (`EXPLAIN QUERY PLAN`) and record it. If it
   says `SCAN` on a table that will grow, note it as a risk, with a fix to try.

If step 3 or 4 does not fit, finish at home (**≈45 min**): the budget and the plan check are
the minimum for today.

## Evidence packet and hand-in (10 min)

| | |
|---|---|
| **Requirement** | The availability check stays usable at the festival's busiest moment |
| **Decision** | What you changed and why; what you ruled out (from A2) |
| **Change** | `git diff HEAD~1` (the index and your test) |
| **Check** | The plan test: fails before, passes after. `explain.py` before and after (plan, steps) |
| **Result** | Your claim from worksheet §8, with the before and after tables from `results.csv` |
| **Defence** | Each student: what you explained, your prediction, whether it was right (A5) |
| **Product** | Link to `docs/performance.md` with the budget, the baseline and the plan (B) |

Also hand in the filled worksheet and `results.csv`.

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 11, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 11 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### Optional extensions

- **The festival list.** The list page makes a different request with a different plan. Run
  `python scripts/explain.py "/api/events?from=2026-10-09&to=2026-10-12"` in Part A2, before
  your fix, and again after it. What is an `AUTOMATIC COVERING INDEX`, and why is building one
  for every request expensive? (To see "before" again after committing the fix, `git stash`
  is not enough: the index is already in your database, and the app and `explain.py` recreate
  it from `schema.sql`. Use the commit before your fix and a new database:
  `git switch --detach HEAD~1`, then `python scripts/seed_festival.py --db list-before.db` and
  `python scripts/explain.py --db list-before.db "/api/events?from=2026-10-09&to=2026-10-12"`,
  check that it says `Indexes on reservations: none`, then `git switch -`.)
- **A work budget instead of a time budget.** Write a test that counts SQLite steps for the
  availability check, adds 20,000 reservations for another event, and checks that the count
  did not grow. Why does this pass on every laptop?
- **A scoped workflow experiment.** Design, and if there is time run, a small fair comparison:
  diagnosing a slow query with an agent versus without. Use worksheet §1 and §7 for the
  design; log minutes in four categories (implement, review, debug, rework); randomise which
  pair gets which task; say what your result cannot show.

### How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Baseline | Three runs and a sweep, each with achieved rate, errors, samples and percentiles; the knee located; the 8 pm question answered from the data | One run, or an average only, or no rate stated |
| Diagnosis | Hypotheses written before the evidence; each ruled in or out by a named line of `explain.py` output; the event-size experiment used | "It needed an index" with no evidence, or timings only |
| Fix and check | The plan test fails before and passes after; the index is one line in `schema.sql`; nothing else changed | A timing assertion in a test, or no failing test first |
| Claim | Before and after on the same machine, with ranges over runs, errors, conditions, and what was not measured | "It's 10× faster" with no conditions or spread |
| Defence | Path complete and in order; prediction reasoned, then checked | Read from the screen line by line; prediction not checked |
