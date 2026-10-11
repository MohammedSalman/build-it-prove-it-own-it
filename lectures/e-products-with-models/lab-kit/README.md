# Extension kit: the AfterHours concierge and its eval

AfterHours (the app after Week 1) with a new feature that contains a model: a **concierge**
that answers *"Something quiet on Friday night?"* with up to three events, or says there is no
good match. The kit also has an **eval**: 20 labelled questions, graders, and a report. The lab
sheet is `lectures/e-products-with-models/lab-e.md`.

Everything runs **offline in replay mode** by default: the model's replies come from
recordings, so you need no API key and no network. The recordings were **authored by the
course team**, not produced by a model (see `recordings/README.md`). Replay checks the code
around the model and the graders. It tells you nothing about how a real model answers.

```
lab-kit/
  README.md             this file
  GRADING.md            the rules: relevance labels, k = 3, abstention, hard rules, rubric, judge
  requirements.txt      pinned packages (the Anthropic SDK is only used by live mode)
  concierge.py          ask one question:   python concierge.py "Something quiet on Friday night?"
  evals.py              run the eval:       python evals.py --config v1
  graders.py            the graders (task A2: three functions to finish)
  judge.py              the model judge for rubric criteria J1 and J2
  evalset.jsonl         20 labelled cases
  evalset-extra.jsonl   4 cases without labels (task A3)
  catalog.json          the frozen festival programme the labels refer to
  human-grades.jsonl    people's grades for J1 and J2 on 20 answers
  budget.json           what the concierge must meet before it ships
  prices.json           list prices per million tokens, with the date they were checked
  recordings/           authored replies for configs v1, v2, v2-small, and the judge
  app/                  AfterHours; app/concierge.py is the feature
  tests/                tests for the app, the concierge, the graders and the eval itself
```

## Set up (about 5 minutes)

You need Python 3.11 or newer. Replace `COURSE` with the folder that holds the course
repository. Use the block for your system; don't mix them.

**macOS / Linux (bash or zsh)**
```bash
cp -R COURSE/lectures/e-products-with-models/lab-kit ~/labe
cd ~/labe
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # expect: 21 failed, 27 passed (the failures are task A2)
python concierge.py "Something quiet on Friday night?"
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\e-products-with-models\lab-kit $HOME\labe
cd $HOME\labe
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m pytest -q                 # expect: 21 failed, 27 passed (the failures are task A2)
python concierge.py "Something quiet on Friday night?"
```

Run every later command from the kit folder with the environment active. The commands are the
same in bash and PowerShell.

## The three configurations

| Config | What changes | Live mode would call |
|---|---|---|
| `v1` | The demo version: every event goes into the prompt, descriptions pasted in, no date or time, no checks on the reply | `claude-opus-5` |
| `v2` | Code shows the model only events that can still be booked; the prompt gives the time, the abstention rule, and marks descriptions as organiser text; a guard drops anything the model was not shown | `claude-opus-5` |
| `v2-small` | The same prompt and code as `v2` on a smaller, cheaper model | `claude-haiku-4-5` |

## Commands

| Command | Use it for |
|---|---|
| `python concierge.py "Something quiet on Friday night?"` | One answer (config `v2`, run 1) |
| `python concierge.py --config v1 --run 2 "..."` | Another config or recorded run |
| `python concierge.py --list` | The questions that have recordings (and the time they were asked) |
| `python concierge.py --show-prompt "Something quiet on Saturday night?"` | Exactly what the model is sent. No model call |
| `python evals.py --config v1` | The eval report for one config |
| `python evals.py --compare v1 v2` | Two configs case by case, with an interval for the difference |
| `python evals.py --config v2 --cases evalset-extra.jsonl` | Your own labelled cases (task A3) |
| `python evals.py --config v2 --judge-check` | The model judge against people's grades (task A4) |
| `python evals.py --config v2 --gate` | Exit 1 unless `budget.json` is met: every case labelled and run, every label valid, the quality, hard-rule, cost and latency lines (for CI) |
| `python evals.py --config oracle` / `--config always-abstain` | Test the eval: answers built from the labels must score 1.00; "no good match" every time sets a floor |
| `python -m pytest -q tests/test_graders.py` | Task A2 |

## Read this before you trust a number

- **The recordings are authored.** The course team wrote every answer by hand to show what an
  eval catches. A score computed from them shows that the graders work, not that any model is
  good or bad.
- **Token counts in replay are estimates** (characters ÷ 4). Real tokenizers differ, and differ
  between models: Anthropic's pricing page says its newer models' tokenizer produces about 30%
  more tokens for the same text. Live mode uses the counts the API returns.
- **Latency in replay was authored with a formula**, not measured. The report says "recorded in
  the file: authored, not measured". Live mode measures the wall-clock time of each call from
  your machine.
- **Replay cannot evaluate a new prompt.** A recording answers one exact prompt. Change the
  prompt, the programme or the question and there is nothing to play back: only a live run
  tells you what the new prompt does. Changes after the reply (the parser, the guard, the
  graders) leave the prompt the same, so replay can test them.
- **Passing the budget in replay is not a ship decision.** It shows the eval and the code around
  the model work. Before launch, run the same eval live, several times, against every line.
- **One eval case is one regression check.** Case `c13` checks one injected instruction in one
  description. Passing it does not show that the concierge resists prompt injection.

## Live mode (optional, costs money)

Only if your course provides an API key and a spending limit. Live mode sends the question and
the whole festival programme to Anthropic's API for every answer.

```bash
export ANTHROPIC_API_KEY=...            # PowerShell: $env:ANTHROPIC_API_KEY = "..."
python concierge.py --live "Something quiet on Friday night?"
python evals.py --config v2 --live --runs 1 --record recordings/my-v2.json
python evals.py --config v2 --recording recordings/my-v2.json      # replay your own run, offline
```

The model ids were configured in September 2026 (`app/concierge.py`, `judge.py`). By then
Anthropic's documentation already listed `claude-opus-5` as a legacy model, with a newer Opus
available. The ids stay pinned on purpose: a model change is a change you evaluate before you
ship it. Check the current model list before you run live mode.
