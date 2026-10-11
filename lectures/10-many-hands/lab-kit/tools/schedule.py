"""How much do more hands help? A tiny model of parallel work.

Give it tasks, their hours, and what each task needs first. It prints the critical path
(the longest chain of tasks that must happen one after another) and the earliest finish
time with 1, 2, 3 ... workers, found by trying every schedule.

    python schedule.py              # the lecture's example: QR tickets at the door
    python schedule.py --workers 6

This is a model, not a measurement. It assumes every worker is equally fast, a task never
needs two workers, and talking costs nothing. Real teams pay for coordination and
integration (Brooks), so treat the numbers as a best case.

To plan your own team's work (Lab 10, Part B), copy one of the two task lists below,
change the tasks, hours and dependencies, and pass it to report() in main().
"""

import argparse
from functools import lru_cache

# name: (hours, [tasks it needs first], short description)
WITHOUT_CONTRACT = {
    "T1": (3, [], "issue a ticket code for each booking"),
    "T2": (2, ["T1"], "show the QR code on My bookings"),
    "T3": (3, ["T1"], "check-in rule: once per ticket, only in the door window"),
    "T4": (4, ["T3"], "door scanner page"),
    "T5": (2, ["T3"], "live count of people inside, for organisers"),
    "T6": (2, ["T2", "T4", "T5"], "end-to-end test: book, scan, counted"),
}

# The same work, with one task added first: agree the contract (what a ticket code holds,
# what the check-in API takes and returns, with examples). Every other task can then
# build against the contract instead of against another task's finished code.
WITH_CONTRACT = {
    "C": (1, [], "agree the ticket contract, with examples"),
    "T1": (3, ["C"], "issue a ticket code for each booking"),
    "T2": (2, ["C"], "show the QR code on My bookings"),
    "T3": (3, ["C"], "check-in rule: once per ticket, only in the door window"),
    "T4": (4, ["C"], "door scanner page"),
    "T5": (2, ["C"], "live count of people inside, for organisers"),
    "T6": (2, ["T1", "T2", "T3", "T4", "T5"], "end-to-end test: book, scan, counted"),
}


def critical_path(tasks: dict) -> tuple[int, list[str]]:
    """Length and tasks of the longest chain of dependencies."""
    memo: dict[str, tuple[int, list[str]]] = {}

    def longest_to(name: str) -> tuple[int, list[str]]:
        if name not in memo:
            hours, needs, _ = tasks[name]
            best = max((longest_to(n) for n in needs), default=(0, []))
            memo[name] = (best[0] + hours, best[1] + [name])
        return memo[name]

    return max(longest_to(n) for n in tasks)


def best_finish(tasks: dict, workers: int) -> int:
    """Earliest time all tasks can be done with this many workers (exhaustive search)."""
    names = sorted(tasks)
    index = {n: i for i, n in enumerate(names)}
    hours = [tasks[n][0] for n in names]
    needs = [sum(1 << index[m] for m in tasks[n][1]) for n in names]
    everything = (1 << len(names)) - 1

    @lru_cache(maxsize=None)
    def search(done: int, running: tuple) -> int:
        # running: sorted tuple of (hours left, task index)
        if done == everything:
            return 0
        started = sum(1 << i for _, i in running)
        ready = [i for i in range(len(names))
                 if not (done | started) >> i & 1 and needs[i] & done == needs[i]]
        free = workers - len(running)
        best = None
        # choose any subset of ready tasks to start now (possibly none, if something runs)
        for mask in range(1 << len(ready)):
            chosen = [ready[k] for k in range(len(ready)) if mask >> k & 1]
            if len(chosen) > free or (not chosen and not running):
                continue
            now = sorted(running + tuple((hours[i], i) for i in chosen))
            step = now[0][0]                       # advance to the next finish
            finished = sum(1 << i for left, i in now if left == step)
            still = tuple(sorted((left - step, i) for left, i in now if left > step))
            total = step + search(done | finished, still)
            if best is None or total < best:
                best = total
        return best

    return search(0, ())


def report(title: str, tasks: dict, max_workers: int) -> None:
    length, chain = critical_path(tasks)
    total = sum(h for h, _, _ in tasks.values())
    print(title)
    print(f"  total work {total} h · critical path {length} h: {' -> '.join(chain)}")
    for w in range(1, max_workers + 1):
        print(f"  {w} worker{'s' if w > 1 else ' '}: done after {best_finish(tasks, w)} h")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--workers", type=int, default=5, help="try 1..N workers (default 5)")
    args = parser.parse_args()
    report("Without a contract (each task builds on the code before it)", WITHOUT_CONTRACT, args.workers)
    report("With a contract first (tasks build against the contract)", WITH_CONTRACT, args.workers)
    print("A model, not a measurement: equal workers, no cost for talking or integrating.")


if __name__ == "__main__":
    main()
