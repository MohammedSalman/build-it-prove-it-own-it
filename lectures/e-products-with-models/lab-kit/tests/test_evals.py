"""Tests of the eval itself: before you trust a score, check the thing that computes it.
These need task A2 (graders.py) to be finished. They replay recordings: offline, no key."""

import json
from pathlib import Path

import pytest

import evals

KIT = Path(__file__).resolve().parents[1]


def run(capsys, *args):
    code = evals.main(list(args))
    return code, capsys.readouterr().out


def test_answers_built_from_the_labels_score_exactly_one(capsys, tmp_path):
    # If a label named a full event or one that has started, this would show a hard failure.
    code, out = run(capsys, "--config", "oracle", "--json", str(tmp_path / "o.json"))
    summary = json.loads((tmp_path / "o.json").read_text())["summary"]
    assert summary["mean_score"] == 1.0 and summary["hard_failures"] == []


def test_always_saying_no_good_match_scores_the_share_of_abstention_cases(capsys, tmp_path):
    run(capsys, "--config", "always-abstain", "--json", str(tmp_path / "a.json"))
    summary = json.loads((tmp_path / "a.json").read_text())["summary"]
    assert summary["mean_score"] == pytest.approx(4 / 20)


def test_replay_gives_the_same_report_every_time(capsys):
    _, first = run(capsys, "--config", "v2")
    _, second = run(capsys, "--config", "v2")
    assert first == second


def test_replay_needs_no_api_key_and_no_network(capsys, monkeypatch):
    anthropic = pytest.importorskip("anthropic")

    def refuse(*args, **kwargs):
        raise AssertionError("replay must not create an API client")
    monkeypatch.setattr(anthropic, "Anthropic", refuse)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    code, out = run(capsys, "--config", "v1")
    assert code == 0 and "Score:" in out


def test_the_demo_version_is_right_on_the_demo_and_wrong_in_three_ways(capsys, tmp_path):
    run(capsys, "--config", "v1", "--json", str(tmp_path / "v1.json"))
    data = json.loads((tmp_path / "v1.json").read_text())
    answers = {(a["case"], a["rep"]): a for a in data["answers"]}
    assert all(answers[("c01", r)]["score"] == 1.0 for r in (1, 2, 3))                    # the demo
    full = [f for a in data["answers"] for f in a["failures"] if f.startswith("H4")]
    started = [f for a in data["answers"] for f in a["failures"] if f.startswith("H5")]
    assert full and started                                                              # 1: hard rules
    assert data["summary"]["abstained_rightly"] == 0                                     # 2: never abstains
    assert all("H6 event 13 must not be suggested here" in answers[("c13", r)]["failures"]
               for r in (1, 2, 3))                                                       # 3: injection


def test_the_injection_case_passes_every_run_of_v2_and_fails_one_of_v2_small(capsys):
    assert run(capsys, "--config", "v2", "--gate")[0] == 0
    code, out = run(capsys, "--config", "v2-small", "--gate")
    assert code == 1
    assert "[FAIL] c13 scores 1.00 in every run (1.00, 0.00, 1.00)" in out


def test_the_judge_agrees_92_percent_but_misses_two_of_three_real_failures(capsys):
    _, out = run(capsys, "--config", "v2", "--judge-check")
    assert "37/40" in out and "(92% agreement)" in out
    assert "Answers the humans failed on J1 or J2: 3. The judge failed 1 of them." in out


def test_unlabelled_cases_are_not_run_and_their_answers_are_not_shown(capsys):
    code, out = run(capsys, "--config", "v2", "--cases", "evalset-extra.jsonl")
    assert "NOT RUN: x1, x2, x3, x4 have no labels yet" in out
    assert "Stargazing" not in out


def test_the_gate_fails_when_cases_are_unlabelled_or_missing(capsys, tmp_path):
    rows = [json.loads(line) for line in (KIT / "evalset.jsonl").read_text().splitlines() if line.strip()]
    for row in rows:
        if row["id"] != "c13":
            row["relevant"] = None
    thin = tmp_path / "thin.jsonl"
    thin.write_text("".join(json.dumps(r) + "\n" for r in rows))
    code, out = run(capsys, "--config", "v2", "--cases", str(thin), "--gate")
    assert code == 1
    assert "[FAIL] every case labelled and run (1 of 20)" in out


def test_every_label_is_checked_not_only_the_three_the_oracle_uses(tmp_path):
    rows = [json.loads(line) for line in (KIT / "evalset.jsonl").read_text().splitlines() if line.strip()]
    rows[0]["relevant"] = [1, 2, 3, 4]                     # 4 is full; the oracle would use 1, 2, 3
    bad = tmp_path / "bad.jsonl"
    bad.write_text("".join(json.dumps(r) + "\n" for r in rows))
    from app import concierge as cg
    problems = evals.label_problems(evals.load_cases(bad), cg.load_catalog(KIT / "catalog.json"))
    assert problems == ["c01: label 4 is full"]            # Saturday 14:00: not started on Friday 17:00
    assert evals.label_problems(evals.load_cases(KIT / "evalset.jsonl"), cg.load_catalog(KIT / "catalog.json")) == []
