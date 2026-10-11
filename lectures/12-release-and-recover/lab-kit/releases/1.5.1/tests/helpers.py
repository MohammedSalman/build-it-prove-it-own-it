"""Helpers for testing what happens when people act at the same time.

You don't need to understand threads to use these. Two ideas:

  hold_everyone_at_payment(monkeypatch)
      Replaces the payment step so that each request waits there until the others
      arrive (or 2 seconds pass). This makes the unlucky timing from Lecture 1 happen
      every time: everybody checks the count before anybody saves.

  at_the_same_time(action, names)
      Runs action(name) for every name, all starting together, and returns what
      happened to each person: the value action returned, or the exception it raised.
"""

import threading

from app import payments


def hold_everyone_at_payment(monkeypatch, people: int = 2, timeout: float = 2.0) -> None:
    gate = threading.Barrier(people)

    def authorize(attendee: str) -> None:
        try:
            gate.wait(timeout=timeout)
        except threading.BrokenBarrierError:
            pass  # the others could not get here (for example, they are waiting for a lock)

    monkeypatch.setattr(payments, "authorize", authorize)


def at_the_same_time(action, names: list[str]) -> dict:
    start_line = threading.Barrier(len(names))
    outcomes = {}

    def run(name):
        start_line.wait()
        try:
            outcomes[name] = action(name)
        except Exception as exc:
            outcomes[name] = exc

    threads = [threading.Thread(target=run, args=(name,)) for name in names]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return {name: outcomes.get(name, TimeoutError("no answer within 30 s")) for name in names}
