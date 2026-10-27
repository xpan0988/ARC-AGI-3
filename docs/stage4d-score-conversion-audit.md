# Stage 4D — Score conversion efficiency audit

27 October 2026 · Research and diagnosis only · Control: Franzen M2 V3, script **362506200**.

## 1. Executive verdict

**NO-GO on changing the competition baseline or spending GPU quota on these hypotheses yet.** The largest observed opportunity is further level progression, but the available evidence does not identify a reliably better way to obtain it. The scheduler already penalizes stalls and values partial score; inference is predominantly generation, with strong prefix reuse. Neither a scheduler rewrite nor forced brevity has earned an experiment.

The smallest evidenced defect remains the action-return type misunderstanding. **New action-history alignment substantially weakens its performance case:** after the known LS20 exception, the exact five omitted actions execute with only **300 additional recorded tokens and 6.40 seconds elapsed**. This is a confirmed execution defect with a small observed continuation cost, not an established score bottleneck.

**Highest-confidence decision:** preserve the reproduced control. If further offline evidence becomes available, screen recurrent return-contract failures first; test a short schema clarification only if their measured cost passes the existing Stage 4 gate. No score-improving intervention is established by the evidence currently possessed.

**Artifacts verified locally.** The [completed-run archive](/Users/xiyuanpan/ARC-AGI-3/baselines/franzen_m2_v3/generated/full_run_362506200) contains the benchmark, execution/server logs, diagnostics, placeholder Parquet and outcome summaries. All 100 benchmark outcomes reconcile with the finished execution-log records; all 21,078 history entries reconcile with per-level action totals. The [downloaded log](/Users/xiyuanpan/ARC-AGI-3/downloads/franzen-m2-v3-baseline.log) is byte-identical to the archived log. All 19 input hashes in [Stage 4 evidence](/Users/xiyuanpan/ARC-AGI-3/docs/stage4-evidence.json) still match; the [main audit](/Users/xiyuanpan/ARC-AGI-3/docs/stage4-human-reasoning-gap-audit.md) and [appendix](/Users/xiyuanpan/ARC-AGI-3/docs/stage4-evidence-appendix.md) were checked against their owning evidence.

The [23-cell prelaunch notebook](/Users/xiyuanpan/ARC-AGI-3/baselines/franzen_m2_v3/generated/full_run_362506200/prelaunch-candidate.ipynb) matches every source cell of the released notebook; their hashes match the recorded pins. All 11 code cells occur verbatim in [notebook-v3.py](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/notebook-v3.py). Across five cached applied harness files, all **102 post-patch hunks** match the release patch. The [release lock](/Users/xiyuanpan/ARC-AGI-3/baselines/franzen_m2_v3/release-lock.json) pins Franzen upstream to `10882e332d883af3e61616df8c8a17d03a328a75`; cached source was used, without remote retrieval. The executed notebook export remains unavailable; prelaunch parity and observed patch application do not replace an executed-export hash check.

## 2. Quantitative score-conversion bottlenecks

### Progress dominates the observed score deficit

| Directly observed or reconstructed from all 100 episodes | Result | Decision implication |
| --- | ---: | --- |
| Public validation | **47.93969 mean; 33 wins across 12/25 games; 417 completed levels** | This is not an official hidden-game leaderboard score. |
| Notebook runtime / observed peak VRAM | **8h20m53.5s / 94.1 of 95.6 GiB** | Nine-hour completion is verified for this public run; no extra batching capacity is established. |
| Score ceiling at exactly the observed completed levels, with no efficiency penalty | **50.00924 mean** | Only **2.06954 points** separate actual score from this fixed-progress ceiling. This is arithmetic headroom, not a predicted improvement. |
| Completed-level action efficiency | **83/417 levels** exceed the human action baseline; **8/33 wins** score below 100 | Wins alone are inadequate; action efficiency still matters. |
| Whole-run expenditure per completed level, including unsuccessful work | **50.55 actions; 41,983 recorded tokens** | These are amortized costs, not costs of a typical solved level. |
| Work assigned to completed levels | **15,667 actions; 11,870,570 tokens** | Means: **37.57 actions / 28,467 tokens**; medians: **28 / 20,702**. |
| Work assigned to terminal unfinished levels with actions | **66 attempts; 5,411 actions; 5,636,375 tokens** | **25.7% of actions / 32.2% of recorded tokens**. Unfinished work is not automatically waste. One further unsuccessful episode records no actions on its next level. |
| Seven unsuccessful episodes one level short | **289,021 tokens/episode mean** | Versus **159,505** for 33 successful episodes. Aggregate resource starvation is not established. |

