"""AfterHours — the campus festival platform (Lab 5 kit).

Run it:   uvicorn app.main:app
Then open http://127.0.0.1:8000
"""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import checkin, db, reservations
from .clock import SystemClock

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
    starts_at: str = Field(description="ISO 8601 festival local time, e.g. 2026-10-09T20:00")
    ends_at: str = Field(description="ISO 8601 festival local time, after starts_at")
    capacity: int = Field(gt=0)


class ReservationRequest(BaseModel):
    attendee: str = Field(min_length=1, max_length=80)


EVENT_SQL = """
    SELECT e.id, e.title, e.venue, e.starts_at, e.ends_at, e.capacity, e.places_left,
           COUNT(r.id) AS reserved
    FROM events e LEFT JOIN reservations r ON r.event_id = e.id AND r.status = 'confirmed'
"""


def _event_json(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "venue": row["venue"],
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "capacity": row["capacity"],
        "reserved": row["reserved"],          # counted: confirmed reservations
        "places_left": row["places_left"],    # the stored counter
    }


def create_app(clock=None) -> FastAPI:
    """Build the app. `clock` is anything with a .now() method; tests pass a FixedClock."""
    clock = clock or SystemClock()
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
        try:
            starts_at = datetime.fromisoformat(body.starts_at)
            ends_at = datetime.fromisoformat(body.ends_at)
        except ValueError:
            raise HTTPException(422, "starts_at and ends_at must be ISO 8601 times")
        if starts_at.tzinfo is not None or ends_at.tzinfo is not None:
            raise HTTPException(422, "Give festival local times without a time zone")
        if ends_at <= starts_at:
            raise HTTPException(422, "ends_at must be after starts_at")
        conn = db.connect()
        try:
            cur = conn.execute(
                "INSERT INTO events (title, venue, starts_at, ends_at, capacity, places_left)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (body.title, body.venue, body.starts_at, body.ends_at, body.capacity, body.capacity),
            )
        finally:
            conn.close()
        return {"id": cur.lastrowid, **body.model_dump()}

    @app.post("/api/events/{event_id}/reservations", status_code=201)
    def reserve(event_id: int, body: ReservationRequest):
        try:
            return reservations.reserve(event_id, body.attendee)
        except reservations.EventNotFound:
            raise HTTPException(404, "No such event")
        except reservations.SoldOut:
            raise HTTPException(409, "Sorry, this event is full")

    @app.get("/api/reservations/{reservation_id}")
    def get_reservation(reservation_id: int):
        try:
            return reservations.get(reservation_id)
        except reservations.ReservationNotFound:
            raise HTTPException(404, "No such reservation")

    @app.post("/api/reservations/{reservation_id}/cancel")
    def cancel(reservation_id: int):
        try:
            return reservations.cancel(reservation_id)
        except reservations.ReservationNotFound:
            raise HTTPException(404, "No such reservation")

    @app.post("/api/reservations/{reservation_id}/check-in")
    def check_in(reservation_id: int):
        try:
            return checkin.check_in(reservation_id, clock.now())
        except reservations.ReservationNotFound:
            raise HTTPException(404, "No such reservation")
        except checkin.CheckInRefused as refused:
            raise HTTPException(409, str(refused))

    return app


app = create_app()
