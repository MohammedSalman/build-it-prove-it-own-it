# Practical defences: format, rubric, and assessor budget

**Weight:** practical defences are 25% of the course mark (course plan §6). **What is
assessed:** "Explain a sampled code path unaided, predict a change's effect, then diagnose or
modify it (tools allowed after the unaided part)." **When:** in a separate slot after demo day,
never during the Week 14 swap or demo day. **Practice first:** Labs 4, 7 and 11 each had a
5-minute practice defence, and Lecture 14 has one more (the agent-off drill in section 3).

The question families are public (`question-bank.md`). Prepare all of them. That is the point:
by the time you can defend any path in your team's product, you can own it.

**What is fixed, and what is a local default.** The course plan (§6) fixes the weight (25%),
the three parts (explain unaided, predict unaided, then diagnose or modify with tools), practice
defences before graded ones, accommodations, and a targeted reassessment for a student who
cannot explain one component. It does not fix how the three parts are weighted, what score
triggers a reassessment, how many attempts there are, or how a reassessment's result is used.
This rubric proposes defaults for those four, marked **local default** below. Your instructor
confirms or changes them and publishes them before the first defence slot.

---

## 1. The format (15 minutes with the student)

| Minutes | Part | Tools | What happens |
|---:|---|---|---|
| 1 | Sample | none | The assessor draws two question families at random; you choose one. The assessor names the path in *your team's* product |
| 5 | **Explain** | **Unaided** | Your team's code is open on the screen at the frozen commit; you may scroll and point, and draw on paper. No notes, no agent, no search, no running anything. Walk the path, say where the decision is made and which promise it protects |
| 3 | **Predict** | **Unaided** | The assessor proposes a change. You say what will happen, why, which tests fail and which still pass, and what a user would notice |
| 6 | **Diagnose or modify** | **Tools allowed** | Now anything you normally use: editor, terminal, tests, docs, an agent. Make the change or find the cause, and show evidence that it is right. Say what each tool did for you |

The code on screen is your team's repository at the commit tagged `defence` when the
maintenance challenge closed. It may include code that a teammate, the receiving team or an
agent wrote. Code you did not type is fair game: you are one of its owners.

## 2. The rubric

Each part is scored 0 to 4. The total out of 12 is scaled to the 25% component
(mark = total ÷ 12 × 25). **Local default:** the three parts carry equal weight.

| Score | **Explain** (unaided) | **Predict** (unaided) | **Diagnose or modify** (tools allowed) |
|---|---|---|---|
| **4** | The whole path in order, with files and functions; where the decision is made and which promise it protects; the test that protects it; answers "why here and not there?" | The effect **and its mechanism**; which tests fail and which still pass; what a user would see; how you would check | Makes the change or finds the cause, with evidence: a test that fails before and passes after, or an experiment that tells two causes apart. Checks that the other promises still hold. Says what the tools did and what you verified yourself |
| **3** | Complete path with small gaps; decision place right; the test named or quickly found | Effect and mechanism right; tests partly | Change works and is checked, but the check is incomplete or does not quite test the requirement |
| **2** | Main steps right, but read line by line from the screen without saying why; misses where the decision or the transaction is | Effect right, mechanism vague; or effect wrong with sound, stated reasoning | Change made but not checked, or checked with a check that cannot fail |
| **1** | Fragments; wrong about where the decision is made | A guess with no reasoning | Accepts a tool's output without checking it |
| **0** | Cannot explain the path | No prediction | Nothing to show |

Notes for assessors:

- **Reasoning over luck.** A wrong prediction with a clear, stated mechanism scores higher
  than a right guess without one. If the student then finds the mistake in the tools part and
  explains it, credit that under *Diagnose or modify*. The course plan says it: a failed
  experiment can earn strong marks when the reasoning and evidence are sound.
- **"I don't know" is honest, not zero.** "I don't know what happens after the COMMIT, but I
  would find out by reading `db.py` or running the concurrency test" shows ownership. Bluffing
  does not.
- **Never graded:** how the student uses an agent in the tools part (only whether they check
  its work), lines of code, commit counts, prompt length, chat logs.
