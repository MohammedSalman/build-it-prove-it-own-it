"""Fill the database with festival-scale data, so you can measure what users would feel.

AfterHours has now run ten festivals (spring and autumn, 2022 to 2026). Nobody ever deletes a
reservation, so the database keeps every festival's events and every reservation ever made.
This script builds that database from scratch:

    python scripts/seed_festival.py                 # 4,000 events, 1,000,000 reservations
    python scripts/seed_festival.py --scale demo    # 10 events, like the demo in class

This term's festival is Friday 9 to Sunday 11 October 2026. Its 400 events are the last ones
inserted, so they have the ids 3601 to 4000 (at demo scale: 1 to 10). The first five are the
events you know from Lecture 1, with the same places taken.

All data is synthetic and made up by this script. The same command always builds the same
database (fixed random seed), so everyone in the class measures the same data.

STOP THE APP FIRST. The script deletes the database file and builds a new one.
It writes to the file named by AFTERHOURS_DB (default: afterhours.db), or --db PATH.
Only the Python standard library is used.
"""

import argparse
import datetime as dt
import os
import random
import sqlite3
import sys
import time
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "app" / "schema.sql"

FESTIVALS = [  # (name, first day); every festival runs for three days
    ("Spring 2022", "2022-03-18"), ("Autumn 2022", "2022-10-14"),
    ("Spring 2023", "2023-03-17"), ("Autumn 2023", "2023-10-13"),
    ("Spring 2024", "2024-03-15"), ("Autumn 2024", "2024-10-11"),
    ("Spring 2025", "2025-03-14"), ("Autumn 2025", "2025-10-10"),
    ("Spring 2026", "2026-03-13"), ("Autumn 2026", "2026-10-09"),   # this term's festival
]
EVENTS_PER_FESTIVAL = 400
TOTAL_RESERVATIONS = 1_000_000

# The five events from Lecture 1 open this term's festival, with the places already taken.
CLASSICS = [
    ("Escape Room: The Locked Lab", "Engineering Building, Room 2.14", "2026-10-09T20:00", 40, 39),
    ("Silent Disco on the Quad", "Main Quad", "2026-10-09T21:30", 150, 112),
    ("Board Game Night", "Student Union, Hall B", "2026-10-10T18:00", 60, 23),
    ("Maker Workshop: Solder Your Own Badge", "Makerspace", "2026-10-10T14:00", 12, 12),
    ("Open Mic", "Campus Cafe", "2026-10-11T19:00", 80, 41),
]

KINDS = [  # (weight, title pattern, capacities, start times)
    (25, "Workshop: {skill}", [12, 16, 20, 24, 30], ["10:00", "12:00", "14:00", "16:00"]),
    (15, "Talk: {topic}", [60, 80, 100, 150, 200], ["12:00", "14:00", "16:00", "18:00"]),
    (15, "{game} Night", [40, 60, 80, 100], ["18:00", "19:00", "20:00"]),
    (10, "Film: {film}", [120, 200, 300], ["16:00", "19:00", "21:30"]),
    (10, "Escape Room: {room}", [20, 30, 40], ["14:00", "18:00", "20:00", "22:00"]),
    (15, "Live: {band}", [300, 400, 500, 800, 1000], ["19:00", "20:00", "21:30"]),
    (10, "Club Night: {theme}", [1000, 1500, 2000, 2500], ["21:30", "23:00"]),
]
WORDS = {
    "skill": ["Screen Printing", "Bike Repair", "Sourdough", "Knitting", "Soldering", "Pottery",
              "Zine Making", "Juggling", "Calligraphy", "First Aid", "Photography", "Beat Making"],
    "topic": ["Sleep Science", "Tiny Satellites", "Urban Foxes", "Coffee Chemistry", "Old Maps",
              "Game Design", "Deep Sea Life", "Protest Songs", "Street Art", "Volcanoes"],
    "game": ["Board Game", "Quiz", "Karaoke", "Chess", "Trivia", "Poker (No Money)", "Bingo"],
    "film": ["Silent Classics", "Cult Horror", "Animated Shorts", "Documentary Double Bill",
             "Sci-Fi Marathon", "Student Films"],
    "room": ["The Lost Library", "Lab 404", "The Vault", "Night Train", "The Observatory"],
    "band": ["The Deadlines", "Null Pointers", "Campus Brass", "The Late Submissions",
             "Stack Overflow Choir", "Four Loops", "The Merge Conflicts"],
    "theme": ["Eighties", "Silent Disco", "Neon", "Afrobeats", "Drum and Bass", "Latin"],
}
VENUES = ["Main Quad", "Student Union, Hall A", "Student Union, Hall B", "Campus Cafe",
          "Makerspace", "Great Hall", "Library Lawn", "Engineering Building, Room 2.14",
          "Arts Centre Studio", "Lecture Theatre 1", "Sports Hall", "Chapel", "Boathouse"]


