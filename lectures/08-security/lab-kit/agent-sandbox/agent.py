"""mini-agent: a model in a loop, with tools, context and permissions.

    python agent.py --replay recordings/add-name-check.json      offline, no key needed
    python agent.py --live --task-file my-contract.md            optional, needs an API key

Each step: send the whole conversation and the tool definitions to the model; if it asks
for tools, run each request through dispatch() (the permission layer decides first), add
the results to the conversation, and go round again. Stop when the stopping rule says so.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import tools as toolbox
from models import LiveModel, RecordingExhausted, ReplayModel, Reply, LIVE_MODEL
from permissions import Permissions
from tools import REGISTRY, ToolError

HERE = Path(__file__).resolve().parent

SYSTEM_PROMPT = """You are a coding agent working in a throwaway copy of a software project.
Look before you change anything, keep changes small, and run the tests.
When you have finished, stop calling tools and reply with a short summary of what you
changed and the evidence (the test output)."""


@dataclass
class Limits:
    max_steps: int = 12            # model calls in one run
    cost_cap_tokens: int = 60_000  # input + output tokens over the whole run (a soft cap, see should_stop)
    max_result_chars: int = 8_000  # a longer tool result is cut before it enters the context


@dataclass
class Outcome:
    reason: str                    # why the loop stopped: done, max_steps, cost_cap, refusal...
    steps: int
    tokens: int
    messages: list = field(default_factory=list)


class RunLog:
    """Everything that happened, in order. Blocked calls also go to blocked.jsonl."""

    def __init__(self, log_dir: Path, run_id: str, echo=None):
        self.log_dir, self.run_id, self.echo = Path(log_dir), run_id, echo
        self.events: list[dict] = []
        self.blocked: list[dict] = []

    def add(self, kind: str, **data) -> None:
        event = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "run": self.run_id, "event": kind, **data}
        self.events.append(event)
        if kind == "blocked":
            self.blocked.append(event)
            self._append("blocked.jsonl", event)
        if self.echo:
            self.echo(describe(event))

    def save(self) -> Path:
        path = self.log_dir / f"{self.run_id}.jsonl"
        for event in self.events:
            self._append(path.name, event)
        return path

    def _append(self, name: str, event: dict) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with open(self.log_dir / name, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def short(value, limit: int = 70) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = text.replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + f"...({len(text)} chars)"


def describe(e: dict) -> str:
    kind = e["event"]
    if kind == "model":
        lines = [f"\n-- step {e['step']} · model call · context ~{e['input_tokens']:,} tokens in --"]
        if e["text"]:
            lines.append(f"   says: {short(e['text'], 110)}")
        lines += [f"   asks: {c['name']} {short(c['input'])}" for c in e["calls"]]
        return "\n".join(lines)
    if kind == "tool":
        lines = e["result"].strip().splitlines() or [""]
        gist = lines[0] if len(lines) == 1 else f"{short(lines[0], 45)} ... {short(lines[-1], 45)}"
        return f"     -> {'ERROR ' if e['is_error'] else 'ok '}{short(gist, 100)}  [{len(e['result']):,} chars]"
    if kind == "blocked":
        return f"     -> BLOCKED {e['tool']}: {e['reason']}"
    if kind == "stop":
        return f"\n== stopped: {e['reason']} after {e['steps']} steps, ~{e.get('tokens', 0):,} tokens =="
    return str(e)


def tool_result(call: dict, text: str, is_error: bool = False) -> dict:
    return {"type": "tool_result", "tool_use_id": call["id"], "content": text, "is_error": is_error}


def dispatch(call: dict, workspace: Path, permissions: Permissions, log: RunLog,
             step: int = 0, max_chars: int = Limits.max_result_chars) -> dict:
    """The only way a tool ever runs. Live or replayed, every request comes through here:
    permission check, then a check of the input against the tool's schema, then the tool
    (which enforces its own bounds), then a size limit on what goes back into the context."""
    name, args = call.get("name", ""), call.get("input", {})
    decision = permissions.check(name, args if isinstance(args, dict) else {}, workspace)
    if not decision.allowed:
        log.add("blocked", step=step, tool=name, input=_abridged(args), reason=decision.reason)
        return tool_result(call, f"BLOCKED by the permission layer: {decision.reason}", True)
    tool = REGISTRY.get(name)
    problem = "no such tool" if tool is None else tool.check_input(args)
    if problem:
        text, is_error = f"bad request for {name}: {problem}", True
    else:
        try:
            text, is_error = tool.run(workspace, **args), False
        except ToolError as e:
            text, is_error = str(e), True
        except Exception as e:                     # the tool crashed; tell the model, keep going
            text, is_error = f"{name} failed: {type(e).__name__}: {e}", True
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n[... cut: {len(text) - max_chars} more characters not shown]"
    log.add("tool", step=step, tool=name, is_error=is_error, result=text)
    return tool_result(call, text, is_error)


def _abridged(args) -> dict:
    if not isinstance(args, dict):
        return {"raw": short(args, 200)}
    return {k: short(v, 200) for k, v in args.items()}


def should_stop(reply: Reply, steps: int, tokens_used: int, limits: Limits) -> str | None:
    """Why the loop must stop now, or None to go round again. Checked after every reply,
    before any of its tool requests run.

      "done"       the model asked for no tools: it says it has finished
      "cost_cap"   tokens_used has reached limits.cost_cap_tokens
      "max_steps"  steps has reached limits.max_steps
    Check them in that order, so a model that finishes on its last allowed step is "done".

    The cost cap is a soft cap: it is checked after a reply has been paid for, so a run can
    go over by up to one call. It stops every later call and every later tool run.
    """
    if not reply.tool_calls:
        return "done"
    if tokens_used >= limits.cost_cap_tokens:
        return "cost_cap"
    if steps >= limits.max_steps:
        return "max_steps"
    return None


def build_system_prompt(workspace: Path) -> str:
    """The instructions the model sees. The project's AGENTS.md is pasted in, as text."""
    notes = workspace / "AGENTS.md"
    if notes.is_file():
        return SYSTEM_PROMPT + "\n\nProject notes from AGENTS.md:\n\n" + notes.read_text(encoding="utf-8")[:6000]
    return SYSTEM_PROMPT


