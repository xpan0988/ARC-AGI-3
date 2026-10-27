# Stage 4: human-inspired reasoning gap audit

27 October 2026 · Research only · Control: Franzen M2 V3, Kaggle script version **362506200**.

## 1. Executive verdict

**No strategic architectural change has yet earned a GPU experiment.** Most of the proposed human-inspired loop is already explicitly supported by Franzen: infer a provisional goal, inspect objects, make discriminating probes, search once mechanics are understood, inspect outcomes, and reconsider the goal and mechanics on later levels. Describing that loop more strongly would principally change the prompt.

Real structural differences remain possible: an evidence-linked bank of competing hypotheses, a belief over hidden state, and an explicit policy for choosing information versus immediate progress. The baseline does not implement those mechanisms. **The available failures do not establish that their absence is the bottleneck.** Its conversation and retained functions already provide substantial memory; adding persistent theories can preserve mistakes as readily as discoveries.

The clearest actionable defect in the newly accessible sequences is smaller: **generated code misuses the action tool's return type**. An LS20 action executes before `action(...)[0]` raises `KeyError: 0`, aborting the intended six-action program after one action. This supports an offline execution-contract screen, not a broad reasoning rewrite. It is not established as the cause of LS20's eventual failure.

**Stage 3B's decision remains unchanged:** there is insufficient evidence for unconditional predictive verification. The new sample contains useful batches and probes, but no established failed precondition followed by an unnecessary continuation.

## 2. Current versus proposed architecture

“Implemented” below means explicit prompt/tool/harness support, not proof that the model consistently uses it correctly. Detailed configuration and code references are in the [appendix](/Users/xiyuanpan/ARC-AGI-3/docs/stage4-evidence-appendix.md).

| Proposed capability | Assessment | What the actual baseline supplies; remaining difference |
|---|---|---|
| A. Infer uncertain goals | **Partially implemented** | The prompt asks for the goal as currently understood, revision from evidence, and goal reassessment at level transitions. Sampled reasoning entertains alternatives. No host-maintained competing-goal bank, confidence calibration, or evidence-based promotion rule. |
| B. Discover mechanisms through informative experiments | **Partially implemented** | Explicit discriminating-probe instructions; Python inspection, segmentation, diffs, search and conditional action programs. No implemented expected-information-value calculation or experiment selector. Probe quality remains model-dependent. |
| C. Reason about hidden state and history | **Partially implemented** | Ordered per-action transitions and observations, persistent conversation, retained helpers, and within-action animation access. No explicit latent-state belief. Endpoint-based no-op/stale guards are heuristics; unchanged pixels cannot establish unchanged internal state. |
| D. Use visual semantics | **Already implemented as support** | Current-grid and difference images; color/shape/rotation/containment/adjacency features; explicit cautions about backgrounds, HUDs and object identity. Correct semantic interpretation remains unverified in general. |
| E. Switch between exploration, execution and revision | **Partially implemented** | Observe–plan–act instructions, short probes, search after understanding, conditional programs, automatic stop guards and model returns. No host-owned phase controller or stopping rule comparing information value against execution value. |
| F. Transfer across levels while detecting changes | **Partially implemented** | Explicit transfer and goal-reassessment prompts; conversation and eligible functions survive levels, with a warning to recheck helper assumptions. No separately validated mechanism memory. Late-level use could not be audited from the prefixes. |

Thus the meaningful proposed differences would be **state management and decision policy**, not a new list of reasoning stages. Merely adding instructions to identify goals, interpret colors, inspect animations, or reuse mechanics is substantially redundant. Mandatory prospective verification would be a distinct execution policy, but its benefit remains unestablished.

## 3. Failure analysis and evidence limits

The control completed **100 public episodes**, winning **33/100 across 12/25 games**, completing **417 levels including repeats**, with mean public score **47.94**, **21,078 actions**, **17,506,945 generated tokens**, and notebook runtime **8h20m53.5s**. Observed peak VRAM was **94.1/95.6 GiB**. These are ordinary public-game validation results, not an official hidden-game leaderboard score.

