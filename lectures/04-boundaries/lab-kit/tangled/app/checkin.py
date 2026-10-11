"""Door check-in: who may be let in, and when.

Lab 4, OPTIONAL extension. This module is a SHELL.

It would hide the door rules (when the door opens and closes, who counts as expected)
and how a check-in is recorded. Today they live in two route handlers in main.py, with
the door window written out twice in two different styles.

Suggested interface. Change it if you can argue for something better.
"""

from datetime import datetime


class ReservationNotFound(Exception):
    pass


class CheckInRefused(Exception):
    """Raised with a sentence the door volunteer can read."""


def door_list(event_id: int, now: datetime) -> dict:
    """The door view of one event: expected, checked_in, door_open, people."""
    raise NotImplementedError("optional extension")


def check_in(reservation_id: int, now: datetime) -> dict:
    """Record that a confirmed attendee arrived. Raises ReservationNotFound or CheckInRefused."""
    raise NotImplementedError("optional extension")
