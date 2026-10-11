import os
import tempfile

# app.main builds a module-level app on import; keep it away from the real database.
os.environ.setdefault("AFTERHOURS_DB", os.path.join(tempfile.mkdtemp(), "import.db"))

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test client backed by a fresh, seeded database."""
    monkeypatch.setenv("AFTERHOURS_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("AFTERHOURS_PAYMENT_DELAY", "0")
    with TestClient(create_app()) as c:
        yield c


def event_by_title(client, title):
    return next(e for e in client.get("/api/events").json() if e["title"] == title)


# ---- Lab 6 helpers ---------------------------------------------------------------

def reserve_via_api(client, event, attendee, key=None, client_id="maya-phone"):
    """POST a reservation the way the page does. With a key, it also sends a Client-Id."""
    headers = {"Idempotency-Key": key, "Client-Id": client_id} if key else {}
    return client.post(f"/api/events/{event['id']}/reservations",
                       json={"attendee": attendee}, headers=headers)


def rows_for(event, attendee, status="confirmed"):
    """How many reservations with this status the database holds for one person at one event."""
    from app import db

    conn = db.connect()
    try:
        return db.query_one(
            conn,
            "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ? AND attendee = ? AND status = ?",
            (event["id"], attendee, status),
        )["n"]
    finally:
        conn.close()


def count_payments(monkeypatch):
    """Record who is asked to pay. Returns a list that fills up as payments happen."""
    from app import payments

    calls = []
    real_authorize = payments.authorize

    def counting_authorize(attendee):
        calls.append(attendee)
        return real_authorize(attendee)

    monkeypatch.setattr(payments, "authorize", counting_authorize)
    return calls
