"""Ask the AfterHours concierge one question.

    python concierge.py "Something quiet on Friday night?"               replay (offline), config v2
    python concierge.py --config v1 "Something quiet on Friday night?"   the demo version
    python concierge.py --run 2 "Something quiet on Friday night?"       another recorded run
    python concierge.py --show-prompt "Something quiet on Saturday night?"   what the model is sent
    python concierge.py --list                                           questions with recordings
    python concierge.py --live "..."                                     optional: a real model call

The clock is fixed at Friday 9 October 2026, 17:00 (festival time) unless you pass --now.
The programme is the frozen catalog.json unless you pass --db with an AfterHours database.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from app import concierge as cg

HERE = Path(__file__).resolve().parent
DEMO_NOW = "2026-10-09T17:00"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ask the AfterHours concierge (replay by default).")
    p.add_argument("question", nargs="?", help="what a student asks")
    p.add_argument("--config", default="v2", choices=sorted(cg.CONFIGS))
    p.add_argument("--run", type=int, default=1, help="which recorded run to play back (replay)")
    p.add_argument("--now", default=DEMO_NOW, help="festival local time, e.g. 2026-10-10T22:30")
    p.add_argument("--db", help="read the programme from this AfterHours database, not catalog.json")
    p.add_argument("--show-prompt", action="store_true", help="print what the model would be sent, then stop")
    p.add_argument("--list", action="store_true", help="list the questions this config has recordings for")
    p.add_argument("--live", action="store_true", help="ask the real model (needs a key, costs money)")
    p.add_argument("--yes", action="store_true", help="with --live: do not ask for confirmation")
    args = p.parse_args(argv)

    config = cg.CONFIGS[args.config]
    recording = HERE / "recordings" / f"{config.name}.json"
    if args.list:
        for question, asked_at in cg.ReplayModel(recording).questions():
            extra = f"   (--now {asked_at})" if asked_at and asked_at != DEMO_NOW else ""
            print(f"{question}{extra}")
        return 0
    if not args.question:
        p.error("ask a question, or use --list")

    now = datetime.fromisoformat(args.now)
    try:
        events = cg.events_from_db(args.db) if args.db else cg.load_catalog(HERE / "catalog.json")
    except FileNotFoundError as e:
        sys.exit(f"ERROR: {e}")
    if args.show_prompt:
        prompt = cg.prompt_for(args.question, events, now, config)
        print(f"== system ({config.name}) ==\n{prompt.system}\n\n== user ==\n{prompt.user}")
        print(f"\n== {len(prompt.system) + len(prompt.user):,} characters, about "
              f"{cg.estimate_tokens(prompt.system + prompt.user):,} tokens (characters / 4) ==")
        return 0

    if args.live:
        print(f"Live mode sends the question and the whole programme to {config.model} through the "
              "Anthropic API. It costs money and needs ANTHROPIC_API_KEY.")
        if not args.yes and input("Continue? [y/N] ").strip().lower() != "y":
            return 1
        try:
            model = cg.LiveModel(config.model, config.effort)
        except ImportError:
            sys.exit("Live mode needs the Anthropic SDK: pip install -r requirements.txt")
        source = f"LIVE {config.model}"
    else:
        model = cg.ReplayModel(recording)
        who = "AUTHORED by the course team, not a real model's output" if model.provenance == "authored" \
            else model.provenance
        source = f"replay of recordings/{recording.name} ({who}), run {args.run}"

    try:
        result = cg.ask(args.question, events, now, config, model, rep=args.run)
    except cg.NoRecording as e:
        print(f"No answer: {e}", file=sys.stderr)
        times = [t for q, t in cg.ReplayModel(recording).questions() if q == args.question and t != args.now]
        if times:
            print(f"This question was recorded with --now {times[0]}.", file=sys.stderr)
        print(f"Recorded questions: python concierge.py --config {config.name} --list", file=sys.stderr)
        return 2
    except Exception as e:                      # a live call failed: say so plainly
        if not args.live:
            raise
        sys.exit(f"ERROR: the live model call failed: {type(e).__name__}: {e}")

    print(f"AfterHours concierge · config {config.name} · {source}")
    print(f"Q: {args.question}   (now: {cg.spoken_time(now)})\n")
    if result.answer is None:
        print(f"The reply could not be read: {result.format_error}")
        return 1
    by_id = {e.id: e for e in events}
    for n, event_id in enumerate(result.answer.suggestions, 1):
        e = by_id.get(event_id)
        if e is None:
            print(f"  {n}. (no event {event_id} in the programme)")
        else:
            left = "FULL" if e.places_left <= 0 else f"{e.places_left} places left"
            print(f"  {n}. {e.title} · {cg.when(e)} · {e.venue} · {left}")
    if result.answer.abstains:
        print("  (no suggestions)")
    print(f'\n"{result.answer.message}"')
    if result.dropped:
        print(f"\nThe guard dropped event(s) {result.dropped}: not in the list the model was shown.")
    r = result.reply
    print(f"\ntokens: {r.input_tokens:,} in / {r.output_tokens:,} out ({r.tokens_source}) · "
          f"latency {r.latency_ms / 1000:.2f} s ({r.latency_source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
