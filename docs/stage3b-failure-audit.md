# Stage 3B: failure prevalence and feasibility audit

26 October 2026. **Decision: INSUFFICIENT EVIDENCE. Do not implement the verification mechanism or authorize the proposed GPU experiment yet.** The accessible evidence establishes that continuations occur, but not that incorrect continuations are common or costly. It also demonstrates useful exploratory sequences that a strict “unknown prediction means stop” rule could interrupt.

## Evidence and coverage

Inspected the existing Franzen Milestone 2 version 3 notebook, its embedded diagnostics, actual patched guard configuration, and published output-file previews. These are **publisher-produced execution results, not a new local reproduction**. Stage 2’s novelty-versus-progress finding remains relevant but cannot establish the failure rate of a reasoning agent.

The saved notebook contains **100 run summaries: 25 demonstration games × four passes**, with **21,245 actions**, **17,504,777 generated tokens**, **417 completed levels**, and **33 complete wins**. Benchmark time is **8:10:56**; notebook runtime is **8:21:48**. Summaries do not expose snippet boundaries or continuation intent. The separate diagnostic `note` token totals sum to 17,954,840; calculations below consistently use the main token column, rather than silently mixing accounting conventions.

The [published output listing](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution/output) contains per-game transcripts and event JSONL files. Complete files were not retrieved: the installed Kaggle CLI required authentication, and browser download attempts produced no file. Three readable transcript previews were each truncated at **102,399 characters**. Only complete analysis sections were counted, excluding the trailing partial section.

| Pass 0 prefix | Complete analysis turns | Python calls | Calls executing actions | Calls executing ≥2 actions | Executed actions | Actions in multi-action calls | Actions after the first |
|---|---:|---:|---:|---:|---:|---:|---:|
| AR25 | 3 | 6 | 3 | 2 | 8 | 7 | 5 |
| BP35 | 2 | 8 | 2 | 0 | 2 | 0 | 0 |
| CD82 | 3 | 8 | 3 | 0 | 3 | 0 | 0 |
| **Total** | **8** | **22** | **8** | **2** | **13** | **7** | **5** |

A sequence means one executed Python tool call, including loops making several `action(...)` calls. Counts use execution-result action echoes, not action names in generated code, animation frames, or requested-but-skipped actions. Initial automatic resets are outside the 13 model-issued actions.

Thus **25% of action-bearing Python calls**, or **9.1% of all Python calls**, execute multiple actions **in these prefixes**. The 13 actions cover only **0.061%** of the reported action total. The first three accessible alphabetic pass-0 transcripts are a convenience sample, all at level 1; neither game coverage nor temporal coverage is representative. Whole-run batching frequency is **unknown**.

## Concrete classifications and existing protection

**AR25, analysis step 1:** one snippet probes UP, DOWN, LEFT, RIGHT, inspecting each transition. All four execute; all report gameplay changes and 109 changed cells. The preceding reasoning describes testing controls, without committing to a specific displacement. The three continuations are **intentional exploration**, not established contradictions. A later comparison of initial and final object bounds leads the agent to discount movement; an opposite-direction round trip cannot by itself establish that nothing moved. This is a possible evidence-interpretation problem, not proof that the intervening actions should have been stopped. Full frame evidence would be needed to resolve it.

**AR25, analysis step 3:** one snippet separately tests SPACE and two mouse locations. All three execute and report no gameplay change; two actions therefore follow a no-op. These are distinct exploratory probes, not repetitions of a stated prediction. **No-op continuation is observed; incorrect continuation is not established.** Their ultimate usefulness and counterfactual savings cannot be classified from this prefix. The earlier mouse-only snippet at step 2 has no continuation to prevent.

**CD82, analysis step 2:** generated code lists LEFT, RIGHT, UP, DOWN but breaks when `gameplay_changed` becomes true. Only LEFT executes. Counting four actions from the source would invent three wasted actions. The agent already uses an adaptive stopping condition. BP35’s two observed actions occur in separate snippets and provide no continuation opportunity.

The actual version 3 configuration enables batch no-op and stale-state blocking, with per-action guards starting at level 2:

| Existing protection | Source-established behavior | Consequence for this proposal |
|---|---|---|
| Batch no-op stop | Stops a requested `action([...])` batch after a transition with no interior gameplay change; applies at level 1 too | Already covers this class of waste inside a batch |
| Stale-state stop | A no-op arms a latch; subsequent action calls within the snippet are blocked when level gating permits | AR25’s separate single-action probes remain allowed at level 1 |
| Terminal/level latch | Stops batch execution at death/level completion and prevents later snippet actions against the obsolete board | Terminal continuation is already protected |
| Generated conditional code | May inspect results and exit independently | CD82 demonstrates this protection actually operating |

