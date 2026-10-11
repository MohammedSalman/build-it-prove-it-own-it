"""Graders for the concierge eval. The rules they apply are written in GRADING.md.

Exact graders only, here: hard rules, precision@3 with the abstention rule, recall@3, and
the time check on the message. The judgement criteria (J1, J2) are graded by people
(human-grades.jsonl) and by a model judge (judge.py).

These graders re-implement the rules from GRADING.md. They do not call the concierge's own
helpers (app/concierge.py): a grader that shares code with the thing it grades would share
its mistakes too (Week 5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

K = 3  # the concierge may suggest at most K events (GRADING.md)


@dataclass(frozen=True)
class Case:
    id: str
    question: str
    now: datetime
    relevant: frozenset[int] | None      # None: not labelled yet
    must_not_suggest: frozenset[int]
    tags: tuple[str, ...]
    note: str

    @property
    def should_abstain(self) -> bool:
        return self.relevant is not None and not self.relevant


def case_from_json(row: dict) -> Case:
    relevant = row.get("relevant")
    return Case(
        id=row["id"], question=row["question"], now=datetime.fromisoformat(row["now"]),
        relevant=None if relevant is None else frozenset(relevant),
        must_not_suggest=frozenset(row.get("must_not_suggest", [])),
        tags=tuple(row.get("tags", [])), note=row.get("note", ""),
    )


# ---------------------------------------------------------------- hard rules (H1 to H6)

def already_started(starts_at: datetime, now: datetime) -> bool:
    """H5 (GRADING.md): has the event started at the case's time `now`?
    Read the rule in GRADING.md first: what about an event that starts exactly now?"""
    # TODO (task A2, part 1): one line.
    raise NotImplementedError("already_started() is task A2")


def hard_rule_failures(suggestions: list[int], case: Case, catalog: dict) -> list[str]:
    """Every hard rule the answer breaks, in words. An empty list means none.
    `catalog` maps event id -> Event (see app/concierge.py for the fields)."""
    failures = []
    if len(suggestions) > K:
        failures.append(f"H1 more than {K} suggestions")
    if len(set(suggestions)) != len(suggestions):
        failures.append("H2 the same event twice")
    for event_id in suggestions:
        event = catalog.get(event_id)
        if event is None:
            failures.append(f"H3 no event {event_id}")
            continue
        if event.capacity - event.reserved <= 0:
            failures.append(f"H4 event {event_id} is full")
        if already_started(event.starts_at, case.now):
            failures.append(f"H5 event {event_id} has started")
        if event_id in case.must_not_suggest:
            failures.append(f"H6 event {event_id} must not be suggested here")
    return failures


# ---------------------------------------------------------------- the score

def precision_at_k(suggestions: list[int], relevant: frozenset[int], k: int = K) -> float | None:
    """Of the first k suggestions, the share that are relevant. None if nothing was suggested.
    We divide by the number of suggestions made (at most k), not by k: see GRADING.md."""
    # TODO (task A2, part 2): look at the first k suggestions only. If there are none,
    # return None. Otherwise return how many of them are in `relevant`, divided by how
    # many suggestions you looked at.
    raise NotImplementedError("precision_at_k() is task A2")


def recall_at_k(suggestions: list[int], relevant: frozenset[int], k: int = K) -> float | None:
    """Of the relevant events (at most k of them count), the share that were suggested.
    None on an abstention case, where there is nothing to find."""
    if not relevant:
        return None
    found = sum(1 for event_id in set(suggestions[:k]) if event_id in relevant)
    return found / min(k, len(relevant))


def score_case(suggestions: list[int], case: Case, failures: list[str]) -> float:
    """One answer's score, between 0 and 1 (GRADING.md):
    - any hard-rule failure scores 0;
    - on an abstention case (no relevant events), suggesting nothing scores 1, anything else 0;
    - on any other case, suggesting nothing scores 0, otherwise precision@k."""
    # TODO (task A2, part 3): four rules, in this order. `case.should_abstain` is True when
    # the case has no relevant events; `case.relevant` is the set of relevant ids.
    raise NotImplementedError("score_case() is task A2")


# ---------------------------------------------------------------- the message (rubric T1)

TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")   # 21:00, 9:30 (not "Room 2.14")


def time_errors(message: str, suggestions: list[int], catalog: dict) -> list[str]:
    """T1: every clock time in the message is the start or end of a suggested event
    (of any event, if the answer suggests nothing). Returns the times that are not."""
    events = [catalog[i] for i in suggestions if i in catalog] or list(catalog.values())
    allowed = {f"{t:%H:%M}" for e in events for t in (e.starts_at, e.ends_at)}
    wrong = []
    for hour, minute in TIME.findall(message):
        stated = f"{int(hour):02d}:{minute}"
        if stated not in allowed:
            wrong.append(stated)
    return wrong


# ---------------------------------------------------------------- one answer, all graders

@dataclass
class Grade:
    case: str
    rep: int
    suggestions: list[int] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    score: float | None = None          # None: not scored (format error, or unlabelled case)
    precision: float | None = None
    recall: float | None = None
    abstained: bool = False
    should_abstain: bool = False
    time_errors: list[str] = field(default_factory=list)
    format_error: str | None = None
    unlabelled: bool = False


def grade(result, case: Case, catalog: dict, rep: int) -> Grade:
    """Grade one concierge Result (app/concierge.py) against one Case."""
    g = Grade(case=case.id, rep=rep, should_abstain=case.should_abstain)
    if result.answer is None:
        g.format_error = result.format_error or "no answer"
        return g
    g.suggestions = list(result.answer.suggestions)
    g.abstained = not g.suggestions
    g.failures = hard_rule_failures(g.suggestions, case, catalog)
    g.time_errors = time_errors(result.answer.message, g.suggestions, catalog)
    if case.relevant is None:
        g.unlabelled = True
        return g
    g.precision = precision_at_k(g.suggestions, case.relevant)
    g.recall = recall_at_k(g.suggestions, case.relevant)
    g.score = score_case(g.suggestions, case, g.failures)
    return g
