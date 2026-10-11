# These tests came with the cancellation feature, written in the same session as the code,
# and they pass. For Lab 5 they play the part of tests an agent wrote from its own code.
# We wrote them to show that pattern (see the README): treat them as given, not as truth.

from .conftest import event_by_title, reserve

ESCAPE_ROOM = "Escape Room: The Locked Lab"   # seeded with 39 of 40 places taken


def test_cancelling_frees_a_place(client):
    event = event_by_title(client, ESCAPE_ROOM)
    booking = reserve(client, event, "Maya")
    assert client.get(f"/api/events/{event['id']}").json()["places_left"] == 0

    res = client.post(f"/api/reservations/{booking['id']}/cancel")

    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"
    assert client.get(f"/api/events/{event['id']}").json()["places_left"] == 1


def test_cancel_unknown_reservation_is_404(client):
    assert client.post("/api/reservations/9999/cancel").status_code == 404
