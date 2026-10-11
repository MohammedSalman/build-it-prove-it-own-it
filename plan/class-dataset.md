# The class dataset: one contract

Across the term, each student records how many minutes a lab took them, split by kind of
work. Week 11 charts the data to teach the economics of agentic work; Week 14 uses it in the
course retrospective. This file is the single contract both use. Labs, templates, collectors,
and analysis scripts follow it exactly.

## What students record

For **every lab from 1 to 13**, each student (not the pair) records three numbers for their
own work in that lab, including its homework. The row is handed in at the end of the lab, or
together with the lab's homework when it has some:

| Field | Meaning |
|---|---|
| `producing_min` | Minutes spent producing: writing code, tests, text, prompts; waiting for an agent to produce |
| `checking_min` | Minutes spent checking: running, reading, reviewing, comparing, measuring |
| `integrating_min` | Minutes spent making separate pieces work together: merging, resolving conflicts, wiring parts. Write `0` when there was none |

Estimates are fine (the form may offer an "estimated" tick box; the CSV does not store it). The
numbers are **not assessed** and are handed in separately from
the pair's evidence packet, as one row per student, under a pseudonym the student chooses once
for the whole term. No names.

## File format

One CSV, UTF-8, with a header row and exactly these six columns, in this order:

```
source,student,lab,producing_min,checking_min,integrating_min
```

| Column | Rule |
|---|---|
| `source` | `class` for real collected data, `synthetic` for invented example data. Tools never mix the two in one chart |
| `student` | The pseudonym. Never a name or student number |
| `lab` | Integer 1–13 |
| `producing_min`, `checking_min`, `integrating_min` | Integers 0–300. Blank is allowed only for `integrating_min` in data collected before this contract, and is read as 0 |

Lines starting with `#` are comments (used to label synthetic files).

**Validity.** A row is excluded, and counted in the tool's "excluded" line, if any value is
outside 0–300, if the row total is 0, or if the row total exceeds 360 minutes.

**Privacy.** Tools print aggregates only. They never print one student's row, and they hide
any lab with fewer than 5 valid rows. Week 11's overall line covers the labs shown (or all rows
when none is shown, so a student can analyse their own file); Week 14's overall line needs at
least 5 students.

## How the numbers are summarised

- **Total** for a row = producing + checking + integrating.
- **Shares** are reported for all three kinds; integration is its own category, never folded
  into checking.
- Week 11 reports **pooled** shares (sum of each kind over all rows, divided by the sum of
  totals). Week 14 reports the **median of individual shares** (each student's share across
  their rows, then the median across students). Both label which one they show.

## Collection schedule

| Labs | What is collected |
|---|---|
| 1–13 | All three numbers per student per lab (`integrating_min` is 0 when there was none) |
| 14, Extension | Not collected |

Week 11 charts Labs 1–10 (the labs completed by then). Week 14 charts Labs 1–13.
