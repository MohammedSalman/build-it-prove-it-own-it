# AfterHours 1.5.0 · Event categories

Pull request #31, "Add event categories and a filter to the events page", merged Friday
9 October 2026 at 17:40.

- Every event has a category: games, music, film, maker or other.
- `GET /api/events?category=games` returns only that category.
- The events page has filter buttons (All, Games, Music, Film, Maker).
- `POST /api/events` accepts an optional `category` (default `other`).
- Schema: `events` gains a `category` column (see `app/schema.sql`).

Tests: `python -m pytest -q` in this folder, 12 passed. CI green.
