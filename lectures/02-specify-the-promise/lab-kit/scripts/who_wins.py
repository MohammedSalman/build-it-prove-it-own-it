"""Who wins? The same demand under different policies.

AUTHORED BY THE COURSE STAFF, NOT BY AN AGENT. Neither agent's waitlist implements any of
these policies. The only policy here that matches real code is "open to all", which is what
both agents' apps do when a place frees up (checked in the lecture's verification). Every
person below is made up.

Two questions, one script:

  1. The rush. Booking opens at 12:00 and 8 students want the last 4 places.
     First come first served, a lottery, or a quota kept for first-years?
  2. A freed place. On Friday at 14:00 someone cancels. Three people are waiting.
     Who gets the place, and when?

Usage (from the lab-kit folder):
    python scripts/who_wins.py
    python scripts/who_wins.py --kept 1 --offer-minutes 120 --seed 3

Only the Python standard library is used.
"""

import argparse
import random
from dataclasses import dataclass


# ---------------------------------------------------------------- 1. the rush

@dataclass(frozen=True)
class Applicant:
    name: str
    year: int            # year of study
    pressed_at: float    # seconds after booking opened at 12:00
    note: str


CROWD = [
    Applicant("Kai", 3, 0.4, "refreshing the page from 11:59"),
    Applicant("Maya", 2, 0.9, ""),
    Applicant("Sam", 3, 1.6, ""),
    Applicant("Ben", 4, 2.2, ""),
    Applicant("Lee", 2, 3.1, ""),
    Applicant("Ana", 1, 9.5, "on the bus, slow mobile data"),
    Applicant("Zoe", 1, 38.0, "uses a screen reader; busy page"),
    Applicant("Omar", 1, 1500.0, "in a lab until 12:25"),
]
PLACES = 4


def first_come_first_served(crowd, places):
    """The earliest presses win. AfterHours does nearly this today: there, the first request
    to get through payment and be saved wins, so a slow payment can lose to a later press."""
    return sorted(crowd, key=lambda p: p.pressed_at)[:places]


def lottery(crowd, places, window_s, seed):
    """Everyone who applies within the window has the same chance; one draw at the end."""
    entrants = sorted((p for p in crowd if p.pressed_at <= window_s), key=lambda p: p.name)
    return random.Random(seed).sample(entrants, min(places, len(entrants)))


def quota(crowd, places, kept):
    """`kept` places are kept for first-years (first come first served among them);
    the rest go first come first served to everyone not yet placed."""
    in_order = sorted(crowd, key=lambda p: p.pressed_at)
    kept_winners = [p for p in in_order if p.year == 1][:kept]
    rest = [p for p in in_order if p not in kept_winners][: places - len(kept_winners)]
    return sorted(kept_winners + rest, key=lambda p: p.pressed_at)


def expected_first_years_in_lottery(crowd, places, window_s, draws=20000):
    entrants = [p for p in crowd if p.pressed_at <= window_s]
    rng = random.Random(0)
    total = sum(sum(p.year == 1 for p in rng.sample(entrants, min(places, len(entrants))))
                for _ in range(draws))
    return total / draws


# ---------------------------------------------------------------- 2. a freed place

@dataclass(frozen=True)
class Waiting:
    name: str
    sees_messages_after: int   # minutes between a message arriving and this person reading it
    note: str


WAITLIST = [   # in the order they joined
    Waiting("Sam", 90, "in a lecture until 15:30, phone away"),
    Waiting("Ana", 3, ""),
    Waiting("Zoe", 12, ""),
]
NEWCOMER = ("Lee", 2)   # not on the waitlist; happens to open the page 2 minutes after 14:00
FREED_AT = 14 * 60      # 14:00, in minutes since midnight
EVENT_STARTS = 20 * 60  # 20:00: after this nobody is offered anything; the door decides


def hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def open_to_all():
    """Both agents' apps: nobody is told; whoever completes a booking first gets the place."""
    name, after = NEWCOMER
    return name, FREED_AT + after, "Lee never joined; nobody waiting is told"


def auto_promote():
    """Number 1 gets the place at once, and the payment is authorised without asking."""
    first = WAITLIST[0]
    return (first.name, FREED_AT,
            f"payment authorised before {first.name} knows; he reads it at "
            f"{hhmm(FREED_AT + first.sees_messages_after)}")


