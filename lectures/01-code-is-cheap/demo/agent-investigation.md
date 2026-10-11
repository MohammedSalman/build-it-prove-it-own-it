# Saved agent output — the bounded investigation (Lecture 1, section 4)

**What this is.** The real, unedited answer of a coding agent given the task contract below
on a throwaway copy of the AfterHours starter. Use it in class when a live run is slow or
unavailable. Only change: the long scratch path of the Python environment is shortened to
`<venv>`.

- Agent: Codex CLI 0.154.0-alpha, model gpt-6-astra, 2026-09-27
- Permissions actually enforced: a sandbox that allowed file reads and writes inside the copy
  and **blocked opening network ports**. That block is why the agent could not run the app.
- The contract also said "do not modify any file". The agent complied (verified by diffing
  the copy afterwards). Note the difference: the port block was enforced; the no-edit rule
  was only requested.

## The task contract

```
Goal:     Find out whether AfterHours can confirm more reservations for an event than its
          capacity, and why.
Context:  Small FastAPI + SQLite app. Read AGENTS.md first. The promise:
          confirmed reservations for an event <= its capacity.
Limits:   Investigate only. Do NOT modify any file. You may read files and run tests/scripts.
Deliver:  1. The code path of one reservation request, with file:line references.
          2. Every assumption that path makes (timing, users, database, network).
          3. Whether the promise can break, how, and your evidence. Say which claims you
             verified by running something and which you inferred from reading.
          4. The smallest repair you'd suggest (not applied), and what it would NOT fix.
Stop:     When you have evidence for 3, or if blocked (say what blocked you).
```

## The agent's answer (verbatim)

1. **Reservation request path**

- Browser trims the attendee name and POSTs JSON: `app/static/index.html:122–133`.
- FastAPI validates the attendee length (1–80 characters) and integer event ID, then calls the reservation function: `app/main.py:33–34,96–99`.
- `app/reservations.py:23–34` opens a connection, reads capacity, counts reservations, and rejects an already-full event.
- `app/reservations.py:36` calls simulated payment authorization, which normally sleeps 0.3 seconds: `app/payments.py:20–26`.
- `app/reservations.py:39–45` inserts the reservation, returns its ID, and closes the connection.
- The route returns HTTP 201, or maps missing/full events to 404/409: `app/main.py:96–103`. The browser displays confirmation: `app/static/index.html:134–136`.

2. **Assumptions and missing guarantees — inferred from reading**

- **Timing:** The count must remain valid until insertion. Nothing prevents another request from checking or inserting during that interval. Payment delay enlarges the window; it is not required for the race.
- **Users:** A supplied name is sufficient; there is no authentication, attendee uniqueness, or idempotency key. Repeated clicks and retries represent new reservations. The browser leaves the button enabled while the request runs.
- **Database:** Requests must reach the intended shared database, with initialized schema and valid capacity. Every reservation row counts as confirmed; there is no status column. The code relies on event existence and capacity remaining valid between reads and insertion.
- **Atomicity:** Connections use autocommit (`app/db.py:30–39`). Separate statements do not form one protected check-and-insert operation. Foreign keys enforce event existence, but the schema has no aggregate capacity constraint (`app/schema.sql:9–14`).
- **Failures/network:** Database operations and payment authorization are expected to succeed; the route only handles missing/full events. Payment currently has no network operation and charges nothing. HTTP confirmation can be lost after insertion; retrying can create another reservation. Browser fetch failures have no recovery handler.

3. **Can the promise break? Yes, by code analysis; reproduction was blocked.**

With capacity 1 and count 0:

```text
A reads 0 → passes → waits in payment
B reads 0 → passes → waits in payment
A inserts and commits → returns 201
B inserts and commits → returns 201
Result: 2 confirmed reservations, capacity 1
```

SQLite can serialize the individual inserts without rechecking either request’s earlier count.

**Executed command:**

```sh
PYTHONDONTWRITEBYTECODE=1 AFTERHOURS_DB=/tmp/afterhours-investigation.db AFTERHOURS_CLASSROOM_GATE=0 AFTERHOURS_PAYMENT_DELAY=0.3 <venv>/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Relevant output:

```text
Application startup complete.
ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 8765): operation not permitted
Application shutdown complete.
```

**Verified by execution:** application startup completed, but this environment prohibited listening on localhost. **Inferred from source:** the overselling interleaving above. I stopped at that blocker as requested; I did not run the race script or tests. No repository files were modified.

4. **Smallest suggested repair — not applied**

Start `BEGIN IMMEDIATE` before reading capacity/count; keep the check and insert inside that transaction; explicitly commit before returning success and roll back on failure. Preserve the separate connection per request. No schema change is needed.

This would serialize cooperating reservation writers. It would **not** fix duplicate submissions, lost-response retries, payment/database coordination, existing overselling, or writes bypassing this transaction protocol. Holding SQLite’s writer lock during payment also increases contention; lock timeouts would still need handling.