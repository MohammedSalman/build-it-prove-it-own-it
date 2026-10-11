"""Property-based tests for reserving and cancelling (Lab 5).

Hypothesis invents random sequences of steps, such as
    reserve Maya, reserve Sam, cancel 1, reserve Lee, cancel 1
runs each sequence against the real app, and checks a property after every step.
When a property fails, Hypothesis shrinks the sequence to a short one that still fails.

Run:  python -m pytest properties
"""

from hypothesis import given

from .model import ReferenceModel
from .sequences import capacities, do, event, new_event, same_every_time, steps


@same_every_time
@given(capacity=capacities, steps=steps)
def test_capacity_is_never_exceeded(client, capacity, steps):
    """The Week 1 promise: confirmed reservations <= capacity, after every step."""
    event_id = new_event(client, capacity)
    made = []
    for step in steps:
        do(client, event_id, made, step)
        now = event(client, event_id)
        assert now["reserved"] <= now["capacity"]


@same_every_time
@given(capacity=capacities, steps=steps)
def test_app_agrees_with_the_model(client, capacity, steps):
    """After every step, the app answers and counts exactly as the reference model does."""
    event_id = new_event(client, capacity)
    model = ReferenceModel(capacity)
    made = []
    for step in steps:
        got = do(client, event_id, made, step)
        expected = model.reserve() if step[0] == "reserve" else model.cancel(step[1])
        assert got == expected, f"{step}: app answered {got}, model says {expected}"

        now = event(client, event_id)
        assert now["reserved"] == model.confirmed(), f"after {step}: reserved"
        assert now["places_left"] == model.places_left(), f"after {step}: places_left"
