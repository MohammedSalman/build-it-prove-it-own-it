`v1/tickets.py` handles four operations:

- **Selling:** Creates a ticket for October 9, 10, or 11, 2026. It stores the holder and day, then generates a code such as `FRI-0006` using the ticket’s ID. Sales are allowed even after that day has passed.
- **Reading:** Looks up a ticket by ID and returns its ID, holder, day, and code. Missing tickets return HTTP 404.
- **Changing day:** Allows a change strictly before midnight at the start of the destination day. It preserves the ID, holder, and original code. The old day and previous scans do not prevent a change. Invalid days return 422; late changes return 409.
- **Scanning:** Requires an exact, known code. Normally, the ticket’s stored day must match the app clock’s date. Repeated scans are allowed. When `wristband_mode` is enabled, any known ticket is admitted regardless of date; unknown codes still return 404.

Added [tests/test_tickets_characterization.py](<scratch>) with **75 cases** covering response shapes, persistence, validation, errors, midnight boundaries, repeated scans, day changes, and flag behavior. No files under `v1/` changed.

Surprises: a Saturday ticket can retain a `FRI` code; used or expired tickets can move to future days; even a same-day “change” fails once that day begins.

Ran from the repository folder:

```text
<venv>/bin/python -m pytest -q -p no:cacheprovider
```

Output:

```text
........................................................................ [ 87%]
..........                                                               [100%]
82 passed in 0.67s
```