def run(task: str, model, workspace: Path, permissions: Permissions, limits: Limits, log: RunLog) -> Outcome:
    system = build_system_prompt(workspace)
    tool_defs = [REGISTRY[name].schema() for name in permissions.allow if name in REGISTRY]
    messages = [{"role": "user", "content": task}]
    steps = tokens = 0
    while True:
        try:
            reply = model.next(system, messages, tool_defs)              # 1. ask the model
        except RecordingExhausted:
            log.add("stop", reason="recording_exhausted", steps=steps, tokens=tokens)
            raise
        steps += 1
        tokens += reply.usage["input_tokens"] + reply.usage["output_tokens"]
        messages.append({"role": "assistant", "content": reply.content})  # 2. keep what it said
        log.add("model", step=steps, text=reply.text, input_tokens=reply.usage["input_tokens"],
                output_tokens=reply.usage["output_tokens"], stop_reason=reply.stop_reason,
                calls=[{"name": c["name"], "input": _abridged(c.get("input"))} for c in reply.tool_calls])
        if reply.stop_reason in ("refusal", "max_tokens"):               # the harness always stops here
            reason = reply.stop_reason
        else:
            reason = should_stop(reply, steps, tokens, limits)          # 3. stop?
        if reason:
            log.add("stop", reason=reason, steps=steps, tokens=tokens)
            return Outcome(reason, steps, tokens, messages)
        results = [dispatch(call, workspace, permissions, log, steps, limits.max_result_chars)
                   for call in reply.tool_calls]                         # 4. run each request
        messages.append({"role": "user", "content": results})           # 5. results go back in


# ---------------------------------------------------------------------------------------
# Workspace and evidence.

