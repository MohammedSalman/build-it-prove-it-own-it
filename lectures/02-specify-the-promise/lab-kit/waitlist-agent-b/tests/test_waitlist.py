from app import reservations, waitlist

from .conftest import event_by_title
from .helpers import at_the_same_time, hold_everyone_at_payment

ESCAPE_ROOM = "Escape Room: The Locked Lab"   # seeded with 39 of 40 places taken
WORKSHOP = "Maker Workshop: Solder Your Own Badge"  # seeded full (12 of 12)


def join(client, event_id, name):
    return client.post(f"/api/events/{event_id}/waitlist", json={"attendee": name})


def test_events_report_how_many_people_are_waiting(client):
    events = client.get("/api/events").json()
    assert all(e["waitlisted"] == 0 for e in events)


def test_joining_the_waitlist_of_a_full_event(client):
    event = event_by_title(client, WORKSHOP)
    res = join(client, event["id"], "Sam")
    assert res.status_code == 201
    assert res.json()["attendee"] == "Sam"
    assert res.json()["event_id"] == event["id"]
    assert res.json()["position"] == 1
    assert client.get(f"/api/events/{event['id']}").json()["waitlisted"] == 1


def test_people_queue_in_the_order_they_join(client):
    event = event_by_title(client, WORKSHOP)
    positions = [join(client, event["id"], name).json()["position"] for name in ["Sam", "Lee", "Ana"]]
    assert positions == [1, 2, 3]


def test_the_waitlist_does_not_use_up_places(client):
    event = event_by_title(client, WORKSHOP)
    join(client, event["id"], "Sam")
    after = client.get(f"/api/events/{event['id']}").json()
    assert after["reserved"] == 12
    assert after["places_left"] == 0


def test_joining_twice_keeps_your_place_in_line(client):
    event = event_by_title(client, WORKSHOP)
    join(client, event["id"], "Sam")
    join(client, event["id"], "Lee")
    again = join(client, event["id"], "Sam")
    assert again.status_code == 200
    assert again.json()["position"] == 1
    assert client.get(f"/api/events/{event['id']}").json()["waitlisted"] == 2


def test_you_cannot_wait_for_an_event_that_has_places(client):
    event = event_by_title(client, ESCAPE_ROOM)
    res = join(client, event["id"], "Sam")
    assert res.status_code == 409
    assert client.get(f"/api/events/{event['id']}").json()["waitlisted"] == 0


def test_whoever_misses_the_last_place_can_join_the_waitlist(client):
    event = event_by_title(client, ESCAPE_ROOM)
    client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Maya"})
    turned_away = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": "Sam"})
    assert turned_away.status_code == 409
    assert join(client, event["id"], "Sam").status_code == 201


def test_waitlists_are_per_event(client):
    workshop = event_by_title(client, WORKSHOP)
    escape = event_by_title(client, ESCAPE_ROOM)
    client.post(f"/api/events/{escape['id']}/reservations", json={"attendee": "Maya"})
    join(client, workshop["id"], "Sam")
    assert join(client, escape["id"], "Lee").json()["position"] == 1


def test_waitlist_for_unknown_event_is_404(client):
    assert join(client, 9999, "Sam").status_code == 404


def test_waitlist_needs_a_name(client):
    event = event_by_title(client, WORKSHOP)
    assert join(client, event["id"], "").status_code == 422


def test_people_joining_at_once_get_different_places_in_line(client):
    event = event_by_title(client, WORKSHOP)
    names = ["Maya", "Sam", "Lee", "Ana"]

    outcomes = at_the_same_time(lambda name: waitlist.join(event["id"], name), names)

    assert all(isinstance(r, dict) for r in outcomes.values()), outcomes
    assert sorted(r["position"] for r in outcomes.values()) == [1, 2, 3, 4]
    assert client.get(f"/api/events/{event['id']}").json()["waitlisted"] == 4


def test_the_same_person_joining_twice_at_once_is_listed_once(client):
    event = event_by_title(client, WORKSHOP)

    outcomes = at_the_same_time(lambda _: waitlist.join(event["id"], "Sam"), ["tab-1", "tab-2"])

    assert all(isinstance(r, dict) for r in outcomes.values()), outcomes
    assert sorted(r["created"] for r in outcomes.values()) == [False, True]
    assert {r["position"] for r in outcomes.values()} == {1}
    assert client.get(f"/api/events/{event['id']}").json()["waitlisted"] == 1


def test_last_place_race_then_waitlist_keeps_the_promise(client, monkeypatch):
    event = event_by_title(client, ESCAPE_ROOM)
    hold_everyone_at_payment(monkeypatch, people=2)

    outcomes = at_the_same_time(lambda name: reservations.reserve(event["id"], name), ["Maya", "Sam"])
    losers = [name for name, r in outcomes.items() if isinstance(r, reservations.SoldOut)]
    assert len(losers) == 1, outcomes

    assert join(client, event["id"], losers[0]).status_code == 201
    after = client.get(f"/api/events/{event['id']}").json()
    assert after["reserved"] == after["capacity"] == 40
    assert after["waitlisted"] == 1
