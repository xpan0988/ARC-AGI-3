# Stage 2: active exploration and memory baselines

## Findings

**Legal filtering improved exploration efficiency, but the memory heuristic did
not improve game-solving performance in this experiment. No policy won a game.**
The control reached one level in three runs; legal random and memory each did
so in two runs. With only three policy seeds and sparse successes, these counts
do not establish a general ranking of solving ability.

Primary results: 25 games × 3 seeds per policy, 256 actions per run.
The final evidence set is `local_output/experiments/stage2-dljbgqqk/`.
All 450 runs completed successfully: 115,200 actions including verification
repeats. All 225 repeated game/policy/seed pairs matched their full normalized
traces, with zero mismatches. Only the first 57,600 actions contribute to the
primary results below.

| Policy | Runs won | Distinct games won | Sum of per-run maximum levels | Games with any progress | Actions | Repeated observations | Unchanged observations | Mean unique observations/run | Runtime, seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A: original | 0/75 | 0/25 | 3 | 1/25 | 19,200 | 43.15% | 36.32% | 146.53 | 63.90 |
| B: legal | 0/75 | 0/25 | 2 | 1/25 | 19,200 | 28.35% | 17.34% | 184.41 | 76.02 |
| C: memory | 0/75 | 0/25 | 2 | 2/25 | 19,200 | 30.38% | 19.35% | 179.24 | 127.89 |

Every primary run used its entire budget. Unique counts include the initial
observation (maximum 257). Level totals sum maxima across runs/seeds, not
distinct solved levels. Repeats used for determinism do not enter this table.
Runtime is instrumented local loop time, not end-to-end experiment duration.

The [per-game comparison](stage2-comparison.md) lists every game's policy
breakdown and seed-specific level counts. [Per-run CSV](stage2-results.csv)
retains every seed and replicate, additional diagnostics, exact trace names,
and normalized trace digests. The [manifest](stage2-manifest.json) pins the
versions, seeds, budgets, and source hashes for this result.

## Actual progress evidence

Only R11L and SP80 had any level-count increase. The following are all seven
primary-run events; all were `NOT_FINISHED` after the transition, not WIN.
Each increased the public level count from 0 to 1. No run exceeded one level.

| Game | Policy | Seed | One-based action number | JSONL step |
|---|---|---:|---:|---:|
| r11l-495a7899 | memory | 0 | 181 | 180 |
| sp80-589a99af | original | 0 | 150 | 149 |
| sp80-589a99af | original | 1 | 122 | 121 |
| sp80-589a99af | original | 2 | 133 | 132 |
| sp80-589a99af | legal | 1 | 198 | 197 |
| sp80-589a99af | legal | 2 | 79 | 78 |
| sp80-589a99af | memory | 1 | 4 | 3 |

The R11L event executed ACTION6 with `{x: 20, y: 33}` and returned 23 frames.
Its final-grid difference was 1,456 cells, but the evidence of progress is the
public `levels_completed: 0 → 1`, not those pixels. The transition was extracted
and its animation rendered using the unchanged Stage 1 schema. Trace location:
`local_output/experiments/stage2-dljbgqqk/r11l-495a7899_memory_seed0_rep0.jsonl.gz`.
The 23 image comparisons are in the adjacent `progress-r11l-images/` directory;
the extracted single-record source is `progress-r11l.jsonl`.

## Failure analysis and recommendation

1. **Filtering removes wasted actions, not the need to understand a task.**
   The control issued 8,095 unadvertised non-RESET actions out of 19,200.
   Legal and memory issued zero. Legal filtering reduced unchanged observations
   by 18.98 percentage points and repeated observations by 14.80 points, but
   produced no extra wins or aggregate level completions.
2. **Novelty is a weak surrogate for progress.** Original LF52 seed 2 visited
   257 unique observations in 256 actions while completing zero levels. Legal
   TR87 seeds 0 and 2 each visited 256; memory TR87 seed 2 also visited 256,
   again without a level. These are observable distinctions, not evidence of
   approaching a solution. Pixel-based identities cannot tell useful motion
   from counters, animation, or irrelevant changes.
