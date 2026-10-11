"""Payment authorisation — a simulation. Nothing is ever charged.

A real payment provider takes somewhere between a few hundred milliseconds and a few
seconds to answer. We imitate that with a short sleep.

authorize() stands for placing a *hold* on the attendee's money and returns a hold id.
release(hold_id) gives the hold back. The simulation keeps the open holds in memory, so
a test can check that nobody is left with a hold and no place (Lab 6, optional extension).

Classroom gate (demo only): when AFTERHOURS_CLASSROOM_GATE=2, the first request to
reach this point waits here (up to 3 seconds) for a second one, so that in a live demo
the two requests always overlap. It never changes what the reservation code does; it
only makes an unlucky timing happen on cue.
"""

import itertools
import os
import threading
import time

_gate_size = int(os.environ.get("AFTERHOURS_CLASSROOM_GATE", "0"))
_gate = threading.Barrier(_gate_size) if _gate_size > 1 else None

_ledger_lock = threading.Lock()
_hold_numbers = itertools.count(1)
_open_holds: dict[str, str] = {}   # hold id -> attendee


def authorize(attendee: str) -> str:
    """Place a (simulated) hold for `attendee` and return its id."""
    time.sleep(float(os.environ.get("AFTERHOURS_PAYMENT_DELAY", "0.3")))
    if _gate is not None:
        try:
            _gate.wait(timeout=3)
        except threading.BrokenBarrierError:
            _gate.reset()  # nobody else arrived in time; carry on alone
    with _ledger_lock:
        hold_id = f"hold-{next(_hold_numbers)}"
        _open_holds[hold_id] = attendee
    return hold_id


def release(hold_id: str | None) -> None:
    """Give a hold back. Releasing twice, or releasing None, does nothing."""
    if hold_id is None:
        return
    with _ledger_lock:
        _open_holds.pop(hold_id, None)


def open_holds() -> dict[str, str]:
    """A copy of the holds that were placed and never released: {hold id: attendee}."""
    with _ledger_lock:
        return dict(_open_holds)
