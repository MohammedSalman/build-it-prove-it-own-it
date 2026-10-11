# AfterHours 1.5.1 · Event categories, done safely

The fix after the 1.5.0 incident (see the kit README). Same feature, two changes:

- **The schema change works on a database with history.** On start-up the app adds the
  `category` column if it is missing (`app/db.py`, `_add_category_column_if_missing`).
  Adding a column with a default is backward compatible, so rolling back to 1.4.0 still
  works afterwards.
- **The feature ships dark, behind a flag.** Categories appear in the API and on the page
  only when `"event_categories": true` in the environment's flag file
  (`flags/staging.json`, `flags/production.json`). The app re-reads the file on every
  request, so the flag takes effect without a deploy, and turns off just as fast.

New test: `test_a_database_created_by_1_4_keeps_working` starts this release on a copy of
the 1.4.0 schema, the situation 1.5.0 was never tested in.

Tests: `python -m pytest -q` in this folder, 15 passed.
