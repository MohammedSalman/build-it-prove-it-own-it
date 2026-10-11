"""Live mode's request, checked offline: a fake HTTP transport stands in for the API.

Needs the anthropic package from requirements.txt (skipped without it). No network, no key.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from app import concierge as cg

KIT = Path(__file__).resolve().parents[1]
FRIDAY_5PM = datetime(2026, 10, 9, 17, 0)

anthropic = pytest.importorskip("anthropic")
httpx2 = pytest.importorskip("httpx2")


def fake_client(seen, model_id, text='{"suggestions": [6], "message": "Stargazing at 21:00."}'):
    def fake_api(request):
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json={
            "id": "msg_test", "type": "message", "role": "assistant", "model": model_id,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1200, "output_tokens": 40, "cache_read_input_tokens": 0,
                      "cache_creation_input_tokens": 0},
        })
    return anthropic.Anthropic(api_key="test-not-a-real-key",
                               http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(fake_api)))


@pytest.fixture
def events():
    return cg.load_catalog(KIT / "catalog.json")


def test_live_mode_asks_for_a_json_answer_and_measures_the_call(events):
    seen = {}
    config = cg.CONFIGS["v2"]
    model = cg.LiveModel(config.model, config.effort, client=fake_client(seen, config.model))
    result = cg.ask("Something quiet on Friday night?", events, FRIDAY_5PM, config, model)
    body = seen["body"]
    assert body["model"] == "claude-opus-5"
    assert body["output_config"] == {"format": {"type": "json_schema", "schema": cg.ANSWER_SCHEMA},
                                     "effort": "low"}
    assert body["fallbacks"] == "default"
    assert cg.FALLBACK_BETA in seen["headers"]["anthropic-beta"]
    assert "temperature" not in body
    assert result.answer.suggestions == (6,)
    assert result.reply.tokens_source == "API usage" and result.reply.input_tokens == 1200
    assert result.reply.latency_source.startswith("measured now")


def test_the_small_model_gets_no_effort_setting_and_no_fallback(events):
    seen = {}
    config = cg.CONFIGS["v2-small"]
    model = cg.LiveModel(config.model, config.effort, client=fake_client(seen, config.model))
    cg.ask("Something quiet on Friday night?", events, FRIDAY_5PM, config, model)
    assert seen["body"]["model"] == "claude-haiku-4-5"
    assert "effort" not in seen["body"]["output_config"] and "fallbacks" not in seen["body"]
    assert "?beta=true" not in seen["url"]


def test_the_live_judge_check_asks_before_sending_anything(monkeypatch, capsys):
    import evals

    def refuse(*args, **kwargs):
        raise AssertionError("no API client before the user says yes")
    monkeypatch.setattr(anthropic, "Anthropic", refuse)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    assert evals.main(["--config", "v2", "--judge-check", "--live"]) == 1
    out = capsys.readouterr().out
    assert "Live mode sends 20 request(s) to claude-sonnet-5" in out
