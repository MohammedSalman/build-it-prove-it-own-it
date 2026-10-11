"""Run the AfterHours concierge over an eval set and grade every answer.

    python evals.py --config v1                  replay v1's recorded answers (offline, no key)
    python evals.py --config v2 --cases evalset-extra.jsonl
    python evals.py --compare v1 v2              case by case, with an interval for the difference
    python evals.py --config v2 --judge-check    the model judge against grades written by people
    python evals.py --config v2 --gate           exit 1 unless budget.json is met (for CI)
    python evals.py --config oracle              answers built from the labels: must score 1.00
    python evals.py --config always-abstain      "no good match" every time: a floor to beat

Optional live mode (needs an API key, costs money, see README.md):
    python evals.py --config v2 --live --runs 1 --record recordings/my-v2.json
    python evals.py --config v2 --recording recordings/my-v2.json      replay your own run

The rules the graders apply are in GRADING.md. Replay checks the eval harness and the code
around the model. It does not show how any real model behaves.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

import graders
from app import concierge as cg
from judge import JUDGE_MODEL, JUDGE_SCHEMA, build_judge_prompt, live_judge, parse_verdict

HERE = Path(__file__).resolve().parent
SYNTHETIC = {
    "oracle": "answers built from the labels (the first 3 relevant events, or nothing)",
    "always-abstain": "always says 'no good match'",
}


# ---------------------------------------------------------------- inputs

def load_cases(path: Path) -> list[graders.Case]:
    cases = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                cases.append(graders.case_from_json(json.loads(line)))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                sys.exit(f"{path.name} line {number}: {e}")
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        sys.exit(f"{path.name}: two cases have the same id")
    return cases


def label_problems(cases, events) -> list[str]:
    """Check every label before anything runs: a relevant event must exist, have places, not
    have started at the case's time, and not be in the case's must_not_suggest list.
    (The oracle only uses the first three labels, so it cannot catch all of these.)"""
    catalog = {e.id: e for e in events}
    problems = []
    for case in cases:
        for event_id in sorted(case.relevant or []):
            e = catalog.get(event_id)
            if e is None:
                problems.append(f"{case.id}: label {event_id} is not in catalog.json")
                continue
            if e.places_left <= 0:
                problems.append(f"{case.id}: label {event_id} is full")
            if e.starts_at <= case.now:
                problems.append(f"{case.id}: label {event_id} has started at the case's time")
            if event_id in case.must_not_suggest:
                problems.append(f"{case.id}: label {event_id} is also in must_not_suggest")
    return problems


def load_prices() -> dict:
    return json.loads((HERE / "prices.json").read_text(encoding="utf-8"))


class SyntheticModel:
    """Not a model: builds the answer from the labels, to test the eval itself."""

    def __init__(self, kind: str):
        self.kind, self.case = kind, None
        self.provenance = "synthetic"

    def reply(self, prompt, rep=1, schema=None) -> cg.ModelReply:
        ids = [] if self.kind == "always-abstain" else sorted(self.case.relevant or [])[: graders.K]
        text = json.dumps({"suggestions": ids, "message": "(synthetic answer)"})
        return cg.ModelReply(text, "end_turn", 0, 0, "synthetic", 0, "synthetic", None, "synthetic")


def confirm_live(model_id: str, calls: int, yes: bool) -> bool:
    print(f"Live mode sends {calls} request(s) to {model_id} through the Anthropic API, including the "
          "whole festival programme each time. It costs money and needs ANTHROPIC_API_KEY.")
    return yes or input("Continue? [y/N] ").strip().lower() == "y"


def config_for(name: str) -> cg.Config:
    if name in SYNTHETIC:
        # The labels decide the answer; no guard, so a label that names a full or started
        # event shows up as a hard-rule failure (that is a bug in the labels).
        return cg.Config(name, "v2", "none", None, prefilter=True, guard=False, about=SYNTHETIC[name])
    if name not in cg.CONFIGS:
        sys.exit(f"unknown config {name!r}; choose from {', '.join([*cg.CONFIGS, *SYNTHETIC])}")
    return cg.CONFIGS[name]


def recording_path(config: cg.Config, override: str | None) -> Path:
    return Path(override) if override else HERE / "recordings" / f"{config.name}.json"


# ---------------------------------------------------------------- one run over the eval set

def run_eval(config: cg.Config, cases, events, model, runs: int | None) -> list[tuple]:
    """Returns (case, rep, Result or None, Grade or None) for every answer."""
    catalog = {e.id: e for e in events}
    rows = []
    for case in cases:
        if case.relevant is None:
            rows.append((case, 0, None, None))          # unlabelled: do not even look
            continue
        if isinstance(model, SyntheticModel):
            model.case = case
        prompt = cg.prompt_for(case.question, events, case.now, config)
        if isinstance(model, cg.ReplayModel):
            reps = model.runs_for(prompt)
            if not reps:
                sys.exit(f"{case.id}: {model.path.name} has no recording for this exact prompt. Did the "
                         "prompt, the programme (catalog.json) or the question change? Replay cannot "
                         "answer a new prompt; that needs a live run.")
            reps = reps[:runs] if runs else reps
        else:
            reps = list(range(1, (runs or 1) + 1))
        for rep in reps:
            try:
                result = cg.ask(case.question, events, case.now, config, model, rep=rep)
            except cg.NoRecording as e:
                sys.exit(f"{case.id}: {e}")
            try:
                grade = graders.grade(result, case, catalog, rep)
            except NotImplementedError as e:     # task A2 not done yet: list the answers instead
                NOT_DONE.append(str(e))
                grade = None
            rows.append((case, rep, result, grade))
    return rows


NOT_DONE: list[str] = []


def print_listing(config, model, rows, events) -> None:
    """Before graders.py is finished: show every answer so you can grade some by hand."""
    titles = {e.id: e.title for e in events}
    print(f"AfterHours concierge answers · config {config.name} · {source_line(model, config)}")
    print(f"\ngraders.py is not finished ({NOT_DONE[0]}), so nothing is graded yet.")
    print("Here are the answers. Grade a few by hand with GRADING.md (labels and notes: evalset.jsonl),")
    print("then finish task A2.\n")
    for case, rep, result, _ in rows:
        if result is None:
            continue
        if result.answer is None:
            shown = f"format error: {result.format_error}"
        elif result.answer.abstains:
            shown = "no good match"
        else:
            shown = ", ".join(f"{i} {titles.get(i, '?')}" for i in result.answer.suggestions)
        print(f"  {case.id} run {rep}  {case.question}   (asked {cg.spoken_time(case.now)})\n           -> {shown}")


# ---------------------------------------------------------------- numbers

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def percentile(xs, p):
    """Nearest-rank percentile (Week 11): the smallest value with at least p% at or below it."""
    xs = sorted(xs)
    if not xs:
        return None
    rank = max(1, -(-p * len(xs) // 100))          # ceiling of p% of n
    return xs[int(rank) - 1]


def bootstrap(values_per_case: list[float], resamples: int = 2000, seed: int = 1):
    """95% interval for a mean over cases, by resampling cases with replacement.
    Cases are the unit: the runs of one case are not independent of each other."""
    if len(values_per_case) < 2:
        return None
    rng = random.Random(seed)
    n = len(values_per_case)
    means = sorted(sum(rng.choice(values_per_case) for _ in range(n)) / n for _ in range(resamples))
    return means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1]


def summarise(config: cg.Config, rows, prices: dict) -> dict:
    graded = [(c, r, res, g) for c, r, res, g in rows if g is not None]
    scored = [g for *_, g in graded if g.score is not None]
    per_case = {}
    for c, r, res, g in graded:
        if g.score is not None:
            per_case.setdefault(c.id, []).append(g.score)
    case_means = [mean(v) for v in per_case.values()]
    reps = sorted({g.rep for g in scored})
    price = prices["usd_per_million_tokens"].get(config.model)
    answers = [res for *_, res, g in graded]
    costs = []
    for res in answers:
        if price and res.reply.provenance != "synthetic":
            costs.append(res.reply.input_tokens * price["input"] / 1e6 + res.reply.output_tokens * price["output"] / 1e6)
    latencies = [res.reply.latency_ms for res in answers if res.reply.provenance != "synthetic"]
    return {
        "config": config.name,
        "answers": len(graded),
        "cases": len(per_case),
        "unlabelled": sorted({c.id for c, r, res, g in rows if g is None}),
        "mean_score": mean(g.score for g in scored),
        "interval": bootstrap(case_means),
        "per_run": {rep: mean(g.score for g in scored if g.rep == rep) for rep in reps},
        "hard_failures": [(g.case, g.rep, "; ".join(g.failures)) for g in scored if g.failures],
        "format_errors": [(g.case, g.rep, g.format_error) for *_, g in graded if g.format_error],
        "should_abstain": sum(1 for g in scored if g.should_abstain),
        "abstained_rightly": sum(1 for g in scored if g.should_abstain and g.abstained),
        "should_answer": sum(1 for g in scored if not g.should_abstain),
        "abstained_wrongly": [(g.case, g.rep) for g in scored if not g.should_abstain and g.abstained],
        "time_errors": [(g.case, g.rep, t) for *_, g in graded for t in g.time_errors],
        "mean_recall": mean(g.recall for g in scored if g.recall is not None),
        "distribution": {s: sum(1 for g in scored if round(g.score, 2) == s)
                         for s in sorted({round(g.score, 2) for g in scored})},
        "input_tokens": mean(res.reply.input_tokens for res in answers),
        "output_tokens": mean(res.reply.output_tokens for res in answers),
        "tokens_source": answers[0].reply.tokens_source if answers else "",
        "cost_per_answer": mean(costs),
        "price": price,
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "latency_source": answers[0].reply.latency_source if answers else "",
        "served_mismatch": sorted({res.reply.served_model for res in answers
                                   if res.reply.served_model and not res.reply.served_model.startswith(config.model)}),
        "per_case": per_case,
    }


# ---------------------------------------------------------------- printing

def fmt(x, digits=2):
    return "-" if x is None else f"{x:.{digits}f}"


def source_line(model, config) -> str:
    if isinstance(model, SyntheticModel):
        return f"synthetic answers: {config.about}"
    if isinstance(model, cg.ReplayModel):
        who = {"authored": "AUTHORED by the course team, not a real model's output",
               "live recording": "recorded from a live run"}.get(model.provenance, model.provenance)
        return f"replay of {model.path.relative_to(HERE) if model.path.is_relative_to(HERE) else model.path} ({who})"
    return f"LIVE: {config.model} through the Anthropic API"


def print_report(config, model, rows, s, cases_path: Path) -> None:
    print(f"AfterHours concierge eval · config {config.name}: {config.about}")
    print(f"  {source_line(model, config)}")
    runs = max((r for _, r, _, g in rows if g), default=0)
    print(f"  {s['cases']} cases from {cases_path.name} × {runs} run(s) = {s['answers']} answers · k = {graders.K}"
          " · rules: GRADING.md")
    if s["unlabelled"]:
        print(f"\n  NOT RUN: {', '.join(s['unlabelled'])} have no labels yet. Write the relevant ids (or [])"
              f" in {cases_path.name} first. The report does not show answers to unlabelled cases.")
    if s.get("label_problems"):
        print(f"\n  LABEL CHECK: {len(s['label_problems'])} problem(s). Every score below that uses these labels is suspect:")
        for problem in s["label_problems"]:
            print(f"    {problem}")
    if not s["answers"]:
        return
    print("\nPer case (score of each run; notes)")
    for case in sorted({c.id: c for c, *_ in rows if c.relevant is not None}.values(), key=lambda c: c.id):
        grades = [g for c, r, res, g in rows if c.id == case.id and g]
        scores = "  ".join(fmt(g.score) if g.score is not None else ("fmt" if g.format_error else "  - ")
                           for g in grades)
        notes = []
        for g in grades:
            label = f"run {g.rep}: " if len(grades) > 1 else ""
            if g.format_error:
                notes.append(f"{label}format error ({g.format_error})")
            if g.failures:
                notes.append(f"{label}HARD " + "; ".join(g.failures))
            elif g.should_abstain and not g.abstained:
                notes.append(f"{label}should say no good match")
            elif not g.should_abstain and g.abstained:
                notes.append(f"{label}said no good match")
            if g.time_errors:
                notes.append(f"{label}time {', '.join(g.time_errors)} not in the programme")
        question = case.question if len(case.question) <= 46 else case.question[:45] + "…"
        print(f"  {case.id}  {question:<47} {scores}   {' | '.join(notes)}")

    print(f"\nScore: precision@{graders.K} with the abstention rule, mean over {s['answers']} answers: "
          f"{fmt(s['mean_score'])}")
    if s["interval"]:
        lo, hi = s["interval"]
        print(f"  95% interval, resampling the {s['cases']} cases: {fmt(lo)} to {fmt(hi)}")
    if len(s["per_run"]) > 1:
        print("  by run: " + " · ".join(f"run {r} {fmt(v)}" for r, v in s["per_run"].items()))
    print("  answers by score: " + " · ".join(f"{k:.2f}: {v}" for k, v in s["distribution"].items()))
    print(f"  recall@{graders.K} (reported, not in the score): {fmt(s['mean_recall'])}")
    print(f"Hard-rule failures: {len(s['hard_failures'])} of {s['answers']} answers")
    print(f"Abstention: should say no good match {s['should_abstain']} times, did {s['abstained_rightly']};"
          f" should answer {s['should_answer']} times, said no good match {len(s['abstained_wrongly'])}")
    print(f"Format errors (not scored): {len(s['format_errors'])}")
    print(f"Label check: {len(s.get('label_problems', []))} problem(s)")
    print(f"Time check on the messages (T1): {len(s['time_errors'])} wrong time(s)")

    if s["price"] and s["cost_per_answer"] is not None:
        per_1000 = s["cost_per_answer"] * 1000
        print(f"\nCost and latency")
        print(f"  tokens per answer: {s['input_tokens']:,.0f} in, {s['output_tokens']:,.0f} out ({s['tokens_source']})")
        print(f"  cost: ${s['cost_per_answer']:.4f} per answer, ${per_1000:.2f} per 1,000 questions, at {config.model}"
              f" list prices (${s['price']['input']:g} in / ${s['price']['output']:g} out per million tokens)")
        print(f"  latency: p50 {s['p50_ms'] / 1000:.2f} s, p95 {s['p95_ms'] / 1000:.2f} s: {s['latency_source']}")
    if s["served_mismatch"]:
        print(f"\nWARNING: some answers were served by {', '.join(s['served_mismatch'])}, not {config.model}"
              " (a fallback). Those rows measure a different model.")
    if isinstance(model, cg.ReplayModel) and model.provenance == "authored":
        print("\nReplay proves the harness and graders work on these recordings. The recordings were authored:")
        print("they are not evidence about any real model. Only live runs, repeated, measure a model.")


def compare(a_name, b_name, cases, events, prices, runs) -> None:
    results = {}
    for name in (a_name, b_name):
        config = config_for(name)
        model = SyntheticModel(name) if name in SYNTHETIC else cg.ReplayModel(recording_path(config, None))
        rows = run_eval(config, cases, events, model, runs)
        results[name] = (config, model, summarise(config, rows, prices))
    if NOT_DONE:
        sys.exit(f"graders.py is not finished ({NOT_DONE[0]}). Finish task A2 before comparing configs.")
    (_, _, a), (_, _, b) = results[a_name], results[b_name]
    both = [cid for cid in a["per_case"] if cid in b["per_case"]]
    diffs = {cid: mean(b["per_case"][cid]) - mean(a["per_case"][cid]) for cid in both}
    print(f"Compare {a_name} → {b_name} on {len(both)} cases (replay; per-case means over runs)")
    for name, (config, model, s) in results.items():
        print(f"  {name:<14} {source_line(model, config)}")
    print(f"\n  {'':<28}{a_name:>12}{b_name:>12}")
    rows = [("mean score", fmt(a["mean_score"]), fmt(b["mean_score"])),
            ("hard-rule failures", len(a["hard_failures"]), len(b["hard_failures"])),
            ("said no good match wrongly", len(a["abstained_wrongly"]), len(b["abstained_wrongly"])),
            ("abstained rightly", f"{a['abstained_rightly']}/{a['should_abstain']}",
             f"{b['abstained_rightly']}/{b['should_abstain']}"),
            ("wrong times (T1)", len(a["time_errors"]), len(b["time_errors"]))]
    for s in (a, b):
        s["_cost"] = "-" if s["cost_per_answer"] is None else f"${s['cost_per_answer'] * 1000:.2f}"
        s["_p95"] = "-" if s["p95_ms"] is None else f"{s['p95_ms'] / 1000:.2f} s"
    rows += [("cost per 1,000 questions", a["_cost"], b["_cost"]), ("p95 latency (recorded)", a["_p95"], b["_p95"])]
    for label, x, y in rows:
        print(f"  {label:<28}{x!s:>12}{y!s:>12}")
    d = mean(diffs.values())
    interval = bootstrap(list(diffs.values()))
    print(f"\n  difference in mean score ({b_name} minus {a_name}): {d:+.2f}", end="")
    if interval:
        print(f", 95% interval {interval[0]:+.2f} to {interval[1]:+.2f} (resampling cases)")
        if interval[0] <= 0 <= interval[1]:
            print("  The interval includes 0: on these cases the difference could be noise.")
    worse = sorted((cid for cid in both if diffs[cid] < 0), key=lambda cid: diffs[cid])
    better = sorted((cid for cid in both if diffs[cid] > 0), key=lambda cid: -diffs[cid])
    print(f"  worse in {b_name}: " + (", ".join(f"{cid} ({diffs[cid]:+.2f})" for cid in worse) or "none"))
    print(f"  better in {b_name}: " + (", ".join(f"{cid} ({diffs[cid]:+.2f})" for cid in better) or "none"))
    hard_b = sorted({(cid, rep) for cid, rep, _ in b["hard_failures"]})
    if hard_b:
        print(f"  hard-rule failures in {b_name}: " + ", ".join(f"{cid} run {rep}" for cid, rep in hard_b))


def judge_check(config, cases, events, human_path: Path, judge_path: Path, live: bool) -> None:
    catalog = {e.id: e for e in events}
    humans = [json.loads(l) for l in human_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    answers_model = cg.ReplayModel(recording_path(config, None))
    judge = live_judge() if live else cg.ReplayModel(judge_path)
    by_id = {c.id: c for c in cases}
    agree = {"J1": 0, "J2": 0}
    missed = {"J1": 0, "J2": 0}          # human fail, judge pass
    false_alarm = {"J1": 0, "J2": 0}     # human pass, judge fail
    human_fails = caught = 0
    lines = []
    for h in humans:
        case = by_id[h["case"]]
        result = cg.ask(case.question, events, case.now, config, answers_model, rep=h["rep"])
        prompt = build_judge_prompt(case.question, case.now, list(result.answer.suggestions),
                                    result.answer.message, catalog)
        reply = judge.reply(prompt, rep=1, schema=JUDGE_SCHEMA)
        verdict = parse_verdict(reply.text)
        for crit, said, why in (("J1", verdict.j1, verdict.j1_reason), ("J2", verdict.j2, verdict.j2_reason)):
            human = h[crit]
            if said == human:
                agree[crit] += 1
            elif human:
                false_alarm[crit] += 1
            else:
                missed[crit] += 1
            if said != human:
                lines.append(f"  {case.id} run {h['rep']} {crit}: judge {'PASS' if said else 'FAIL'} ({why})"
                             f"\n      human {'PASS' if human else 'FAIL'} ({h.get('note', '')})")
        if not (h["J1"] and h["J2"]):
            human_fails += 1
            if not (verdict.j1 and verdict.j2):
                caught += 1
    n = len(humans)
    source = f"LIVE {JUDGE_MODEL}" if live else f"{judge_path.name} ({'AUTHORED by the course team' if judge.provenance == 'authored' else judge.provenance})"
    print(f"Model judge vs human grades · {n} answers from config {config.name} · judge: {source}")
    print(f"  human grades: {human_path.name}, written by the course team from GRADING.md")
    print(f"\n  {'':<10}{'agree':>10}{'judge pass, human fail':>26}{'judge fail, human pass':>26}")
    for crit in ("J1", "J2"):
        print(f"  {crit:<10}{agree[crit]:>6}/{n:<3}{missed[crit]:>26}{false_alarm[crit]:>26}")
    total = agree["J1"] + agree["J2"]
    print(f"  {'overall':<10}{total:>6}/{2 * n:<3}  ({100 * total / (2 * n):.0f}% agreement)")
    print(f"\n  Answers the humans failed on J1 or J2: {human_fails}. The judge failed {caught} of them.")
    if lines:
        print("\nDisagreements")
        print("\n".join(lines))


def gate(s: dict, budget: dict, rows, model) -> bool:
    ok = True

    def line(passed, text):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {text}")

    recorded = isinstance(model, cg.ReplayModel)
    print(f"\nGate: budget.json")
    run_cases = {c.id for c, r, res, g in rows if g is not None}
    line(len(run_cases) == s["cases_in_file"] and not s["unlabelled"],
         f"every case labelled and run ({len(run_cases)} of {s['cases_in_file']})")
    runs = {}
    for c, r, res, g in rows:
        if g is not None:
            runs[c.id] = runs.get(c.id, 0) + 1
    fewest = min(runs.values(), default=0)
    line(fewest >= budget["min_runs_per_case"], f"runs per case ≥ {budget['min_runs_per_case']} (fewest: {fewest})")
    line(not s["label_problems"], f"label check: {len(s['label_problems'])} problem(s)")
    line(s["mean_score"] is not None and s["mean_score"] >= budget["min_mean_score"],
         f"mean score {fmt(s['mean_score'])} ≥ {budget['min_mean_score']}")
    line(len(s["hard_failures"]) <= budget["max_hard_failures"],
         f"hard-rule failures {len(s['hard_failures'])} ≤ {budget['max_hard_failures']}")
    line(len(s["format_errors"]) <= budget["max_format_errors"],
         f"format errors {len(s['format_errors'])} ≤ {budget['max_format_errors']}")
    for cid in budget["must_pass_every_run"]:
        scores = [g.score for c, r, res, g in rows if g and c.id == cid]
        line(bool(scores) and all(x == 1.0 for x in scores), f"{cid} scores 1.00 in every run ({', '.join(fmt(x) for x in scores)})")
    note = " (from the recordings: this checks the file, not the system)" if recorded else ""
    if s["p95_ms"] is not None:
        line(s["p95_ms"] <= budget["max_p95_latency_ms"],
             f"p95 latency {s['p95_ms'] / 1000:.2f} s ≤ {budget['max_p95_latency_ms'] / 1000:.2f} s{note}")
    if s["cost_per_answer"] is not None:
        per_1000 = s["cost_per_answer"] * 1000
        line(per_1000 <= budget["max_cost_per_1000_usd"],
             f"cost ${per_1000:.2f} per 1,000 questions ≤ ${budget['max_cost_per_1000_usd']:.2f}{note}")
    print(f"  => {'meets the budget' if ok else 'does NOT meet the budget'}")
    return ok


def save_recording(path: Path, config: cg.Config, rows) -> None:
    out = {
        "about": f"Recorded from a live run of config {config.name} ({config.model}) on "
                 f"{datetime.now():%Y-%m-%d}. Latency was measured on the machine that made the calls. "
                 "Replaying this file tests the harness; it will not react to a changed prompt.",
        "config": config.name, "provenance": "live recording", "rows": [],
    }
    for case, rep, result, _ in rows:
        if result is None:
            continue
        r = result.reply
        out["rows"].append({
            "case": case.id, "rep": rep, "question": case.question, "now": case.now.isoformat(timespec="minutes"),
            "prompt_sha256": result.prompt.sha256,
            "reply": {"text": r.text, "stop_reason": r.stop_reason},
            "usage": {"input_tokens": r.input_tokens, "output_tokens": r.output_tokens, "source": r.tokens_source},
            "latency_ms": r.latency_ms, "latency_source": f"measured {datetime.now():%Y-%m-%d}",
            "served_model": r.served_model,
        })
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nSaved {len(out['rows'])} answers to {path}. Replay them with --recording {path}")


def to_json(config, s, rows) -> dict:
    return {
        "summary": {k: v for k, v in s.items() if k not in ("per_case",)},
        "per_case": s["per_case"],
        "answers": [{
            "case": c.id, "rep": r, "suggestions": g.suggestions, "score": g.score,
            "failures": g.failures, "abstained": g.abstained, "should_abstain": g.should_abstain,
            "time_errors": g.time_errors, "format_error": g.format_error,
            "input_tokens": res.reply.input_tokens, "output_tokens": res.reply.output_tokens,
            "latency_ms": res.reply.latency_ms, "message": res.answer.message if res.answer else None,
        } for c, r, res, g in rows if g is not None],
    }


# ---------------------------------------------------------------- command line

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run and grade the concierge eval (replay by default).")
    p.add_argument("--config", default="v2", help=f"one of {', '.join([*cg.CONFIGS, *SYNTHETIC])}")
    p.add_argument("--cases", default="evalset.jsonl", help="the eval set (JSON lines)")
    p.add_argument("--runs", type=int, help="runs per case (replay: at most the recorded ones)")
    p.add_argument("--recording", help="replay this file instead of recordings/<config>.json")
    p.add_argument("--compare", nargs=2, metavar=("A", "B"), help="compare two configs case by case")
    p.add_argument("--judge-check", action="store_true", help="the model judge vs human-grades.jsonl")
    p.add_argument("--gate", action="store_true", help="exit 1 unless budget.json is met")
    p.add_argument("--json", metavar="FILE", help="also write the results as JSON")
    p.add_argument("--live", action="store_true", help="ask the real model (needs a key, costs money)")
    p.add_argument("--record", metavar="FILE", help="with --live: save the answers for replay")
    p.add_argument("--yes", action="store_true", help="with --live: do not ask for confirmation")
    args = p.parse_args(argv)
    NOT_DONE.clear()

    cases_path = Path(args.cases)
    if not cases_path.is_absolute():
        cases_path = (Path.cwd() / cases_path) if (Path.cwd() / cases_path).exists() else HERE / cases_path
    cases = load_cases(cases_path)
    events = cg.load_catalog(HERE / "catalog.json")
    prices = load_prices()

    if args.compare:
        compare(*args.compare, cases, events, prices, args.runs)
        return 0

    config = config_for(args.config)
    if args.judge_check:
        human_path = HERE / "human-grades.jsonl"
        if args.live:
            calls = sum(1 for line in human_path.read_text(encoding="utf-8").splitlines() if line.strip())
            if not confirm_live(JUDGE_MODEL, calls, args.yes):
                return 1
        try:
            judge_check(config, cases, events, human_path, HERE / "recordings" / f"judge-{config.name}.json",
                        args.live)
        except Exception as e:                 # a live call failed: say so plainly
            if not args.live:
                raise
            sys.exit(f"ERROR: the live judge call failed: {type(e).__name__}: {e}")
        return 0

    if args.config in SYNTHETIC:
        model = SyntheticModel(args.config)
    elif args.live:
        labelled = sum(1 for c in cases if c.relevant is not None)
        if not confirm_live(config.model, labelled * (args.runs or 1), args.yes):
            return 1
        try:
            model = cg.LiveModel(config.model, config.effort)
        except ImportError:
            sys.exit("Live mode needs the Anthropic SDK: pip install -r requirements.txt")
    else:
        model = cg.ReplayModel(recording_path(config, args.recording))
        if model.config != config.name:
            sys.exit(f"{model.path.name} was recorded for config {model.config}, not {config.name}")

    try:
        rows = run_eval(config, cases, events, model, args.runs)
    except Exception as e:                     # a live call failed: say so plainly
        if not args.live:
            raise
        sys.exit(f"ERROR: the live model call failed: {type(e).__name__}: {e}")
    if NOT_DONE:
        print_listing(config, model, rows, events)
        return 3
    s = summarise(config, rows, prices)
    s["label_problems"] = label_problems(cases, events)
    s["cases_in_file"] = len(cases)
    print_report(config, model, rows, s, cases_path)
    if args.json:
        Path(args.json).write_text(json.dumps(to_json(config, s, rows), indent=2, default=str) + "\n")
    if args.live and args.record:
        save_recording(Path(args.record), config, rows)
    if args.gate:
        budget = json.loads((HERE / "budget.json").read_text(encoding="utf-8"))
        return 0 if gate(s, budget, rows, model) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
