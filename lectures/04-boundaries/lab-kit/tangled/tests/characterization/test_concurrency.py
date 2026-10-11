"""Characterization test: the last place goes to exactly one person (Week 1, Lab 1)."""

from app import reservations

from ..conftest import ESCAPE_ROOM, event_by_title
from ..helpers import at_the_same_time, hold_everyone_at_payment


def test_the_last_place_goes_to_exactly_one_of_two_people_pressing_at_once(client, monkeypatch):
    event = event_by_title(client, ESCAPE_ROOM)
    hold_everyone_at_payment(monkeypatch, people=2)

    outcomes = at_the_same_time(lambda name: reservations.reserve(event["id"], name), ["Maya", "Sam"])

    winners = [name for name, result in outcomes.items() if isinstance(result, dict)]
    turned_away = [name for name, result in outcomes.items() if isinstance(result, reservations.SoldOut)]
    assert len(winners) == 1, outcomes
    assert len(turned_away) == 1, outcomes
    assert event_by_title(client, ESCAPE_ROOM)["reserved"] == 40
