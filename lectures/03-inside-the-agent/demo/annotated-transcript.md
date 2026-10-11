# Open the box: a real agent transcript, annotated (Lecture 3, hook)

**What this is.** The complete event log that Codex CLI wrote while it ran Lecture 1's
bounded investigation (the task contract below, on a throwaway copy of the AfterHours
starter). The log is `codex-investigation.jsonl` in this folder: 16 JSON events, unedited
except that the long path of the Python environment is shortened to `<venv>` (3 places).
Its final message is word for word the answer saved in
`lectures/01-code-is-cheap/demo/agent-investigation.md` (checked by script; see
`verification.md`).

- Agent: Codex CLI 0.154.0-alpha, model gpt-6-astra, run non-interactively on 2026-09-27
  (`codex exec --json`).
- Enforced by the sandbox: file reads and writes inside the copy; **no network ports**.
- Asked in the contract only: "Do NOT modify any file in the repository."

Nothing below is invented. Line counts and character counts are computed from the log.
The annotations are ours.

## The task (what we sent)

```
TASK CONTRACT: bounded investigation (you are the coding agent in a classroom demo; answer as you normally would)

Goal: Find out whether AfterHours can confirm more reservations for an event than its capacity, and why.
Context: This repo is a small FastAPI + SQLite app. Read AGENTS.md first. The promise that must hold: confirmed reservations for an event <= its capacity.
Environment: a ready Python venv is at <venv> (use <venv>/bin/python, .../uvicorn). Use a throwaway database path via AFTERHOURS_DB=/tmp/afterhours-investigation.db if you run the app.
Limits: Investigate only. Do NOT modify any file in the repository. You may read files and run the tests and scripts.
Deliver, in this order:
  1. The code path of one reservation request, with file:line references.
  2. Every assumption that code path makes (about timing, users, the database, the network).
  3. Whether the promise can break, exactly how, and your evidence (commands you ran and their output). Say clearly which claims you verified by running something and which you inferred from reading.
  4. The smallest repair you would suggest (describe or show it; do not apply it), and what it would NOT fix.
Stop when you have evidence for item 3, or if you are blocked; if blocked, say what blocked you.
Keep the final answer under 600 words.
```

1,541 characters as sent (the real path was longer than `<venv>`).

## The log, event by event

| # | Event (from the log) | What came back into the context | Annotation |
|---|---|---|---|
| 0 | `thread.started`, `turn.started` | | One task, one "turn" of the loop in Codex's terms. Inside it, the model is called again and again |
| 1 | **message:** "I’ll read `AGENTS.md`, trace the reservation request, and run a bounded check using the provided venv and throwaway database. I won’t modify repository files." | | A plan, in plain text. It restates the limit, which is a promise, not a guarantee |
| 2 | **command:** `cat AGENTS.md` | 26 lines, 1,184 characters, exit 0 | The model cannot open a file. It asks the harness to run a command; the harness runs it and pastes the output back |
| 3 | **command:** `rg --files -g '!*.db' ...` (list the files) | `zsh:1: command not found: rg`, exit 127 | A tool failed. The failure is just more text in the context, and the model picks another route |
| 4 | **command:** `nl -ba app/main.py; nl -ba app/reservations.py; nl -ba app/db.py; nl -ba app/payments.py; nl -ba scripts/race.py` | 350 numbered lines, 14,362 characters | Five whole files at once. `race.py` (4,429 characters) is never cited in the answer |
| 5 | **command:** `find . -name AGENTS.md -o -path './tests/*'; nl -ba app/schema.sql; nl -ba app/static/index.html` | 166 lines, 7,091 characters | `index.html` is 6,404 of those characters. The answer cites 15 of its 149 lines (122–136) |
| 6 | **message:** "The capacity check and insert run as separate autocommit statements, with a simulated payment delay between them. That leaves a window for two requests to pass the same check. I’ll test this once with two requests for a one-place event." | | A hypothesis, formed from what is now in its context. Next it tries to test it |
| 7 | **command:** `... <venv>/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765` | `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 8765): operation not permitted`, exit 3 | The sandbox refused to open a port. The harness decided that, not the model. This is a fence |
| 8 | **message:** the final answer (3,897 characters) | | It reports the block and marks its main claim as inferred. Lecture 1 checks every claim |
| 9 | `turn.completed`, usage: `input_tokens 104476`, `cached_input_tokens 90880`, `output_tokens 1553`, `reasoning_output_tokens 196` | | It read about 67 tokens for every token it wrote |

## What entered the context (visible parts, characters)

| Source | Characters |
|---|---:|
| Task contract | 1,541 |
| AGENTS.md | 1,184 |
| main.py, reservations.py, db.py, payments.py (cited) | 9,929 |
| race.py (read, never cited) | 4,429 |
| index.html (15 of 149 lines cited) | 6,404 |
| schema.sql and the file list | 686 |
| The agent's own commands | 583 |
| The agent's two short messages | 394 |
| Error output (`rg` missing, port refused) | 414 |
| **Total visible before the final answer** | **25,564** |

By the rough rule of 4 characters per token, that is about 6,400 tokens. The run reported
104,476 input tokens. Two things explain the gap: parts of the context the log does not show
(below), and the loop itself. Every model call sends the whole conversation again, so the
same text is counted once per call. 90,880 of the input tokens were served from a prompt
cache, which means they had been sent before.

## What the log does not show

- The instructions Codex gives the model (its system prompt) and the definitions of its
  tools. They are in the context on every call. Their size is not in the log.
- The model's reasoning. The usage line counts 196 reasoning tokens; their text is not
  in the log.
- Where one model call ends and the next begins. Some boundaries are forced: the message in
  row 6 describes code the model had only just read, and the final answer quotes the error
  from row 7, so each of those came from a later call than the output it uses.

## How to use it in class

Project the table above (or Fig 3.1 in the chapter) and ask: "At row 7, what exactly did the
model have in front of it?" The answer is rows 1–6 plus the hidden instructions: nothing else.
There is no memory, no understanding of the repository beyond that text, and no ability to
act except by asking.