3. **This memory design did not beat legal random.** It had more repeated and
   unchanged observations, fewer unique observations, the same aggregate level
   count, and roughly 1.68× the instrumented runtime. Its isolated R11L success
   is real, but its SP80 success was less frequent than the control's. That is
   insufficient evidence to promote this heuristic as a better solver.
4. **State identity and action abstraction are limited.** Raw final grids can
   fragment semantically similar states or alias hidden states. Coordinate bins
   can conflate clicks with different effects. Short-cycle/no-effect penalties
   can discourage useful repetition and delayed effects; the random branch
   mitigates but does not solve that problem. No goal or action semantics are
   inferred. These are design limitations, not diagnoses from hidden game code.
5. **More activity also produced more deaths.** Death transitions were 136,
   190, and 200 for original, legal, and memory respectively; explicit resets
   were 135, 189, and 200 (a final-action death can exhaust the budget before a
   reset). Final-grid repeated rates were 48.11%, 34.15%, and 35.08%, preserving
   the same ranking as full-stack fingerprints. Multi-frame responses numbered
   3,093, 4,938, and 5,071; they were recorded rather than silently discarded.

**Recommendation:** stop tuning this model-free heuristic for now. Keep original
as the historical control and use legal random as the stronger exploration
baseline for the next experiment. A bounded perception/reasoning-agent pilot is
more informative than adding increasingly specific novelty bonuses: test whether
interpreting visible structure and action effects increases actual level
completion under a fixed action/runtime budget. An LLM is a candidate for that
next stage, not a demonstrated solution or a dependency introduced here.
Retain paired seeds, full transition evidence, and the no-model controls.

This experiment does not show that all model-free approaches fail. It tests
these three fixed policies on 25 public versions, three policy seeds, one
environment seed, and a short action budget. More seeds, a different state
representation, longer horizons, or a reasoning model could change the result;
none was tested. Public-game performance is not hidden-game/Kaggle qualification.

## Scope and fixed experimental design

This is a bounded exploration experiment, not a game-solving architecture.
Policy parameters were fixed before the full comparison. No LLM, pretrained
model, additional service, or new dependency was used. Game implementations
were not inspected for strategies; the official wrapper downloaded/loaded
the public games for execution, and analysis used public observations only.

The experiment uses all 25 versioned games in the public catalog fetched on
2026-10-26, policy seeds 0, 1, and 2, and an exact budget of 256 agent actions
per game-policy-seed run (or earlier WIN). The public environment seed and
NumPy's process-global RNG seed are both fixed at 0 before each run.
There are 225 primary runs, each repeated once for determinism: 450 runs in
total. The repeats are verification, not additional independent samples.

The unchanged vendor loop uses `counter <= MAX_ACTIONS`. The evaluator sets
`MAX_ACTIONS = 255` for all three policies to obtain exactly 256 actions. This
is a common experimental budget override; default `play_local.py` and the
notebook retain their existing 80-action cap/inclusive-loop behavior. No
policy receives a larger budget. Policy order rotates between seeds and
replicates to reduce systematic warm-cache timing bias.

## Implementation and memory design

All policy classes and runtime helpers are in `agent/my_agent.py`, the only
source file embedded by the notebook builder. `MyAgent` remains the original
control; its class body was checked against repository HEAD by AST equality.
Selection is explicit through `--policy original|legal|memory`, or
`POLICY=...` for `make play-local` and `make notebook`. The default is original.
For a non-default notebook, the builder appends a small class named `MyAgent`
inheriting the selected implementation. There are no imports of local scripts
or additional runtime files in the notebook agent.

| Policy | Decision rule |
|---|---|
| A: original | Existing starter, including its pre-existing LS20 ACTION4 weighting; samples all non-RESET enum actions, even if unadvertised. |
| B: legal | Uniform choice among advertised, known, non-RESET actions; uniform 0–63 coordinates for ACTION6. |
| C: memory | Advertised actions, under-tested state/action preference, per-progress-count action evidence, short-cycle penalties, and 10% legal-random exploration. |

