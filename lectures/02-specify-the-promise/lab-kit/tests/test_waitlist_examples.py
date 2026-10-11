"""Acceptance examples for the AfterHours waitlist, written as tests.

Each example is one product decision, written so that a machine can check it against any
implementation. Don't run this file on its own. Run it against all three apps with:

    python scripts/compare.py            (from the lab-kit folder)

compare.py copies this file into a scratch copy of base/, waitlist-agent-a/ and
waitlist-agent-b/, runs it there, and prints which example passes where.

Rules for writing an example
  * One decision per example. The docstring says it in Given / When / Then.
  * Use people and numbers, not "a user" and "some places".
  * Talk to the app through its HTTP API (the helpers below), so the same example can judge
    all three apps. The one exception is free_a_place(): no app can cancel yet, so it deletes
    a reservation row directly. It works only because all three apps share Week 1's database,
    and it skips anything a real cancel feature would trigger.

The two given examples encode decisions the course staff made for this exercise. Another
team could decide the opposite. That is the point: an example is a decision.
"""

import pytest

try:
    from app import db  # present when compare.py has copied this file into an app
except ImportError:  # run from the lab-kit folder by mistake
    pytest.skip("Run this file with: python scripts/compare.py", allow_module_level=True)


WORKSHOP = "Maker Workshop: Solder Your Own Badge"   # seeded full: 12 of 12 places taken
ESCAPE_ROOM = "Escape Room: The Locked Lab"           # seeded with 39 of 40 places taken


# ---------------------------------------------------------------- helpers (use these)

def event_by_title(client, title):
    return next(e for e in client.get("/api/events").json() if e["title"] == title)


def join_waitlist(client, event, name):
    """Press "Join waitlist" as `name`. Returns the HTTP response."""
    return client.post(f"/api/events/{event['id']}/waitlist", json={"attendee": name})


def reserve(client, event, name):
    """Press "Reserve" as `name`. Returns the HTTP response."""
    return client.post(f"/api/events/{event['id']}/reservations", json={"attendee": name})


def waiting_count(client, event):
    """How many people the app says are on this event's waitlist."""
    return client.get(f"/api/events/{event['id']}").json()["waitlisted"]


def free_a_place(event):
    """Free one place at `event` by deleting one reservation row.

    Neither agent built a way to cancel, so nothing in either app can free a place yet.
    This helper stands in for the cancel feature a later week adds. Call it only inside a
    test that uses the `client` fixture (that fixture points the app at a scratch database).
    """
    conn = db.connect()
    try:
        conn.execute(
            "DELETE FROM reservations WHERE id = "
            "(SELECT MIN(id) FROM reservations WHERE event_id = ?)",
            (event["id"],),
        )
    finally:
        conn.close()


# ---------------------------------------------------------------- given examples

def test_example_1_someone_with_a_place_cannot_also_wait_for_one(client):
    """
    Given Maya has just taken the last place at the escape room
    When  Maya presses "Join waitlist" for the escape room
    Then  she is told she already has a place (HTTP 409 Conflict)
    And   the escape room's waitlist stays empty
    """
    escape_room = event_by_title(client, ESCAPE_ROOM)
    assert reserve(client, escape_room, "Maya").status_code == 201

    response = join_waitlist(client, escape_room, "Maya")

    assert response.status_code == 409, f"got {response.status_code}: {response.json()}"
    assert waiting_count(client, escape_room) == 0


def test_example_2_joining_twice_tells_you_that_you_were_already_on_the_list(client):
    """
    Given the workshop is full and Sam is number 1 on its waitlist
    When  Sam presses "Join waitlist" again
    Then  the answer says he was already on it: HTTP 200 OK, not 201 Created
    And   he is still number 1, and the list holds one entry for him

    The status code is how the API tells the page "already on it". What the page then shows
    Sam is a separate, manual check.
    """
    workshop = event_by_title(client, WORKSHOP)
    assert join_waitlist(client, workshop, "Sam").status_code == 201

    again = join_waitlist(client, workshop, "Sam")

    assert again.status_code == 200, f"got {again.status_code}: {again.json()}"
    assert again.json()["position"] == 1
    assert waiting_count(client, workshop) == 1


# ---------------------------------------------------------------- your examples
#
# Copy this template, give it a new number and name, and fill it in.
# A test name must start with test_ or pytest will not run it.
#
# def test_example_3_SHORT_NAME_OF_THE_DECISION(client):
#     """
#     Given ...
#     When  ...
#     Then  ...
#     """
#     workshop = event_by_title(client, WORKSHOP)
#     ...                      # set up the Given with join_waitlist / reserve / free_a_place
#     response = ...           # do the When, once
#     assert ...               # check the Then
