"""Catalog: the festival's events and how many places each has left.

Lab 4, OPTIONAL extension. This module is a SHELL.

It would hide two decisions: how events are stored, and what counts as a taken place.
Today "count the confirmed reservations" is written out in several places (main.py and
reservations.py, in SQL). After the split it is written once, here.

Suggested interface. Change it if you can argue for something better, and say why in
an ADR.
"""

from datetime import datetime


class EventNotFound(Exception):
    pass


def list_events(now: datetime) -> list[dict]:
    """Every event with capacity, reserved, places_left and booking_open, by start time."""
    raise NotImplementedError("optional extension")


def get_event(event_id: int, now: datetime) -> dict:
    """One event, shaped like list_events() items. Raises EventNotFound."""
    raise NotImplementedError("optional extension")


def create_event(title: str, venue: str, starts_at: str, ends_at: str | None, capacity: int) -> dict:
    """Save a new event and return it (ends_at defaults to two hours after the start)."""
    raise NotImplementedError("optional extension")