Legal and memory policies reset on NOT_PLAYED/GAME_OVER or an empty usable
action set. The inherited loop stops on WIN. RESET is a recovery command and
need not appear in the advertised action list. No new game-ID-specific branch
was introduced. The control's existing LS20 branch was deliberately preserved.

Memory belongs to one agent/game instance. It contains:

- Visit counts for observation keys; action/outcome counts keyed by
  `(observation, action bucket)`; and fallback counts keyed by the public
  `levels_completed` value and action bucket. The progress count is not
  assumed to be a public current-level index.
- A 12-transition recent-state/action window for detecting returns and repeated
  state/action cycles. A known recent state/action pair receives a penalty.
- A transition ledger containing source/destination keys, the exact action and
  parameters, unchanged-response and unchanged-endpoint flags, cycle flags,
  response frame count, reset/death state, and actual level-count delta.
- Episode markers. Death, RESET, full reset, or changed level count clears the
  recent cycle window; per-game visits and learned action evidence remain.
  Another game or seed run starts with a fresh memory instance.

Decision keys hash the final rendered grid, state, level count, win-level
count, and advertised actions. Intermediate frames do not create distinct
decision states solely because their animation histories differ. A separate
full-stack key records transient observable changes. GUID/reset-event flags
are not state identities. These hashes can alias different hidden states and
are never treated as a representation of the full environment state.

ACTION6 coverage uses 64 spatial bins (8×8 bins, each containing 8×8 pixels),
with uniform coordinates within the selected bin. Exact coordinates remain
in the ledger/traces; bin membership only shares action statistics. Simple
actions use their ID as their bucket. Ties are broken first by action family,
then by coordinate bin, so ACTION6 does not receive 64 tie-break tickets.
This generic spatial prior can still conflate productive and unproductive
clicks inside the same bin; it is not object recognition.

For a candidate, the fixed score is:

```
2 / sqrt(1 + state-action attempts)
+ 1 / sqrt(1 + progress-count/action attempts)
+ mean inverse visit count of observed destinations
- 2 * unchanged-endpoint count / (1 + evidence attempts)
- occurrences of this state/action pair in the recent window
```

Evidence uses state-local outcomes when available, otherwise the progress-count
fallback. The 10% random branch prevents permanent suppression of an action
whose useful effects may be delayed or context-dependent. Pixel change and
novel destinations are exploration evidence; only public level-count increases
and WIN are reported as actual progress. No reward is inferred from colors,
action labels, sprite motion, or the amount of changed pixels.

Memory updates inside `take_action` after the actual response, including the
last budget-limited action and WIN. The existing Stage 1 tracing wrapper stays
outside this hook and pairs the same outgoing request with the full response.
All returned animation frames are preserved. Instrumentation was not rewritten;
the visualizer only gained optional gzip input support.

## Metrics and reproducibility

Metrics are computed from the saved Stage 1 traces, not from the policy's own
memory counters. Every game/seed/policy has a separate row and trace.

- **Wins:** observed WIN, with both successful runs and distinct games reported.
- **Levels:** maximum public `levels_completed` in a run. Maxima avoid hiding
  progress after full resets or double-counting a re-solved level. Aggregate
  sums across seeds do not mean distinct levels; final counts are also saved.
- **Actions:** actual trace records, including RESET. Initial environment setup
  reset is outside the agent budget, consistently with Stage 1.
- **Repeated-state frequency:** fraction of post-action observations whose
  Stage 1 fingerprint was seen earlier in that run, including the initial
  observation. Unique observation counts also include that initial observation.
  The primary fingerprint includes the entire frame stack plus state/progress/
  available actions. Final-grid equivalents are additionally saved in CSV.
