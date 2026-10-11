# Review checklist

Work through it top to bottom. It is ordered by **risk**, not by file. Write each finding
as:

> **file:line** · what you see · why it matters · what you ask the author to do

A finding you cannot point at (a line, a command, a test) is a **question**. Write it as
one: "What happens to the confirmation if this raises?"

## 0 · Before you read any code (about 5 minutes)

- [ ] **Claims.** List what the description says the change does. Each claim is something
      to check, not something to believe.
- [ ] **Evidence.** What did the author run? Can you run it too? A green CI run only says
      the tests that still exist passed.
- [ ] **Size and scope.** `git diff --stat BASE HEAD`. Does every file serve the stated
      purpose? If the change has several purposes, ask for it to be split.
- [ ] **Tests first.** Which tests were added, changed or **deleted**?
      `git diff --stat BASE HEAD -- tests/` and
      `git diff --diff-filter=D --name-only BASE HEAD`.
      For every deleted test: what did it check, and what checks that now?
      For every new test: does it run the real path, or only a helper next to it?

## 1 · Read the risky hunks first

1. **Promises and data.** Anything that touches an invariant (capacity; one confirmation
   per booking), a transaction boundary, or the schema. What moved into or out of a
   transaction?
2. **Errors.** Every `try`/`except`: what is caught, what happens next, and **who finds
   out**? `except Exception:` followed by `pass`, or by a log line below the level the app
   logs at, is a finding.
3. **Defaults.** Every changed default value: timeouts, log levels, flags, limits. Who
   relied on the old value? Was the change mentioned in the description?
4. **Secrets.** Tokens, passwords, keys and URLs with credentials in code, tests or
   configuration, **including as default values**. A secret that reached git history must
   be revoked, not just deleted.
5. **Calls into libraries.** Does every function called exist in the pinned version? Did
   anyone run this line? Check in seconds, for example for `json.loads`:
   `python -c "import json; print(hasattr(json, 'loads'))"`
6. **Work per request.** Queries inside loops, lists with no limit. Ask for a measurement
   before you call it slow or fine.
7. **Observability.** If this fails in production, which log line or number tells you?
   Is that line logged at a level that will actually be shown?
8. **Everything else** (UI, docs, formatting) last. Check that the docs claim only what
   the code does.

## 2 · Decide

- [ ] **Approve**, **approve with comments**, or **request changes**. Name the findings
      that block the merge.
- [ ] Treat an AI reviewer's comments as extra findings to check. They are a signal, not
      the approval. A person approves, and that person owns the approval.
- [ ] An approval says what you checked and on what evidence ("read the transaction and
      error hunks; ran the tests and the check"). A bare "LGTM" says neither.