**Scoring check.** For completed level `i`, reconstruct credit as `min(115, 100 × (human_actions / used_actions)^2)`, weighted by `i`; unfinished levels receive zero. Divide by the sum of all level weights, then cap at the completed-level weight fraction × 100. This reproduces **100/100 archived final scores**, maximum error below `1.5e-14`. The local [score calculator](/Users/xiyuanpan/ARC-AGI-3/.venv/lib/python3.12/site-packages/arc_agi/scorecard.py:151) corroborates the calculation, but is version 0.9.9 versus the run's 0.9.8: agreement with actual outcomes is the verification here, not a claim about a newly checked competition scorer. Efficient levels can offset inefficient ones before the aggregate cap; simply counting levels above the human baseline overstates score loss.

Per-level token/time estimates partition each episode's ordered history at cumulative `actions_per_level` boundaries; these arrays sum to history length in all 100 episodes. Tokens are charged where the next action records them. This reconstructs resource accounting, not observations, Python-call boundaries or the usefulness of discoveries.

**Token accounting caveat:** 17,506,945 is the action-associated benchmark total; every `final_generated_tokens` and history `uncached_input_tokens` field is zero. Episode `solver_note` totals instead sum to **18,082,669**, including **575,724** tokens beyond action-associated accounting in 64 episodes. Server request statistics report **18,118,783 output tokens** for requests entering during the benchmark. These are different accounting scopes, not extra proven waste. Terminal reasoning, timeout/rollback handling and server bookkeeping cannot be fully reconciled without request identities linked to episodes.

### Late allocation produces both breakthroughs and unresolved work

Between periodic summaries at notebook seconds **24,174.0–30,041.7** (97.8 minutes), recorded generation increases **3,114,690 tokens**, actions increase **3,557**, and mean score rises **42.00 → 47.94**. These summaries are **per-game averages across four passes**, not episode trajectories. Across six games whose displayed aggregate score does not increase, token-average differences × four total approximately **350,796 tokens**; rounding prevents exact attribution. Conversely, SC25 gains **31.57** game-average points, VC33 **25.03**, and DC22 **14.94**. Neither group supplies a hindsight-free reallocation policy. [Execution log](/Users/xiyuanpan/ARC-AGI-3/baselines/franzen_m2_v3/generated/full_run_362506200/execution.log:2046)

Actual episode histories demonstrate why elapsed stagnation is ambiguous. SK48 p0 has **7h17m without a recorded action**, between actions 44 and 45; it subsequently completes levels 1–3 near the deadline. CN04 p0 completes level 2 at elapsed **349.0 minutes**, then levels 3–5 by **413.8 minutes**. Such intervals include scheduler waiting. Separately, S5I5 p1 spends **123,740 action-associated tokens** on level 3 and completes it. These are counterexamples to interpreting long elapsed stalls or a fixed token threshold as confirmed futility; they do not prove the existing scheduling order optimal.

### Reasoning and execution losses

The accessible sample remains **13 early level-1 prefixes**, comprising **37 complete analysis sections, 75 Python calls, 30 action-bearing snippets and 49/21,078 actions (0.2325%)**. The 45 inspection-only calls may support useful reasoning. Repeated mechanic analysis, unproductive thought, repeated failed plans and delay after a correct discovery cannot be assigned population costs from this purposive sample.

One return-schema exception is observed: **1/75 Python calls**, also **1/30 action-bearing snippets**. In [LS20 p2](/Users/xiyuanpan/ARC-AGI-3/downloads/stage4-browser-evidence/ls20-9607627b_p2.preview.txt:920), `action([act])[0]` executes LEFT then raises `KeyError: 0`. History actions 7–11 are exactly the omitted `LEFT, LEFT, UP, UP, UP`; together they record **300 tokens**, ending **6.396 seconds** after the failed call's executed LEFT. That bounds the observed continuation expenditure, without proving every token/second would disappear under a prompt change. The preceding **3,381 tokens** generated the plan and must not all be called wasted. No extra in-game action is demonstrated in this recovery. A dictionary stub independently reproduces one action then `KeyError(0)`; direct dictionary access permits the six calls. This tests the contract, not puzzle correctness or score.

Three sampled actions have unchanged endpoints; one supplies informative animation. Five sampled programs execute multiple actions, with no established invalid continuation among their 19 post-first actions. Additional guards, forced single-action execution and mandatory prediction checks therefore lack a demonstrated savings denominator. The four set-subscript SyntaxWarning lines in the full log occur together, including duplicated logging; they establish neither four independent exceptions nor their recovery costs.

## 3. Existing harness capabilities versus actual shortcomings

