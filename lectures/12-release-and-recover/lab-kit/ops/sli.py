"""The service level indicator (SLI) for AfterHours, written as code.

One definition of "good", used everywhere it matters:
  * traffic.py judges every simulated visitor's request with it and reports the SLI,
  * the "sli" gate in deploy.py and rollback.py probes a new release and judges the
    answers with it before the release counts as deployed.

The SLI: the share of festival-page requests that got a correct answer within 0.5 s.

    kind      request                               good when
    "list"    GET  /api/events                      200, a JSON list, and every event
                                                    in it has places_left >= 0
    "event"   GET  /api/events/{id}                 200, a JSON object with places_left >= 0
    "book"    POST /api/events/{id}/reservations    201 (booked) or 409 (full: a correct
                                                    answer, not a failure)
    "create"  POST /api/events                      201

    A request with no answer at all (status None) is bad.
    A request that took longer than SLOW seconds is bad, whatever it returned.

Part A3: write is_good() so that it follows this table, then run
    python -m pytest -q ops/tests/test_sli.py
"""

SLOW = 0.5  # seconds


def is_good(kind: str, status: int | None, seconds: float, body) -> bool:
    """Was this one request served well, from the visitor's point of view?

    kind     "list", "event", "book" or "create" (see the table above)
    status   the HTTP status code, or None if there was no answer
    seconds  how long the request took
    body     the parsed JSON answer (a list or a dict), or text, or None
    """
    raise NotImplementedError("the SLI is not defined yet: write is_good() in ops/sli.py (Part A3)")
