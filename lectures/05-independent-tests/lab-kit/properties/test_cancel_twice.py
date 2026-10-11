"""Lab 5, Part A2: write this property yourself.

Requirement R3: cancelling a reservation that is already cancelled changes nothing.
As a property: for ANY sequence of steps, cancelling a reservation a second time answers
200 and leaves the event exactly as the first cancel left it.
"""

import pytest
from hypothesis import assume, given

from .sequences import capacities, do, event, new_event, same_every_time, steps


@pytest.mark.skip(reason="Lab 5, Part A2: write this property, then delete this line")
@same_every_time
@given(capacity=capacities, steps=steps)
def test_cancelling_twice_is_the_same_as_cancelling_once(client, capacity, steps):
    event_id = new_event(client, capacity)
    made = []
    for step in steps:
        do(client, event_id, made, step)
    assume(made)                  # skip sequences where nobody got a reservation
    first = made[0]

    # TODO 1: cancel reservation `first`, then read the event:   once = event(client, event_id)
    # TODO 2: cancel `first` again and assert that the answer is 200
    # TODO 3: read the event again and assert that it equals `once`
