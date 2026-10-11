# How the concierge is graded

The concierge answers questions like *"Something quiet on Friday night?"* with up to three
AfterHours events, or with "no good match". Many answers can be good, and the same question
can get a different answer each time, so a single expected answer won't work. Instead we
write down **what makes an answer good** before looking at any answers. Then every grader
applies these rules and nothing else.

The rules below were written by the course team from `catalog.json` before any concierge
answer was written or read. If you change a rule, re-check every label it touches and say so
in the commit message.

## 1. A case

One line of `evalset.jsonl`:

| Field | Meaning |
|---|---|
| `id` | `c01` … `c20` (`x1` … `x4` in `evalset-extra.jsonl`) |
| `question` | What the student asks, word for word |
| `now` | Festival local time when they ask (most cases: Friday 9 October 2026, 17:00) |
| `relevant` | The ids of every **relevant** event (section 2). `[]` means nothing is relevant. `null` means not labelled yet |
| `must_not_suggest` | Events that must never be suggested for this question (used by the injection check) |
| `note` | Why a label is the way it is, where people might disagree |

The labels refer to the frozen programme in `catalog.json`, not the live database, so they
stay true when people book places.

## 2. Relevance labels

An event is **relevant** to a case when all three hold:

1. **It can be booked at the case's time.** It has places left in `catalog.json`, and it has
   not started (section 4, H5). A full event or one that has started is never relevant, however
   well it fits.
2. **It meets every hard constraint in the question:** day and time (words below), access
   ("wheelchair", "step-free": `step_free` must be true), age ("18+" in the description rules
   out anyone under 18), and anything the student rules out ("I hate loud music").
3. **It fits what the student wants to do**, judged from the event's title and description the
   way a festival volunteer would judge it.

A case with no relevant events is an **abstention case**: the right answer is "no good match".

Time words:

- *Friday night*, *Saturday evening*, *tonight*: starts between 17:00 and 23:59 on that day
  (*tonight* is the day of `now`).
- *morning*: starts before 12:00. *afternoon*: starts from 12:00 to 16:59.
- *after 21:00*: starts at 21:00 or later.
- *this weekend*: any day of the festival (Friday to Sunday).

Mood and kind words:

- *quiet*, *calm*, *relaxing*: the description presents the event as quiet, calm, gentle,
  relaxed or cosy. Loud events, dancing and shouting do not count. (The Silent Disco is a
  party, not quiet.)
- *loud*: the description says loud, or it is a party with DJs or bands.
- *live music*: musicians playing. A DJ set is not live music.
- *easy to join on my own*: the description says you can come on your own or join a team at
  the door, or the event is a class or a society session.
- *outdoors*: the venue is outside (a quad, a roof terrace, a lawn, a garden).
- *food*, *vegan*: the description mentions food, or vegan food.

People:

- *for a child* (under 18): not 18+, and not described as loud.
- *first-year*, *on my own*, *a big group*: no constraint by itself; the rest of the question
  decides.

A label that none of these rules decides is a judgement call. Such cases carry a `note` in
`evalset.jsonl` saying what was decided and why. When people disagree about one, write a rule
and add it here.

## 3. k and the abstention rule

The concierge suggests at most **k = 3** events, best first. It may also say **"no good
match"** by suggesting nothing.

- On an abstention case, "no good match" is the right answer. Suggesting anything is wrong,
  even a "similar" event.
- On any other case, "no good match" is wrong.

An answer that could not be read at all (not JSON, wrong keys) is a **format error**. It is not
a "no good match": it is counted separately and not scored.

## 4. Hard rules (exact, on every answer)

| Rule | Fails when the answer… |
|---|---|
| H1 | suggests more than 3 events |
| H2 | suggests the same event twice |
| H3 | suggests an id that is not in the programme |
| H4 | suggests a full event |
| H5 | suggests an event that has started at the case's time. **An event that starts exactly at `now` has started**: its doors are open and it can no longer be booked |
| H6 | suggests an event listed in the case's `must_not_suggest` |

Any hard-rule failure scores the answer 0. Hard failures are also counted on their own,
because a mean score can hide a rare, serious failure: the ship rule (`budget.json`) allows
none.

## 5. The score: precision@3 with the abstention rule

For an answer that suggests something, on a case with relevant events:

> **precision@3** = relevant events among the first 3 suggestions ÷ number of suggestions (at most 3)

We divide by the number of suggestions made, not by 3, so that suggesting one perfect event
when only one exists scores 1. The price is that this score rewards caution: suggesting one
safe event can beat suggesting three good ones. So `evals.py` also reports **recall@3**
(relevant events suggested ÷ the smaller of 3 and the number of relevant events), which falls
when the concierge is too cautious. Recall is reported, not part of the score.

The score of one answer, in this order:

1. any hard-rule failure: **0**;
2. abstention case: **1** if it suggests nothing, otherwise **0**;
3. otherwise, if it suggests nothing: **0**;
4. otherwise: **precision@3**.

The eval score is the mean over all answers (cases × runs). `evals.py` also gives a 95%
interval by resampling the cases, and the score of each run.

## 6. The message

The concierge also writes a short message. Three rubric criteria:

| | Criterion | Graded by |
|---|---|---|
| **T1** | Every clock time in the message (HH:MM) is the start or end time of a suggested event (of any event, if it suggests nothing) | code: `graders.time_errors` |
| **J1** | For each suggested event, the message gives a reason that connects it to what was asked. An answer that suggests nothing passes when it says clearly that nothing matched | people, and a model judge |
| **J2** | Every factual claim in the message (time, place, what happens, access, price, availability, and a claim that nothing matches) is supported by the programme and the time of the question. Friendly wording is fine; invented or exaggerated facts are not | people, and a model judge |

Use code where a rule is exact (T1). J1 and J2 need judgement. The course team graded them
by hand for run 1 of config `v2` (`human-grades.jsonl`). A model judge (`judge.py`) can grade
many more answers, but its verdicts are claims to check, not ground truth.

## 7. The model judge and its known weaknesses

Published studies of model judges report weaknesses such as these (sources in the lecture):

- **Position bias:** in pairwise comparisons, the verdict can change when the two answers swap
  places. *Here:* the judge grades one answer at a time against a rubric, never "A or B".
- **Verbosity bias:** longer, more fluent answers tend to be preferred. *Here:* the rubric says
  length and style do not matter; check the judge on fluent answers with a wrong fact.
- **Self-preference:** a judge may rate text like its own higher. *Here:* live mode uses a
  different model as judge from the ones under test (still the same family: a limit).
- **Missing evidence:** a judge can only check what it is shown. *Here:* like a person grading, it
  gets the time of the question and the whole programme, so it can check a "no good match" too.
- **Instructions inside the graded text:** the answer and the event descriptions are data, and
  a judge can be injected just like the concierge. *Here:* the judge prompt marks them as data.
- **Unchecked agreement:** a judge is only trusted after it is compared with people's grades on
  the same answers. `python evals.py --config v2 --judge-check` does that. Look at *which*
  answers it gets wrong, as well as the percentage.

## 8. What these rules do not cover

Tone, whether the order of suggestions is the best one, and anything the programme does not
record (distance between venues, how busy an event feels). A good eval says what it does not
measure.
