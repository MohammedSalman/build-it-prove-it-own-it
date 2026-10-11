"""The SLI definition from ops/sli.py, one case per rule (Part A3)."""

from sli import is_good

PROGRAMME = [
    {"id": 1, "title": "Escape Room", "capacity": 40, "reserved": 40, "places_left": 0},
    {"id": 2, "title": "Open Mic", "capacity": 80, "reserved": 41, "places_left": 39},
]


def test_a_fast_correct_programme_is_good():
    assert is_good("list", 200, 0.02, PROGRAMME)


def test_a_server_error_is_bad():
    assert not is_good("list", 500, 0.02, "Internal Server Error")


def test_no_answer_at_all_is_bad():
    assert not is_good("list", None, 5.0, "Connection refused")


def test_a_slow_answer_is_bad_even_when_it_is_correct():
    assert not is_good("list", 200, 0.8, PROGRAMME)


def test_a_page_that_is_not_a_programme_is_bad():
    assert not is_good("list", 200, 0.02, "<html>Service Unavailable</html>")


def test_an_oversold_event_makes_the_programme_wrong():
    oversold = PROGRAMME + [{"id": 3, "capacity": 12, "reserved": 13, "places_left": -1}]
    assert not is_good("list", 200, 0.02, oversold)


def test_one_event_is_good_when_it_is_found_and_not_oversold():
    assert is_good("event", 200, 0.01, PROGRAMME[1])
    assert not is_good("event", 404, 0.01, {"detail": "No such event"})
    assert not is_good("event", 200, 0.01, {"id": 3, "places_left": -1})


def test_booked_and_full_are_both_correct_answers():
    assert is_good("book", 201, 0.31, {"id": 228})
    assert is_good("book", 409, 0.02, {"detail": "Sorry, this event is full"})


def test_a_failed_booking_is_bad():
    assert not is_good("book", 500, 0.31, "Internal Server Error")
    assert not is_good("book", 201, 0.9, {"id": 229})


def test_creating_an_event_needs_201():
    assert is_good("create", 201, 0.01, {"id": 6})
    assert not is_good("create", 500, 0.01, "Internal Server Error")
