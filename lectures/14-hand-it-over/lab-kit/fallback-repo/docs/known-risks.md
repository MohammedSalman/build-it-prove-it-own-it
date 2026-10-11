# Known risks

What is not done, or not safe, in this version. Each risk says who it hurts, how we know, what
limits it today, and what would fix it. Nothing here is hidden elsewhere: if you find a risk
that is not on this list, add it.

Checked on the handover date against this version of the code. "Verified" means we ran the
check shown; "by reading" means we read the code and did not run anything.

| ID | Risk | Who it hurts | How we know | What limits it today | What would fix it |
|---|---|---|---|---|---|
| KR-1 | One person can hold two places at the same event (two tabs, or a retried request after a lost response) | Everyone else who wanted that place | Verified: two `POST /api/events/3/reservations` with `{"attendee": "Maya"}` both answer 201 and add two reservations | Nothing | An idempotency key per reservation attempt, and a uniqueness rule on active reservations (course Week 6) |
| KR-2 | There are no accounts: anyone can reserve under any name, and anyone can create events with `POST /api/events` | Attendees whose names are used; organisers | Verified: `POST /api/events` answers 201 with no login | Only reachable on the machine or network where you run it | Authentication, and an ownership check on every change (course Week 8) |
| KR-3 | The person who loses the last place has had a payment authorised that nothing releases | That person | By reading `app/reservations.py`: the second check raises `SoldOut` after `payments.authorize` | Payments are simulated; nothing is charged | Release the hold when the second check fails (course Week 6) |
| KR-4 | A request that waits more than 5 s for SQLite's write lock fails with HTTP 500 instead of a clear message | Whoever is booking at that moment | By reading `app/db.py` (`busy_timeout` 5000 ms); ADR 0001 explains why the lock is held only about 1 ms | Writes are short | Catch the lock timeout and answer 503 with "try again"; measure under load (course Weeks 11, 12) |
| KR-5 | Attendee names are personal data, and they are kept everywhere: in every log line of a reservation, in the database with no deletion date, and in every backup | Attendees | Verified by reading: four `log.info("[%s] …", attendee, …)` calls in `app/reservations.py` | Logs go to the terminal only | Log the reservation number instead of the name; delete reservations a set time after the festival, and say how long in the privacy notice |
| KR-6 | After a reservation, the page rebuilds every event card, so keyboard focus is thrown away; the result message disappears after 3.5 s | Keyboard and screen-reader users | By reading `app/static/index.html` (`replaceChildren` and a 3500 ms timer). The course's Week 9 saw the same focus loss in a browser on its copy of this page | None | Update the card in place; keep the result on the card (course Week 9) |
| KR-7 | `starts_at` is free text. `POST /api/events` accepts `"tomorrow-ish"`, and such an event sorts after every real date | Anyone reading the programme | Verified: answered 201 and listed last | Nothing in the code: anyone who can reach the app can create events (KR-2) | Validate ISO 8601 in `NewEvent` and add a test |
| KR-8 | No licence has been chosen for this repository's own code | Anyone who wants to reuse it | This file | Used only inside the course | The course team chooses a licence and adds a `LICENSE` file |
| KR-9 | Only the four direct dependencies are pinned in `requirements.txt`. The other 17 packages (see `docs/licences.md`) are resolved when you install, so a fresh install months from now can get newer versions that behave differently | Whoever sets up a fresh copy | By reading `requirements.txt`; `scripts/licences.py` lists the 21 installed packages | CI installs fresh on every push, so a break shows up there first | Record the full set with `pip freeze > constraints.txt` and install with `pip install -r requirements.txt -c constraints.txt` |

## Not risks, but worth knowing

- Payments are a simulation (`app/payments.py` sleeps about 0.3 s). Nothing is ever charged.
- The seed data is made up. `guest-001` … are not people.
- `scripts/race.py` and `scripts/rush.py` need the app running; the tests do not.
