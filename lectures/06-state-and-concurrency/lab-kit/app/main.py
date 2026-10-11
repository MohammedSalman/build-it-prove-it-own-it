"""AfterHours — the campus festival platform (Lab 6 kit: retries and state).

Run it:   uvicorn app.main:app
Then open http://127.0.0.1:8000
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import db, idempotency, reservations

STATIC = Path(__file__).with_name("static")

log = logging.getLogger("afterhours")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d  %(message)s", "%H:%M:%S"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


class NewEvent(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    venue: str = Field(min_length=1, max_length=120)
    starts_at: str = Field(description="ISO 8601 local time, e.g. 2026-10-09T20:00")
    capacity: int = Field(gt=0)


class ReservationRequest(BaseModel):
    attendee: str = Field(min_length=1, max_length=80)


KEY_REUSED = "This Idempotency-Key was already used for a different request"

# Only confirmed reservations use up a place; cancelled rows stay for the record.
EVENT_SQL = """
    SELECT e.id, e.title, e.venue, e.starts_at, e.capacity,
           COUNT(r.id) AS reserved
    FROM events e LEFT JOIN reservations r ON r.event_id = e.id AND r.status = 'confirmed'
"""


def _event_json(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "venue": row["venue"],
        "starts_at": row["starts_at"],
        "capacity": row["capacity"],
        "reserved": row["reserved"],
        "places_left": row["capacity"] - row["reserved"],
    }


def create_app() -> FastAPI:
    db.init_db()
    app = FastAPI(title="AfterHours")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/events")
    def list_events():
        conn = db.connect()
        try:
            rows = conn.execute(EVENT_SQL + " GROUP BY e.id ORDER BY e.starts_at").fetchall()
        finally:
            conn.close()
        return [_event_json(r) for r in rows]

    @app.get("/api/events/{event_id}")
    def get_event(event_id: int):
        conn = db.connect()
        try:
            row = db.query_one(conn, EVENT_SQL + " WHERE e.id = ? GROUP BY e.id", (event_id,))
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, "No such event")
        return _event_json(row)

    @app.post("/api/events", status_code=201)
    def create_event(body: NewEvent):
        conn = db.connect()
        try:
            cur = conn.execute(
                "INSERT INTO events (title, venue, starts_at, capacity) VALUES (?, ?, ?, ?)",
                (body.title, body.venue, body.starts_at, body.capacity),
            )
        finally:
            conn.close()
        return {"id": cur.lastrowid, **body.model_dump()}

    @app.post("/api/events/{event_id}/reservations", status_code=201)
    def reserve(
        event_id: int,
        body: ReservationRequest,
        # One key per reservation attempt, the same on every retry of that attempt.
        idempotency_key: str | None = Header(default=None, min_length=1, max_length=100),
        # Which browser or phone is retrying. Keys only need to be unique per client.
        client_id: str | None = Header(default=None, min_length=1, max_length=100),
    ):
        if idempotency_key is not None and client_id is None:
            raise HTTPException(400, "Send a Client-Id header with every Idempotency-Key")

        def refuse(status: int, detail: str) -> HTTPException:
            # Rule 2 for refused attempts too: bind the key to this request, so it cannot be
            # reused for a different one later. The refusal itself is not replayed: a retry
            # of the same request is simply tried again.
            if idempotency_key is not None:
                try:
                    idempotency.remember_refusal(client_id, idempotency_key,
                                                 idempotency.fingerprint(event_id, body.attendee),
                                                 status, detail)
                except idempotency.KeyReused:
                    return HTTPException(422, KEY_REUSED)
            return HTTPException(status, detail)

        try:
            return reservations.reserve(event_id, body.attendee,
                                        client_id=client_id, key=idempotency_key)
        except reservations.EventNotFound:
            raise refuse(404, "No such event")
        except reservations.SoldOut:
            raise refuse(409, "Sorry, this event is full")
        except reservations.AlreadyReserved:
            raise refuse(409, "You already have a place at this event")
        except reservations.KeyReused:
            raise HTTPException(422, KEY_REUSED)

    @app.post("/api/reservations/{reservation_id}/cancel")
    def cancel(reservation_id: int):
        # Anyone who knows a reservation number can cancel it. Week 8 fixes that.
        try:
            return reservations.cancel(reservation_id)
        except reservations.ReservationNotFound:
            raise HTTPException(404, "No such reservation")

    return app


app = create_app()