def make_events(rnd: random.Random, festivals: list, per_festival: int) -> list:
    """Return (title, venue, starts_at, capacity, share) for every event, oldest first.

    `share` is how full the event should end up (1.0 = sold out).
    """
    weights = [kind[0] for kind in KINDS]
    events = []
    for number, (name, first_day) in enumerate(festivals):
        current = number == len(festivals) - 1
        day0 = dt.date.fromisoformat(first_day)
        todo = per_festival
        if current:
            events += [(t, v, s, cap, taken / cap) for t, v, s, cap, taken in CLASSICS[:per_festival]]
            todo -= min(len(CLASSICS), per_festival)
        for _ in range(todo):
            _, pattern, caps, times = rnd.choices(KINDS, weights)[0]
            title = pattern.format(**{k: rnd.choice(v) for k, v in WORDS.items()})
            day = day0 + dt.timedelta(days=rnd.randrange(3))
            starts = f"{day.isoformat()}T{rnd.choice(times)}"
            # Past festivals are over and mostly full; this term's is still filling up.
            share = rnd.uniform(0.15, 0.9) if current else rnd.uniform(0.75, 1.0)
            events.append((title, rnd.choice(VENUES), starts, rnd.choice(caps), share))
    return events


def plan_reservations(events: list, total: int | None) -> list[int]:
    """How many reservations each event gets. Never more than its capacity."""
    counts = [min(cap, round(cap * share)) for _, _, _, cap, share in events]
    if total is None:
        return counts
    past = range(0, len(events) - EVENTS_PER_FESTIVAL)
    diff = total - sum(counts)
    step = 1 if diff > 0 else -1
    i = 0
    while diff != 0:                           # spread the difference over past events
        k = past[i % len(past)]
        if 0 < counts[k] + step <= events[k][3]:
            counts[k] += step
            diff -= step
        i += 1
        if i > 50 * len(past):
            sys.exit("Cannot fit that many reservations into the events' capacity.")
    return counts


def build(path: str, scale: str) -> None:
    rnd = random.Random(2026)
    if scale == "demo":
        events = make_events(rnd, FESTIVALS[-1:], 10)
        counts = plan_reservations(events, None)
    else:
        events = make_events(rnd, FESTIVALS, EVENTS_PER_FESTIVAL)
        counts = plan_reservations(events, TOTAL_RESERVATIONS)

    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except FileNotFoundError:
            pass
        except PermissionError:
            sys.exit(f"Could not delete {path}{suffix}. Is the app still running? Stop it first.")

    started = time.perf_counter()
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA.read_text())
    people = [f"student-{n:05d}" for n in range(1, 30_001)]
    conn.execute("BEGIN")
    for (title, venue, starts_at, capacity, _), n in zip(events, counts):
        cur = conn.execute(
            "INSERT INTO events (title, venue, starts_at, capacity) VALUES (?, ?, ?, ?)",
            (title, venue, starts_at, capacity),
        )
        event_id = cur.lastrowid
        start = dt.datetime.fromisoformat(starts_at)
        booked = [(start - dt.timedelta(days=rnd.randrange(1, 21), minutes=rnd.randrange(1440)))
                  .strftime("%Y-%m-%dT%H:%M:00.000Z") for _ in range(n)]
        booked.sort()
        conn.executemany(
            "INSERT INTO reservations (event_id, attendee, created_at) VALUES (?, ?, ?)",
            zip([event_id] * n, rnd.sample(people, n), booked),
        )
    conn.execute("COMMIT")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    n_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    n_res = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    first, last = conn.execute(
        "SELECT MIN(id), MAX(id) FROM events WHERE starts_at >= '2026-10-09'").fetchone()
    conn.close()
    seconds = time.perf_counter() - started
    size = os.path.getsize(path) / 1_000_000
    print(f"Built {path}: {n_events:,} events, {n_res:,} reservations, {size:.0f} MB, "
          f"in {seconds:.1f} s.")
    print(f"This term's festival (9-11 Oct 2026): event ids {first} to {last}.")
    print("Now start the app: uvicorn app.main:app")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scale", choices=["festival", "demo"], default="festival")
    parser.add_argument("--db", default=os.environ.get("AFTERHOURS_DB", "afterhours.db"),
                        help="database file to (re)build (default: AFTERHOURS_DB or afterhours.db)")
    args = parser.parse_args()
    build(args.db, args.scale)


if __name__ == "__main__":
    main()
