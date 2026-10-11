"""Unit tests for app/policy.py under the 24-hour rule.

Fast: no web server, no database, no clock. They talk to the module's interface only.
They FAIL on the kit as handed out (the module is a shell).
"""

from datetime import datetime, timedelta

from app import policy

START = datetime(2026, 10, 9, 20, 0)


def test_the_deadline_is_24_hours_before_the_start():
    assert policy.cancellation(START, now=datetime(2026, 10, 1, 9, 0)).deadline == START - timedelta(hours=24)


def test_one_second_before_the_deadline_it_is_allowed():
    deadline = datetime(2026, 10, 8, 20, 0)
    answer = policy.cancellation(START, now=deadline - timedelta(seconds=1))
    assert (answer.allowed, answer.deadline, answer.reason) == (True, deadline, None)


def test_at_the_deadline_it_is_refused_with_a_reason():
    answer = policy.cancellation(START, now=datetime(2026, 10, 8, 20, 0))
    assert answer.allowed is False
    assert answer.reason == "Cancellations close 24 hours before the event starts."
