# V4 transient feedback repair

Isolated A+B candidate, built for review on 28 October 2026. This replaces the earlier proposed interruption/latch design. It adds no action guards, snippet termination, action replay, automatic model calls, or helper-timeout patch. The original V3 notebook and its 23 cell sources remain unchanged.

## Artifacts and build

- [Candidate notebook](../../local_output/transient_feedback_v4/candidate.ipynb): built, **not executed**; ignored by Git.
- [Builder](build.py), [overlay](patch.py), [bounded history module](history.py).
- [Exact V3-to-V4 source diff](source-diff.patch), [artifact/hash manifest](artifact-manifest.json).
- [CPU results](cpu-validation.json), [regressions](../../tests/test_transient_feedback_v4.py), [dispatch fixture](../../tests/franzen_v4_fixture.py).

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m interventions.transient_feedback_v4.build
```

The builder refuses to overwrite any candidate/companion file. Rebuilding for comparison requires a fresh `--output local_output/transient_feedback_v4/<name>.ipynb`. Identical inputs and flags produce identical notebook bytes. No notebook cells are run by this command. The emitted overlay installs after the V3 release patch and setup cell, before bundle imports.

Two independent switches default to off in the overlay implementation:

| Switch | Effect |
| --- | --- |
| `ARC3_V4_TRANSIENT_FEEDBACK` | A: clarify executed, unchanged endpoints that have transient animation. |
| `ARC3_V4_ANIMATION_HISTORY` | B: capture bounded records and expose historical retrieval/guidance. |

The combined artifact sets **both to `1`** and explicitly sets `ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT=0`. The helper-timeout overlay is never installed. Build a control artifact with `--feedback 0 --history 0`; either A or B can also be selected independently. Set switches before a game starts; changing them during a game is outside the supported evaluation configuration.

The installer validates all three complete V3 source hashes and every replacement anchor, and compiles all outputs before writing to a fresh bundle. Drift or an existing V4 utility module fails installation. It changes only `framework/solver.py`, `agent/tool_agent.py`, `agent/python_tool_sandbox.py`, and adds `utils/animation_history_v4.py` in that candidate bundle. The source diff was applied to a fresh V3 tree and all four outputs matched byte for byte.

## A: feedback

An executed action with `gameplay_changed=False` and positive `animation.transient_pixels` is described as:

```text
ENDPOINT UNCHANGED (executed; intermediate animation: 7 frames, 256 transient pixels)
```

This uses the existing frame/pixel metadata. `_action_verdict`, the agent's fallback trace and the existing batch-stop explanation agree. Terminal verdicts keep precedence. Ordinary no-ops keep their wording. `no_op`, `gameplay_changed`, progress/reward flags, batch stopping, stale-state guards, action counts and execution order keep their V3 meanings.

## B: retrieval by action ID

Each `_execute_action` captures the existing raw chain **before** later actions can overwrite it. Only animations with transient pixels are retained, including those with a persistent endpoint change. Each record has a random session namespace plus a monotonic record/action number, its action display and level. The ID is returned as `animation_id` on that action result and stored in the corresponding transition result. Earlier batch members can be found through the bounded listing.

The model receives concise guidance in the existing animation section of its system prompt. Its Python can inspect an earlier action in the same snippet or a later snippet:

```python
first = action([{'action': 'MOUSE', 'row': 55, 'col': 37}])
earlier_id = first.get('animation_id')
action([{'action': 'MOUSE', 'row': 20, 'col': 20}])

records = animation_history()['records']
if earlier_id is not None:
    observation = animation_frames(earlier_id)
    if 'error' not in observation:
        print(observation['truncated'], observation['frame_indices'])
        print(observation['frames'][0].ascii)  # FrameView: also supports segmentation
        print(animation_timeline(earlier_id)['timeline'])
