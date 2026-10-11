"""Integration test: what an organiser types is what the programme shows.

Copy this file into tests/ of your ah-merge worktree. It checks where two features meet
(start times stored in UTC, and the programme), so it belongs on the merged build.

Time is fixed on purpose. The fixed_clock fixture (tests/conftest.py) replaces the app's
clock, and the festival's zone is a constant in app/festival.py (UTC+2). Nothing in this
test may depend on your computer's clock or time zone: never call datetime.now() here.
"""

from datetime import datetime, timezone

FRIDAY_19_00 = datetime(2026, 10, 9, 17, 0, tzinfo=timezone.utc)   # 19:00 festival time (UTC+2)


def create(client, starts_at):
    """Create an event the way an organiser does: festival time, as on the poster."""
    res = client.post("/api/events", json={
        "title": "Late Lecture", "venue": "Hall A", "starts_at": starts_at, "capacity": 10,
    })
    assert res.status_code == 201, res.text
    return res.json()["id"]


def shown(client, event_id):
    """(night, event) as the programme shows this event."""
    res = client.get("/api/programme")
    assert res.status_code == 200, "no /api/programme here: run this on a build with both features"
    for night in res.json():
        for ev in night["events"]:
            if ev["id"] == event_id:
                return night["night"], ev
    raise AssertionError(f"event {event_id} is not in the programme")


def test_what_the_organiser_types_is_what_the_programme_shows(client, fixed_clock):
    fixed_clock.set(FRIDAY_19_00)
    event_id = create(client, "2026-10-09T20:00")
    night, ev = shown(client, event_id)

    # TODO 1: the programme lists it on Friday night: "Fri 9 Oct"
    # TODO 2: it shows the time the organiser typed: ev["when"] is "Fri 9 Oct · 20:00"
    # TODO 3: at 19:00 it has not started yet (look at ev["status"]), and the server
    #         agrees: booking it now is accepted with 201.
    #         client.post(f"/api/events/{event_id}/reservations", json={"attendee": "Maya"})


# TODO 4 (if you have time): an event that starts at 01:00 on Saturday 10 October must be
# listed under "Sat 10 Oct" and shown as "Sat 10 Oct · 01:00". Write it as a second test,
# using create() and shown() above.
