"""Live mode's request, checked offline: a fake HTTP transport stands in for the API.

Needs the anthropic package from requirements.txt (skipped without it). No network, no key.
"""

import json

import pytest

anthropic = pytest.importorskip("anthropic")
httpx2 = pytest.importorskip("httpx2")

from models import LIVE_MODEL, LiveModel  # noqa: E402


def test_live_mode_sends_the_whole_conversation_and_reads_the_reply(tmp_path):
    seen = {}

    def fake_api(request):
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json={
            "id": "msg_test", "type": "message", "role": "assistant", "model": LIVE_MODEL,
            "content": [{"type": "text", "text": "Reading it."},
                        {"type": "tool_use", "id": "toolu_1", "name": "read_file", "input": {"path": "app/main.py"}}],
            "stop_reason": "tool_use", "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 900,
                      "cache_creation_input_tokens": 0},
        })

    client = anthropic.Anthropic(
        api_key="test-not-a-real-key",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(fake_api)),
    )
    model = LiveModel(client=client)
    messages = [{"role": "user", "content": "task"}, {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
                {"role": "user", "content": "more"}]
    tool_defs = [{"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {}}}]
    reply = model.next("system prompt", messages, tool_defs)

    body = seen["body"]
    assert body["model"] == LIVE_MODEL
    assert body["messages"] == messages            # the whole conversation, every time
    assert body["tools"] == tool_defs
    assert body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in seen["headers"]["anthropic-beta"]
    assert reply.stop_reason == "tool_use"
    assert reply.tool_calls[0]["input"] == {"path": "app/main.py"}
    assert reply.usage == {"input_tokens": 1000, "output_tokens": 20, "estimated": False}

    model.save_recording(tmp_path / "rec.json", "task")
    saved = json.loads((tmp_path / "rec.json").read_text())
    assert saved["turns"][0]["content"] == reply.content
