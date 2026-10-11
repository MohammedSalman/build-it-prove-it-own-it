"""Payment authorisation — a simulation. Nothing is ever charged.

A real payment provider takes somewhere between a few hundred milliseconds and a few
seconds to answer. We imitate that with a short sleep.

Classroom gate (demo only): when AFTERHOURS_CLASSROOM_GATE=2, the first request to
reach this point waits here (up to 3 seconds) for a second one, so that in a live demo
the two requests always overlap. It never changes what the reservation code does; it
only makes an unlucky timing happen on cue.
"""

import os
import threading
import time

_gate_size = int(os.environ.get("AFTERHOURS_CLASSROOM_GATE", "0"))
_gate = threading.Barrier(_gate_size) if _gate_size > 1 else None


def authorize(attendee: str) -> None:
    time.sleep(float(os.environ.get("AFTERHOURS_PAYMENT_DELAY", "0.3")))
    if _gate is not None:
        try:
            _gate.wait(timeout=3)
        except threading.BrokenBarrierError:
            _gate.reset()  # nobody else arrived in time; carry on alone