The specified `~/Downloads` directory contains no relevant run files. The repository's `downloads/` contains the matching log, duplicate unexecuted prelaunch notebooks, placeholder Parquet, and earlier smoke artifacts. Both notebook downloads have the recorded candidate SHA-256; the log and `下载.txt` are byte-identical to the full-run archived log. The ZIP contains LS20 smoke evidence, not the completed 100-episode run.

The local full-run `benchmark.json` has all executed action IDs/parameters and timing/token accounting, but no corresponding observations, reasoning, snippet boundaries or per-action level outcomes. The remote listing names 100 transcripts, 100 event files, 100 viewer files and 100 request logs. A browser attempt to download a full transcript did not complete and reported a reCAPTCHA-service connection error. No challenge or protection was bypassed.

I saved **13 actual-run transcript previews**, each capped at **102,400 characters**, under [downloads/stage4-browser-evidence/](/Users/xiyuanpan/ARC-AGI-3/downloads/stage4-browser-evidence). They supply **37 complete analysis sections, 75 Python calls, and 30 action-bearing snippets containing 49 executed actions**. All 49 match the corresponding benchmark action prefixes. This is a purposive sample across game outcomes and passes, **entirely early level-1 play**, covering **49/21,078 = 0.2325%** of actions. It cannot supply the requested middle/late temporal strata. Trailing partial sections are excluded. Event previews also truncate items; no intact full-run event/image/animation corpus was recovered.

| Finding | Evidence class and denominator | Interpretation |
|---|---|---|
| Repeated failures are real, with substantial partial progress | **Observed:** 13/25 games win none of their four episodes; 52/100 episodes belong to those games. Of 67 unsuccessful episodes, 9 complete zero levels, 30 complete some but less than half, and 28 complete at least half; 7 are one level short. | Prioritize those stalls, but aggregate progress cannot identify their cognitive cause. RE86, S5I5, M0R0 and CN04 provide useful progress-then-failure targets. |
| Tool-result contract failure | **Observed:** 1/30 sampled action-bearing snippets, in LS20 p2. | The first LEFT executes; dictionary indexing with `[0]` then fails. Five requested actions are not executed. A predictive board verifier does not address this type error. |
| An incorrect movement hypothesis is tested | **Observed:** BP35 p0 predicts sliding to the far wall; RIGHT returns near the prior position instead. | A directly refuted local mechanism hypothesis; not evidence that it persisted or caused the episode's final failure. |
| Useful visual and goal inference already occurs | **Observed:** AR25 infers mirrored motion and its four-LEFT alignment matches; FT09's three-click plan completes a level. | Positive controls against claiming the baseline lacks those abilities. |
| Endpoint no-op is not absence of evidence | **Observed:** 3/49 actions are reported as endpoint no-ops. One LF52 action also reports six animation frames and 48 transient pixels; the next turn inspects the timeline. | Within-action animation, not an across-action delayed effect. This example supports preserving animation access, which the baseline already provides. It does not prove harmful guarding. |
| Unnecessary continued execution is not established | **Observed:** 5/30 snippets execute multiple actions, containing 24/49 actions and 19 post-first actions. **Zero demonstrated** failed continuation preconditions or saved actions. | Nineteen is a mechanical continuation count, not a savings estimate. Useful probes, correct positioning, and a level-completing batch are included. |
| Deadline exposure | **Observed:** all 67 unsuccessful episodes have final elapsed times between 29,019.8 and 29,455.4 seconds, against configured per-game elapsed limit 29,018 seconds. **Inference:** deadline/queue/drain behavior censored these attempts. | Elapsed time includes waiting; it is not dedicated GPU time. No inference-service crash/OOM is shown. Exact episode stop causes and counterfactual solvability remain unknown. |

The requested taxonomy is retained in the appendix. **Wrong terminal goal, persistent wrong mechanism, missed visual relation, forgotten history, delayed-effect misinterpretation, excessive low-information exploration and premature commitment cannot be assigned population frequencies. All 67 terminal failures remain causally unclassified.** Local observations above are not upgraded into episode-level diagnoses. The 30 individual sequences and all 100 episode summaries are retained in [stage4-evidence.json](/Users/xiyuanpan/ARC-AGI-3/docs/stage4-evidence.json).

