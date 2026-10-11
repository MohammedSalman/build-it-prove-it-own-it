"""Cancellation policy: until when may people cancel a reservation?

Lab 4, Part A. This module is a SHELL: the interface is written, the body is yours.

It hides one decision that organisers are likely to change: the cancellation rule.
Callers ask cancellation(...) and use the answer. They never compare times or write
the rule down themselves: not in a route, not in SQL, not in the web page.

Conventions at this boundary (units and meaning):
  * starts_at and now are festival local time, as naive datetime objects (no time
    zone), the same convention as events.starts_at in the database. Callers parse
    strings before calling. Strings, SQL and HTML stay on the caller's side.
  * deadline is a moment, not a duration: cancelling is allowed while now < deadline.
  * reason is a sentence a person can read, or None when cancelling is allowed.
  * This module knows nothing about reservation status. "Is it already cancelled?"
    is the caller's question.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Cancellation:
    allowed: bool          # may a confirmed reservation be cancelled at `now`?
    deadline: datetime     # cancelling is allowed while now < deadline
    reason: str | None     # why not, for the person asking (None when allowed)


def cancellation(starts_at: datetime, now: datetime) -> Cancellation:
    """The cancellation rule for an event that starts at `starts_at`, asked at `now`."""
    raise NotImplementedError("Lab 4, Part A: move today's cancellation rule here")
