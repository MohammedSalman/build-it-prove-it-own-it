"""Run the ticket migration one step at a time.

    python migrate.py status                 where are we? shape, steps done, checks, flags
    python migrate.py expand                 step 1: add first_day, last_day
    python migrate.py backfill               step 2: copy day into them (your code, part A3)
    python migrate.py verify                 the verification queries; all zeros = ready
    python migrate.py retire v1              record that every v1 server has been stopped
    python migrate.py flag NAME on|off       switch a flag (some flags have a guard)
    python migrate.py contract               step 3: drop `day` (refuses if anything is wrong)
    python migrate.py meaning --save FILE    write down what every ticket means
    python migrate.py meaning --compare FILE compare today's meaning with a saved one

The database is AFTERHOURS_DB (default afterhours.db), or --db PATH.
"""

import argparse
import json
import os
import sys

from migrations import meaning as meaning_mod
from migrations.backfill import backfill
from migrations.contract import contract
from migrations.steps import StepRefused, connect, expand, retire, set_flag, shape, status, verify


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.environ.get("AFTERHOURS_DB", "afterhours.db"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("expand")
    b = sub.add_parser("backfill")
    b.add_argument("--batch-size", type=int, default=200)
    sub.add_parser("verify")
    r = sub.add_parser("retire")
    r.add_argument("version")
    f = sub.add_parser("flag")
    f.add_argument("name")
    f.add_argument("state", choices=["on", "off"])
    sub.add_parser("contract")
    m = sub.add_parser("meaning")
    group = m.add_mutually_exclusive_group(required=True)
    group.add_argument("--save", metavar="FILE")
    group.add_argument("--compare", metavar="FILE")
    args = parser.parse_args(argv)

    if not os.path.exists(args.db):
        print(f"No database at {args.db}. Make one with: python scripts/make_production_db.py --db {args.db}")
        return 2
    conn = connect(args.db)
    try:
        if args.command == "status":
            print(json.dumps(status(conn), indent=2))
        elif args.command == "expand":
            expand(conn)
            print("expand: added tickets.first_day and tickets.last_day (NULL for every existing ticket)")
        elif args.command == "backfill":
            if shape(conn) != "expanded":
                raise StepRefused("backfill", [f"the tickets table is {shape(conn)}, not expanded"])
            report = backfill(conn, batch_size=args.batch_size)
            conn.execute("INSERT INTO migration_log (step, note) VALUES ('backfill', ?)",
                         (f"{report.rows} rows in {report.batches} batches",))
            print(f"backfill: {report.rows} rows changed in {report.batches} batches")
        elif args.command == "verify":
            counts = verify(conn)
            for name, n in counts.items():
                print(f"{name:>10}: {n}")
            print("ready for the new columns to take over" if not any(counts.values()) else "NOT ready")
            return 0 if not any(counts.values()) else 1
        elif args.command == "retire":
            retire(conn, args.version)
            print(f"recorded: {args.version} retired")
        elif args.command == "flag":
            set_flag(conn, args.name, args.state == "on")
            print(f"flag {args.name}: {args.state}")
        elif args.command == "contract":
            copied = contract(conn)
            print(f"contract: dropped tickets.day, {copied} tickets copied into the new table")
        elif args.command == "meaning":
            now = meaning_mod.meaning(conn)
            if args.save:
                meaning_mod.save(now, args.save)
                print(f"saved the meaning of {len(now)} tickets to {args.save}")
            else:
                saved = meaning_mod.load(args.compare)
                diffs = meaning_mod.differences(saved, now)
                print(f"{len(saved)} tickets saved, {len(now)} now, "
                      f"{'no differences' if not diffs else 'DIFFERENT:'}")
                for line in diffs:
                    print("  " + line)
                return 0 if not diffs else 1
    except StepRefused as exc:
        print(f"REFUSED: {exc.step}")
        for reason in exc.reasons:
            print(f"  - {reason}")
        return 1
    except NotImplementedError as exc:
        print(f"{args.command}: {exc}")
        return 2
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