No harness guard activation is demonstrated in these 13 actions; whole-run activation rates are unavailable. Guard behavior above is source inspection, not a new runtime test. No generic guard verifies a semantic prediction when the board changes. That gap exists, but its prevalence and cost remain unmeasured. The four-cell border used for gameplay-change detection is a heuristic, not ground-truth game semantics. [Franzen source](https://github.com/da-fr/arc-agi-3-solution/tree/10882e332d883af3e61616df8c8a17d03a328a75), [version 3 notebook](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution).

## Opportunity ceiling: four different quantities

| Quantity | Observed prefix evidence | Interpretation |
|---|---|---|
| 1. All actions inside multi-action snippets | **7/13 = 53.8%** | Includes the first action, which a continuation stop cannot save |
| 2. Actions after the first | **5/13 = 38.5%** | Mechanical upper ceiling for directly suppressible actions in this sample |
| 3. Actions after potentially contradictory transitions | **0 established contradictions; 2 post-no-op candidates** | Both candidates belong to deliberate probes; no-op alone does not contradict their purpose |
| 4. Plausibly saved actions | **0 demonstrated; actual savings unidentifiable** | Five mechanically stoppable actions are not five demonstrated savings; interrupted probes may simply be reissued |

For the whole published run, the number of post-first actions is not recoverable from summaries. The deliberately loose bound is **5–21,145 actions (0.024%–99.53% of 21,245)**: five are directly observed; at least one action in each of 100 nonempty runs cannot be a continuation. This is a logical bound, **not an estimate**. A realistic positive savings range cannot be supported. Reporting 38.5% as the population opportunity, or treating unclassified actions as failures or successes, would be misleading.

## Verification overhead under nine hours

No verifier was implemented or benchmarked. The following are **sensitivity assumptions**, not measured costs. Normalize to **1,000 checked sequences** because their actual corpus count is unknown.

| Added work | Assumption | Estimated cost |
|---|---|---|
| Prospective checks | 100–300 extra output tokens per checked sequence | **100,000–300,000 tokens** |
| Interruption/replanning | 5–20% interrupt; one extra response of 512–2,048 tokens per interruption | **50–200 calls; 25,600–409,600 tokens** |
| Combined generation | Sum of the above | **125,600–709,600 tokens** |

The saved benchmark averages approximately **594 generated tokens/second across the entire job**. At unchanged effective throughput, that combined generation corresponds to **3.5–19.9 minutes per 1,000 checked sequences**. This is only a generation-equivalent conversion: longer responses, changed concurrency, prefill, scheduling, and cache pressure can increase cost. Freed action budget does not automatically free comparable GPU time, and saved actions do not automatically improve score.

**Prefix cache:** appending checks and results need not invalidate the existing cached prefix. Extra context and more frequent returns can nevertheless cause earlier history trimming, eviction, and additional prefill. No matching version-3 counterfactual cache measurements exist; assigning a precise penalty would be invented.

**CPU:** assuming an in-process, bounded grid check takes 1–10 ms, checking all 21,245 actions would cost approximately **21–212 CPU seconds**, not necessarily that much wall time. This excludes process startup, arbitrary generated simulations, and repeated expensive segmentation; those would invalidate the estimate.

**False/unknown interruptions:** the rate is unknown. If all five continuations in the two AR25 probe snippets lack acceptable predictions, forcing a model return before each continuation could require **five additional responses to execute the same seven actions**, saving none. The proposed fail-on-unknown behavior therefore has a concrete overhead risk even without an incorrect prediction.

The published notebook leaves **38:12** below nine hours, but its 100 demonstration runs differ from the competition’s 110 hidden games; this is not a transferable spare-time budget. Existing guards deliberately preserve level-1 experimentation. The evidence does not currently justify spending that limited runtime on stricter interruption.

## Smallest additional experiment and decision gate

**Use archived baseline executions; do not launch new inference.** Obtain complete version-3 transcript/event pairs from the already-published outputs. First calculate mechanical snippet counts over all 100 runs; this requires no model and no game replay. Match actual executions to snippets and exclude skipped actions, automatic resets, and repeated transcript history.

For the smallest initial semantic audit, inspect **30 multi-action snippets**, sampled with a fixed seed across games and early/middle/late execution, retaining selection probabilities. Use the contemporaneous reasoning/code and intermediate observations to label: explicit contradiction, intentional probe, already guarded, or unclassifiable. Record remaining actions after the first contradiction, whether later probes remain useful, and whether the continuation was already conditionally checked. Report game-clustered uncertainty and the unclassifiable share; extend annotation only if the decision remains unresolved. Thirty snippets are an initial screen, not a precision guarantee.

Count suffix length only as an upper bound. A conservative “plausibly saved” label requires an explicit failed precondition that makes the remaining actions unnecessary or inapplicable; it cannot assume that replanning succeeds. Compare these counts with the interruption/call sensitivity analysis above. A substantial ambiguous share remains **INSUFFICIENT EVIDENCE**, even if batching is frequent.

This archive audit is smaller and more informative than starting the 21-GPU-hour intervention experiment. Until it finds recurring, costly **unguarded contradictions**, the verification proposal has not passed its feasibility gate. Temporal evidence interpretation is a reasonable alternative to examine, but the current fragments do not establish it as the dominant bottleneck either.

## Audit provenance and preservation

- Local notebook: `/Users/xiyuanpan/Downloads/arc-agi-3-milestone-2-solution.ipynb`; SHA-256 `589eaf393f416effe925c6830fc00fcdc0d6da91193b29ff0029282cbd6ee96e`.
- Ignored source/diagnostic cache: `local_output/research_refs/franzen/`; extracted aggregate rows: `audit-run-summaries.json`. Version-3 guard configuration is in `notebook-v3.py` around lines 10199–10201; patched guard logic around lines 8055–8138 and 8515–8620.
- Preview identifiers under the published `transcripts/` folder: `ar25-0c556536_p0.txt` steps 1–3, `bp35-0a0ad940_p0.txt` steps 1–2, `cd82-fb555c5d_p0.txt` steps 1–3. Full event/frame sequences were unavailable for independent difference validation.
- Agent, evaluator, and Stage 1 trace-module hashes still match the Stage 2 manifest. No agent/baseline code changed; no GPU execution, model downloads, submissions, commits, or pushes. Runtime tests were not rerun for this documentation-only audit.
