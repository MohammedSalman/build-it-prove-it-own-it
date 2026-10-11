"""AfterHours v1: the festival platform as it runs today (day tickets).

Run it:   uvicorn v1.main:app --port 8001
Then open http://127.0.0.1:8001/docs to try the API.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import db, reservations, tickets
from .clock import FixedClock, SystemClock

VERSION = "v1"
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


class NewTicket(BaseModel):
    holder: str = Field(min_length=1, max_length=80)
    day: str = Field(description="A festival day: 2026-10-09, 2026-10-10 or 2026-10-11")


class DayChange(BaseModel):
    day: str


class Scan(BaseModel):
    code: str = Field(min_length=1, max_length=40)


EVENT_SQL = """
    SELECT e.id, e.title, e.venue, e.starts_at, e.capacity,
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
        "reserved": row["reserved"],
        "places_left": row["capacity"] - row["reserved"],
    }


def _default_clock():
    pinned = os.environ.get("AFTERHOURS_NOW")
    return FixedClock(pinned) if pinned else SystemClock()


def create_app(clock=None) -> FastAPI:
    """Build the app. `clock` is anything with a .now() method; tests pass a FixedClock.

    The database is opened (and created and seeded if it is new) when the app starts.
    """
    clock = clock or _default_clock()

    @asynccontextmanager
    async def lifespan(app):
        db.init_db()
        yield

    app = FastAPI(title="AfterHours v1", lifespan=lifespan)

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/version")
    def version():
        return {"version": VERSION}

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

    @app.post("/api/tickets", status_code=201)
    def buy_ticket(body: NewTicket):
        try:
            return tickets.buy(body.holder, body.day)
        except tickets.NotAFestivalDay:
            raise HTTPException(422, f"Not a festival day: {body.day}")

    @app.get("/api/tickets/{ticket_id}")
    def get_ticket(ticket_id: int):
        try:
            return tickets.get(ticket_id)
        except tickets.TicketNotFound:
            raise HTTPException(404, "No such ticket")

    @app.post("/api/tickets/{ticket_id}/change-day")
    def change_day(ticket_id: int, body: DayChange):
        try:
            return tickets.change_day(ticket_id, body.day, clock.now())
        except tickets.NotAFestivalDay:
            raise HTTPException(422, f"Not a festival day: {body.day}")
        except tickets.TicketNotFound:
            raise HTTPException(404, "No such ticket")
        except tickets.ChangeRefused as exc:
            raise HTTPException(409, str(exc))

    @app.post("/api/gate/scan")
    def scan(body: Scan):
        try:
            return tickets.scan(body.code, clock.now())
        except tickets.TicketNotFound:
            raise HTTPException(404, "Unknown code")
        except tickets.GateRefused as exc:
            raise HTTPException(409, str(exc))

    return app


app = create_app()
