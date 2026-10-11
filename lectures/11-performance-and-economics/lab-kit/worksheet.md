# Lab 11 · Experiment worksheet

One per pair. Fill it in as you go, not at the end. Parts of the lab are named in brackets.
Write numbers exactly as the tools print them.

## 1 · The question, before you measure (A1)

**Who is waiting, for what, and when?** (one sentence, e.g. "a student opening an event page
at 8 pm on the first night")

______________________________________________________________________________

**What we believe will happen, and the result that would prove us wrong:**

______________________________________________________________________________

## 2 · The setup (A1)

| | |
|---|---|
| Machine (model, cores, operating system) | |
| Plugged in? What else was running? | |
| Data (`seed_festival.py` output) | |
| Commit (`git log --oneline -1`) | |
| SQLite version (`python -c "import sqlite3; print(sqlite3.sqlite_version)"`) | |
| Request measured | `GET /api/events/{id}`, ids 3601-4000 |
| Command | |

## 3 · Baseline: before any change (A1)

**3 runs at 20 requests per second** (`python scripts/load.py`)

| Run | Achieved rate | Requests | Errors | p50 | p95 | p99 | Max |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |

**Sweep** (`python scripts/load.py --rates 10,20,40,80,160 --duration 5`): copy the summary.

| Target rate | Achieved (median) | Errors (all runs) | p95 (median) | p95 range over runs |
|---|---|---|---|---|
| 10/s | | | | |
| 20/s | | | | |
| 40/s | | | | |
| 80/s | | | | |
| 160/s | | | | |

Where is the knee on your machine (between which two rates)? ______

At 8 pm we expect about 200 availability checks per second. What would a student see?

______________________________________________________________________________

## 4 · Find the cause (A2)

**Hypotheses** (at least three, written before you run `explain.py`):

| # | Hypothesis | What result would rule it out? | Result |
|---|---|---|---|
| H1 | | | |
| H2 | | | |
| H3 | | | |

**Evidence** (`python scripts/explain.py`)

| | |
|---|---|
| SQL statements per availability check | |
| Query plan (copy it) | |
| SQLite steps | |
| Rows in `reservations` | |
| Time for one request, no load (`explain.py`) | |

Which hypotheses are ruled out, and by which line of evidence?

______________________________________________________________________________

## 5 · The change and its deterministic check (A3)

| | |
|---|---|
| The change (paste the diff, or the one line) | |
| Test that checks it (file and test name) | |
| Test result **before** the change | |
| Test result **after** the change | |
| Query plan after | |
| SQLite steps after | |

## 6 · Remeasure (A4)

Same machine, same data, same commands, as soon as possible after the baseline.

**3 runs at 20 requests per second**

| Run | Achieved rate | Requests | Errors | p50 | p95 | p99 | Max |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |

**Sweep** (same command as before)

| Target rate | Achieved (median) | Errors (all runs) | p95 (median) | p95 range over runs |
|---|---|---|---|---|
| 10/s | | | | |
| 20/s | | | | |
| 40/s | | | | |
| 80/s | | | | |
| 160/s | | | | |

## 7 · Compare honestly (A4)

- Is the difference between before and after bigger than the spread between runs of the
  same build? ______
- Name two things **other than your change** that could have made the second measurement
  faster or slower, and what you did about each:
  1. ______________________________________________________________
  2. ______________________________________________________________
- What did you **not** measure? (other requests, other machines, many users booking, …)

  ______________________________________________________________

## 8 · The claim

Complete the sentence. It is your evidence packet's **Result** line.

> On ______ (machine), with ______ (data), at ______ requests per second, p95 latency of the
> availability check went from ______ (range ______) to ______ (range ______) over three
> runs each, with ______ errors before and ______ after. The query plan changed from
> ______ to ______, and a test now checks it. We did not measure ______.
