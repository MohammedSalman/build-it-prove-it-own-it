"""Week 1's concurrency test: the last place goes to exactly one of two people."""

import importlib

from ..helpers import at_the_same_time, hold_everyone_at_payment
from .test_events import ESCAPE_ROOM, event_by_title


def test_the_last_place_goes_to_exactly_one_of_two_people_pressing_at_once(client, monkeypatch):
    reservations = importlib.import_module(f"{client.version}.reservations")
    payments = importlib.import_module(f"{client.version}.payments")
    event = event_by_title(client, ESCAPE_ROOM)
    hold_everyone_at_payment(monkeypatch, payments, people=2)

    outcomes = at_the_same_time(lambda name: reservations.reserve(event["id"], name), ["Maya", "Sam"])

    winners = [name for name, result in outcomes.items() if isinstance(result, dict)]
    turned_away = [name for name, result in outcomes.items() if isinstance(result, reservations.SoldOut)]
    assert len(winners) == 1, outcomes
    assert len(turned_away) == 1, outcomes
    assert client.get(f"/api/events/{event['id']}").json()["reserved"] == 40
