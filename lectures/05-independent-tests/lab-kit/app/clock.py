"""Where the app gets the current time.

Code that depends on "now" asks a clock instead of calling datetime.now() itself.
The running app uses SystemClock. Tests pass a FixedClock, so a test about 22:00:00
runs at 22:00:00, whatever time it really is when you run it.

Times are plain (naive) datetimes in festival local time, the same as the event times
stored in the database. Time zones come back in Week 10.
"""

from datetime import datetime


def _as_datetime(value: datetime | str) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


class SystemClock:
    """The real time on the server."""

    def now(self) -> datetime:
        return datetime.now()


class FixedClock:
    """A clock that shows whatever time the test sets.

        clock = FixedClock("2026-10-09T21:59:59")
        clock.set("2026-10-09T22:00:00")
    """

    def __init__(self, at: datetime | str):
        self.at = _as_datetime(at)

    def now(self) -> datetime:
        return self.at

    def set(self, at: datetime | str) -> None:
        self.at = _as_datetime(at)
