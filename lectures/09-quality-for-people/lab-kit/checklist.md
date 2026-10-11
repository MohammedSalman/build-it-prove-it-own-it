# Manual checks: can a person use this page?

`python -m pytest -q` says `9 passed` on this page, and it would say the same on a fixed
one. Backend tests send HTTP requests; they never press Tab, never listen to a screen reader,
never look at a colour and never wait for a spinner. **Green backend tests establish nothing
about focus, announcements, contrast or what a person believes happened.** The procedures
below are how you find out. Each one is done by a person, and you record what you observed,
not what you expected.

## Supported combinations

These are the combinations this course supports. The instructor rehearses the kit on them
before the lab; the exact words a screen reader speaks can still differ between versions, so
your own transcript is the evidence. Others may work; if you use one, say so in your findings.

| Check | Supported combination | Notes |
|---|---|---|
| Keyboard pass | **Chrome** (current version) or **Firefox** (version 127 or newer) on Windows, macOS or Linux | Safari is not a supported browser for the keyboard pass: by default its Tab key skips links and buttons (see the setup notes below) |
| Screen-reader pass on macOS | **VoiceOver with Safari** | VoiceOver is built into macOS |
| Screen-reader pass on Windows | **NVDA with Firefox** (NVDA with Chrome is also fine) | NVDA is free and open source: https://www.nvaccess.org/download |
| Contrast | Any supported browser's developer tools, plus `scripts/contrast.py` | The script is the ground truth for this lab |
| States under a slow connection | Chrome or Firefox, app started in slow mode | See `README.md`, "Slow payment day" |

On Linux, do the keyboard, contrast and states checks yourself and do the screen-reader pass
on a partner's Mac or Windows machine.

## Before you start: calibrate on a page you know works

Open the course chapter (`site/lectures/09-quality-for-people.html`) and press Tab a few
times. Focus should move through links and buttons, and you should see a ring around each
one. If Tab skips the links, **your setup is wrong, not the page**. Fix it before you judge
AfterHours:

- **macOS, Chrome:** Chrome settings → Appearance → turn on "Pressing Tab on a webpage
  highlights links, as well as form fields".
- **macOS, Firefox 127 or newer:** Tab reaches links and controls by default. If yours
  doesn't, search Firefox's settings for "tab key" and turn on "Use the tab key to move focus
  between form controls and links".
- **macOS, any app:** System Settings → Keyboard → turn on "Keyboard navigation" (lets Tab
  move between all controls, including in dialogs).
- **Safari (for the VoiceOver pass only):** Tab alone moves between fields; Option-Tab also
  reaches links and buttons. Safari settings → Advanced → "Press Tab to highlight each item on
  a webpage" swaps the two. VoiceOver's own keys (below) do not depend on this setting.

Start the app (`uvicorn app.main:app`) and open http://127.0.0.1:8000 in a fresh tab.

---

## C1 · Keyboard pass (Chrome or Firefox) · about 10 minutes

Put the mouse or trackpad out of reach. Use only Tab, Shift+Tab, Enter, Space and the arrow
keys.

1. Reload the page. Press **Tab** once. Write down where focus went and whether you can
   **see** where it is.
