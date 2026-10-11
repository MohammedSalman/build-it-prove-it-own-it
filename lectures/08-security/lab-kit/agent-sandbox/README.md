# mini-agent: reference solution (instructor only)

The complete Week 3 mini-agent: the lab kit's `lab-kit/mini-agent/` with the two student
parts filled in (`safe_write_path()` in `tools.py`, the limits in `should_stop()` in
`agent.py`). Everything else is identical to the kit.

**Week 8 copies this folder, frozen, into its own kit.** The interface below is the contract
between the two weeks. Change it only together with Week 8.

## Run it

The agent works on a copy of the AfterHours app, which it expects at `../afterhours`. To use
this solution, copy its files over a student's `lab-kit/mini-agent/`, or pass `--repo`:

```bash
# from lab-kit/mini-agent, after copying the solution files in
python -m pytest -q                                           # 35 passed
python agent.py --replay recordings/add-name-check.json       # stopped: done, 10 passed
python agent.py --replay recordings/code-freeze.json --permissions permissions-readonly.json
python agent.py --replay recordings/runaway.json              # stopped: max_steps after 12
python agent.py --replay recordings/runaway.json --max-steps 30   # stopped: cost_cap after 15
```

PowerShell uses the same commands with `recordings\...` paths.

## Files

| File | What it is |
|---|---|
| `agent.py` | The loop (`run`), the dispatcher (`dispatch`), the stopping rule (`should_stop`), the run log, the CLI |
| `tools.py` | The tool registry and the four tools: `list_files`, `read_file`, `write_file`, `run_tests` |
| `permissions.py` | The permission layer: loads a JSON rules file, answers allow or block for each request |
| `models.py` | `ReplayModel` (plays recorded turns, offline) and `LiveModel` (Anthropic API, optional) |
| `permissions.json` | Rules for a change task: four tools, writes only to `app/*` and `tests/*`, no `.env` reads |
| `permissions-readonly.json` | Rules for an investigation during a code freeze: no `write_file` |
| `recordings/*.json` | Three authored recordings (see "Recordings") |
| `tests/` | 35 tests for the agent itself, including traversal, symlink, schema, and blocked-call tests |

## The interface (frozen for Week 8)

### 1. Tool registry (`tools.py`)

```python
Tool(name: str, description: str, input_schema: dict, run: Callable[..., str])
Tool.check_input(args) -> str | None  # None if args fit input_schema, else what is wrong
register(tool: Tool) -> Tool          # adds it to REGISTRY (a dict, mutated in place)
REGISTRY: dict[str, Tool]
ToolError                             # raise it inside a tool to refuse; the message goes to the model
```

A tool function is called as `run(workspace: Path, **input)` and returns the text that goes
back into the model's context. Registering a tool does **not** allow it. The permission file
decides that, and a tool that is registered but not listed in `allow` is blocked.

### 2. The dispatcher (`agent.py`)

```python
dispatch(call: dict, workspace: Path, permissions: Permissions, log: RunLog,
         step: int = 0, max_chars: int = 8000) -> dict     # a tool_result content block
```

`run()` sends **every** `tool_use` block to `dispatch()`, whether the reply came from
`ReplayModel` or `LiveModel`. Nothing else calls a tool function. The order inside is fixed:

1. `permissions.check(name, input, workspace)`. If blocked: log a `blocked` event, return
   an error result that starts with `BLOCKED by the permission layer:`. The tool function
   never runs.
2. Look up the tool in `REGISTRY` and check the input against its schema
   (`Tool.check_input`: required keys, value types, `additionalProperties: false`). An
   unknown tool or an input that does not fit gives an error result starting
   `bad request for`; the tool never runs.
3. Call the tool. `ToolError` and crashes become error results.
4. Cut the result text to `max_chars` and log a `tool` event.

Tests that pin this: `tests/test_permissions.py::test_every_replayed_request_goes_through_the_dispatcher`
and `::test_the_loop_hands_every_request_to_dispatch`.

### 3. Permission config (JSON file, `--permissions PATH`)

```json
{
  "allow":       ["list_files", "read_file", "write_file", "run_tests"],
  "write_paths": ["app/*", "tests/*"],
  "read_deny":   [".env", "*.env", "*.pem", "*.key", "secrets/*"]
}
```

- `allow`: the only tools that may run. **Default deny**: anything else is blocked,
  including registered tools. The model is also shown only the allowed tools' definitions.
- `write_paths`: `write_file` targets must match one pattern (fnmatch; `*` crosses `/`).
  Paths are normalised first, and a path that leaves the workspace never matches.
- `read_deny`: `read_file` and `list_files` may not target a matching path or file name,
  in any letter case, either as asked or where the path really lands after symlinks
  (the latter only when `check` is given the workspace, as `dispatch` does). Read paths
  must be relative and stay inside the workspace.
- Any other keys (such as `about`) are ignored.

In code: `Permissions.load(path)`, `Permissions(allow=[...], write_paths=[...])`,
`.check(name, args, workspace=None) -> Decision(allowed: bool, reason: str)`.
`python permissions.py RULES.json TOOL PATH` probes one request from the command line
(without the workspace, so symlinks are not followed).

### 4. Blocked-call log

Every blocked request is appended, as it happens, to `<log-dir>/blocked.jsonl`
(default `logs/blocked.jsonl`, next to `agent.py`). One JSON object per line:

