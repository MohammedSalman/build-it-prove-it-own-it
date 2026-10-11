# AfterHours 1.4.0

The release running in staging and production at the start of festival week.

- Everything from Week 1, including Patch B (the last place goes to one person).
- `GET /healthz` answers `{"status": "ok", "release": ..., "pid": ...}` when the process is
  up and can open its database. The deploy script's `live` gate calls it.
- The events page shows a message instead of a blank page when the programme cannot load.

Tests: `python -m pytest -q` in this folder, 9 passed.