| Source-established capability | Actual shortcoming or evidence limit |
| --- | --- |
| Per-level action/token counters reset on completion; priority includes level-weight normalization, action efficiency, a continuation-value tail, and declining action/token hazard | Already recognizes expensive stalls. Hazard is heuristic; it does not observe semantic breakthroughs or estimate calibrated marginal score/token. |
| Ten admission slots; queued priorities refresh; slot normally retained until context eviction | Strong cache reuse, but long waits are observed. Admission/trim/priority events are missing, so individual waits cannot be priced against forgone score. Low server queue time excludes harness waiting. |
| Tail value fades over the final 20%; current-level value and hazard remain active | Actual log announces fade at elapsed 387.1 minutes with 96.5 minutes remaining. Late score gains confirm useful work, not that fade selects the best opportunities. |
| `ProgressPace` already implements a smoothed completed-level token-cost multiplier bounded to 0.5–2 | **Disabled** (`ARC3_PRIORITY_PACE=0`). Enabling it is a possible existing option, not new functionality; benefit is untested. |
| Batch actions, terminal/no-op/stale-state guards, persistent helpers and animation access | A dictionary-return misunderstanding occurs despite existing result guidance. Recurrence is unknown. Non-changing endpoints and inspection calls are not sufficient evidence of waste. |
| 58 Ki context drain and coalesced history trimming; preserved reasoning; 12 Ki output ceiling | Cold rebuilds and long replies exist, but available measurements do not establish a dominant avoidable overhead. |

Sources: [gate and queue](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/ARC3-Inference/inference/agent/tool_agent.py:1976), [handover](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/ARC3-Inference/inference/agent/tool_agent.py:6372), [priority/pace calculation](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/ARC3-Inference/inference/agent/priority_scheduler.py:52), [enabled settings](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/notebook-v3.py:10160), [dictionary return](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/ARC3-Inference/inference/agent/python_tool_sandbox.py:489).

**Inference efficiency, measured from the actual full-run [server log](/Users/xiyuanpan/ARC-AGI-3/baselines/franzen_m2_v3/generated/full_run_362506200/serve.log):**

- **9,332 unique completed request-stat records** enter during the benchmark: 673.11M logical input tokens, 630.48M cached (**93.67%**); median per-request cached fraction **97.21%**. Only **460/9,332** have less than 10% cache reuse; these are not all avoidable misses.
- Median initial prefill **0.265 s**, p95 **1.323 s**; median server queue **1.54 ms**, p99 **5.343 s**. Summed request prefill is **5,088 s**, versus **259,913 s** summed forward duration (**1.96%**). These overlap across requests and are not exclusive GPU times or a wall-time savings estimate.
- Benchmark throughput is **594.34 recorded tokens/s**; server output accounting gives **615.11 tokens/s**. Completed-request service intervals overlap almost continuously across the benchmark; this does not measure GPU utilization, but provides no evidence of sustained global starvation from tools. Tool-specific timings and CPU/I/O attribution remain unavailable.
- All **9,326 logged chat HTTP response statuses** are 200; this differs from the request-stat denominator. There are **seven distinct timeout messages**, printed twice each, concentrated at notebook seconds 29,588–29,604, consistent with deadline-clipped requests. No repeated main-run request-failure, malformed-call or degenerate-reasoning warnings, fatal server crash or CUDA OOM is shown. Startup `wrapt` errors/warnings did not prevent service.
- **104/9,332 requests (1.11%)** report at least 12,288 output tokens (some up to three tokens above the configured ceiling). Without finish reasons/tool outcomes, this is not a count of wasted or aborted plans.

Thus cache retention has measured value; its opportunity cost remains unmeasured. No evidence justifies changing quantization, batching or concurrency. Public-run diagnostics regeneration totals 302.64 seconds across 49 saves, overlapping inference; official mode already selects minimal diagnostics and disables request logs. Removing those costs is not a new competition intervention. The public notebook's **39m06.5s** nine-hour margin is also not a proven hidden-run reserve: public and competition paths use different session counts/deadlines.

## 4. Candidate improvements, ranked

Ranking reflects evidence of an addressable mechanism, not claimed score gains. All remain unimplemented.

| Rank / exact proposed change | Evidence strength / expected score conversion | Effort | Runtime/GPU risk | Decision |
| --- | --- | --- | --- | --- |
| **1. Clarify the existing action-return guidance:** explicitly say one dictionary for single/batch calls, with `r = action([...]); r.get(...)`; no `[0]` | **Confirmed local defect; weak performance opportunity.** One observed error; exact plan suffix resumes for 300 tokens/6.40 s. Could prevent aborted programs; no established score effect. | Very small | Tiny prompt cost; behavioral regression possible | **NO-GO for a GPU test now; offline recurrence screen only** |
| **2. Enable existing `ARC3_PRIORITY_PACE=1`**, preserving gate, hazard, fade and stream count | **Hypothesis.** 32.2% of recorded tokens land on unfinished levels, and waits are substantial. Neither demonstrates that current allocation is wrong. Pace uses completed-level cost, not a semantic progress detector. | Small configuration change; evaluation is the real cost | Token redistribution at a common ceiling; cache policy retained, but outcome variance/high regression risk | **NO-GO** |
| **3. Lower per-request output ceiling from 12,288 to 6,144** | **Speculation.** Only 104 requests reach the current ceiling; the lower ceiling would interrupt **527/9,332 (5.65%)** recorded replies. No attribution shows they were unproductive. | Very small | Could save generation or increase retries/duplicate thought and destroy useful plans | **NO-GO** |

