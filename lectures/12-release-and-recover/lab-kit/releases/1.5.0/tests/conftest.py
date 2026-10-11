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