- **No change:** Stage 1 `observation_changed == false`. This includes captured
  metadata; `no_frame_change` separately ignores metadata-only differences.
  Repeated observations and unchanged responses are distinct metrics.
- **Runtime:** wall time for `agent.main`, including policy, environment,
  tracing, and gzip writes. Environment initialization/downloads, trace metric
  calculation, image rendering, and notebook generation are excluded. These
  are local instrumented timings, not isolated policy compute benchmarks.

The evaluator clears mutable GameAction singleton payloads and resets NumPy's
global RNG to 0 before each environment construction, makes a fresh environment
and agent, and uses Stage 1's `"<seed>:<short-game-id>"`
Python RNG convention after agent initialization. Each repeat is compared by
SHA-256 of the full normalized transition sequence: actions, parameters,
reasoning, arrays, metadata, and differences. Only environment GUIDs are
excluded. Runtime is deliberately not a determinism target. A trace error,
discontinuity, legal-policy advertisement violation, or replication mismatch
causes a failing experiment exit rather than a silently successful result.

An initial complete matrix omitted the NumPy reset and failed replication in
four LF52 pairs: original seeds 0/1/2 and memory seed 0. In each pair, identical
requests and prior observations produced a different next frame; none of their
level counts differed. Resetting NumPy to 0 before each run fixed all four
targeted checks. The final matrix was rerun with this correction applied to
every game/policy, without changing policy parameters. The rejected preliminary
run remains at `local_output/experiments/stage2-iga12aqv/`; it is not the final
evidence set. The diagnosis used public trace comparisons and generic framework
seed plumbing, not game implementation inspection.

`play_local.py --seed` retains Stage 1's policy-RNG-only meaning. Use the
evaluator for the full environment/NumPy initialization and reproducibility
checks described here; the local runner is not claimed to provide exact
environment replay for every public game by itself.

The manifest records versioned game IDs, source hashes, Python/package versions,
vendor revision, budgets, seeds, and runtime scope. Compressed traces retain
the existing JSONL schema and are readable by the Stage 1 visualizer.

## Reproduction

Verification beyond the main matrix:

- All 19 unit/integration tests passed, including the unchanged Stage 1 tests,
  advertised action/coordinate checks, memory isolation and boundaries,
  no-op/cycle penalties, multi-frame semantics, compressed-trace metrics,
  NumPy-seed isolation, and all three bundled agents running the official loop.
- `make verify-local` passed for LS20 and VC33. Both added policies also passed
  seeded, traced local-runner smoke tests on those games.
- All three notebook variants built; the generated notebook was restored to
  the default original policy. No official Kaggle execution was tested.
- Nine additional 256-action traces in a **fresh Python process**, covering
  LF52/R11L/SP80 × all three policies at seed 0, matched the main matrix's full
  normalized trace digests. Evidence is in
  `local_output/experiments/stage2-_zzxah_p/`. This cross-process check covers
  those nine cases, not every seed/game combination on a different host.
- The 23-frame R11L progress transition rendered successfully. The Stage 1
  visual tests still pass for plain JSONL, and a new test covers gzip input.
- Source compilation and `git diff --check` passed. No vendor edits, package
  installation, commits, pushes, or Kaggle submissions were made in this stage.

From the repository root, after caching the public games through the official
runner (see README):

```bash
OPERATION_MODE=offline .venv/bin/python scripts/evaluate_policies.py \
  --seeds 0,1,2 --actions 256 --replicates 2
ARC_LOCAL_INTEGRATION=1 OPERATION_MODE=offline \
  .venv/bin/python -m unittest discover -s tests -v
OPERATION_MODE=offline make verify-local
make notebook POLICY=legal
make notebook POLICY=memory
make notebook
```

The evaluator prints its fresh output directory. It does not fetch additional
games; confirm that the manifest contains all 25 rather than assuming all
public games are cached. On restricted machines, `MPLCONFIGDIR=/tmp/arc-stage1-mpl`
can be prefixed to commands to keep the dependency's font cache writable.
No Kaggle execution, submission, or push is part of these commands.
