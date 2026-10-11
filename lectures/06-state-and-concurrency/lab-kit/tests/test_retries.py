"""Task A3: a reservation request is safe to retry.

The rules from Lecture 6:
  1. Scope. One key per reservation attempt, per client. The server stores (client, key).
  2. The same key with a different request is rejected (HTTP 422), and nothing is saved.
  3. Sends of one attempt that overlap make at most ONE reservation, and a send that finds
     its attempt already answered returns that answer (even when that booking filled the
     event).
  4. The reservation and the stored answer are saved in the same transaction.

Most of these tests fail on the kit. Four already pass; their docstrings say why they are
here anyway.
"""

import sqlite3
import threading

import pytest
from fastapi import HTTPException

from app import db, idempotency, reservations
from app.main import ReservationRequest

from .conftest import count_payments, event_by_title, reserve_via_api, rows_for
from .helpers import at_the_same_time, hold_everyone_at_payment

BOARD_GAMES = "Board Game Night"   # seeded with 23 of 60 places taken
ESCAPE_ROOM = "Escape Room: The Locked Lab"   # seeded with 39 of 40 places taken
WORKSHOP = "Maker Workshop: Solder Your Own Badge"  # seeded full: 12 of 12


def test_a_retry_with_the_same_key_gets_the_same_answer(client, monkeypatch):
    event = event_by_title(client, BOARD_GAMES)
    paid = count_payments(monkeypatch)

    first = reserve_via_api(client, event, "Maya", key="k-1")
    retry = reserve_via_api(client, event, "Maya", key="k-1")    # the response was lost

    assert first.status_code == 201
    assert retry.status_code == 201
    assert retry.json() == first.json()          # the same reservation, the same answer
    assert rows_for(event, "Maya") == 1
    assert paid == ["Maya"]                      # the retry did not pay again


def test_the_same_key_for_a_different_request_is_rejected(client):
    """Given Maya's phone reserved Board Game Night with key k-1,
    when the same phone sends key k-1 again, but for Sam,
    then the server refuses with HTTP 422 and Sam gets no place."""
    event = event_by_title(client, BOARD_GAMES)
    reserve_via_api(client, event, "Maya", key="k-1")

    reused = reserve_via_api(client, event, "Sam", key="k-1")

    # TODO (Task A3): write the "then" part: the status code, and that Sam has no place.
    # Then add one more test below in the same style: the same key sent for a DIFFERENT EVENT.
    pytest.fail("Task A3: write the assertions for this test, then delete this line")


def test_a_key_refused_once_cannot_be_reused_for_a_different_request(client):
    """Given Maya's phone was refused for the (full) workshop with key k-1,
    when the same phone sends key k-1 for Sam at Open Mic,
    then the server refuses with HTTP 422: the key still belongs to Maya's request."""
    workshop = event_by_title(client, WORKSHOP)
    open_mic = event_by_title(client, "Open Mic")
    assert reserve_via_api(client, workshop, "Maya", key="k-1").status_code == 409

    reused = reserve_via_api(client, open_mic, "Sam", key="k-1")

    assert reused.status_code == 422
    assert rows_for(open_mic, "Sam") == 0


def test_two_refusals_with_one_key_for_different_people_at_once(client, monkeypatch):
    """A buggy client reuses one key for Maya and for Sam at the full workshop, at the same
    moment. Both are refused; the one whose refusal is recorded second must get 422 (a
    different request), not 409. This already passes on the kit: the refusal path is in the
    provided main.py and idempotency.remember_refusal()."""
    workshop = event_by_title(client, WORKSHOP)
    route = next(r.endpoint for r in client.app.routes
                 if getattr(r, "path", "") == "/api/events/{event_id}/reservations"
                 and "POST" in r.methods)
    real_remember = idempotency.remember_refusal
    both_refused = threading.Barrier(2)

    def remember_together(*args, **kwargs):
        both_refused.wait(timeout=2)     # both refusals get here before either is recorded
        return real_remember(*args, **kwargs)

    monkeypatch.setattr(idempotency, "remember_refusal", remember_together)

    def send(name):
        try:
            route(workshop["id"], ReservationRequest(attendee=name),
                  idempotency_key="k-1", client_id="shared-phone")
            return 201
        except HTTPException as exc:
            return exc.status_code

    outcomes = at_the_same_time(send, ["Maya", "Sam"])

    assert sorted(outcomes.values()) == [409, 422], outcomes


def test_a_retry_of_a_refused_attempt_is_tried_again(client):
    """Refusals are not replayed (the lab's policy; Stripe's API chooses the other way).
    Maya's first try finds the workshop full; a place frees up; her retry with the same key
    books it. This already passes on the kit, which ignores keys."""
    workshop = event_by_title(client, WORKSHOP)
    assert reserve_via_api(client, workshop, "Maya", key="k-1").status_code == 409
    conn = db.connect()
    try:
        someone = db.query_one(conn, "SELECT id FROM reservations WHERE event_id = ?"
                                     " AND status = 'confirmed' LIMIT 1", (workshop["id"],))["id"]
    finally:
        conn.close()
    client.post(f"/api/reservations/{someone}/cancel")

    retry = reserve_via_api(client, workshop, "Maya", key="k-1")

    assert retry.status_code == 201
    assert rows_for(workshop, "Maya") == 1


