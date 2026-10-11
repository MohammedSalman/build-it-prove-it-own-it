# Saved agent output: an accessibility audit by reading (Lecture 9, section 3; Lab 9, Part A)

**What this is.** The real, unedited answer of a coding agent given the task contract below
on a throwaway copy of the Week 9 lab kit (the kit only: no answer key, no solutions). Use it
in class when a live run is slow or unavailable, and in the lab to compare against your own
manual findings. Only change: the long scratch path of the copy is shortened to `<kit>`.

- Agent: Codex CLI 0.154.0-alpha.6.2, model gpt-6-astra (reasoning effort high), 2026-09-27
- Permissions actually enforced: a sandbox that allowed file reads and writes inside the copy
  and blocked opening network ports. The agent looked for a browser and found none, so it
  could not load the page in one. What it calls VERIFIED was run against a stub of the page
  in Node.js, not in a browser; it says so itself.
- The contract said "do not modify any file". The agent complied (verified afterwards:
  `git status` and `git diff` in the copy were empty). As in Lecture 1, the no-edit rule was
  only requested; the port block was enforced.
- The page it audited is byte-for-byte the kit's `app/static/index.html`. The copy's
  `AGENTS.md` was the Week 1 version: the kit's UI rule ("pytest does not check the page…")
  was added after this run.

## The task contract

```
Goal:     Find the usability and accessibility problems in AfterHours' web page
          (app/static/index.html) that would stop or mislead a real person reserving a place:
          a keyboard-only user, a screen-reader user, someone with low vision, or anyone on a
          slow connection.
Context:  Small FastAPI + SQLite app. Read AGENTS.md first. The backend tests pass; that is
          not in question. The page talks to POST /api/events/{id}/reservations, which can
          take several seconds when the payment provider is slow.
Limits:   Investigate only. Do NOT modify any file. You may read files and run commands.
Deliver:  For each problem: what a person would experience, where (file:line), the WCAG 2.2
          success criterion if one applies, and a manual check a person could do to confirm it.
          Mark every claim as VERIFIED (you ran or measured something, say what) or INFERRED
          (from reading only). Compute any contrast ratios you mention, and show the numbers.
          Finish with what you could NOT check, and why.
Stop:     When you have covered the page, or if blocked (say what blocked you).
```

## What we checked afterwards (instructor summary; the answer itself follows unedited)

| The agent's finding | Maps to | Our check | Status |
|---|---|---|---|
| 1 Reserve is a `<div>`; keyboard cannot reach or activate it | K1 (planted) | Keyboard pass in Chrome: the only Tab stop is the name field | verified by us |
| 2 `outline: none` removes the focus indicator | K3 (planted) | Keyboard pass; computed `outline-style: none` on focus | verified by us |
| 3 No persistent label; placeholder may act as a fallback name | K2 (planted) | Chrome's accessibility tree: name "e.g. Maya Chen", taken from the placeholder | verified by us |
| 4 Contrast 2.6565:1 and 2.1477:1 | K4 (planted) | Same numbers from our script and from the browser's computed colours | verified by us |
| 5 No status semantics for loading, results, errors | K5 (planted), part of K6 | Accessibility tree: no live region on the page | verified by us (announcements need a person) |
| 6 Messages vanish after about 3.5 s; cites 2.2.1 Timing Adjustable | real, not planted | The toast does hide after 3.5 s. Whether 2.2.1 is the right criterion is debatable | the behaviour: verified; the criterion: needs checking |
| 7 Double click sends two POSTs; success then "just filled up"; spinner stops early | K6 (planted) | Real browser, 3 s payment delay: two POSTs, #228 then 409; spinner hidden while request 2 still running | verified by us |
| 8 Programme load failure leaves an unexplained page | real, not planted | Blocked `/api/events`: no message, no retry | verified by us |
| 9 A too-long name gets "Something went wrong. Please try again." | real, not planted | Read `main.py` (max 80) and the page's catch-all message | verified by reading |
| 10 A lost response still says "Please try again" | real, not planted (the unknown state) | Killed the server mid-request: the page said "Please try again" | verified by us |
| 11 Dates show weekday and time, no calendar date | real, not planted | True for this page | verified (minor) |
| (not found) Focus falls to the page after a reservation | K7 (inherited from Week 1) | Hidden while Reserve is a `<div>`; appears once K1 is fixed | the agent could not see it |

Two lessons for students: the agent found every planted problem and several real ones by
reading, which is genuinely useful; and it could not see what a person sees or hears, which it
said plainly. Its "verified" meant "ran against a stub", which is weaker than it sounds.

## The agent's answer (verbatim)

Found **11 problems**, including a keyboard blocker and misleading reservation feedback. No files were modified.

