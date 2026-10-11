"""Where the model's next turn comes from: a recording (default) or the Anthropic API (optional).

Both return the same Reply, so the loop, the dispatcher and the permission layer are the
same code in both modes. That is the point of replay: it tests the harness.

Replay never reads the tool results. It plays the next recorded turn whatever happened,
so a replayed "model" cannot react to a blocked call or a failed write. Replay proves the
harness works. It says nothing about how a real model behaves.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Live mode, configured September 2026 from Anthropic's model list at that date.
# Check https://platform.claude.com/docs/en/about-claude/models/overview before use.
LIVE_MODEL = "claude-opus-5"
LIVE_MAX_TOKENS = 16000          # the most one reply may write (not the run's cost cap)


@dataclass
class Reply:
    content: list[dict]       # content blocks as plain dicts: text, tool_use, thinking...
    stop_reason: str          # "tool_use", "end_turn", "max_tokens", "refusal"
    usage: dict               # {"input_tokens": n, "output_tokens": m, "estimated": bool}

    @property
    def tool_calls(self) -> list[dict]:
        return [block for block in self.content if block.get("type") == "tool_use"]

    @property
    def text(self) -> str:
        return "\n".join(block["text"] for block in self.content if block.get("type") == "text")


class RecordingExhausted(Exception):
    """The loop asked for another turn but the recording has none left."""


def estimate_tokens(*parts) -> int:
    """A rough token count: characters of JSON divided by 4. Real tokenizers differ."""
    return max(1, len(json.dumps(parts, ensure_ascii=False)) // 4)


class ReplayModel:
    """Plays back the assistant turns in a recording, one per call, in order."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.task: str = data["task"]
        self.about: str = data.get("about", "")
        self.turns: list[dict] = data["turns"]
        self.position = 0

    def next(self, system: str, messages: list[dict], tools: list[dict]) -> Reply:
        if self.position >= len(self.turns):
            raise RecordingExhausted(
                f"{self.path.name} has only {len(self.turns)} turns and the loop asked for more. "
                "A stopping rule should have ended the run before this."
            )
        turn = self.turns[self.position]
        self.position += 1
        usage = {
            # What this call would have sent: the whole context, every time.
            "input_tokens": estimate_tokens(system, tools, messages),
            "output_tokens": estimate_tokens(turn["content"]),
            "estimated": True,
        }
        return Reply(content=turn["content"], stop_reason=turn["stop_reason"], usage=usage)


class LiveModel:
    """Asks Claude through the Anthropic API (the `anthropic` package from requirements.txt).
    Needs an API key (ANTHROPIC_API_KEY) and costs money; see README.md."""

    def __init__(self, model: str = LIVE_MODEL, client=None):
        if client is None:
            import anthropic                     # only needed in live mode
            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.turns: list[dict] = []              # kept so a live run can be saved as a recording

    def next(self, system: str, messages: list[dict], tools: list[dict]) -> Reply:
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=LIVE_MAX_TOKENS,
            system=system,
            tools=tools,
            messages=messages,
            cache_control={"type": "ephemeral"},        # the prefix is re-sent every step; cache it
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",                        # if the model declines, the API retries on a fallback
        )
        data = response.to_dict()
        content = [{k: v for k, v in block.items() if v is not None} for block in data["content"]]
        usage = data["usage"]
        input_tokens = (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0) \
            + (usage.get("cache_creation_input_tokens") or 0)
        reply = Reply(
            content=content,
            stop_reason=data["stop_reason"],
            usage={"input_tokens": input_tokens, "output_tokens": usage.get("output_tokens") or 0,
                   "estimated": False},
        )
        self.turns.append({"stop_reason": reply.stop_reason, "content": content,
                           "recorded_usage": reply.usage, "model": data.get("model")})
        return reply

    def save_recording(self, path: str | Path, task: str) -> None:
        record = {
            "about": f"Recorded from a live run of {self.model}. Replaying it tests the harness; "
                     "the replayed turns will not react to different tool results.",
            "task": task,
            "turns": self.turns,
        }
        Path(path).write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
