"""Who is asking? Sign-in, tokens, and the current user.

Authentication answers "who are you?". It does not answer "may you do this to that?".
That second question is authorization, and each route has to ask it for itself.

How sign-in works here:
  1. POST /api/login with a name and a password.
  2. We check the password against its stored hash (see passwords.py).
  3. We hand back a random token. The browser sends it with every later request:
         Authorization: Bearer <token>
  4. current_user() turns that header back into a user, or answers 401.
"""

import hashlib
import secrets

from fastapi import Header, HTTPException

from . import db, passwords


def token_hash(token: str) -> str:
    """We store only this, so a copy of the database is not a copy of everyone's sign-in."""
    return hashlib.sha256(token.encode()).hexdigest()


def login(name: str, password: str) -> dict:
    """Check a name and password. Returns {"token", "name", "role"} or raises 401."""
    conn = db.connect()
    try:
        user = db.query_one(conn, "SELECT id, name, role, password_hash FROM users WHERE name = ?", (name,))
        if user is None or not passwords.matches(password, user["password_hash"]):
            # The same answer for "no such user" and "wrong password": don't help guessers.
            raise HTTPException(401, "Wrong name or password")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions (token_hash, user_id) VALUES (?, ?)", (token_hash(token), user["id"]))
    finally:
        conn.close()
    return {"token": token, "name": user["name"], "role": user["role"]}


def logout(token: str) -> None:
    conn = db.connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
    finally:
        conn.close()


def bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip() or None


def current_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency: the signed-in user, from the Authorization header, or 401.

    The user comes from our own sessions table, never from anything else in the request.
    """
    token = bearer_token(authorization)
    user = None
    if token is not None:
        conn = db.connect()
        try:
            user = db.query_one(
                conn,
                "SELECT u.id, u.name, u.role FROM sessions s JOIN users u ON u.id = s.user_id "
                "WHERE s.token_hash = ?",
                (token_hash(token),),
            )
        finally:
            conn.close()
    if user is None:
        raise HTTPException(401, "Sign in first", headers={"WWW-Authenticate": "Bearer"})
    return {"id": user["id"], "name": user["name"], "role": user["role"]}


def require_organiser(user: dict) -> None:
    """Authorization by role: only organisers get past this line."""
    if user["role"] != "organiser":
        raise HTTPException(403, "Organisers only")