def make_workspace(repo: Path, workspace: str | None = None) -> Path:
    """A throwaway copy of the project. The agent works here, never in your real folder."""
    if workspace:
        return Path(workspace).resolve()
    if not repo.is_dir():
        sys.exit(f"No project to copy at {repo}. Pass --repo PATH (the folder with the app).")
    target =Path(tempfile.mkdtemp(prefix="mini-agent-")) / repo.name
    shutil.copytree(repo, target, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", ".pytest_cache", "*.db", "*.db-*"))
    return target.resolve()


def snapshot(workspace: Path) -> dict[str, str]:
    files = {}
    for dirpath, dirnames, filenames in os.walk(workspace):
        dirnames[:] = [d for d in dirnames if d not in toolbox.SKIP_DIRS]
        for name in filenames:
            if ".db" not in name:
                path = Path(dirpath) / name
                files[path.relative_to(workspace).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def changes(before: dict, after: dict) -> list[str]:
    out = [f"{p} (new)" for p in sorted(after.keys() - before.keys())]
    out += [f"{p} (changed)" for p in sorted(before.keys() & after.keys()) if before[p] != after[p]]
    out += [f"{p} (deleted)" for p in sorted(before.keys() - after.keys())]
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="mini-agent: a model in a loop with tools and permissions")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--replay", metavar="RECORDING", help="play back a recording (offline)")
    mode.add_argument("--live", action="store_true", help=f"ask {LIVE_MODEL} through the API (costs money)")
    p.add_argument("--task", help="the task contract as text (live mode; replay uses the recording's task)")
    p.add_argument("--task-file", help="read the task contract from a file")
    p.add_argument("--permissions", default=str(HERE / "permissions.json"))
    p.add_argument("--repo", default=str(HERE.parent / "afterhours"), help="project to copy into the workspace")
    p.add_argument("--workspace", help="use this folder instead of a fresh throwaway copy")
    p.add_argument("--max-steps", type=int, default=Limits.max_steps)
    p.add_argument("--cost-cap", type=int, default=Limits.cost_cap_tokens, help="token budget for the whole run")
    p.add_argument("--log-dir", default=str(HERE / "logs"))
    p.add_argument("--extra-tools", default="", help="comma-separated modules that register more tools")
    p.add_argument("--record", metavar="PATH", help="live mode: save the run as a recording")
    p.add_argument("--no-check", action="store_true", help="skip the harness's own test run at the end")
    p.add_argument("--yes", action="store_true", help="live mode: skip the confirmation question")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")      # never crash on a console that lacks a character

    for module in filter(None, a.extra_tools.split(",")):
        importlib.import_module(module.strip())
    permissions = Permissions.load(a.permissions)
    limits = Limits(max_steps=a.max_steps, cost_cap_tokens=a.cost_cap)

    if a.replay:
        model = ReplayModel(a.replay)
        task = Path(a.task_file).read_text(encoding="utf-8") if a.task_file else (a.task or model.task)
        run_id, label = Path(a.replay).stem + time.strftime("-%Y%m%d-%H%M%S"), f"replay of {a.replay}"
    else:
        task = Path(a.task_file).read_text(encoding="utf-8") if a.task_file else a.task
        if not task:
            p.error("live mode needs --task or --task-file")
        print("Live mode sends the task and every file the agent reads to Anthropic's API, and\n"
              "run_tests executes code the model wrote on this computer. Use a throwaway machine\n"
              "or container, keep secrets out of the project, and set a spending limit.")
        if not a.yes and input("Continue? [y/N] ").strip().lower() != "y":
            return 1
        try:
            model = LiveModel()
        except ImportError:
            print("Live mode needs the Anthropic SDK: pip install -r ../requirements.txt")
            return 2
        run_id, label = "live-" + time.strftime("%Y%m%d-%H%M%S"), f"live run of {LIVE_MODEL}"

    workspace = make_workspace(Path(a.repo), a.workspace)
    log = RunLog(Path(a.log_dir), run_id, echo=print)
    print(f"mini-agent · {label}\nworkspace: {workspace}\npermissions: {permissions.source} "
          f"(allow: {', '.join(permissions.allow)})\nlimits: {limits.max_steps} steps, "
          f"{limits.cost_cap_tokens:,} tokens\n\nTASK\n{task.strip()}")
    before = snapshot(workspace)
    try:
        outcome = run(task, model, workspace, permissions, limits, log)
    except RecordingExhausted as e:
        print(f"\nERROR: {e}")
        outcome = None
    except Exception as e:                       # live mode: the API call itself failed
        if isinstance(model, ReplayModel):
            raise
        print(f"\nERROR: the live model call failed: {type(e).__name__}: {e}")
        outcome = None
    finally:
        log_path = log.save()
    if a.record and isinstance(model, LiveModel):
        model.save_recording(a.record, task)

    print("\nEVIDENCE (collected by the harness, not claimed by the model)")
    if not a.no_check:
        check = toolbox.run_tests(workspace).splitlines()
        print(f"  tests in the workspace: {check[-1] if check else '?'}")
    changed = changes(before, snapshot(workspace))
    print(f"  files changed: {', '.join(changed) if changed else 'none'}")
    print(f"  blocked calls: {len(log.blocked)} (see {Path(a.log_dir) / 'blocked.jsonl'})")
    print(f"  full log: {log_path}")
    if isinstance(model, ReplayModel):
        print("  token counts are estimates (characters / 4); replay shows the harness works, "
              "not how a model behaves")
    if outcome is None:
        return 2
    return 0 if outcome.reason == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
