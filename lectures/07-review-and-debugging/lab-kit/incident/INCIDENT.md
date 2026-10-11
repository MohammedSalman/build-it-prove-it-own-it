# Incident: confirmations stopped arriving

> Planted for Lab 7. The people are fictional; the code and the log lines are real output
> of the repository in `history.bundle`.

**Reported** Thursday 8 October 2026, 10:40, by Jo (door-volunteer lead), in the team
channel:

> Five people at the info desk this morning said they never got a booking confirmation.
> They all booked last night or this morning. The app told them "You're in!" and they
> are on the door list. Has something changed?

## What the team knows

- **Nothing is ever emailed.** "Sent" means "a row in the `outbox` table". The mailer that
  will drain the outbox in production does not exist yet.
- **Deploys.** `main` is deployed every evening at 18:00. The last deploy was Wednesday
  7 October, 18:00.
- **Last known good.** The tag `v0.2` marks the Monday 5 October deploy. That evening Priya
  booked a place by hand and saw the confirmation in the outbox. No one has checked by hand
  since.
- **The API.** Bookings still answer `201 Created`, and the people are really booked: the
  event counts went up.
- **The log.** For one of the affected bookings (request id `41e941e7`), this is the only
  line in the server log:

  ```
  INFO:     127.0.0.1:63121 - "POST /api/events/3/reservations HTTP/1.1" 201 Created
  ```

- **CI** is green on every commit of `main`.

## Your job

Find out why, with evidence, before anyone changes code:

1. Keep a hypothesis log (`../hypothesis-log.md`). Each experiment must be able to rule
   something out.
2. Find the commit that changed the behaviour, with `git bisect` and
   `check_confirmation.py` (in this folder).
3. Only then fix it, and add a test that would have caught it.

## The check

`check_confirmation.py` answers one question: after one booking through the API, is there
exactly one confirmation for that person in the outbox? Run it from the repository root:

```bash
python ../incident/check_confirmation.py
echo $?                    # PowerShell: $LASTEXITCODE
```

Exit code `0` means good, `1` means bad (the incident), `125` means "this revision cannot
be tested". These are the codes `git bisect run` understands.
