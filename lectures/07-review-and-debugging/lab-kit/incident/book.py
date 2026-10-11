"""Book a place (or join a waitlist) on a running AfterHours app, and show what came back.

Prints the HTTP status, the X-Request-ID header (search the server log for it) and the
JSON body. The same command works in bash, zsh and PowerShell.

Usage (with the app running in another terminal):
    python ../incident/book.py                          # Maya books Board Game Night (event 3)
    python ../incident/book.py --event 4 --name Lee --email lee@example.org --waitlist
    python ../incident/book.py --url http://127.0.0.1:8001

Only the Python standard library is used.
"""

import argparse
import json
import urllib.error
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--event", type=int, default=3, help="event id (3 = Board Game Night)")
    parser.add_argument("--name", default="Maya")
    parser.add_argument("--email", default="maya@example.org")
    parser.add_argument("--waitlist", action="store_true", help="join the waitlist instead")
    args = parser.parse_args()

    path = "waitlist" if args.waitlist else "reservations"
    url = f"{args.url.rstrip('/')}/api/events/{args.event}/{path}"
    body = json.dumps({"attendee": args.name, "email": args.email}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            status, headers, payload = res.status, res.headers, res.read()
    except urllib.error.HTTPError as err:
        status, headers, payload = err.code, err.headers, err.read()
    except urllib.error.URLError as err:
        raise SystemExit(f"Could not reach {args.url}: {err.reason}. Is the app running?")

    print(f"POST {url}")
    print(f"HTTP {status}")
    print(f"X-Request-ID: {headers.get('X-Request-ID', '(none)')}")
    print(payload.decode(errors="replace") or "(empty body)")


if __name__ == "__main__":
    main()
