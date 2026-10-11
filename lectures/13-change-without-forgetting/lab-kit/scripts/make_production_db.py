"""Make a copy of "production": a v1 database with the festival and many day tickets.

    python scripts/make_production_db.py --db prod.db            (600 tickets, seed 13)
    python scripts/make_production_db.py --db prod.db --tickets 2000 --seed 7

The people are synthetic. The same seed always gives the same tickets.
"""

import argparse
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v1 import db as v1_db  # noqa: E402

FIRST = ["Maya", "Sam", "Lee", "Ada", "Tom", "Noor", "Jonas", "Priya", "Kofi", "Mei", "Luca",
         "Zara", "Omar", "Ines", "Tariq", "Hana", "Felix", "Aisha", "Ravi", "Elena"]
LAST = ["Okafor", "Nguyen", "Schmidt", "Haddad", "Kowalski", "Tanaka", "Silva", "Byrne",
        "Mensah", "Rossi", "Khan", "Larsen", "Moreau", "Ibrahim", "Park", "Quinn"]


def make(path: str, tickets: int = 600, seed: int = 13) -> int:
    """Create a fresh v1 database at `path`. Returns the number of tickets in it."""
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    v1_db.init_db(path)          # schema, events, the five seed tickets, the flags
    rng = random.Random(seed)
    conn = v1_db.connect(path)
    try:
        conn.execute("BEGIN")
        for _ in range(tickets - len(v1_db.SEED_TICKETS)):
            holder = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            day = rng.choice(list(v1_db.DAY_CODES))
            cur = conn.execute("INSERT INTO tickets (holder, day, code) VALUES (?, ?, ?)",
                               (holder, day, f"new-{rng.random()}"))
            conn.execute("UPDATE tickets SET code = ? WHERE id = ?",
                         (f"{v1_db.DAY_CODES[day]}-{cur.lastrowid:04d}", cur.lastrowid))
        conn.execute("COMMIT")
        return conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="prod.db")
    parser.add_argument("--tickets", type=int, default=600)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()
    n = make(args.db, args.tickets, args.seed)
    print(f"{args.db}: v1 schema, {n} day tickets")


if __name__ == "__main__":
    main()
