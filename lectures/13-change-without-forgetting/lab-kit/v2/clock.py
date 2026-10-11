"""Where the app gets the current time.

Code that depends on "now" asks a clock instead of calling datetime.now() itself.
The running app uses SystemClock, or a FixedClock when AFTERHOURS_NOW is set.
Tests pass a FixedClock, so a test about Friday 18:00 runs at Friday 18:00, whatever
time it really is when you run it.

Times are plain (naive) datetimes in festival local time, the same as the days stored
in the database.
"""

from datetime import datetime


def _as_datetime(value: datetime | str) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


class SystemClock:
    """The real time on the server."""

    def now(self) -> datetime:
        return datetime.now()


class FixedClock:
    """A clock that shows whatever time you set.

        clock = FixedClock("2026-10-09T18:00:00")
        clock.set("2026-10-10T12:00:00")
    """

    def __init__(self, at: datetime | str):
        self.at = _as_datetime(at)

    def now(self) -> datetime:
        return self.at

    def set(self, at: datetime | str) -> None:
        self.at = _as_datetime(at)
