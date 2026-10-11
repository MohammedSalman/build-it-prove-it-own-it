"""Release gates: the checks a release must pass before it counts as deployed.

ops/pipeline.json lists which gates run, in order ("gates": [...]). They stop at the
first failure. Each gate returns (passed, one line saying what it saw).

  live   GET /healthz answers 200 and names the release we just started.
         It asks: is the process up, and can it open its database?
  sli    Sends the read-only requests a visitor sends (the programme, then each
         event) for a few seconds, and judges every answer with sli.is_good().
         It asks: would a visitor get correct, fast answers from this release?
         Read-only on purpose: a gate should not create real bookings.
"""

import time

from envs import base_url, http, load_pipeline


def live_gate(env: str, release: str, config: dict) -> tuple[bool, str]:
    status, body, seconds = http("GET", base_url(env) + "/healthz", timeout=2.0)
    if status != 200:
        return False, f"GET /healthz -> {status or 'no answer'}"
    if not isinstance(body, dict) or body.get("release") != release:
        return False, f"GET /healthz -> 200, but it names release {body!r}, not {release}"
    return True, f"GET /healthz -> 200 in {seconds * 1000:.0f} ms, release {release}"


def sli_gate(env: str, release: str, config: dict) -> tuple[bool, str]:
    import sli as definition  # ops/sli.py

    target = float(config.get("sli_target", 0.99))
    duration = float(config.get("sli_probe_seconds", 3))
    base = base_url(env)
    good = total = 0
    first_bad = ""
    event_ids = [1]

    def judge(kind: str, path: str) -> object:
        nonlocal good, total, first_bad
        status, body, seconds = http("GET", base + path)
        total += 1
        if definition.is_good(kind, status, seconds, body):
            good += 1
        elif not first_bad:
            first_bad = f"GET {path} -> {status or 'no answer'} in {seconds * 1000:.0f} ms"
        return body if status == 200 else None

    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        programme = judge("list", "/api/events")
        if isinstance(programme, list) and programme:
            event_ids = [e.get("id") for e in programme[:5] if isinstance(e, dict)]
        for event_id in event_ids:
            judge("event", f"/api/events/{event_id}")
        time.sleep(0.05)

    share = good / total if total else 0.0
    passed = total >= 10 and share >= target
    detail = f"{good} of {total} probe requests good = {share:.1%} (target {target:.0%})"
    if first_bad:
        detail += f"; first bad: {first_bad}"
    return passed, detail


GATES = {"live": live_gate, "sli": sli_gate}


def run_gates(env: str, release: str) -> list[tuple[str, bool, str]]:
    """Run the pipeline's gates in order; stop at the first one that fails."""
    config = load_pipeline()
    results = []
    for name in config.get("gates", ["live"]):
        gate = GATES.get(name)
        if gate is None:
            results.append((name, False, f"unknown gate '{name}' in ops/pipeline.json"))
            break
        try:
            passed, detail = gate(env, release, config)
        except NotImplementedError as exc:
            passed, detail = False, str(exc)
        except Exception as exc:  # a bug in a gate must stop the release, not crash the deploy
            passed, detail = False, f"the gate itself crashed: {type(exc).__name__}: {exc}"
        results.append((name, passed, detail))
        if not passed:
            break
    return results