```json
{"time": "2026-09-27T22:30:45", "run": "code-freeze-20260927-223045", "event": "blocked",
 "step": 4, "tool": "run_shell", "input": {"command": "rm -f afterhours.db && ..."},
 "reason": "tool 'run_shell' is not on the allowlist in permissions-readonly.json"}
```

Each input value is shortened to 200 characters. The file is append-only across runs; filter
by `run`. The same events, with every model turn and tool result, are in
`<log-dir>/<run-id>.jsonl`. In code, `RunLog.blocked` holds the run's blocked events.

### 5. Adding a tool without editing the agent (`--extra-tools`)

A module that registers tools when imported can be loaded with
`--extra-tools module_name` (comma-separated; the module must be importable from the
mini-agent folder). Example of a stub with a side effect that only records what it would do:

```python
# notify_stub.py
import json
from pathlib import Path
import tools

SENT = Path(__file__).with_name("sent.jsonl")

def notify(workspace, message):
    with open(SENT, "a", encoding="utf-8") as f:
        f.write(json.dumps({"message": message}) + "\n")
    return "sent"

tools.register(tools.Tool(
    "notify", "Send a short message to the team (stub: records it locally).",
    {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
    notify,
))
```

```bash
python agent.py --replay my-recording.json --extra-tools notify_stub                          # blocked, logged, nothing recorded
python agent.py --replay my-recording.json --extra-tools notify_stub --permissions allow.json # allowed: one call recorded
```

`tests/test_permissions.py::test_a_tool_added_with_extra_tools_still_obeys_the_rules` runs
exactly this.

### 6. Recording format (`--replay PATH`)

```json
{
  "about": "who wrote it and what it can and cannot show",
  "task": "the task contract text",
  "suggested_permissions": "permissions.json",
  "turns": [
    {"stop_reason": "tool_use",
     "content": [{"type": "text", "text": "..."},
                 {"type": "tool_use", "id": "toolu_a_01", "name": "list_files", "input": {}}]},
    {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done. ..."}]}
  ]
}
```

The blocks have the shape of Anthropic Messages API content blocks. `tool_use` ids must be
unique in a recording. `ReplayModel` returns the turns in order and **never reads the tool
results**, so a replayed "model" cannot react to what happened. `suggested_permissions` is
documentation only; pass `--permissions` explicitly. A live run saved with `--record` has
the same format plus `recorded_usage` per turn.

### 7. Limits, stop reasons, exit codes

`Limits(max_steps=12, cost_cap_tokens=60_000, max_result_chars=8_000)`. CLI: `--max-steps`,
`--cost-cap`. The cost cap is **soft**: it is checked after each reply, so a run can go over
by up to one call (the runaway recording stops at ~60,188 for a 60,000 cap). Stop reasons: `done`, `cost_cap`, `max_steps` (the stopping rule, checked in
that order after each reply, before its tools run), `refusal` and `max_tokens` (from the
API, always stop). Exit code 0 for `done`, 1 for any other stop, 2 if a recording runs out.
In replay, token counts are **estimates** (characters of JSON ÷ 4).

## Recordings (all authored, none captured)

| Recording | Use with | What it shows |
|---|---|---|
| `add-name-check.json` | `permissions.json` | A change task: failing test first, a one-line fix, 10 passed, 7 steps. On the unfinished kit the writes fail, yet the replayed final message still says "10 passed" |
| `code-freeze.json` | `permissions-readonly.json` | An investigation that tries `write_file` on `app/schema.sql` and then `run_shell`; both blocked and logged; no files change |
| `runaway.json` | `permissions.json` | 30 turns that never finish; stops at `max_steps` (12) or, with `--max-steps 30`, at `cost_cap` (step 15) |

The course team wrote these in the shape of API replies. They are not model output.

## What this is not

- **Not a security boundary.** The permission layer governs only the requests that go
  through this harness. `run_tests` executes code the model wrote, and that code can do
  anything your user account can (network, files outside the workspace). `run_tests` strips
  environment variables that look like secrets, which does nothing about files on disk.
  Real isolation is a container or OS sandbox with no secrets and no network.
- **Path checks are check-then-act.** `safe_write_path()` checks, then `write_file` writes.
  Another process could swap a folder for a symlink in between (Lecture 1's race, on the
  file system). Operating-system sandboxes enforce the boundary where the check and the
  act are one step.
- **Replay is not model behaviour.** Replay shows the loop, dispatcher, permissions and
  stopping rule work on recorded requests. It says nothing about whether a model follows
  instructions or resists injected text.

## Live mode (optional)

`LiveModel` in `models.py` uses the Anthropic Python SDK (`anthropic==1.8.0`), model
`claude-opus-5`, configured September 2026. It calls `client.beta.messages.create` with the
full conversation every step (the Messages API is stateless), top-level
`cache_control={"type": "ephemeral"}` so the re-sent prefix is cached, and server-side
refusal fallbacks (`betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"`).
It needs `ANTHROPIC_API_KEY` (or another credential the SDK finds); the pinned
`anthropic==1.8.0` is in the kit's `requirements.txt`. The request shape is tested offline in
`tests/test_live_adapter.py` with a fake HTTP transport. No live call was made while building
the kit.
