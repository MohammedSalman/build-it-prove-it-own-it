`v1/tickets.py` handles four operations:

- **Selling:** Accepts October 9–11, 2026, stores the holder and day, and creates a unique code such as `FRI-0006`. Purchases remain allowed after the ticket’s day has passed.
- **Reading:** Returns the ticket’s ID, holder, day, and code. Missing tickets return 404.
- **Changing day:** Allows a change strictly before midnight on the destination day. It preserves the ID, holder, and original code. Invalid dates return 422; late changes return 409.
- **Gate scanning:** Looks up the exact code and normally admits only on the stored ticket day. Repeat scans are allowed. Unknown codes return 404; wrong-day scans return 409. When `wristband_mode` is enabled, any known ticket is admitted regardless of date.

Added 80 cases in [tests/test_tickets_characterization.py](tests/test_tickets_characterization.py), covering response shapes, persistence, validation, errors, midnight boundaries, code stability, repeat scans, and feature flags. No files under `v1/` changed.

The main surprise: written requirement T3 says **both days must still be ahead**, but the code checks only the destination. Even a previously scanned ticket can move forward and admit again. The tests preserve that current behavior.

Ran from the repository folder:

```text
<venv>/bin/python -m pytest -q -p no:cacheprovider
```

Output:

```text
........................................................................ [ 82%]
...............                                                          [100%]
87 passed in 0.76s
```