**VERIFIED** means measured contrast or executed the page’s unchanged JavaScript using `node -` with an in-memory DOM stub and simulated network responses. It does **not** mean browser-tested. **INFERRED** means source inspection only.

All page locations below refer to [app/static/index.html](<kit>/app/static/index.html).

1. **INFERRED — Keyboard users cannot activate Reserve.**  
   **Where:** `app/static/index.html:128–137`.  
   Reserve is a `<div>` with only a click listener: no native button semantics, tab stop, or keyboard handler. Screen-reader button navigation also cannot reliably discover it as a control.  
   **WCAG:** [2.1.1 Keyboard](https://www.w3.org/TR/WCAG22/#keyboard), [4.1.2 Name, Role, Value](https://www.w3.org/TR/WCAG22/#name-role-value).  
   **Manual check:** Enter a name, then use only Tab, Shift+Tab, Enter and Space to reach and activate Reserve. Also inspect a screen reader’s button list.

2. **INFERRED — Keyboard focus is visually suppressed.**  
   **Where:** `app/static/index.html:22`, `35–39`.  
   The universal `outline: none` rule removes the focus outline without supplying a replacement. A sighted keyboard user may not know when the name field is focused.  
   **WCAG:** [2.4.7 Focus Visible](https://www.w3.org/TR/WCAG22/#focus-visible).  
   **Manual check:** Tab into and out of the name field and compare its appearance; check whether focus is visibly distinguishable.

3. **INFERRED — The name field lacks a persistent, explicit label.**  
   **Where:** `app/static/index.html:78–80`, `143–146`.  
   “e.g. Maya Chen” is the only prompt and disappears after typing. The page does not initially explain that a name is required. Some browser/screen-reader combinations may expose the placeholder as a fallback name, so this is **not** a verified claim that the input is completely unnamed.  
   **WCAG:** [3.3.2 Labels or Instructions](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html).  
   **Manual check:** Enter a name, leave the field, then return. Check whether its purpose and required status remain clear visually and through a screen reader.

4. **VERIFIED — Essential text has insufficient contrast.**  
   **Where:** `app/static/index.html:10–16`, `39`, `46`, `54`.  
   People with low vision may struggle to read the date, venue, name example and Reserve text. Calculated using `python3 -B -` and the source’s solid CSS colors:

   | Text | Foreground / background | Relative luminances | Contrast |
   |---|---|---|---|
   | Date and venue | `#625b8a` / `#1f1a3d` | 0.119138 / 0.013670 | **2.6565:1** |
   | Name placeholder | `#625b8a` / `#1f1a3d` | 0.119138 / 0.013670 | **2.6565:1** |
   | Reserve | `#ffffff` / `#f59e0b` | 1.000000 / 0.438904 | **2.1477:1** |

   Calculation: linearize sRGB channels, compute `L = 0.2126R + 0.7152G + 0.0722B`, then `(Llighter + 0.05) / (Ldarker + 0.05)`. These are ordinary-size text styles; the required ratio is **4.5:1**.  
   **WCAG:** [1.4.3 Contrast (Minimum)](https://www.w3.org/TR/WCAG22/#contrast-minimum).  
   **Manual check:** Inspect the computed foreground/background colors in browser developer tools and enter them into a contrast calculator.

5. **INFERRED — Loading, success and errors lack accessible announcements.**  
   **Where:** `app/static/index.html:74`, `84`, `97–106`, `145–165`.  
   The spinner is an empty `<i>` without a text alternative. The toast has no live-region/status semantics. A screen-reader user may hear nothing while waiting or when a reservation succeeds or fails. The blank-name branch moves focus to the input, but does not associate the error message with it.  
   **WCAG:** [4.1.3 Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html); [1.1.1 Non-text Content](https://www.w3.org/TR/WCAG22/#non-text-content) for the informative spinner.  
   **Manual check:** With a screen reader running, trigger delayed loading, blank-name validation, success and a sold-out response. Check whether each state is announced without manually searching the page.

6. **VERIFIED — Confirmation and errors disappear after about 3.5 seconds.**  
   **Where:** `app/static/index.html:97–102`, `158–165`.  
   Someone reading slowly or using magnification can miss the outcome or reservation number. Source inspection finds no persistent confirmation/history or timer controls.  
   **Evidence:** `node -` output: `TOAST: hidden after approximately 3509ms; no new user action`.  
   **WCAG:** [2.2.1 Timing Adjustable](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html). W3C specifically distinguishes temporary messages whose information remains available elsewhere; this page provides no such alternative.  
   **Manual check:** Complete a reservation, wait four seconds, then try to recover its number or extend the message’s display time.

7. **VERIFIED — Repeated clicks send concurrent reservations and can contradict an earlier success.**  
   **Where:** `app/static/index.html:137`, `142–168`.  
   During a slow response, Reserve remains unchanged and has no pending-request guard. A person can click again, then see “just filled up” after already seeing confirmation. The spinner can also stop while another request remains pending.  
   **Evidence:** `node -` produced:
   ```text
   DOUBLE CLICK: pending POSTs=2; button text=Reserve; busy visible=true
   FIRST RESPONSE, SECOND STILL PENDING: busy visible=false; message=You're in! Reservation #101 for Silent Disco on the Quad.
   SECOND RESPONSE: message=Sorry, that event just filled up.
   ```
   Additional places could be reserved if multiple requests succeed; that consequence was not exercised against the database.  
   **WCAG:** Usability/data-integrity issue; no standalone criterion asserted.  
   **Manual check:** In a disposable test session, delay POST responses and double-click Reserve. Count requests, then simulate a 201 followed by a 409 and watch the messages.

8. **VERIFIED — Event-loading failures leave an unexplained empty or stale page.**  
   **Where:** `app/static/index.html:109–114`, `168`, `171`.  
   `load()` has no error handling, HTTP-status check or guaranteed spinner cleanup. Failed initial loading leaves no events or recovery message; failed refreshes retain old availability and keep the spinner active.  
   **Evidence:** `node -` output:
   ```text
   INITIAL GET FAILURE: rejected=simulated offline; cards=0; busy visible=true; toast visible=false
   GET HTTP 500: rejected=events.map is not a function; old cards retained=1; busy visible=true
   ```
   A simulated successful reservation followed by failed refresh also left the spinner active.  
   **WCAG:** Usability issue; no standalone criterion asserted for the missing recovery flow.  
   **Manual check:** Block `/api/events` and reload. Separately, allow the initial load but block the refresh after a simulated reservation. Check for an explanation and retry control.

9. **VERIFIED — Invalid names receive an unhelpful “try again” message.**  
   **Where:** `app/static/index.html:79`, `143–155`, `161–165`; server limit at `app/main.py:33–34`.  
   The server limits names to 80 characters, but the page neither communicates/enforces that limit nor displays returned validation details. A person retrying the same long name cannot resolve the problem.  
   **Evidence:** With a simulated validation response, `node -` output: `81-CHARACTER NAME / MOCK 422: sent length=81; message=Something went wrong. Please try again.`  
   **WCAG:** [3.3.1 Error Identification](https://www.w3.org/TR/WCAG22/#error-identification), [3.3.3 Error Suggestion](https://www.w3.org/TR/WCAG22/#error-suggestion).  
   **Manual check:** Enter 81 characters and submit in a test session. Check whether the message identifies the name field and explains the limit.

10. **VERIFIED — A lost response is treated as permission to retry, although the outcome may be unknown.**  
    **Where:** `app/static/index.html:151–165`.  
    If the connection fails after the server accepts a reservation, “Please try again” can lead someone to reserve again. The page offers no way to check their existing reservation. The actual server-commit/lost-response scenario remains inferred.  
    **Evidence:** A rejected POST in `node -` produced: `POST RESPONSE LOST: message=Something went wrong. Please try again.`  
    **WCAG:** Usability issue; no standalone criterion asserted.  
    **Manual check:** With a disposable backend and proxy, let a reservation commit but drop its response. Compare the page’s advice with the saved reservation before retrying.

11. **VERIFIED — Event dates omit the calendar date.**  
    **Where:** `app/static/index.html:92–94`, `130`.  
    A person sees weekday and time, but cannot establish which week the festival takes place from the page. Events a week apart can appear identical.  
    **Evidence:** `node -` output:
    ```text
    DATE DISPLAY: 2026-10-09T20:00 -> Fri 08:00 PM; 2026-10-16T20:00 -> Fri 08:00 PM
    ```
    **WCAG:** Usability issue; no standalone criterion asserted.  
    **Manual check:** Without consulting the API or source, try to determine the event’s day, month and year.

**VERIFIED — Repository checks:** `git status --short`, `git diff --exit-code`, and `git diff --cached --exit-code` returned no output and exit code 0. Backend tests were not rerun.

**What I could not check:** Browser discovery returned `No browser is available`, then `[]`. Consequently, I could not verify actual keyboard behavior, accessibility-tree names, screen-reader speech, rendered focus indicators, zoom/reflow, text-spacing changes, forced colors, or toast overlap. Network checks used simulations, not a running payment flow; I did not start the app or submit real reservations because those operations can write database files. The entire page source was covered, but this is not a browser-based WCAG conformance assessment.