**Candidate 1 — benefit, cost, risk and cheapest validation.** The contract applies to all games and is therefore intrinsically general, unlike a game-ID fix. Its only quantified instance is approximately **0.0017%** of recorded run tokens in the subsequent continuation; recurrence cannot be extrapolated from early prefixes. Prompt text can cost more than this saves, and completing previously aborted wrong plans can harm successful games. Cheapest meaningful screen: complete archived Python calls and their recovery sequences, classified by error type and conservatively charged tokens; use dictionary stubs, without environment actions. The existing [Stage 4 gate](/Users/xiyuanpan/ARC-AGI-3/docs/stage4-human-reasoning-gap-audit.md) requires recurrence in **at least three games** and attributable recovery generation **at least 0.5%** of run tokens (about 87,535). Current evidence fails both requirements; those are screening thresholds, not expected gains.

**Candidate 2 — benefit, cost, risk and cheapest validation.** Faster historical progress could receive resources earlier under the same total generation/wall limits; the sign of score change is unknown. Already successful, reasoning-heavy games could lose allocation: R11L p3 wins with **309,496 tokens**, while expensive completed levels also exist. The algorithm is game-independent, but its historical cost reference is unqualified on hidden games. Public-game parameter fitting or penalizing elapsed wait as if it were active inference would overfit. Cheapest meaningful screen: actual handover snapshots, level completions and per-episode active service, evaluated chronologically with only then-available information, including cache reconstruction costs. Frozen-trajectory reordering can expose ranking errors but cannot demonstrate counterfactual score gains. A bounded paired inference comparison would still be necessary before adoption; current evidence does not justify spending that GPU budget.

**Candidate 3 — benefit, cost, risk and cheapest validation.** Stopping long, tool-free replies could increase useful reasoning per second only if subsequent retries cost less and important reasoning survives. Request caps are game-independent but can hurt difficult hidden games and successful long solutions. Cheapest meaningful screen: link capped request finish reasons to tool execution and later recovery, separating completed useful calls, truncated calls and reasoning-only replies. Server token lengths alone cannot do this. No token-savings estimate is promoted from mechanically truncating historical replies.

## 5. One recommended next intervention

**No baseline intervention is justified yet.** The sole next check worth considering is the zero-GPU return-contract recurrence screen above, if complete archived transcripts/requests can be obtained. Its target is the short schema clarification, not a compatibility wrapper, automatic code rewrite or broader harness. The harmless stub check is already complete; repeating it cannot establish opportunity size.

Complete archival access was unavailable in Stage 4; another set of 102,400-character prefixes would not resolve this. Stop here unless the complete existing files become accessible. Do not start a general reasoning, memory or scheduling research program under the remaining competition budget.

## 6. Explicit GO / NO-GO decision

**NO-GO:** baseline changes, GPU experiments for these candidates, and claims of improved competition score. **GO only for offline archival measurement** if the required existing files become available; no new benchmark is needed for that screen.

The audit used **zero Kaggle GPU time**, made no Kaggle calls or submissions, and performed no model/environment execution, downloads, installations, commits or pushes. Only this report was added; the baseline, Stage 1/2/3 artifacts and existing user files were preserved.

## 7. Missing evidence that prevents stronger conclusions

- Complete middle/late transcripts, Python outcomes, observations and request logs for the 100 episodes: needed to price repeated analysis, failed programs, wrong plans, no-change actions and delayed use of discoveries. The currently accessible 49 actions cannot classify 67 terminal failures.
- A request-ID → episode/level/tool-call mapping, with finish reason and timeout handling: needed to reconcile the **0.61M** server-versus-action accounting difference and establish whether any is recoverable waste.
- Admission, handover, trim and priority timestamps: needed to separate inference from waiting and assess whether recently progressing episodes lost valuable opportunities. Periodic game averages cannot substitute.
- A measured recurrent loss large enough to clear the offline gate, then a bounded, separately authorized comparison using actual partial/action-efficient score at common resource ceilings, with successful controls. No such treatment evidence or hidden-game qualification exists.

