# Lab 3 · Inside the Agent

**Time:** 2 hours · **Work in:** pairs · **Hand in:** one evidence sheet per pair (end of lab)

In the lecture you read a real agent's log and the loop that produced it. Today you finish a
small agent of your own. You make its writes safe, give it a stopping rule, watch its
permission layer block forbidden requests, and write the contract and the rules for a task.
Then you apply the week to your team's product.

Agents are allowed in this lab. If one helps you, say where. You must be able to explain every
line you hand in without it.

> **Read this first.** The kit runs **offline in replay mode**. The "model" is a recording
> that the course team wrote in the exact shape of real API replies; it is not model output.
> A recording plays its next turn whatever the tools returned. So replay proves that the
> *harness* works (the loop, the dispatcher, the permission layer, the stopping rule). It
> says nothing about how a real model behaves. And the kit's permission layer is a
> **teaching model, not a security boundary**: code that `run_tests` executes can still do
> anything your user account can do.

| Part | What | Minutes |
|---|---|---:|
| 0 | Set up | 10 |
| A | The mini-agent: A1 watch · A2 safe writes · A3 stopping rule · A4 forbidden requests · A5 your contract | 65 |
| B | Your team's product: AGENTS.md, three contracts, the CI gate | 25 |
| | Evidence sheet and hand-in | 10 |