```

`animation_history()` returns metadata only. `animation_frames(id)` returns metadata plus `frames: list[FrameView]`; `animation_timeline(id)` returns metadata plus the existing diff-timeline format. Missing/expired/cross-game IDs return an explicit error dictionary, never the latest animation. Queries travel over the existing sandbox `animation` message and the existing `step_env(query='animation')` callback, with a historical-query discriminator and ID. They execute no gameplay and spend no action budget. No new message type or model request is introduced.

`last_animation_frames` and `last_animation_timeline` keep their exact previous target, lazy invalidation and return shapes. Their existing timeline-disable switch still works. Historical timelines belong to opt-in B and remain available independently of that last-animation guidance switch.

## Bounds, clearing and memory

- At most **4 records**, each at most **16 post-action frames plus its pre-action board**.
- Each frame must fit **64×64**, with integer ARC colors 0–15. Unsupported grids retain explicit truncation metadata and no frame data.
- Each encoded record is capped at **256 KiB**; aggregate encoded storage is capped at **1 MiB per live game session**. Oldest records are evicted first. Storage consists of detached JSON bytes, not references to full raw chains.
- Long animations are uniformly sampled, including both endpoints. `original_frames`, `retained_frames`, `frame_indices`, `truncated` and `truncation_reason` disclose omissions. Timeline steps map back to original indices and include `from_frame_index`; a gap compares sampled boards, not every intervening transition.
- An executed RESET, death, level completion/change or run completion clears history. A new game has a separate namespace/store. Boundary-crossing animations are not retained in history. Existing last-animation handling, including fatal-animation preservation through automatic RESET, is unchanged.

The dense CPU probe retained **812,712 encoded bytes** across four records; traced additional Python peak was **4,109,269 bytes** while storing/querying 101-frame inputs. This excludes the baseline raw chain, native allocations and model memory. Object overhead and decoded/frame/timeline responses add bounded temporary allocations beyond the encoded-byte cap. Retained encoded payload is at most 100 MiB for 100 live game sessions, or 120 MiB for 120; it is not limited to the number of active inference streams.

The V3 single last-animation chain and its memory behavior remain unchanged to preserve compatibility. These bounds apply to the **additional history**, not all baseline memory. Sampling can omit decisive frames. Callers can also keep returned objects in the sandbox, subject to its existing process limits.

## CPU verification and remaining risks

**39 tests passed:** 24 V4 regressions plus all 15 unchanged helper-timeout regressions. The path exercised is actual `_dispatch_tool → _run_python_tool → sandbox subprocess → step_env → _execute_action → history query → FrameView/timeline → tool result`, with synthetic TAAF/file/display adapters. The emitted notebook overlay itself was applied to a fresh source fixture.

Real offline replays recovered TN36 p0 action 5 after action 6 (**7 frames / 256 transient pixels**) and SC25 p3 action 36 after action 38 (**5 frames / 36 transient pixels**). All **44** replayed post-action boards matched their archived events. Local `arc-agi` is 0.9.9 versus archived 0.9.8; exact historical intermediate-frame identity is not established.

With both switches disabled, tested tool payloads, executed actions, retained helpers, summaries, progress flags and rendered system prompts matched V3 exactly. Baseline notebook parity and archived smoke hashes also passed the existing verifier. This is CPU behavioral equivalence over the regression cases, not an exhaustive proof or a mounted Kaggle-bundle import.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_transient_feedback_v4.py' -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_helper_timeout.py' -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python baselines/franzen_m2_v3/verify.py
```

Checks require the existing ignored source caches; real-game prefixes additionally require local offline environments and `downloads/results.zip`. The complete solver cache came from the [pinned Franzen commit](https://github.com/da-fr/arc-agi-3-solution/blob/10882e332d883af3e61616df8c8a17d03a328a75/ARC3-Inference/inference/framework/solver.py); every V3 notebook patch post-image and Git blob `e40976c69db03c39b0b3c3a3295813a58efcb7c8` matched. Tests fail on missing/drifted inputs and download nothing. CLI tests still emit existing unclosed-pipe `ResourceWarning` messages; their supervisor was not changed.

Remaining pre-submission risks: the model may ignore the retrieval guidance, overinterpret sampled timelines, or spend extra reasoning on unhelpful animation. Additional CPU work and prompt text have not been timed on Kaggle. Full package import, model behavior, score changes and unseen-game generalization remain untested. The prior latch-based screen should not be reused without adapting its mechanism criteria to voluntary historical retrieval. Stop at review; no GPU evaluation or submission has been run or authorized by these artifacts.
