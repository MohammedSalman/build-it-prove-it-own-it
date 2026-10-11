"""AfterHours, the campus festival platform.

In the Week 12 kit you do not start this by hand: ops/deploy.py starts it for an
environment (staging or production) with that environment's database.
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import __version__, db, reservations

STATIC = Path(__file__).with_name("static")

log = logging.getLogger("afterhours")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d  %(message)s", "%H:%M:%S"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


CATEGORIES = ("games", "music", "film", "maker", "other")


class NewEvent(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    venue: str = Field(min_length=1, max_length=120)
    starts_at: str = Field(description="ISO 8601 local time, e.g. 2026-10-09T20:00")
    capacity: int = Field(gt=0)
    category: str = Field(default="other", pattern="^(games|music|film|maker|other)$")


class ReservationRequest(BaseModel):
    attendee: str = Field(min_length=1, max_length=80)


EVENT_SQL = """
    SELECT e.id, e.title, e.venue, e.starts_at, e.capacity, e.category,
           COUNT(r.id) AS reserved
    FROM events e LEFT JOIN reservations r ON r.event_id = e.id
"""


def _event_json(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "venue": row["venue"],
        "starts_at": row["starts_at"],
        "capacity": row["capacity"],
        "category": row["category"],
        "reserved": row["reserved"],
        "places_left": row["capacity"] - row["reserved"],
    }


def create_app() -> FastAPI:
    db.init_db()
    app = FastAPI(title="AfterHours")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(STATIC / "index.html")

    @app.get("/healthz")
    def healthz():
        """Liveness: the process is up and can open its database."""
        conn = db.connect()
        try:
            db.query_one(conn, "SELECT 1 AS ok")
        finally:
            conn.close()
        return {"status": "ok", "release": __version__, "pid": os.getpid()}

    @app.get("/api/events")
    def list_events(category: str | None = None):
        where, params = "", ()
        if category:
            if category not in CATEGORIES:
                raise HTTPException(422, f"category must be one of {', '.join(CATEGORIES)}")
            where, params = " WHERE e.category = ?", (category,)
        conn = db.connect()
        try:
            rows = conn.execute(
                EVENT_SQL + where + " GROUP BY e.id ORDER BY e.starts_at", params
            ).fetchall()
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
                "INSERT INTO events (title, venue, starts_at, capacity, category) VALUES (?, ?, ?, ?, ?)",
                (body.title, body.venue, body.starts_at, body.capacity, body.category),
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

    return app


app = create_app()
