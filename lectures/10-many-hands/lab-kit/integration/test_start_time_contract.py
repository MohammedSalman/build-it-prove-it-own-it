"""Contract tests for start times: both sides of one boundary, checked with the same examples.

  producer   what the organiser types  ->  what the API stores and serves   (Ana's side)
  consumer   what the API serves       ->  what the programme shows          (Ben's side)

Copy this file into tests/ of your ah-merge worktree after you have written
docs/contracts/start-times.md. EXAMPLES must be exactly the rows of your contract's
Examples table: the table is what people read, this list is what the computer checks.
"""

from datetime import datetime, timezone

import pytest

from app import programme

EXAMPLES = [
    # typed (festival time)   stored and served (UTC)   night          shown
    ("2026-10-09T20:00",      "2026-10-09T18:00:00Z",   "Fri 9 Oct",   "Fri 9 Oct · 20:00"),
    # TODO 1: a row for an event that starts at 01:00 on Saturday 10 October (festival time)
    # TODO 2: one more row of your own choosing
]
BEFORE_THE_FESTIVAL = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)


def row(starts_at):
    """One event as the API serves it."""
    return {"id": 1, "title": "Contract example", "venue": "Lab", "starts_at": starts_at,
            "capacity": 5, "reserved": 0, "places_left": 5}


@pytest.mark.parametrize("typed, served, night, shown", EXAMPLES, ids=[e[0] for e in EXAMPLES])
def test_producer_stores_and_serves_utc(client, typed, served, night, shown):
    created = client.post("/api/events", json={
        "title": "Contract example", "venue": "Lab", "starts_at": typed, "capacity": 5,
    })
    assert created.json()["starts_at"] == served
    assert client.get(f"/api/events/{created.json()['id']}").json()["starts_at"] == served


@pytest.mark.parametrize("typed, served, night, shown", EXAMPLES, ids=[e[0] for e in EXAMPLES])
def test_consumer_shows_festival_time(typed, served, night, shown):
    nights = programme.build([row(served)], now=BEFORE_THE_FESTIVAL)
    # TODO 3: check that nights[0]["night"] is this example's night, and that the one
    #         event in it (nights[0]["events"][0]) has this example's "when" label.


# TODO 4: readers are strict. Write a test that a start with no offset, such as
# "2026-10-09T20:00", makes programme.build raise ValueError instead of guessing.
# (hint: with pytest.raises(ValueError): ...)
