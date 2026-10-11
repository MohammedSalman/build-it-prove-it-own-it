import os
import tempfile

# app.main builds a module-level app on import; keep it away from the real database.
os.environ.setdefault("AFTERHOURS_DB", os.path.join(tempfile.mkdtemp(), "import.db"))

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

# A week before the festival: every event is days away, whatever the cancellation rule.
A_WEEK_BEFORE = "2026-10-02T12:00"

ESCAPE_ROOM = "Escape Room: The Locked Lab"   # Fri 9 Oct 20:00-21:30, 39 of 40 places taken
BOARD_GAMES = "Board Game Night"              # Sat 10 Oct 18:00-22:00, 23 of 60 taken, 2 cancelled
WORKSHOP = "Maker Workshop: Solder Your Own Badge"  # Sat 10 Oct 14:00, 12 of 12 taken (full)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test client backed by a fresh, seeded database, with the clock pinned."""
    monkeypatch.setenv("AFTERHOURS_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("AFTERHOURS_PAYMENT_DELAY", "0")
    monkeypatch.setenv("AFTERHOURS_NOW", A_WEEK_BEFORE)
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def set_now(monkeypatch):
    """Move the app's clock: set_now("2026-10-09T19:30")."""

    def move(when: str) -> None:
        monkeypatch.setenv("AFTERHOURS_NOW", when)

    return move


def event_by_title(client, title):
    return next(e for e in client.get("/api/events").json() if e["title"] == title)


def book(client, title, attendee):
    """Reserve a place (at the current pinned time) and return the reservation."""
    event = event_by_title(client, title)
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": attendee})
    assert res.status_code == 201, res.text
    return res.json()


def my_bookings(client, attendee):
    return client.get("/api/my-reservations", params={"attendee": attendee}).json()
