"""AfterHours — the campus festival platform.

Run it:   uvicorn app.main:app
Then open http://127.0.0.1:8000 (attendees) or http://127.0.0.1:8000/door (door volunteers)
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from . import clock, db, reservations

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
    starts_at: str = Field(description="Festival local time, whole minutes, e.g. 2026-10-09T20:00")
    ends_at: str | None = Field(default=None, description="Same format; default: 2 hours after the start")
    capacity: int = Field(gt=0)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def whole_minutes(cls, value: str | None) -> str | None:
        # Every stored time has this one text format (festival local time, whole minutes).
        if value is not None:
            datetime.strptime(value, "%Y-%m-%dT%H:%M")   # raises ValueError -> HTTP 422
        return value


class ReservationRequest(BaseModel):
    attendee: str = Field(min_length=1, max_length=80)


EVENT_SQL = """
    SELECT e.id, e.title, e.venue, e.starts_at, e.ends_at, e.capacity,
           COALESCE(SUM(CASE WHEN r.status = 'confirmed' THEN 1 ELSE 0 END), 0) AS reserved
    FROM events e LEFT JOIN reservations r ON r.event_id = e.id
"""


def _event_json(row, now: datetime) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "venue": row["venue"],
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "capacity": row["capacity"],
        "reserved": row["reserved"],
        "places_left": row["capacity"] - row["reserved"],
        "booking_open": now < datetime.fromisoformat(row["starts_at"]),
    }


def create_app() -> FastAPI:
    db.init_db()
    app = FastAPI(title="AfterHours")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(STATIC / "index.html")

    @app.get("/door", include_in_schema=False)
    def door_page():
        return FileResponse(STATIC / "door.html")

    @app.get("/api/events")
    def list_events():
        conn = db.connect()
        try:
            rows = conn.execute(EVENT_SQL + " GROUP BY e.id ORDER BY e.starts_at").fetchall()
        finally:
            conn.close()
        now = clock.now()
        return [_event_json(r, now) for r in rows]

    @app.get("/api/events/{event_id}")
    def get_event(event_id: int):
        conn = db.connect()
        try:
            row = db.query_one(conn, EVENT_SQL + " WHERE e.id = ? GROUP BY e.id", (event_id,))
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, "No such event")
        return _event_json(row, clock.now())

    @app.post("/api/events", status_code=201)
    def create_event(body: NewEvent):
        ends_at = body.ends_at
        if ends_at is None:
            # Organisers often leave the end time out; assume a two-hour event.
            ends_at = (datetime.fromisoformat(body.starts_at) + timedelta(hours=2)).isoformat(timespec="minutes")
        conn = db.connect()
        try:
            cur = conn.execute(
                "INSERT INTO events (title, venue, starts_at, ends_at, capacity) VALUES (?, ?, ?, ?, ?)",
                (body.title, body.venue, body.starts_at, ends_at, body.capacity),
            )
        finally:
            conn.close()
        return {"id": cur.lastrowid, **body.model_dump(), "ends_at": ends_at}

    @app.post("/api/events/{event_id}/reservations", status_code=201)
    def reserve(event_id: int, body: ReservationRequest):
        conn = db.connect()
        try:
            ev = db.query_one(conn, "SELECT starts_at, capacity FROM events WHERE id = ?", (event_id,))
            if ev is None:
                raise HTTPException(404, "No such event")
            taken = db.query_one(
                conn,
                "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ? AND status = 'confirmed'",
                (event_id,),
            )["n"]
        finally:
            conn.close()
        if clock.now() >= datetime.fromisoformat(ev["starts_at"]):
            raise HTTPException(409, "This event has already started")
        if taken >= ev["capacity"]:
            # Fail fast, before the slow payment step.
            raise HTTPException(409, "Sorry, this event is full")
        try:
            saved = reservations.reserve(event_id, body.attendee)
        except reservations.EventNotFound:
            raise HTTPException(404, "No such event")
        except reservations.SoldOut:
            raise HTTPException(409, "Sorry, this event is full")
        # Show people how long they can still cancel for free.
        saved["cancel_until"] = ev["starts_at"]
        return saved

    # --- Cancellation: people can cancel any time before the event starts ---------------

    @app.post("/api/reservations/{reservation_id}/cancel")
    def cancel_reservation(reservation_id: int):
        conn = db.connect()
        try:
            row = db.query_one(
                conn,
                """SELECT r.id, r.event_id, r.attendee, r.status, e.starts_at
                   FROM reservations r JOIN events e ON e.id = r.event_id
                   WHERE r.id = ?""",
                (reservation_id,),
            )
            if row is None:
                raise HTTPException(404, "No such reservation")
            if row["status"] == "cancelled":
                raise HTTPException(409, "This reservation is already cancelled")
            now = clock.now()
            if now >= datetime.fromisoformat(row["starts_at"]):
                raise HTTPException(409, "This event has already started")
            conn.execute(
                "UPDATE reservations SET status = 'cancelled', cancelled_at = ? WHERE id = ?",
                (now.isoformat(timespec="seconds"), reservation_id),
            )
        finally:
            conn.close()
        log.info("[%s] reservation #%d cancelled", row["attendee"], reservation_id)
        return {
            "id": row["id"],
            "event_id": row["event_id"],
            "attendee": row["attendee"],
            "status": "cancelled",
        }

    # --- My bookings: see your reservations and cancel them ----------------------------

    @app.get("/api/my-reservations")
    def my_reservations(attendee: str):
        now = clock.now().isoformat(timespec="seconds")
        conn = db.connect()
        try:
            rows = conn.execute(
                """SELECT r.id, r.event_id, e.title, e.venue, e.starts_at, r.status,
                          e.starts_at AS cancel_until,
                          CASE WHEN r.status = 'confirmed' AND e.starts_at > ? THEN 1 ELSE 0 END
                              AS can_cancel
                   FROM reservations r JOIN events e ON e.id = r.event_id
                   WHERE r.attendee = ?
                   ORDER BY e.starts_at, r.id""",
                (now, attendee),
            ).fetchall()
        finally:
            conn.close()
        return [{**dict(r), "can_cancel": bool(r["can_cancel"])} for r in rows]

    # --- Door check-in for volunteers ---------------------------------------------------

    @app.get("/api/events/{event_id}/door")
    def door_list(event_id: int):
        conn = db.connect()
        try:
            ev = db.query_one(
                conn,
                "SELECT id, title, venue, starts_at, ends_at, capacity FROM events WHERE id = ?",
                (event_id,),
            )
            if ev is None:
                raise HTTPException(404, "No such event")
            people = conn.execute(
                """SELECT id, attendee, checked_in_at FROM reservations
                   WHERE event_id = ? AND status = 'confirmed'
                   ORDER BY attendee""",
                (event_id,),
            ).fetchall()
            expected = db.query_one(
                conn, "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ?", (event_id,)
            )["n"]
            inside = db.query_one(
                conn,
                "SELECT COUNT(*) AS n FROM reservations WHERE event_id = ? AND checked_in_at IS NOT NULL",
                (event_id,),
            )["n"]
        finally:
            conn.close()
        now = clock.now()
        opens = datetime.fromisoformat(ev["starts_at"]) - timedelta(minutes=30)
        return {
            "event": dict(ev),
            "expected": expected,
            "checked_in": inside,
            "door_open": opens <= now < datetime.fromisoformat(ev["ends_at"]),
            "people": [dict(p) for p in people],
        }

    @app.post("/api/reservations/{reservation_id}/check-in")
    def check_in(reservation_id: int):
        conn = db.connect()
        try:
            row = db.query_one(
                conn,
                """SELECT r.id, r.attendee, r.status, r.checked_in_at, e.starts_at, e.ends_at
                   FROM reservations r JOIN events e ON e.id = r.event_id
                   WHERE r.id = ?""",
                (reservation_id,),
            )
            if row is None:
                raise HTTPException(404, "No such reservation")
            if row["status"] != "confirmed":
                raise HTTPException(409, "This reservation was cancelled")
            if row["checked_in_at"]:
                raise HTTPException(409, f"Already checked in at {row['checked_in_at'][11:16]}")
            now = clock.now()
            opens = datetime.strptime(row["starts_at"], "%Y-%m-%dT%H:%M") - timedelta(minutes=30)
            if now < opens:
                raise HTTPException(409, f"Check-in opens at {opens:%H:%M}")
            if now >= datetime.strptime(row["ends_at"], "%Y-%m-%dT%H:%M"):
                raise HTTPException(409, "This event has ended")
            stamp = now.isoformat(timespec="seconds")
            conn.execute("UPDATE reservations SET checked_in_at = ? WHERE id = ?", (stamp, reservation_id))
        finally:
            conn.close()
        log.info("[%s] checked in (reservation #%d)", row["attendee"], reservation_id)
        return {"id": row["id"], "attendee": row["attendee"], "checked_in_at": stamp}

    return app


app = create_app()
