"""The current time, as AfterHours sees it.

Code that needs "now" calls clock.now(). Times are festival local time as naive
datetime objects (no time zone), the same convention as events.starts_at.

You can pin the clock for demos and manual testing:

    AFTERHOURS_NOW=2026-10-09T12:00 uvicorn app.main:app

The tests pin it the same way (see tests/conftest.py).
"""

import os
from datetime import datetime


def now() -> datetime:
    pinned = os.environ.get("AFTERHOURS_NOW")
    if pinned:
        return datetime.fromisoformat(pinned)
    return datetime.now().replace(microsecond=0)
