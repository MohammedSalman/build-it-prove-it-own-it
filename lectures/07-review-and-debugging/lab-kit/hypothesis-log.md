# Hypothesis log

Debugging as an experiment: write the hypothesis and its prediction **before** you run
anything. An experiment is useful only if at least one possible result would rule a
hypothesis out. The best experiment is **discriminating**: its result differs between the
hypotheses that are still alive.

## The symptom

- **Given** (starting conditions): ______________________________________________
- **When** (what you do): _______________________________________________________
- **Expected:** _______________________________________________________________
- **Actual:** _________________________________________________________________

## Hypotheses and experiments

| # | Hypothesis | If it is true, we will see… | Experiment (exact command) | Result | Verdict |
|---|---|---|---|---|---|
| H1 | | | | | ✗ ruled out · ✓ supported · ? |
| H2 | | | | | |
| H3 | | | | | |
| H4 | | | | | |
| H5 | | | | | |

## Narrowing

- Last known good revision: ________ · First known bad revision: ________
- Command used with `git bisect run`: ______________________________________
- First bad commit (full hash): ___________________________________________
- What that commit changed, in one sentence: _______________________________

## Conclusion

- Cause (the line that fails, and why): ____________________________________
- Why nobody noticed (what hid the failure): _______________________________
- Why CI stayed green: _____________________________________________________
- The fix, and the test that now fails without it: _________________________
