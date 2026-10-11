"""Task A2: the graders. These fail until you finish the three TODOs in graders.py.
Every expected value here comes from GRADING.md, not from the code."""

from datetime import datetime
from pathlib import Path

import pytest

import graders
from app import concierge as cg

KIT = Path(__file__).resolve().parents[1]
CATALOG = {e.id: e for e in cg.load_catalog(KIT / "catalog.json")}


def case(relevant, now="2026-10-09T17:00", must_not=()):
    return graders.case_from_json({"id": "t", "question": "?", "now": now, "relevant": relevant,
                                   "must_not_suggest": list(must_not)})


# ---- part 1: H5, an event that has started

def test_an_event_that_starts_exactly_now_has_started():
    assert graders.already_started(datetime(2026, 10, 9, 21, 0), now=datetime(2026, 10, 9, 21, 0))


def test_an_event_one_minute_away_has_not_started():
    assert not graders.already_started(datetime(2026, 10, 9, 21, 1), now=datetime(2026, 10, 9, 21, 0))


def test_an_event_from_last_night_has_started():
    assert graders.already_started(datetime(2026, 10, 9, 22, 0), now=datetime(2026, 10, 10, 22, 30))


def test_suggesting_an_event_that_has_started_breaks_h5():
    saturday_late = case([13], now="2026-10-10T22:30")
    assert graders.hard_rule_failures([12], saturday_late, CATALOG) == ["H5 event 12 has started"]


# ---- part 2: precision@3

@pytest.mark.parametrize("suggestions, expected", [
    ([6, 10], 1.0),            # both relevant
    ([6, 2], 0.5),             # one of two
    ([2, 6, 10], 2 / 3),       # two of three
    ([2, 8, 6, 10], 1 / 3),    # only the first three count: 2, 8, 6
    ([2], 0.0),
])
def test_precision_at_3(suggestions, expected):
    assert graders.precision_at_k(suggestions, frozenset({6, 9, 10})) == pytest.approx(expected)


def test_precision_of_no_suggestions_is_undefined():
    assert graders.precision_at_k([], frozenset({6})) is None


# ---- part 3: the score, with the abstention rule

def test_a_hard_rule_failure_scores_zero_even_if_everything_else_is_relevant():
    assert graders.score_case([6, 10], case([6, 10]), ["H4 event 7 is full"]) == 0.0


def test_saying_no_good_match_is_right_when_nothing_is_relevant():
    assert graders.score_case([], case([]), []) == 1.0


def test_suggesting_something_when_nothing_is_relevant_scores_zero():
    assert graders.score_case([6], case([]), []) == 0.0


def test_saying_no_good_match_when_something_is_relevant_scores_zero():
    assert graders.score_case([], case([5]), []) == 0.0


def test_otherwise_the_score_is_precision_at_3():
    assert graders.score_case([6, 2], case([6, 9, 10]), []) == 0.5
