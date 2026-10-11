"""Authorization: may this person do this to that thing?

Adversarial tests. Each one plays a user trying something they should not be able to do,
and then checks the state of the system, not only the status code.

On the kit, the first test FAILS (the programme leaks attendee names) and the second is
yours to write (task A2). The other three already pass: they guard rules the kit gets
right, so your fixes must keep them green.
"""

import pytest

from .conftest import event_by_title, signed_in

ESCAPE_ROOM = "Escape Room: The Locked Lab"   # seeded with 39 of 40 places taken


def test_the_public_programme_does_not_name_attendees(client):
    event = event_by_title(client, ESCAPE_ROOM)
    client.post(f"/api/events/{event['id']}/reservations", headers=signed_in(client, "Maya"))

    for who in [{}, signed_in(client, "Sam")]:          # a stranger, then another student
        programme = client.get("/api/events", headers=who).text
        assert "Maya" not in programme
        assert "guest-001" not in programme


def test_a_student_cannot_cancel_someone_elses_reservation(client):
    """Lab 8, task A2: write this test. Delete the skip line when you start."""
    pytest.skip("Lab 8, task A2: write this adversarial test")
    event = event_by_title(client, ESCAPE_ROOM)
    maya, sam = signed_in(client, "Maya"), signed_in(client, "Sam")
    # 1. Maya reserves the last place. Keep her reservation id.
    # 2. Sam, with his OWN token, asks to cancel Maya's reservation.
    # 3. Assert that Sam is refused. 403 or 404? Choose one and say why in a comment.
    # 4. Assert that Maya still has her reservation (GET /api/me/reservations with her
    #    token) and the event still has no places left. A status code is not enough:
    #    check the state.


def test_an_organiser_can_cancel_anyones_reservation(client):
    event = event_by_title(client, ESCAPE_ROOM)
    maya = signed_in(client, "Maya")
    booking = client.post(f"/api/events/{event['id']}/reservations", headers=maya).json()
    assert client.delete(f"/api/reservations/{booking['id']}", headers=signed_in(client, "Olu")).status_code == 204
    assert client.get("/api/me/reservations", headers=maya).json() == []


def test_the_door_list_is_for_organisers_only(client):
    event = event_by_title(client, ESCAPE_ROOM)
    client.post(f"/api/events/{event['id']}/reservations", headers=signed_in(client, "Maya"))
    url = f"/api/events/{event['id']}/attendees"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=signed_in(client, "Sam")).status_code == 403
    door = client.get(url, headers=signed_in(client, "Olu"))
    assert door.status_code == 200
    assert "Maya" in door.json()["attendees"]


def test_nobody_can_cancel_without_signing_in(client):
    event = event_by_title(client, ESCAPE_ROOM)
    maya = signed_in(client, "Maya")
    booking = client.post(f"/api/events/{event['id']}/reservations", headers=maya).json()
    assert client.delete(f"/api/reservations/{booking['id']}").status_code == 401
    assert [r["id"] for r in client.get("/api/me/reservations", headers=maya).json()] == [booking["id"]]
