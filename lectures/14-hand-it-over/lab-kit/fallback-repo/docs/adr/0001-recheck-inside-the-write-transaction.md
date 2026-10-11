# 0001. Re-check the capacity inside the write transaction, after payment

**Status:** accepted (Week 1). **Owner:** the team's release steward at the time.

## Context

`reserve()` counts the reservations, asks the payment provider to authorise (about 300 ms
in this app, simulated), then saves. In the first version the count was checked only
before payment. Two people pressing Reserve for the last place within those 300 ms both saw
room and both were saved: `scripts/race.py` oversold the event in 10 of 10 trials, while all
7 tests of the time passed, because every test sent one request at a time.

SQLite allows one writer at a time for the whole database file. `BEGIN IMMEDIATE` takes that
write lock at once; other writers wait for it (here up to 5 seconds, then fail).

## Decision

Keep the first count as a quick early answer ("full" without making anyone pay). After
payment, open `BEGIN IMMEDIATE`, count again, and insert only if there is still room, then
`COMMIT`. The decision and the write happen together, under the write lock, and the lock is
held for about a millisecond.

The promise it protects, **confirmed reservations ≤ capacity**, is tested with two people
held at the payment step together (`tests/test_concurrency.py`), so the dangerous order
happens on every run.

## Alternatives we rejected

- **Disable the Reserve button while a request is in flight** (the page only). It stops one
  person double-clicking in one browser. Two people on two phones never touch each other's
  button: `race.py` still oversold 10 of 10.
- **Take the write lock before the first check and hold it through payment.** Correct for
  capacity (`race.py` kept the promise 10 of 10), but every booking for every event then
  queues behind each payment. With 20 people booking 20 different events at once, 3 got
  HTTP 500 and the slowest waited 5.3 s, against 0.35 s for this decision (`scripts/rush.py`,
  one laptop, Week 1; your numbers will differ, the pattern should not).

## Consequences

- Good: the promise holds under concurrency; unrelated bookings do not wait for each other's
  payments.
- The person who loses the last place has had a payment authorised that nothing releases
  (known risk KR-3).
- The same person can still hold two places (two tabs, or a retried request): nothing makes a
  reservation unique (KR-1).
- If a request ever waits more than 5 seconds for the write lock, the user gets HTTP 500
  instead of a clear message (KR-4).
