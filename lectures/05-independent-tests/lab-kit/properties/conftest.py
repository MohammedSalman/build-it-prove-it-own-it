import logging
import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    """One app and database per test file; every example makes its own new event."""
    folder = tempfile.mkdtemp()
    quiet = logging.getLogger("afterhours")
    level = quiet.level
    quiet.setLevel(logging.WARNING)       # hundreds of examples would flood the output
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("AFTERHOURS_DB", os.path.join(folder, "properties.db"))
        mp.setenv("AFTERHOURS_PAYMENT_DELAY", "0")
        with TestClient(create_app()) as c:
            yield c
    quiet.setLevel(level)
    shutil.rmtree(folder, ignore_errors=True)