**Cost and generalization.** The notebook left **39m06.5s** below nine hours. At the observed aggregate benchmark rate of about **594 generated tokens/second**, 5% more generation corresponds to about **24.5 minutes**, and 10% to **49.1 minutes**. These are sensitivity conversions, not measured intervention costs; changed prefill, concurrency, cache pressure and extra calls can worsen them. Hidden-game workload and timing remain unverified. Extra hypotheses also require invalidation when goals change, and a prediction can accurately execute the wrong goal. No hidden-game benefit can currently be claimed.

## 4. One recommended experiment

**Offline screen of a minimal action-return schema clarification.** This deliberately tests the smallest directly evidenced weakness; it does not claim to instantiate a different human reasoning architecture.

| Item | Preregistered proposal; not implemented here |
|---|---|
| Exact change to investigate | Add one short example to the Python tool guidance: `r = action([...])` returns **one dictionary**, for single actions and batches; read flags with `r.get(...)` and batch executions with `r.get('executed_actions', [])`. Do not index the return with `[0]`. Change no guard, model, memory or scheduler setting. |
| Supporting evidence / expected benefit | The LS20 p2 error is attributable to precisely this mismatch. The expected benefit is fewer aborted programs and recovery turns; score benefit and recurrence are unknown. |
| Required data | Complete transcripts for the 100 archived episodes, plus action/event alignment around errors and recovery. The current prefixes suffice to confirm the example, not its population cost. |
| Offline method / GPU cost now | **0 GPU-hours.** Enumerate actual tool calls, separate return-schema errors from unrelated Python errors, and identify recovery/reissued-action costs from subsequent evidence. Use a stub returning the recorded dictionary to reproduce the failing access and the documented access; never advance the game. Review matched correct uses to test whether the proposed wording addresses an ambiguity. This establishes API correctness and opportunity, not improved solving. |
| Offline acceptance threshold | Proceed only if the full archive shows the same attributable error in **at least three distinct games** and conservatively attributable recovery generation totals **at least 0.5%** of run tokens. Include unknown recovery costs separately; do not estimate them from prefixes. These are decision thresholds, not expected effects. |
| Early rejection | Reject as a performance direction if the error is isolated, corrected immediately at negligible cost, below either threshold, or the complete evidence remains inaccessible. The current sample does **not** pass this gate. |
| Main regression risk | Extra prompt text may have no behavioral effect or cost more than it saves. Removing a type error can allow a wrong longer plan to run; existing terminal/no-op guards must stay intact. No automatic code rewriting. |
| GPU evaluation only if the offline gate passes | A separate, explicitly authorized, paired control/clarification pilot: same unchanged weights/settings and matched environment and explicitly pinned inference seeds; freeze 12 episode pairs across six games, including correct-use and successful controls, before treatment. Cap total cost at **3 GPU-hours including startup**; an incomplete matrix is inconclusive. This is a screening budget, not a throughput guarantee. |
| Pilot acceptance threshold | At least **50% fewer return-schema exceptions per Python call**, **+2 absolute mean public-score points**, no fewer wins or completed levels, and no more than **2% extra generated tokens** at common resource ceilings. Report every timeout and per-game difference. Too few error opportunities is inconclusive; no extension of the pilot by default. A small public pilot cannot qualify hidden-game generalization. |

Re-enabling full world-model sections, adding an ensemble, constructing a simulator, forcing single-action turns, or building a formal information-gain planner would introduce larger, presently unsupported changes. The alternative of leaving the strategic architecture alone is a valid outcome of this audit.

## 5. Go / No-Go

**GO:** preserve the control and perform the offline contract screen if complete archival access becomes available.

**NO-GO:** spend remaining Kaggle quota on the broad human-inspired architecture, unconditional predictive verification, or the schema prompt pilot before its offline gate passes. The defensible Stage 4 result is substantial overlap plus unresolved causal evidence, with one narrow execution defect worth screening.

Only research documents and captured browser evidence were added. No baseline/production code, build scripts, dependencies or configuration changed; no model installation, GPU run, Kaggle submission, commit or push was performed.
