# Practical defences: question bank

Twelve question families, one per thing every team's AfterHours has by Week 14 (the product
checklist). In the defence the assessor rolls a d12 twice and you choose one of the two
families. The assessor then names the **path in your team's product** and the **change** to
predict; the prompts below are the templates they adapt. Format and rubric: `rubric.md`.

This bank is public on purpose. Prepare every family on your own product: for each one, find
the files, trace the path out loud without notes, and try one prediction for real. Practise in
pairs, the way Labs 4, 7 and 11 did. Tip: most answers start from a promise and a test.
Ask "what must stay true here, and which test would notice if it did not?"

Each family lists what the assessor **listens for**. It is a guide to a strong answer, not a
script to recite.

---

### 1 · The reservation path (Weeks 1, 6)
- **Explain:** Follow one press of Reserve from the page to the database row and back. Where
  is the capacity decided? Where does the transaction start and end?
- **Predict:** Someone removes the second capacity check ("we already checked"). Two people
  press Reserve for the last place at the same moment. What happens, and which tests notice?
- **Diagnose or modify:** Add a test for three people and two places left, or make the
  refusal message name the event.
- **Listen for:** check-then-act; the decision and the write under one lock or transaction;
  the concurrency test forcing both people past the first check; sequential tests still
  passing without the second check.

### 2 · Retries and idempotency (Week 6)
- **Explain:** A phone sends the same reservation twice with the same idempotency key. Follow
  both requests. Where is the stored answer, and when is it written?
- **Predict:** The same key arrives with a different payload (another event). What should
  happen, what does your code do, and which test says so?
- **Diagnose or modify:** Add or fix the test for the concurrent same-key case.
- **Listen for:** key scope; answer and reservation stored in one transaction; the unique rule
  on active reservations; "no answer" is not "nothing happened".

### 3 · Time rules and the clock (Weeks 4, 5)
- **Explain:** How does your product decide whether a cancellation (or a door check-in) is
  still allowed? Where does "now" come from?
- **Predict:** The organisers change the window (for example 24 hours to 48). Which files
  change, and which tests fail before you update them?
- **Diagnose or modify:** Make that change, with a boundary test one second either side.
- **Listen for:** the rule in one module; the injectable clock; end-exclusive boundaries;
  expected values taken from the written rule, not the code.

### 4 · Who may do what (Week 8)
- **Explain:** What stops Maya cancelling Sam's reservation? Where is the caller identified,
  and where is ownership checked?
- **Predict:** The ownership check is removed from one endpoint. Which test fails, and what
  could a stranger now do?
- **Diagnose or modify:** Add an adversarial test for another endpoint that changes data.
- **Listen for:** authentication is not authorisation; the check on the server, never the
  client; tests written from the attacker's side.

### 5 · The page and its states (Week 9)
- **Explain:** What does a person see, hear (with a screen reader) and where is focus, from
  pressing Reserve to the answer? Include the case where no answer comes back.
- **Predict:** The server takes five seconds to answer. What does the page show at 0.1 s, 2 s
  and 5 s, and what happens if the person presses again?
- **Diagnose or modify:** Improve one state's message or focus handling, and re-check it with
  the keyboard.
- **Listen for:** system state and user belief; a live region for results; the button's own
  immediate change; honest messages about unknown outcomes.

### 6 · An integration contract (Week 10)
- **Explain:** Pick the shared decision your contract fixes (for example how start times are
  stored and shown). Who produces it, who consumes it, and which test checks each side?
- **Predict:** The producer changes the format without telling anyone. What breaks, and when
  would CI notice?
- **Diagnose or modify:** Extend the contract test with an awkward example.
- **Listen for:** both sides tested against the same written contract; CI on the merged
  result; time zones fixed explicitly.

### 7 · Performance (Week 11)
- **Explain:** Which query serves your budgeted page, and how does the database find the
  rows? Use `EXPLAIN QUERY PLAN` words.
- **Predict:** The index is dropped, or the festival grows ten times. What do you expect for the
  median and for p95? State your assumptions (query mix, load, what else is waiting), and say
  how you would measure it.
- **Diagnose or modify:** Measure it, or add a check that the query plan uses the index.
- **Listen for:** measured, not assumed; percentiles; the budget and its method; one machine is
  one observation. Both percentiles can move together; an answer that says which way it expects
  them to move, and why, and how it would check, is strong whatever it predicts.

### 8 · Release and recovery (Week 12)
- **Explain:** How does a new version go out, and how would you roll it back? How is a backup
  restored and how do you know the restored data is right?
- **Predict:** The health check fails five minutes after a release. What happens next,
  step by step, and what data could be lost?
- **Diagnose or modify:** Run the restore check on a copy, or add an application-level check.
- **Listen for:** the runbook's actual steps; rollback versus roll forward; RPO and RTO in
  plain words; checks of meaning (every reservation has an event; confirmed ≤ capacity).

### 9 · A schema change (Week 13)
- **Explain:** Walk through your expand → migrate → contract change. Which version of the app
  runs during each step, and what does each one read and write?
- **Predict:** Someone runs the contract step while the old version is still running. What
  fails, and for whom?
- **Diagnose or modify:** Write the verification query for one step, or add a test that both
  versions work against the expanded schema.
- **Listen for:** writes from both versions surviving; contract only after the old version is
  retired; comparing meaning, not checksums.

### 10 · Request ids and logs (Week 7)
- **Explain:** How does a request id reach every log line of one booking, and how would you use
  it to follow an incident?
- **Predict:** An exception is raised in the confirmation step. What does the person see, and
  what does the log show?
- **Diagnose or modify:** Add the missing log line or the test that proves the id is present.
- **Listen for:** where evidence disappears (swallowed exceptions, log levels); the id in the
  response header; no personal data in logs that do not need it.

### 11 · The code the other team wrote (Week 14)
- **Explain:** The receiving team's drop-in pull request on your product (merged or not). How
  is a reservation for a drop-in event refused, and what happens to an existing database when
  the new version starts?
- **Predict:** You roll the code back to the version before their change, on a database the
  new version has already started on. What still works, and what do people now see?
- **Diagnose or modify:** Add the test their pull request is missing, or fix one thing their
  handover feedback raised.
- **Listen for:** ownership of code you did not type; the refusal before payment; migrations
  and rollback safety; their decision record.

### 12 · A test and its oracle (Week 5)
- **Explain:** Pick one requirement-derived test. Where does its expected value come from,
  and what would it catch that a test written from the code would not?
- **Predict:** A named mutant (for example `<` becomes `<=` in a boundary). Is it caught or
  does it survive, and by which test?
- **Diagnose or modify:** Write a test that kills a surviving mutant from your
  `docs/quality.md`.
- **Listen for:** an independent source of truth; boundary values; what a surviving mutant
  means; never weakening a test to go green.

---

## If a family does not fit your product

Every family matches an item of the product checklist, so each should exist in every team's
product by Week 14. If one truly does not (for example your festival has no cancellation, so
family 3 uses the door check-in instead), your team tells the instructor **before** the defence
slots, and the assessor adapts or redraws. Families 1, 4 and 12 always apply.
