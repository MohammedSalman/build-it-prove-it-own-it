import pytest
from fastapi.testclient import TestClient

from app.clock import FixedClock
from app.main import create_app


@pytest.fixture
def clock():
    """The time the app sees. Move it in a test with clock.set("2026-10-09T21:59:59")."""
    return FixedClock("2026-10-09T12:00:00")


@pytest.fixture
def client(tmp_path, monkeypatch, clock):
    """A test client backed by a fresh, seeded database and the fixed clock above."""
    monkeypatch.setenv("AFTERHOURS_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("AFTERHOURS_PAYMENT_DELAY", "0")
    with TestClient(create_app(clock=clock)) as c:
        yield c


def event_by_title(client, title):
    return next(e for e in client.get("/api/events").json() if e["title"] == title)


def reserve(client, event, attendee="Maya"):
    """Reserve a place and return the reservation. Fails the test if it doesn't get a 201."""
    res = client.post(f"/api/events/{event['id']}/reservations", json={"attendee": attendee})
    assert res.status_code == 201, res.text
    return res.json()
