# Task contract

Copy this card for every task you delegate, to an agent or to a teammate. Fill in every line.
A blank line is a decision you left to the agent.

```
Goal:      What must be true when this is done? One or two sentences, in terms of
           behaviour a user or a test can see.
Context:   What the agent needs to know that it cannot find by itself: the files that
           matter, the promise that must keep holding, decisions already made
           (link the scope agreement), what "done" looks like to the user.
Limits:    What it may and may not change (folders, schema, dependencies, tests).
           What it may run. What it must not touch at all.
Deliver:   What you get back: failing test first? the diff? test output? a list of
           the assumptions it made? what it did NOT do?
Stop:      When it is finished (a check that passes), when it is blocked (then: say
           what blocked you), and a hard limit (steps or time).
Cost cap:  Tokens or money for the run, AND your own checking budget: how long you
           will spend reviewing, and the size of change you will reject unread.
Owner:     The person accountable for accepting the result.
```

## Which lines are enforced?

For each line, write where it lives:

| Line | Only asked (prompt, AGENTS.md) | Enforced (config, sandbox, CI) | How |
|---|---|---|---|
| Limits: folders | | | e.g. `write_paths` in permissions.json |
| Limits: no network | | | |
| Stop: hard limit | | | e.g. `--max-steps` |
| Cost cap | | | e.g. `--cost-cap` |
| ... | | | |

A limit that exists only as text in the prompt is a request. Decide, for each one, whether
a request is good enough for what could go wrong.
