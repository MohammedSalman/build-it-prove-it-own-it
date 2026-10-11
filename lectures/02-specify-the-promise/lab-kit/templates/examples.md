# Acceptance examples: <feature name>

Copy to `docs/examples.md`. Each example is one decision, with people and numbers. Each one
names the check that proves it: an automated test, or written steps a person follows.

## 1. <short name of the decision>

- **Given** <the starting situation: who, which event, how many places, who is waiting>
- **When** <one action>
- **Then** <what the person sees and what the system now holds>
- **Check:** `tests/test_….py::test_…`

## 2. …

## 4. Usability: <short name>

A usability criterion says what a real person can do, how fast or how easily, and how you
will find out.

- **Given** <a person who has never used the app, on a phone>
- **When** <they are asked to do one task, with no help>
- **Then** <they finish it within N seconds / without a wrong turn / and can say the result>
- **Check:** <how many people, who runs the session, the pass mark (e.g. 3 of 3)>

## 5. Accessibility: <short name>

An accessibility criterion names the people and the assistive technology, and ties to a
WCAG 2.2 success criterion where one fits.

- **Given** <a screen reader user (VoiceOver or NVDA) / a keyboard-only user / zoom at 200%>
- **When** <they do the task>
- **Then** <what they hear or can reach, and that nothing disappears before they read it>
- **WCAG 2.2:** <number and name, e.g. 4.1.3 Status Messages>
- **Check:** <steps, which tool, pass mark>