def test_keys_belong_to_one_client(client):
    """Two phones may pick the same key string. Each must get its own answer.

    This already passes on the kit, because the kit ignores keys. It is here to stop a fix
    that stores keys without the client: that fix would refuse Sam, or show him Maya's answer.
    """
    event = event_by_title(client, BOARD_GAMES)

    maya = reserve_via_api(client, event, "Maya", key="k-1", client_id="maya-phone")
    sam = reserve_via_api(client, event, "Sam", key="k-1", client_id="sam-phone")

    assert maya.status_code == 201
    assert sam.status_code == 201
    assert sam.json()["attendee"] == "Sam"
    assert sam.json()["id"] != maya.json()["id"]


def test_two_requests_with_the_same_key_at_once_make_one_reservation(client, monkeypatch):
    """The phone stopped waiting and resent while the first request was still paying."""
    event = event_by_title(client, BOARD_GAMES)
    gate = hold_everyone_at_payment(monkeypatch, people=2)  # both look the key up before either saves

    outcomes = at_the_same_time(
        lambda send: reservations.reserve(event["id"], "Maya", client_id="maya-phone", key="k-1"),
        ["first send", "resend"],
    )

    assert gate.all_arrived, "the two sends did not meet at the payment gate: order not forced"
    assert all(isinstance(r, dict) for r in outcomes.values()), outcomes
    assert outcomes["first send"]["id"] == outcomes["resend"]["id"]
    assert rows_for(event, "Maya") == 1


def test_a_send_that_finds_the_last_place_taken_by_its_own_attempt_gets_that_answer(client, monkeypatch):
    """The first send looks the key up (nothing yet) and is paused right there. Meanwhile the
    resend of the same attempt books the escape room's last place. When the first send goes
    on, the event is full, but because of this very attempt: it must replay that answer,
    not say "full"."""
    event = event_by_title(client, ESCAPE_ROOM)
    real_find = idempotency.find
    paused, go_on = threading.Event(), threading.Event()
    first_look = {}

    def find_then_pause(conn, client_id, key):
        answer = real_find(conn, client_id, key)
        if threading.current_thread().name == "first send" and not go_on.is_set():
            first_look["found"] = answer
            paused.set()
            go_on.wait(timeout=5)        # hold the first send just after its first look-up
        return answer

    monkeypatch.setattr(idempotency, "find", find_then_pause)
    outcomes = {}

    def first_send():
        try:
            outcomes["first send"] = reservations.reserve(
                event["id"], "Maya", client_id="maya-phone", key="k-1")
        except Exception as exc:
            outcomes["first send"] = exc

    thread = threading.Thread(target=first_send, name="first send")
    thread.start()
    try:
        # The order this test needs: the first send has looked (and found nothing) BEFORE the
        # resend books. If that did not happen, fail instead of passing by luck.
        assert paused.wait(timeout=2), "the first send never looked the key up: order not forced"
        assert first_look["found"] is None, "the first send already found an answer: order not forced"
        try:
            outcomes["resend"] = reservations.reserve(
                event["id"], "Maya", client_id="maya-phone", key="k-1")
        except Exception as exc:
            outcomes["resend"] = exc
    finally:
        go_on.set()
        thread.join(timeout=10)

    assert all(isinstance(r, dict) for r in outcomes.values()), outcomes
    assert outcomes["first send"]["id"] == outcomes["resend"]["id"]
    assert rows_for(event, "Maya") == 1


def test_two_sends_with_one_key_for_different_people_at_once_book_only_one(client, monkeypatch):
    """A buggy client reuses one key for Maya and for Sam, and both sends overlap. Whichever
    books first wins; the other must be refused as a different request (rule 2), not booked
    and not answered with the winner's reservation."""
    event = event_by_title(client, BOARD_GAMES)
    gate = hold_everyone_at_payment(monkeypatch, people=2)  # both look the key up before either saves

    outcomes = at_the_same_time(
        lambda name: reservations.reserve(event["id"], name, client_id="shared-phone", key="k-1"),
        ["Maya", "Sam"],
    )

    assert gate.all_arrived, "the two sends did not meet at the payment gate: order not forced"
    booked = [name for name, r in outcomes.items() if isinstance(r, dict)]
    refused = [name for name, r in outcomes.items() if isinstance(r, reservations.KeyReused)]
    assert len(booked) == 1 and len(refused) == 1, outcomes
    assert outcomes[booked[0]]["attendee"] == booked[0]
    assert rows_for(event, "Maya") + rows_for(event, "Sam") == 1


def test_the_reservation_and_its_stored_answer_are_saved_together(client, monkeypatch):
    """If storing the answer fails, the reservation must not stay behind on its own.

    Otherwise the retry finds no stored answer and tries to book a second place.
    """
    event = event_by_title(client, BOARD_GAMES)
    real_save = idempotency.save

    def failing_save(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error (simulated)")

    monkeypatch.setattr(idempotency, "save", failing_save)
    with pytest.raises(sqlite3.OperationalError):
        reservations.reserve(event["id"], "Maya", client_id="maya-phone", key="k-1")
    assert rows_for(event, "Maya") == 0          # nothing half-saved

    monkeypatch.setattr(idempotency, "save", real_save)
    retry = reservations.reserve(event["id"], "Maya", client_id="maya-phone", key="k-1")
    assert retry["attendee"] == "Maya"
    assert rows_for(event, "Maya") == 1


def test_a_request_without_a_key_still_works(client):
    """Older clients send no key. They must still be able to book.

    This already passes on the kit. It stops a fix that makes the key compulsory by accident.
    """
    event = event_by_title(client, BOARD_GAMES)

    res = reserve_via_api(client, event, "Maya")

    assert res.status_code == 201
    assert rows_for(event, "Maya") == 1