2. Keep pressing Tab. For every stop, write one line: what it is, and whether you can see it.
   Stop when focus leaves the page (it moves to the browser's own toolbar) or comes back to
   the start.
3. **Task:** reserve a place at *Board Game Night* for "Kim", keyboard only. Can you do it?
   If not, where exactly were you stuck?
4. If you did reserve: press **Tab once more** straight after the result appears. Where are
   you now: next to the event you just booked, or back at the top of the page?
5. Go backwards with Shift+Tab. Is the order the same in reverse?

**Record:** the list of stops; whether you finished the task; where focus was after the
result; any stop where you could not see focus.

## C2 · Screen-reader pass · about 15 minutes (work in pairs: one listens, one writes)

Turn the volume up, or use the visual transcript so your partner can write down the exact
words.

**VoiceOver + Safari (macOS)**
- Turn VoiceOver on or off: **Command-F5**. The VoiceOver modifier "VO" is **Control-Option**
  (or Caps Lock).
- Next or previous item: **VO-Right Arrow / VO-Left Arrow**. Activate (click) the item:
  **VO-Space**.
- The rotor, which lists things on the page by type: **VO-U**, then Left/Right Arrow to
  change list, Up/Down to pick an item.
- Transcript: the caption panel shows what VoiceOver is speaking. Turn it on in VoiceOver
  Utility (**VO-Fn-F8**) → Visuals → Panels and Menus → "Show caption panel".

**NVDA + Firefox (Windows)**
- The NVDA key is **Insert** (you can choose Caps Lock instead in NVDA's settings).
- Browse mode is where you read a page; focus mode is where you type. **NVDA+Space**
  switches between them.
- In browse mode: **H** jumps to the next heading, **F** to the next form field (NVDA counts
  edit boxes *and buttons* as form fields), **NVDA+F7** opens the Elements List.
- Transcript: open the NVDA menu (**NVDA+N**) → Tools → **Speech Viewer**.

**Procedure** (the same for both)
1. Reload the page with the screen reader running. Move to the name field. **Write down the
   exact words** you hear. Does it tell you what to type?
2. Find every control that reserves a place, using the rotor (VO-U) or F / NVDA+F7. How many
   are there, and what is each one called? Could you tell them apart without seeing the
   page?
3. Type a name, move to a Reserve control for an event with places left, and activate it.
   On the kit this is where step 2 bites: Reserve is not a control. Put the screen reader's
   cursor on the word "Reserve" and try its activate command (VO-Space; in NVDA's browse mode,
   Enter). If nothing happens, ask your partner to click it with the mouse while you leave the
   screen reader where it is. **Write down which way it was activated.** Then, **without
   moving**, wait five seconds. What did you hear, if anything, about the result?
4. Restart the app in slow mode and repeat step 3. What did you hear while you waited?
5. After you fix K1 in the lab (Reserve becomes a real button), repeat step 3 activating it
   from the keyboard, so that you test the announcement on its own.

**Record:** the exact words for each step, the combination and version you used.

## C3 · Contrast · about 10 minutes

For each of these: the event's time and venue line, the Reserve label, the hint text inside
the name field, any message the page shows, the name field's border, and the focus ring (if
there is one):

1. Right-click it → **Inspect**. In the Computed styles, copy `color` (for text) or
   `border-color` / `outline-color` (for edges and rings).
2. Copy the `background-color` of the thing behind it. If it says transparent, walk up to
   the first parent element that has a solid colour.
3. Run `python scripts/contrast.py "<colour>" "<background>"`.
4. Compare: normal text needs **4.5:1**. Large text (at least 18 pt, or 14 pt bold) and the
   visible edges of controls and focus indicators need **3:1**.

Alternatives: Firefox's Accessibility Inspector (DevTools → Accessibility → "Check for
issues" → Contrast), or the contrast section of Chrome's colour picker. If Chrome's picker
shows an APCA value instead of a ratio such as 4.50, use the script: this course uses the
WCAG 2.2 ratio.

**Record:** each pair of colours, the ratio, the threshold, pass or fail.

## C4 · States under a slow connection · about 10 minutes

1. Stop the app, delete `afterhours.db*`, and start it in slow mode (`README.md`).
2. Type "Maya". Press Reserve on the escape room (1 place left) **once**. For three seconds,
   watch the whole screen. Write down what changed near the button and anywhere else.
3. Reset (step 1). This time press Reserve, then again after about a second and a half, as
   an impatient person would. Write down every message you see, in order, and the last one.
4. Run `python scripts/who_booked.py --name Maya`. What does the database hold? Does it
   match what the last message told Maya?
5. Repeat step 3 on *Board Game Night*, which has plenty of room. What does
   `who_booked.py` show now?
6. (Chrome) In developer tools, open the Network panel and change "No throttling" to
   **Offline**. Press Reserve. What does the page say? Is it true? Is anything still
   spinning a minute later? Set it back to "No throttling".

**Record:** a two-column timeline, **what the screen said** and **what the database held**,
for steps 3 and 5.

---

## Findings table

One row per problem. "Found by" names the procedure and the exact combination (for example
"C1, Firefox 131 on Windows 11").

| # | What a person experiences | Where (file:line) | Found by | WCAG 2.2 criterion (if one applies) | Severity: blocks / misleads / slows | Fixed? Re-checked with |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |

Useful criteria: 1.3.1 Info and Relationships · 1.4.3 Contrast (Minimum) · 1.4.11 Non-text
Contrast · 2.1.1 Keyboard · 2.4.3 Focus Order · 2.4.7 Focus Visible · 3.3.1 Error
Identification · 3.3.2 Labels or Instructions · 4.1.2 Name, Role, Value · 4.1.3 Status
Messages. Not every problem maps to a criterion; a page can meet every criterion and still
mislead people. Write "none (usability)" when that is the honest answer.
