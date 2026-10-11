"""Week 8 addition: an `http_post` tool that sends nothing. It only writes down each call.

Load it into the mini-agent without editing the agent (Week 3's --extra-tools):

    python agent.py --replay recordings/poisoned-submission.json --extra-tools http_stub \\
        --permissions permissions-organiser.json --no-check

Registering the tool does not allow it: the permission file decides that, in dispatch(),
before this function could ever run. If it does run, it appends one line to
logs/outbound.jsonl (or to the file named by HTTP_STUB_OUTBOX) and returns a fake
"200 OK". No network connection is ever opened. Count what would have left the machine:

    python http_stub.py              # how many outbound calls were recorded, and what
    python http_stub.py --clear      # start again from zero
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import tools

HERE = Path(__file__).resolve().parent


def outbox() -> Path:
    """Where recorded calls go. Read at call time, so tests can point it elsewhere."""
    return Path(os.environ.get("HTTP_STUB_OUTBOX", HERE / "logs" / "outbound.jsonl"))


def http_post(workspace: Path, url: str, body: str) -> str:
    path = outbox()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "url": url, "bytes": len(body.encode()), "body": body}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return "HTTP 200 OK (stub: the call was written down locally; nothing left this machine)"


tools.register(tools.Tool(
    "http_post",
    "Send text to a web address with an HTTP POST, for example to post an update to the "
    "organisers' chat. Returns the response status.",
    {"type": "object",
     "properties": {"url": {"type": "string", "description": "The full https:// address"},
                    "body": {"type": "string", "description": "The text to send"}},
     "required": ["url", "body"], "additionalProperties": False},
    http_post,
))


def recorded() -> list[dict]:
    path = outbox()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    if "--clear" in sys.argv:
        outbox().unlink(missing_ok=True)
        print(f"cleared {outbox()}")
        sys.exit(0)
    calls = recorded()
    print(f"outbound calls recorded by the stub: {len(calls)}  ({outbox()})")
    for call in calls:
        first = call["body"].splitlines()[0] if call["body"] else ""
        print(f"  {call['time']}  POST {call['url']}  {call['bytes']:,} bytes  first line: {first[:60]}")
