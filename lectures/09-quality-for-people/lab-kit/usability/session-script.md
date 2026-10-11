# Unaided usability session: script (homework, about 1.5 hours)

You run this with **another team**, on **your team's own AfterHours**. Their members are your
participants; you are theirs. "Unaided" means nobody helps the participant while they work.
The kit page is for practice only; the real session is on your product.

| Step | Who | Time |
|---|---|---|
| 1. Prepare: pick the flow, write three tasks, reset the data | your team | 20 min |
| 2. Run two sessions (two participants from the other team) | facilitator + observer from your team | 2 × 15 min |
| 3. Take part in the other team's two sessions | two of you as participants | 2 × 15 min (at the same time as step 2, or swapped) |
| 4. Debrief: combine notes, list problems, choose what to fix | your team | 20 min |

Roles for each session: one **facilitator** (the only person who talks to the participant),
one **observer** (silent, fills in `note-sheet.md`), one **participant** from the other team.

## 1. Prepare (20 min)

- [ ] Choose **one flow** people care about, such as booking a place, or checking in at the
      door.
- [ ] Write **three tasks** as goals with a reason, not steps. Each task says how the
      participant will know they are done. Example: *"The festival opens on Friday. You and
      your friend Lee want to go to Board Game Night together. Get a place for both of you,
      then tell me how you know you both have one."*
- [ ] Make one task meet a **slow moment**, if your product has one (for example start the
      app with a slow payment setting for task 2), so you see how people handle a wait.
- [ ] Reset the data to a known state, and have your equivalent of `who_booked.py` ready so
      you can compare what the participant believes with what the system holds.
- [ ] Use made-up names in the app. Write participants down as P1, P2; no real names in your
      notes.

## 2. The session (15 min each)

**Welcome (read it, roughly word for word, about 1 minute)**

> Thanks for helping. We are testing our app, not you: if something is hard, that's the app's
> fault and exactly what we need to find. I'll give you a few tasks. Please think aloud as you
> go: say what you're looking at, what you expect, and anything that surprises you. I won't
> be able to help or answer questions while you work, because we want to see what happens
> when we're not there; I'll answer everything at the end. You can stop at any time.
> [Observer's name] will take notes. We won't record your screen or voice unless you say yes.
> Is that OK?

**Think-aloud warm-up (30 seconds).** "To practise, tell me what you see on this page, out
loud." Do not correct them.

**Tasks (about 3 minutes each).** Hand over the task on a card, or read it once. Then stay
quiet. Start the observer's clock.

**While they work: what you may say**

| Say (neutral) | Never say (coaching) |
|---|---|
| "What are you thinking?" | "Try the button on the right." |
| "What do you expect to happen?" | "Is the Reserve button clear?" |
| "What are you looking for?" | "You did that right." / "Nearly!" |
| "Keep going as if I weren't here." | Anything that explains how the app works |
| (silence: count to ten before you speak) | Answering their question during the task |

If they ask you something, turn it back: "What would you do if I weren't here?" If they are
completely stuck for two minutes, say "Let's move on to the next task", and write down where
they stopped. That is a finding, not a failure.

**After each task:** "How do you know you're done?" and "Did anything surprise you?" Then
compare their answer with the system state (your `who_booked` equivalent) and note any gap.

**Closing (2 minutes):** "What was the hardest part?" · "If you could change one thing, what
would it be?" Now answer their questions, and thank them.

## 3. Debrief (20 min, your team)

1. Put both observers' notes side by side.
2. List every **problem** with its evidence: what was observed, how many participants met it
   (1 of 2, 2 of 2), and whether they finished the task.
3. Mark **belief gaps**: moments where the participant believed something the system did not
   hold (or the other way round). These are the most serious.
4. Rate each: **blocks** (could not finish), **misleads** (finished believing something
   false), **slows** (finished, with hesitation or detours).
5. Choose **one flow to fix**. Fix it, then check the fix with the same task (a teammate who
   has not seen the fix is a better participant than you).

Remember what two participants can tell you: the big problems in this flow, for people like
them. It cannot tell you the page works for keyboard or screen-reader users (use
`checklist.md` for that), or how often a problem happens across all users.

## Ethics, briefly

Participants are classmates. Nobody's grade depends on how well they do as a participant.
They may decline or stop at any time. Record audio or screen only with explicit permission,
and delete the recording after your debrief. Keep notes anonymous (P1, P2).
