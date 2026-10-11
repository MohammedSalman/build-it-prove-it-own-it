# Frozen copy of Week 3's mini-agent

| | |
|---|---|
| **Copied from** | `lectures/03-inside-the-agent/solutions/mini-agent/` (Week 3's finished reference solution) |
| **Copied on** | 2026-09-27 |
| **Changed since** | nothing: all 18 files below are byte-for-byte the Week 3 files |

Week 8 does not edit Week 3's agent. It uses the agent exactly as Week 3 left it and adds
files beside it. `README.md` in this folder is Week 3's own documentation of the interface
this week depends on (tool registry, single dispatcher, permission file, blocked-call log,
`--extra-tools`, recording format). It is the solution README from Week 3, so it calls
itself "instructor only"; in Week 8 the whole agent is handed out on purpose.

## Check that the copy is still frozen

```
python check_frozen.py
```

It recomputes the SHA-256 of every file in the table below and prints `ok` or `CHANGED`.

## The frozen files (SHA-256)

```
a8d04065c225dcd06604296cb4822e6128b404c39d6d8527120665cc0d78d625  .gitignore
5722bb46286bdce9cb6d14517ab5f418f84e8bf4cf2c731552f26bdac1acb6cb  README.md
de9ab941f16a5c115622a3d2b1289f3645f88cd890017c4c5222ed972a3ee694  agent.py
900a806a86c4b47c1ede770f1c95c20499e0ca4b71a84781a2c883a7283a75d7  models.py
72271c7206436a1eb4c9c1cde7bedd84f52cc02172030cf9ac218d339e34e2fb  permissions-readonly.json
d3088b572cffc9c46ac04cc6ee0d88e495d3701711d1a76d3159dcb92cfa889a  permissions.json
3e927fc158484844de24799b020f3411e1cffa1274c6d5c0f364e54f9fdb1f97  permissions.py
900ad5ede42030e383e74fc5276d43bf10c5c256bfbd9066dc52675fe533240b  pytest.ini
8b2d753c920639bc8b1c985d6aeedff8b9d27ce4855a4c513dd9439089434857  recordings/add-name-check.json
82146fdcd4560a6a3b33c7fbcf4ce4a41afda3807e3678506502a601ec58abbb  recordings/code-freeze.json
e5411fd3f365109dd92c7daac165c13385f5d0a7233d3ff3c15b4ff44f40b9a0  recordings/runaway.json
b52f2567cfa11a80c90e707295c6c1c23ffd67a43cccabd9d1651113e41b926c  tests/conftest.py
a3466792c4a615a59e1622af3af810b414b55a76bd6f044535628590f4c06333  tests/test_live_adapter.py
b826627954ff9479cf4f0889dc5b51d2d84d5ecf81063b997e41e81b0361ef6b  tests/test_permissions.py
0b479eb6b704ab014b9e5af53843452b98b1250560aae56de4651c47ce7e8d32  tests/test_replay.py
459271dfbca82b38637cc77591a70ac82c6ad4ce62e241c730632644947efb71  tests/test_stopping.py
8dd83843c056792dfa8012cd5886eb60a63433e688543f5afa59da561b6fb636  tests/test_write_file.py
84aecb63b391be3c09696c7b491c57718d61b7f061635fedb61c10ffab726f8d  tools.py
```

## Week 8 additions (new files; none of them changes a frozen file)

| File | What it is |
|---|---|
| `FROZEN-COPY.md`, `check_frozen.py` | This note and its check |
| `http_stub.py` | The `http_post` tool, loaded with `--extra-tools http_stub`. It opens no connection; it writes each call to `logs/outbound.jsonl`. `python http_stub.py` counts them |
| `permissions-organiser.json` | The kit's too-broad rules file (allows `http_post`, can read `exports/`) |
| `recordings/poisoned-submission.json` | An authored recording: a "model" that obeys an instruction hidden in an event submission |
| `tests/test_injection.py` | Week 8's tests: every request goes through `dispatch()`; what each rules file lets out |
| `conftest.py` | Skips two Week 3 tests that replay Week 3 recordings against Week 3's app (reasons below) |

## Two Week 3 tests are skipped here, and why

The agent looks for its project at `../afterhours`. In Week 3 that was the Week 1 app; in
this kit it is the Week 8 app with sign-in. Two of Week 3's own tests replay Week 3
recordings that only fit Week 3's app:

- `test_replay.py::test_the_add_name_check_replay_finishes_and_its_claims_hold`: the
  recording overwrites `app/main.py` with Week 3's version and expects Week 3's 10 tests.
- `test_stopping.py::test_the_runaway_recording_is_stopped_by_the_step_limit`: the
  recording reads the app's files; the Week 8 files are bigger, so the run reaches the
  60,000-token cap before step 12 and stops with `cost_cap` instead of `max_steps`.

`conftest.py` marks exactly these two as skipped and prints the reason (`pytest -rs`).
Both still pass, with the other 33, when the frozen copy runs in Week 3's own layout
(`lectures/08-security/verification.md` shows the run).
