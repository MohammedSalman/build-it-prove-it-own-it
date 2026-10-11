from app import reservations

from .conftest import event_by_title, signed_in
from .helpers import at_the_same_time, hold_everyone_at_payment

ESCAPE_ROOM = "Escape Room: The Locked Lab"   # seeded with 39 of 40 places taken


def test_the_last_place_goes_to_exactly_one_of_two_people_pressing_at_once(client, monkeypatch):
    event = event_by_title(client, ESCAPE_ROOM)
    users = {name: client.get("/api/me", headers=signed_in(client, name)).json() for name in ["Maya", "Sam"]}
    hold_everyone_at_payment(monkeypatch, people=2)

    outcomes = at_the_same_time(lambda name: reservations.reserve(event["id"], users[name]), ["Maya", "Sam"])

    winners = [name for name, result in outcomes.items() if isinstance(result, dict)]
    turned_away = [name for name, result in outcomes.items() if isinstance(result, reservations.SoldOut)]
    assert len(winners) == 1, outcomes
    assert len(turned_away) == 1, outcomes
    assert client.get(f"/api/events/{event['id']}").json()["reserved"] == 40
