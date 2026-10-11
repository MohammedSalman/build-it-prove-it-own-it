"""Incident check: does a booking still put a confirmation in the outbox?

    Given  a fresh, seeded AfterHours database (Board Game Night has free places)
    When   Maya books one place through the API
    Then   the API answers 201, and the outbox holds exactly one message,
           addressed to maya@example.org, whose subject names Board Game Night

Run it from the root of the AfterHours repository (the folder with app/ in it):

    python ../incident/check_confirmation.py

Exit codes follow the rules of `git bisect run`:
    0    good: the confirmation arrived
    1    bad: the booking succeeded but no confirmation arrived (the incident)
    125  this revision cannot be tested (git bisect skips it)

It uses a throwaway database in a temporary folder and never touches afterhours.db.
It needs only the packages in requirements.txt.
"""

import logging
import os
import sqlite3
import sys
import tempfile

GOOD, BAD, SKIP = 0, 1, 125
EVENT = "Board Game Night"


def main() -> int:
    work = tempfile.mkdtemp(prefix="afterhours-check-")
    os.environ["AFTERHOURS_DB"] = os.path.join(work, "check.db")
    os.environ["AFTERHOURS_PAYMENT_DELAY"] = "0"
    os.environ["AFTERHOURS_CLASSROOM_GATE"] = "0"
    # git bisect swaps the source files under us. Keep compiled bytecode in the temporary
    # folder, so an old .pyc from another revision can never be reused by mistake.
    sys.pycache_prefix = os.path.join(work, "pycache")
    sys.path.insert(0, os.getcwd())

    if not os.path.isdir(os.path.join(os.getcwd(), "app")):
        print("SKIP  run this from the root of the AfterHours repository (no app/ folder here)")
        return SKIP
    try:
        from fastapi.testclient import TestClient
        from app.main import create_app
    except Exception as exc:  # this revision cannot even be imported: not our question
        print(f"SKIP  cannot import the app at this revision: {exc!r}")
        return SKIP
    logging.getLogger("afterhours").setLevel(logging.CRITICAL)  # keep bisect output short

    # raise_server_exceptions=False: a crash in the app comes back as HTTP 500, like a
    # real server would answer, instead of a Python traceback from this script.
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        events = client.get("/api/events").json()
        event = next(e for e in events if e["title"] == EVENT)
        res = client.post(f"/api/events/{event['id']}/reservations",
                          json={"attendee": "Maya", "email": "maya@example.org"})

    if res.status_code != 201:
        # A different failure from the incident we are chasing: don't call it good or bad.
        print(f"SKIP  the booking itself failed (HTTP {res.status_code}), a different problem")
        return SKIP

    conn = sqlite3.connect(os.environ["AFTERHOURS_DB"])
    try:
        rows = conn.execute("SELECT recipient, subject FROM outbox ORDER BY id").fetchall()
    finally:
        conn.close()

    arrived = (len(rows) == 1 and "maya@example.org" in rows[0][0] and EVENT in rows[0][1])
    verdict = "GOOD" if arrived else "BAD "
    print(f"{verdict}  booking answered 201; outbox holds {len(rows)} message(s): {rows}")
    return GOOD if arrived else BAD


if __name__ == "__main__":
    sys.exit(main())
