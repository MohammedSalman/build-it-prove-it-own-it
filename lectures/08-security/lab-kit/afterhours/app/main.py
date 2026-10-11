"""AfterHours — the campus festival platform (Week 8 kit: sign-in added).

Run it:   uvicorn app.main:app
Then open http://127.0.0.1:8000
"""

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import auth, db, reservations

STATIC = Path(__file__).with_name("static")

log = logging.getLogger("afterhours")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d  %(message)s", "%H:%M:%S"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


class Login(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class NewEvent(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    venue: str = Field(min_length=1, max_length=120)
    starts_at: str = Field(description="ISO 8601 local time, e.g. 2026-10-09T20:00")
    capacity: int = Field(gt=0)


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


def _names_by_event(conn) -> dict[int, list[str]]:
    names: dict[int, list[str]] = {}
    for row in conn.execute(
        "SELECT r.event_id, u.name FROM reservations r JOIN users u ON u.id = r.user_id ORDER BY r.id"
    ):
        names.setdefault(row["event_id"], []).append(row["name"])
    return names


def create_app() -> FastAPI:
    db.init_db()
    app = FastAPI(title="AfterHours")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(STATIC / "index.html")

    # ---- signing in -------------------------------------------------------------

    @app.post("/api/login")
    def login(body: Login):
        return auth.login(body.name, body.password)

    @app.post("/api/logout", status_code=204)
    def logout(authorization: str | None = Header(default=None), user: dict = Depends(auth.current_user)):
        auth.logout(auth.bearer_token(authorization))
        return Response(status_code=204)

    @app.get("/api/me")
    def me(user: dict = Depends(auth.current_user)):
        return user

    # ---- the programme (public) ---------------------------------------------------

    @app.get("/api/events")
    def list_events():
        conn = db.connect()
        try:
            rows = conn.execute(EVENT_SQL + " GROUP BY e.id ORDER BY e.starts_at").fetchall()
            # The door volunteers' page shows who is coming. Sending the names with the
            # programme saves it a second request.
            names = _names_by_event(conn)
        finally:
            conn.close()
        return [{**_event_json(r), "attendees": names.get(r["id"], [])} for r in rows]

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
    def create_event(body: NewEvent, user: dict = Depends(auth.current_user)):
        auth.require_organiser(user)
        conn = db.connect()
        try:
            cur = conn.execute(
                "INSERT INTO events (title, venue, starts_at, capacity) VALUES (?, ?, ?, ?)",
                (body.title, body.venue, body.starts_at, body.capacity),
            )
        finally:
            conn.close()
        return {"id": cur.lastrowid, **body.model_dump()}

    # ---- the door list (organisers only) -------------------------------------------

    @app.get("/api/events/{event_id}/attendees")
    def door_list(event_id: int, user: dict = Depends(auth.current_user)):
        auth.require_organiser(user)
        conn = db.connect()
        try:
            if db.query_one(conn, "SELECT id FROM events WHERE id = ?", (event_id,)) is None:
                raise HTTPException(404, "No such event")
            names = _names_by_event(conn).get(event_id, [])
        finally:
            conn.close()
        return {"event_id": event_id, "attendees": names}

    # ---- reservations (signed in) ---------------------------------------------------

    @app.post("/api/events/{event_id}/reservations", status_code=201)
    def reserve(event_id: int, user: dict = Depends(auth.current_user)):
        try:
            return reservations.reserve(event_id, user)
        except reservations.EventNotFound:
            raise HTTPException(404, "No such event")
        except reservations.SoldOut:
            raise HTTPException(409, "Sorry, this event is full")

    @app.get("/api/me/reservations")
    def my_reservations(user: dict = Depends(auth.current_user)):
        return reservations.my_reservations(user)

    @app.delete("/api/reservations/{reservation_id}", status_code=204)
    def cancel(reservation_id: int, user: dict = Depends(auth.current_user)):
        try:
            reservations.cancel(reservation_id, user)
        except reservations.ReservationNotFound:
            raise HTTPException(404, "No such reservation")
        return Response(status_code=204)

    return app


app = create_app()
