# Recordings

Replay mode plays these files back instead of calling a model. Every file says where its
contents came from in its `provenance` and `about` fields.

| File | Provenance | What it holds |
|---|---|---|
| `v1.json` | authored | 20 cases × 3 runs for config `v1` (the demo version) |
| `v2.json` | authored | 20 cases × 3 runs for config `v2`, plus the 4 extra cases × 3 runs (task A3) |
| `v2-small.json` | authored | 20 cases × 3 runs for config `v2-small` |
| `judge-v2.json` | authored | a model judge's verdicts (J1, J2) on run 1 of `v2` |

**Authored** means the course team wrote every reply by hand, in the shape of a concierge
answer, to show what an eval can catch. They are not model output, and a score computed from
them says nothing about any real model. Some defects are planted on purpose; the lecture and
the instructor notes list them.

Each row stores:

- `prompt_sha256`: the fingerprint of the exact prompt the concierge builds for that question,
  time and programme. Replay finds a reply by this fingerprint, so a changed prompt finds
  nothing.
- `usage`: token counts **estimated** as characters ÷ 4 of the prompt and the reply. A real
  tokenizer gives different numbers, and different models count the same text differently.
  Thinking tokens, which a large model would also bill as output, are not included.
- `latency_ms`: **authored** with a formula (a base time plus a time per output token, times a
  seeded random factor that gives about one answer in twelve a slow tail). It is not a
  measurement of anything. The formula is in each file's `about` field.

A file you record yourself with `evals.py --live --record FILE` has provenance `live recording`,
token counts from the API's `usage` field, and latency measured on your machine.
