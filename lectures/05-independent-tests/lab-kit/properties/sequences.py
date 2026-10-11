"""Random sequences of reserve and cancel steps, and how to run them against the app."""

from hypothesis import settings
from hypothesis import strategies as st

# One step is ("reserve", name) or ("cancel", n): cancel the n-th reservation made so far
# (n = 1 is the first one). If there is no n-th reservation, the app should answer 404.
steps = st.lists(
    st.one_of(
        st.tuples(st.just("reserve"), st.sampled_from(["Maya", "Sam", "Lee", "Ana"])),
        st.tuples(st.just("cancel"), st.integers(min_value=1, max_value=4)),
    ),
    max_size=12,
)
capacities = st.integers(min_value=1, max_value=3)

# derandomize=True: the same examples on every run, as long as the Hypothesis version, the
# Python version and the test stay the same (the pinned requirements take care of the first),
# so a failure you see is a failure your partner sees. deadline=None: slow laptops don't cause
# false alarms. Hypothesis's own "ci" profile makes the same three choices (derandomize,
# deadline, database).
same_every_time = settings(max_examples=150, derandomize=True, deadline=None, database=None)


def new_event(client, capacity: int) -> int:
    res = client.post("/api/events", json={
        "title": "Property test", "venue": "Lab", "starts_at": "2026-10-09T20:00",
        "ends_at": "2026-10-09T22:00", "capacity": capacity,
    })
    assert res.status_code == 201, res.text
    return res.json()["id"]


def do(client, event_id: int, made: list, step) -> int:
    """Run one step against the app and return its HTTP status.

    `made` lists the app's reservation ids in the order they were made.
    """
    action, arg = step
    if action == "reserve":
        res = client.post(f"/api/events/{event_id}/reservations", json={"attendee": arg})
        if res.status_code == 201:
            made.append(res.json()["id"])
        return res.status_code
    reservation_id = made[arg - 1] if arg <= len(made) else 999_999
    return client.post(f"/api/reservations/{reservation_id}/cancel").status_code


def event(client, event_id: int) -> dict:
    return client.get(f"/api/events/{event_id}").json()
