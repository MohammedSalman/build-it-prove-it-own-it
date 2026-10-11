"""AfterHours — the campus festival platform (starter, Week 1).

Run it:   uvicorn app.main:app
Then open http://127.0.0.1:8000
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StringConstraints

from . import db, reservations, waitlist

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
    attendee: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


EVENT_SQL = """
    SELECT e.id, e.title, e.venue, e.starts_at, e.capacity,
           COUNT(r.id) AS reserved,
           (SELECT COUNT(*) FROM waitlist w WHERE w.event_id = e.id) AS waitlisted
    FROM events e LEFT JOIN reservations r ON r.event_id = e.id
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
        "waitlisted": row["waitlisted"],
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
    def reserve(event_id: int, body: ReservationRequest):
        try:
            return reservations.reserve(event_id, body.attendee)
        except reservations.EventNotFound:
            raise HTTPException(404, "No such event")
        except reservations.SoldOut:
            raise HTTPException(409, "Sorry, this event is full")

    @app.post("/api/events/{event_id}/waitlist", status_code=201)
    def join_waitlist(event_id: int, body: ReservationRequest):
        try:
            return waitlist.join(event_id, body.attendee)
        except reservations.EventNotFound:
            raise HTTPException(404, "No such event")
        except waitlist.EventNotFull:
            raise HTTPException(409, "Places are still available. Reserve a place instead.")
        except waitlist.AlreadyReserved:
            raise HTTPException(409, "You already have a reservation for this event.")

    return app


app = create_app()