def timed_offer(offer_minutes):
    """Offer the place to number 1 for a fixed time. If the offer runs out unread, that person
    moves to the end of the waitlist and the new number 1 gets an offer. Offers stop when the
    event starts."""
    queue = list(WAITLIST)
    start = FREED_AT
    missed = []
    while start < EVENT_STARTS:
        person = queue.pop(0)
        if person.sees_messages_after <= offer_minutes:
            if not missed:
                note = f"the place stayed empty for {person.sees_messages_after} min"
            elif len(missed) == 1:
                note = f"{missed[0]}'s offer ran out unread at {hhmm(start)}; {missed[0]} moved to the end"
            else:
                note = f"{len(missed)} offers ran out unread first ({', '.join(missed)})"
            return person.name, start + person.sees_messages_after, note
        missed.append(person.name)
        queue.append(person)
        start += offer_minutes
    return ("nobody", EVENT_STARTS,
            f"{len(missed)} offers ran out unread; the place is empty when the event starts")


def lottery_among_waiting(seed):
    """Draw one name from the waitlist; that person gets the place at once."""
    winner = random.Random(seed).choice(WAITLIST)
    return winner.name, FREED_AT, f"each of the {len(WAITLIST)} waiting had a 1 in {len(WAITLIST)} chance"


# ---------------------------------------------------------------- report

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kept", type=int, default=2, help="places kept for first-years (quota)")
    parser.add_argument("--window", type=int, default=30, help="lottery entry window, minutes")
    parser.add_argument("--offer-minutes", type=int, default=60, help="how long a timed offer lasts")
    parser.add_argument("--seed", type=int, default=5, help="seed for both lottery draws")
    args = parser.parse_args()
    window_s = args.window * 60

    print(f"1. THE RUSH: {PLACES} places, {len(CROWD)} people. Booking opens at 12:00.\n")
    print(f"   {'who':<6}{'year':>5}  {'pressed at':<12}note")
    for p in sorted(CROWD, key=lambda p: p.pressed_at):
        minutes, seconds = divmod(p.pressed_at, 60)
        print(f"   {p.name:<6}{p.year:>5}  12:{int(minutes):02d}:{seconds:04.1f}   {p.note}")
    print()
    policies = [
        ("first come, first served", first_come_first_served(CROWD, PLACES)),
        (f"lottery (enter by 12:{args.window:02d}, seed {args.seed})",
         lottery(CROWD, PLACES, window_s, args.seed)),
        (f"quota ({args.kept} kept for first-years)", quota(CROWD, PLACES, args.kept)),
    ]
    for title, winners in policies:
        names = ", ".join(p.name for p in winners)
        first_years = sum(p.year == 1 for p in winners)
        print(f"   {title:<40} {names:<24} first-years: {first_years}")
    entrants = sum(p.pressed_at <= window_s for p in CROWD)
    print(f"\n   In the lottery each of the {entrants} entrants has a {PLACES} in {entrants} chance;"
          f" on average {expected_first_years_in_lottery(CROWD, PLACES, window_s):.1f}"
          f" of the {PLACES} winners are first-years.")

    print(f"\n2. A FREED PLACE: at {hhmm(FREED_AT)} someone cancels.")
    print("   Waiting, in order: " + ", ".join(f"{i}. {w.name}" for i, w in enumerate(WAITLIST, 1))
          + f". {NEWCOMER[0]} is not waiting; he opens the page at {hhmm(FREED_AT + NEWCOMER[1])}.\n")
    rows = [
        ("open to all (both agents' apps)", open_to_all()),
        ("auto-promote number 1 (authored)", auto_promote()),
        (f"timed offer, {args.offer_minutes} min (authored)", timed_offer(args.offer_minutes)),
        (f"lottery among the waiting (authored, seed {args.seed})", lottery_among_waiting(args.seed)),
    ]
    print(f"   {'policy':<50} {'gets it':<8} {'at':<6} what else happens")
    for title, (who, when, note) in rows:
        print(f"   {title:<50} {who:<8} {hhmm(when):<6} {note}")


if __name__ == "__main__":
    main()