- **Hidden checks only test published requirements.** Predictions and modifications are about
  behaviour the team's own documents or the course's published examples define.

## 3. Reassessment

The course plan provides a targeted reassessment for a student who cannot explain one
component. **Local defaults**, to be confirmed and published before the first defence: a score
of **0 or 1 on Explain** counts as "could not explain"; the student gets **one** reassessment
on the same question family with a different path or a different change (Explain and Predict
only, 10 minutes with the student), within a window your instructor publishes; its Explain and
Predict scores replace the first attempt's, and *Diagnose or modify* stands.

## 4. Accommodations

Follow the student's approved adjustments from your institution. The format absorbs these
without changing what is assessed:

- **Extra time** on each part, in proportion (for example 7.5 / 4.5 / 9 minutes at +50%).
- **Written instead of spoken** Explain and Predict, under the same "unaided" rules, followed
  by two minutes of spoken follow-up questions.
- **The student's own set-up** for the screen: magnification, screen reader, keyboard layout,
  font size.
- **A break** between the unaided part and the tools part.
- **Remote** over screen share, with the camera on during the unaided part only.

## 5. Assessor-minutes budget per student

| Item | Assessor minutes | Why |
|---|---:|---|
| Changeover and sampling | 2 | Previous student leaves, next one settles, two families drawn |
| Explain (unaided) | 5 | |
| Predict (unaided) | 3 | |
| Diagnose or modify | 6 | The assessor watches and asks "how do you know?" |
| Marking notes | 3 | Scores plus one line of evidence per part, written straight away |
| Live total | 19 | |
| **Booked slot** | **20** | One minute of slack: 3 students per assessor-hour |
| Moderation | +2 | A second assessor sits in on about 10% of defences (20 minutes each), spread across assessors |
| Reassessment reserve | +1.2 | Plan for about 10% of students needing one, at about 12 assessor-minutes each |
| **Planning figure** | **23.2, call it 23 per student** | 20 + 2 + 1.2 |

**Worked examples** (planning figure 23 minutes, 20-minute slots):

| Students | Assessor-hours | With 3 assessors | With 4 assessors | With 6 assessors |
|---:|---:|---:|---:|---:|
| 40 | 15.3 | 5.1 h each | 3.8 h each | 2.6 h each |
| 100 | 38.3 | 12.8 h each | 9.6 h each | 6.4 h each |
| 200 | 76.7 | 25.6 h each | 19.2 h each | 12.8 h each |

Formula: `assessor-hours = students × 23 / 60`. Add a 10-minute break for the assessor after
every six slots (two hours).

**If that is too much:** run *Diagnose or modify* as a supervised 10-minute task in a
separate room (one invigilator for many students, tools allowed), and have the assessor spend
2 minutes checking its evidence afterwards. The assessor's live time falls to 14 minutes per
student (changeover 2, Explain 5, Predict 3, evidence check 2, notes 2), booked as 15-minute
slots; with the same moderation and reassessment allowances the planning figure is about 18
(15 + 2 + 1.2), plus the invigilator's time. The three parts stay as the course plan describes them;
the tools part is simply watched by an invigilator instead of the assessor.

## 6. Assessor procedure

**Before the slots**
1. When the maintenance challenge closes, each team tags its repository: `git tag defence`
   and `git push origin defence`. That commit is what students defend.
2. Prepare the draws: a d12 (or a random-number list made by someone else), and the
   question bank. For each team, note which files hold each family's path (the team's
   `AGENTS.md` map and module map help).
3. Check each defence machine: the team's repository at the `defence` tag, tests pass, an
   editor with a large font, no notes open. Agents are available but closed during the
   unaided part.

**In the slot** (use a visible timer)
1. Draw two families; the student chooses one. Say the path and the change aloud.
2. Explain (5 min), Predict (3 min): listen; ask at most two short questions ("where is that
   decided?", "which test would fail?"). Do not teach.
3. Diagnose or modify (6 min): tools on. Ask "how do you know?" at least once.
4. Student leaves. Write the three scores and one line of evidence for each.

**After the session**
- List students who need a reassessment; offer times within the published window.
- Moderation: compare scores with the second assessor where they sat in; agree any change
  and note why.