Commands are given for **macOS/Linux** (bash or zsh) and **Windows PowerShell**. Where only
one line is shown, it is the same in both, except that PowerShell may use `\` in paths.

---

## Part 0 · Set up (10 min)

Replace `COURSE` with the folder that holds the course repository.

**macOS / Linux**
```bash
cp -R COURSE/lectures/03-inside-the-agent/lab-kit ~/lab3
cd ~/lab3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd mini-agent
python -m pytest -q
```

**Windows PowerShell**
```powershell
Copy-Item -Recurse COURSE\lectures\03-inside-the-agent\lab-kit $HOME\lab3
cd $HOME\lab3
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
cd mini-agent
python -m pytest -q
```

- [ ] pytest reports **18 failed, 17 passed**. The 18 failures are your tasks A2 and A3.
  On Windows without Developer Mode you may see **15 failed, 16 passed, 4 skipped**: the
  symlink tests need a right your account does not have. That is fine; the symlink rules are
  still part of your task.
- [ ] Every later command runs from the `mini-agent` folder with the environment active.

The agent's file tools never work in your folder. Each run copies `../afterhours` into a new
throwaway folder in your system's temp directory and prints its path, so you can look inside
afterwards. (The copy protects your files from the agent's writes. It does not contain the
tests that `run_tests` executes; they run as you.)

## Part A · The mini-agent (65 min)

### A1 · Watch the loop (10 min)

```bash
python agent.py --replay recordings/add-name-check.json
```

Read the output from the top: the task contract, then one block per model call, then the
**EVIDENCE** section that the harness collects itself. Open `agent.py` and find `run()` and
`dispatch()`. Answer:

1. How many model calls were there, and how many tool requests? Which call asked for more
   than one tool, and which asked for none? Why does the loop end after that one?
2. Which call sent the largest context, and what made it grow?
3. The model's last message says `python -m pytest -q` gives **10 passed**. What does the
   EVIDENCE section say? Which do you believe, and why did the replayed "model" not notice?
4. How many times did the task text travel to the model during this run?

### A2 · Make writes safe (20 min)

Two of the writes in A1 failed with `NotImplementedError`. Open `tools.py` and implement
`safe_write_path()`. Its docstring states the rules: refuse empty paths, absolute paths, any
`..`, any symlink along the path (even one that points inside the workspace), and folders.

```bash
python -m pytest -q tests/test_write_file.py        # until all 12 pass
python agent.py --replay recordings/add-name-check.json
```

- [ ] `tests/test_write_file.py`: 12 passed (or 9 passed, 3 skipped on Windows without symlinks)
- [ ] The replay now ends with `tests in the workspace: 10 passed` and
      `files changed: tests/test_names.py (new), app/main.py (changed)`

Then answer: `read_file` already checks paths with `resolve()` and `is_relative_to()`. Why is
that check not enough for writes? (Hint: look at
`test_refuses_a_linked_file_even_when_it_points_inside`, and at which path the permission
layer checks.)

### A3 · The stopping rule (15 min)

Run the recording that never finishes:

```bash
python agent.py --replay recordings/runaway.json
```

It runs until the recording runs out, 30 calls later. Now open `agent.py` and finish
`should_stop()`: it already stops when the model asks for no tools; add the cost cap and the
step limit, in the order the docstring gives.

```bash
python -m pytest -q tests/test_stopping.py          # until all 8 pass
python agent.py --replay recordings/runaway.json
python agent.py --replay recordings/runaway.json --max-steps 30
```

| Command | Stop reason | Steps | Tokens (estimated) |
|---|---|---:|---:|
| `runaway.json` | | | |
| `runaway.json --max-steps 30` | | | |

Answer:

1. Look at the `context ~N tokens in` line of each step. Why does the running total grow
   faster than any single step?
2. The second run has a cap of 60,000 tokens. How far over it did the run go, and why can
   `should_stop()` not stop exactly at the cap? What would a harness have to check, and
   when, to make the cap exact?
3. For a real run, which limit would you rely on first, the steps or the tokens? What is
   left behind when a run is stopped halfway (look in the workspace and in `logs/`)?

### A4 · Forbidden requests (10 min)

This recording is an investigation during a code freeze. Run it with the read-only rules,
then open the blocked-call log:

```bash
python agent.py --replay recordings/code-freeze.json --permissions permissions-readonly.json
```
```bash
cat logs/blocked.jsonl                  # PowerShell: Get-Content logs\blocked.jsonl
```

Now run it again with the default rules (leave out `--permissions`):

```bash
python agent.py --replay recordings/code-freeze.json
```

Answer:

1. Which requests were blocked in each run, and by which rule? Did any file change?
2. In the second run, the replayed model says "That write was blocked" at step 4. Was it?
   Explain what you see. What do these two runs prove, and what do they not prove?
3. Which rules file fits a code-freeze investigation? Why is choosing it part of writing the
   contract?

### A5 · Your contract and its rules (10 min)

The task: **"Add tests (tests only) for what the API does when an event is full and when an
event has a capacity of 1."**

1. Copy `../task-contract-template.md` to `my-contract.md` and fill in all seven lines for
   this task, including both halves of the cost cap and the owner.
2. Copy `permissions.json` to `permissions-a5.json` and tighten it so that every limit in
   your contract that *can* be enforced *is* enforced.
3. Probe your rules. `permissions.py` answers `allowed` or `BLOCKED` for one request:
   ```bash
   python permissions.py permissions-a5.json write_file tests/test_full_events.py
   python permissions.py permissions-a5.json write_file app/main.py
   python permissions.py permissions-a5.json write_file tests/test_basics.py
   ```
   The first should be allowed and the second blocked. Decide what the third should be,
   and say why.
4. Fill in the "Which lines are enforced?" table at the bottom of your contract. Name at
   least one line that this harness cannot enforce, and say what could.

### Optional extensions (if you finish early; not marked)

- **Keep the context small.** Add a `read_lines` tool (path, first line, last line) to
  `tools.py`, register it, and allow it. Copy `add-name-check.json`, replace the whole-file
  reads with line ranges, replay both, and compare the token totals.
- **A hook.** Make `dispatch()` run the tests after every successful `write_file` and add the
  result to the tool's output. Is that a sign or a fence? Who pays for it in tokens?
- **Live mode** (only with a key and budget provided by the course; see `../README.md`). Run
  your A5 contract live with `--record`, then replay your own recording. Compare what the
  model claimed with what the harness collected.

## Part B · Your team's product (25 min)

This week's items on the [product checklist](../../plan/product-checklist.md): **AGENTS.md
states commands, map, rules, and the product's promises**; **three task contracts written for
next week's work**. And the CI gate.

1. **Grow `AGENTS.md`** (10 min). Commands that run (tests, the app, your concurrency check),
   a map of the folders, the rules agents must follow, and your product's promises: at least
   your Week 1 invariant and the key rule from your Week 2 scope agreement. Keep it under a
   page. Everything in it is sent to the model on every call.
2. **Three task contracts** (8 min) in `docs/contracts/`, one file each, for work planned for
   next week. Each has all seven lines, both halves of the cost cap, an owner, and the
   "Which lines are enforced?" table.
3. **Turn on the CI gate** (7 min). On GitHub: **Settings → Branches → Add classic branch
   protection rule** for `main`, and tick three options:
   - **Require a pull request before merging**, with 1 required approval (a teammate reviews);
   - **Require status checks to pass before merging**, and select the `test` check from your
     CI workflow (it appears in the list only after CI has run once);
   - **Do not allow bypassing the above settings**. Without it, the rule does not apply to
     the repository's admins, which probably includes you.

   Then prove it: open a pull request that breaks a test and check that nobody, including
   the repository owner, can merge it. Close it afterwards. Protected branches are available
   for public repositories on GitHub Free, and for private ones only on paid plans. If your
   repository cannot have one, tell your instructor and write the rule into AGENTS.md for
   now; say in your hand-in that it is a sign, not a fence.

## Evidence sheet (10 min, one per pair)

| | Hand in |
|---|---|
| A1 | Your four answers |
| A2 | `pytest` output for `tests/test_write_file.py`; the EVIDENCE lines of the replay; your answer about `resolve()` |
| A3 | The table; `pytest` output for `tests/test_stopping.py`; your two answers |
| A4 | The two lines of `logs/blocked.jsonl` from the read-only run; your three answers |
| A5 | `my-contract.md`, `permissions-a5.json`, and the output of the three probes |
| B | Links to the AGENTS.md change, `docs/contracts/`, a screenshot of the branch rule, and the blocked pull request (or your note about why there is none) |

**One measurement (each of you, on your own; not assessed).** Estimate your own minutes on
Lab 3, including its homework: **producing** (writing code, tests, text or prompts; waiting
for an agent to produce), **checking** (running, reading, reviewing, comparing, measuring) and
**integrating** (merging, resolving conflicts, wiring parts together; 0 if there was none).
Estimates are fine; say so. Hand in one row under your term pseudonym (chosen in Lab 1 and
kept all term; never your name or student number), separately from the pair's packet: at the
end of the lab, or with its homework if it has some. Format: `plan/class-dataset.md`.

- Pseudonym: ______ · Lab 3 · Producing: ____ min · Checking: ____ min · Integrating: ____ min

### How this is marked (studio practice, formative)

| | Strong | Developing |
|---|---|---|
| Safe writes (A2) | All write tests pass; explains why the symlink that points inside must be refused | Tests pass, but cannot say what `resolve()` misses |
| Stopping rule (A3) | Tests pass; the table matches the runs; explains why the total grows faster than each step | Tests pass; numbers or explanation missing |
| Evidence over claims (A1, A4) | Uses the harness's evidence, not the replayed messages; says what replay does and does not prove | Repeats the recording's claims ("10 passed", "that write was blocked") |
| Contract and rules (A5) | Seven lines; rules enforce every enforceable limit; probes shown; names a limit only review or CI can hold | Lines missing, or the rules file allows writes outside the task |
| Team increment (B) | AGENTS.md has commands, map, rules and promises; three complete contracts; the gate is on, cannot be bypassed, and a failing PR was shown to be blocked | Generic AGENTS.md; contracts without cost caps or owners; a gate that admins can bypass |
