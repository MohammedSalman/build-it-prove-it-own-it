"""Shared fixtures.

`client` is an app of one version on a fresh database of one shape. Which versions and
shapes a test runs against is decided by the `setup` fixture, which each folder sets in
its own conftest.py:

    tests/characterization/   v1-old, v1-expanded, v2-expanded, v2-contracted
    tests/v2/                  v2-expanded, v2-contracted

So one test file photographs v1 AND checks that v2 behaves the same on every shape of
the database it has to work on.
"""

import os
import tempfile

# The apps' modules can be imported before any fixture runs; keep them off real files.
os.environ.setdefault("AFTERHOURS_DB", os.path.join(tempfile.mkdtemp(), "import.db"))

import pytest  # noqa: E402

from v1.clock import FixedClock  # noqa: E402

from .helpers import app_client, use_database  # noqa: E402

BEFORE_THE_FESTIVAL = "2026-10-01T12:00:00"   # Thursday 1 October: every day still ahead


@pytest.fixture
def clock():
    """The time the apps see. Move it in a test with clock.set("2026-10-09T18:00:00")."""
    return FixedClock(BEFORE_THE_FESTIVAL)


@pytest.fixture
def setup():
    """(version, shape). Folders override this with a parametrized version."""
    return ("v1", "old")


@pytest.fixture
def database(tmp_path, monkeypatch, setup):
    """Path of this test's fresh database, in the shape `setup` names."""
    return use_database(tmp_path, monkeypatch, setup[1])


@pytest.fixture
def client(database, setup, clock):
    with app_client(setup[0], clock) as c:
        c.version, c.shape, c.db = setup[0], setup[1], database
        yield c
