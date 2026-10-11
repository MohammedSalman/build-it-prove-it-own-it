"""Send one request to the running app, as anyone you like. A request is just text you write.

Usage (with the app running in another terminal):
    python scripts/client.py GET /api/events                         # as a stranger
    python scripts/client.py --as Maya POST /api/events/1/reservations
    python scripts/client.py --as Sam GET /api/me/reservations
    python scripts/client.py --as Sam DELETE /api/reservations/229
    python scripts/client.py --as Olu GET /api/events/1/attendees

--as NAME signs in first with that demo account's password (from app/db.py), then sends
the request with the token. In real life Sam knows only his own password. This script
knows all four so you can play every part.

Only the Python standard library is used.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import DEMO_ACCOUNTS  # noqa: E402

PASSWORDS = {name: password for name, _role, password in DEMO_ACCOUNTS}


def send(base: str, method: str, path: str, body: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.status, res.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--as", dest="who", choices=sorted(PASSWORDS), help="sign in as this demo account first")
    p.add_argument("--base", default="http://127.0.0.1:8000", help="where the app runs")
    p.add_argument("--json", help='a JSON body, e.g. \'{"title": "Quiz"}\'')
    p.add_argument("method", choices=["GET", "POST", "DELETE"])
    p.add_argument("path", help="for example /api/events")
    a = p.parse_args()

    token = None
    if a.who:
        status, text = send(a.base, "POST", "/api/login", {"name": a.who, "password": PASSWORDS[a.who]})
        if status != 200:
            print(f"sign-in as {a.who} failed: {status} {text}")
            return 1
        token = json.loads(text)["token"]

    print(f"> {a.method} {a.path}")
    print(f"> Authorization: Bearer {token[:6]}... ({a.who}'s token)" if token else "> (no token: a stranger)")
    status, text = send(a.base, a.method, a.path, json.loads(a.json) if a.json else None, token)
    print(f"< {status}")
    if text:
        try:
            print(json.dumps(json.loads(text), indent=2)[:4000])
        except ValueError:
            print(text[:4000])
    return 0 if status < 400 else 1


if __name__ == "__main__":
    sys.exit(main())
