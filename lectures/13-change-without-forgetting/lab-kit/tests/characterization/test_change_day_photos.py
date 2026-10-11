"""Lab 13, part A1: photograph what change-day does TODAY, before the migration.

How to take a photograph (one row at a time):
  1. Add a row with the situation and `None` as the observed status.
  2. Run:  python -m pytest -q tests/characterization/test_change_day_photos.py
     The test fails and prints what v1 actually answered.
  3. Copy that status into the row. Run again: green on all four setups.
  4. Only now open docs/requirements.md (T3) and fill in `label`:
       "promise: T3"   the observed answer is what T3 asks for
       "QUIRK: ..."    the observed answer contradicts T3. Keep the photograph as it is
                       and say which sentence it contradicts. Don't fix v1 or v2 now.

Every expected value in this table comes from running the code. The labels come from
the requirements. Keep the two apart.
"""

import pytest

from ..helpers import FRI, SAT, SEED, SUN

PHOTOS = [
    # (whose ticket, what time it is, move to, observed status, label)
    ("Maya", "2026-10-08T12:00:00", SAT, 200, "promise: T3"),   # Thursday: both days still ahead
    # TODO: Friday 9 Oct 18:00: Maya's Friday ticket -> Saturday
    # TODO: Saturday 10 Oct 12:00: Maya's Friday ticket -> Sunday
    # TODO: Friday 9 Oct 18:00: Sam's Saturday ticket -> Friday
    # TODO: Saturday 10 Oct 12:00: Sam's Saturday ticket -> Sunday
    # TODO: one more situation you think matters
]


@pytest.mark.parametrize("holder, now, new_day, observed, label", PHOTOS)
def test_change_day_photo(client, clock, holder, now, new_day, observed, label):
    ticket_id = SEED[holder][0]
    clock.set(now)
    res = client.post(f"/api/tickets/{ticket_id}/change-day", json={"day": new_day})
    assert res.status_code == observed, f"{client.version} answered {res.status_code}: {res.text}"
