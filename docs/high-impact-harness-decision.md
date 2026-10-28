# High-impact harness decision

28 October 2026 · Independent Track B investigation · Franzen M2 V3

**Implementation update:** the user subsequently selected the isolated [V4 A+B candidate](../interventions/transient_feedback_v4/README.md): clarify transient feedback and retain bounded, retrievable animation history. It supersedes the interruption/latch design proposed below. V4 is CPU-tested and built for review; the submitted V3 remains unchanged. The original research and screen below are historical proposals, not evidence of V4 score improvement.

**GO — implement and screen one bounded candidate: preserve unread transient feedback before another level-1 probe overwrites it.** A selective handoff in the Python sandbox can deliver evidence through Franzen’s existing animation tools and follow-up prompt. Do not adopt or submit it without a score-based experiment.

**Status:** failure mechanism observed; isolated CPU prototype passed; model behavior, score improvement and hidden-game generalization **untested**. The submitted baseline and helper-timeout intervention remain unchanged. No GPU, submission, model download, commit or push was used.

## A. Most important remaining bottleneck

The consequential bottleneck is forming a useful mechanism model early enough to progress. More search cannot compensate for a mistaken account of what controls do. The strongest newly identified, directly addressable harness contribution is **discarding transient probe feedback before the model receives it**, then presenting the action as a no-op.

This is narrower than a diagnosis of all failures. M0R0 p2, for example, writes `if nA==nB: return (A,B)`, replays its observed history without mismatches, and later explicitly trusts that model when considering overlap. Historical agreement does not validate an untested exclusion. CN04 and TU93 also show mistaken search constraints and dynamics. These support a broad reasoning problem, but do not yet specify a reliable host-side correction for arbitrary generated programs. The transient-feedback failure has a concrete interception point and a smaller experiment.

### Evidence that changes the decision

All transcript references below identify members of [results.zip](../downloads/results.zip); line numbers refer to the original, complete text, not extracted summaries.

| Episode | Original behavior and corroboration | Competitive relevance |
| --- | --- | --- |
| **TN36 p0** | `transcripts/tn36-ef4dde99_p0.txt:699–745`: a Python loop clicks the blue button, prints endpoint differences, then clicks elsewhere. The button is labeled `NO-OP`. CPU replay of action **5** produces **7 distinct frames / 256 transient pixels**, despite an unchanged interior endpoint. Action **56** repeats the loss with **270** transient pixels (`:3650`). Later reasoning calls the button inert and rejects a commit-button interpretation (`:5584–5749`). | **0/7 levels**, 69,736 action-associated generated tokens. The missing evidence concerns how to operate the puzzle, before any level credit. |
| **TN36 p2** | `transcripts/tn36-ef4dde99_p2.txt:850–880`: `probe(55,37)` is followed by `probe(42,21)` in one snippet; the first result is reduced to endpoint diffs. Replay of action **3** again produces **7 frames / 256 transient pixels**. | **0/7 levels**, 63,980 action-associated tokens. Independent recurrence within the game. |
| **TN36 p3, stronger comparison** | `transcripts/tn36-ef4dde99_p3.txt:869,1009–1059`: the button is the last action, so the ordinary opener reports **7 frames / 270 transient pixels**. The model reads the timeline and frames, then varies the switches and observes different travel distances (`:1682`). | Level 1 completes after **15 actions**; the episode eventually reaches **4/7**. Same weights/harness, different stochastic trajectory—not a treatment comparison. |
| **SC25 p3** | `transcripts/sc25-635fd71a_p3.txt:3822–3851`: a four-click loop overwrites animations from actions **36** and **37**. Replay finds respectively **36** and **81** transient pixels. The model subsequently says those clicks had “no animation,” while correctly inspecting the final click’s animation (`:4032–4107`). | Recurrence in another game. Level 1 consumes **120 actions**, versus **40** in the winning p2; p3 ends at **5/6**. Missing feedback is established; its share of the delay is not. |

**Counterevidence matters:** TN36 p1 loses one such animation yet recovers and reaches 2/7; p3 receives the feedback but still fails later levels. SC25 p3 eventually solves level 1. This mechanism is neither necessary nor sufficient for final failure.

### Population check and verification limits

I replayed the archive’s **100 action sequences / 21,078 actions** through the installed offline CPU environment. Every post-action 64×64 board and completed-level value matched its archived event. No game implementation was inspected to obtain solutions; actions came from the archive.

The local `arc-agi` runtime is **0.9.9**, versus **0.9.8** in the run. Endpoint parity is verified; it does not prove every intermediate frame was identical historically. The replay also matches directly logged animation metadata in the TN36 p3 comparison. Therefore the missing intermediate details are **reconstructed CPU evidence**, supported by archived behavior and source—not newly recovered historical frames.

An exact echo-to-event mapping completed for **68/100 episodes**. I excluded the other 32 from snippet-loss counts rather than guessing through missing/truncated output. Within the mapped subset, direct review confirmed **13 overwritten, uninspected transient-only actions in 10 snippets across five episodes and two games**: TN36 p0/p1/p2 and SC25 p1/p3. They all occur on level 1. These are loss events, not 13 lost solutions or 13 additional required model turns.

Across the full CPU replay, **73** nonterminal level-1 actions in **nine games** have unchanged interior endpoints and transient pixels. Most are already the last action or are inspected. That larger number is exposure to the condition, **not** evidence that nine games would improve.

## B. Why the existing harness does not prevent it

Franzen already provides animation frames/timelines, transition history, probes, search, retained functions, goal revision and cross-level guidance. The relevant gap is their interaction:

1. `_action_verdict` labels an unchanged interior endpoint `NO-OP`, without mentioning its animation. The individual transition retains compact animation metadata.
2. `_HarnessGameSession` stores **one** raw animation record, replaced by every executed non-RESET action. Historical endpoint frames and metadata cannot reconstruct its intermediate frames.
3. `_summarize_step_sequence` advertises only the last executed action’s animation.
4. The stale-state guard normally prevents another call from overwriting a no-op’s feedback, but the release sets **`ARC3_GUARDS_FROM_LEVEL=2`**. Multiple single-action calls inside a level-1 snippet bypass that protection. The separate batch no-op guard does not close this multicall gap.

Sources: [released notebook patch](../local_output/research_refs/franzen/notebook-v3.py), lines **8138–8195, 8346–8349, 8504–8529, 8727–8787, 10199**; [sandbox](../local_output/research_refs/franzen/ARC3-Inference/inference/agent/python_tool_sandbox.py), lines **489–593**; [agent summary](../local_output/research_refs/franzen/ARC3-Inference/inference/agent/tool_agent.py), lines **3711–3809**. All 11 prelaunch code cells occur verbatim in the cached notebook source; the CPU fixture also verified the release pins and relevant patch hunks. This does not replace the still-unavailable executed-notebook source export.

The successful TN36 comparison is especially useful: **the existing animation-aware opener already elicited the desired inspection when the evidence survived.** The candidate repairs the boundary that prevents that opener from seeing earlier feedback.

### Alternatives considered

| Candidate | Baseline overlap and reason not selected |
| --- | --- |
| Evidence-linked hypothesis/constraint register | Freeform hypotheses, history replay and revision already occur; persistent structured world-model sections exist but are disabled. A genuinely new register needs a trustworthy mapping from claims to arbitrary Python constraints and observations. The M0R0 case also defeats a simple “replay agrees, therefore validated” rule. Larger integration and behavioral uncertainty. |
| Fresh-context rescue after stagnation | Ordinary context trimming retains recent reasoning; a deliberate restart would differ. Pass variance is real, but does not establish that discarding reasoning at a chosen threshold helps from the same current state. Upstream reports a regression from removing thinking history. |
| Simulator checking / generic verification | The model already writes simulators, verifiers and history checks. Upstream stronger verification prompting did not clearly improve score. A generic checker cannot test unobserved mechanics or certify goal semantics. |
| Scheduler, longer reasoning, efficiency or helper-timeout changes | Existing priority scheduling accounts for spend and progress. Unfinished computation can still produce breakthroughs. The timeout defect is real and separately addressed; it does not explain the TN36 evidence loss. None offers a more direct route from these observations to additional levels. |

These are rejected directions for this decision, not an implementation backlog. Upstream experiment claims come from [WRITEUP.md §6](../local_output/research_refs/franzen/WRITEUP.md); their limited, non-controlled nature is acknowledged there.

## C. One concrete change

**Add a snippet-local unread-transient handoff, restricted to level 1.** Keep the ordinary level-2-and-later guards and all numerical `no_op`/`gameplay_changed` meanings.

- After an actually executed, nonterminal action, arm a latch when the **last action’s** endpoint has `gameplay_changed=False` and its animation has `transient_pixels>0`. For batch returns, use the last entry of `gameplay_changed_per_action`, not the aggregate flag.
- Allow subsequent computation and printing. Successfully fetching nonempty `last_animation_frames` or `last_animation_timeline` clears the latch. Fetching is observable; understanding is not claimed.
- Before the next `action(...)` sends anything to the host, if the latch remains armed, end the snippet through an explicit controlled exception: **the requested next action was not executed; the previous action animated and reverted; inspect the existing animation accessor**. Preserve stdout, executed-action results and the normal helper-export path.
- The next model request receives the existing animation-aware summary and unchanged current game state. A new snippet starts with a fresh latch, so deliberate continuation remains possible. No automatic action replay, environment reset, extra critic call, hypothesis bank or animation-history database is needed.

This extends an existing guard’s coverage for one evidence-loss condition; it is not a claim that Franzen lacked animation support. It also differs from globally enabling level-1 stale-state blocking: genuinely inert probes remain batchable, and programs that fetch animation feedback can continue within the same snippet.

**Cost estimate:** roughly half a day for a default-off isolated overlay, flag plumbing, focused regression checks and evaluation setup. Main changes belong in the sandbox bootstrap’s `action`, `_animation_fetch` and outer exception handler, plus one short explanation in tool guidance. Use the existing retention and observation interfaces.

**CPU feasibility:** an isolated copy of the release sandbox passed **13 checks**, including pre-overwrite refusal, inspection-based continuation, ordinary no-op and persistent-change controls, level-2 preservation, terminal precedence, batch-last-action semantics and helper export on handoff. These use synthetic host responses and real sandbox execution; they are **protocol tests, not model or score tests**.

## D. Why it might improve unseen games—and how much is justified

The condition depends on observable transitions, not game IDs, coordinates, known solutions or public-game rules. Rejected moves, program previews and temporary signals can all carry information that endpoint comparisons erase. Preserving that evidence can prevent an operative control from being excluded, unlock the first level, and make later levels reachable with the same model.

The magnitude remains uncertain. Replacing all five affected archived episode scores with each game’s best observed pass would increase the 100-episode mean by only **about 1.60 points**. That is an illustrative substitution, **neither an expected gain nor an upper bound**. A larger improvement requires better downstream solving or broader applicability; neither is demonstrated. There is no basis to attribute the **47.94 → 24.47** local/leaderboard difference to this mechanism.

Principal regressions are interrupting useful multi-action exploration, spending reasoning on decorative flashes, losing a snippet’s unexecuted suffix, and confusing transient feedback with progress. The controlled-exception path must not clear helpers or swallow terminal outcomes. Repeated alerts can consume more inference than they save. Restricting the change to level 1 bounds exposure but does not eliminate these risks.

## E. Cheap falsification experiment

**CPU gate before GPU:** integrate the default-off overlay in a separate candidate, verify flag-off equivalence, and exercise the complete agent dispatch with replayed TN36/SC25 responses. Confirm unchanged executed prefixes, preserved animation identity, accurate skipped-action reporting, normal helper exports and a reachable next model request. The current prototype does not yet establish this full integration.

**Screen: hard cap two GPU-hours, including startup and outputs.** Freeze six games—**TN36, SC25, LF52, SU15, CD82, LP85**—and inference seeds **17 and 29** before running. These cover observed losses, animation-heavy controls and reliable solving. Use ordinary game starts and the same environment seed in both arms. Run 12 control/candidate pairs with the same weights, sampling settings, context policy and action rules; leave the helper-timeout overlay disabled in both arms.

Use the existing `max_generated_tokens_per_game=65,536` in the evaluation wrapper, a common action cap of 256 and balanced arm order. Log actual usage, including the possible final-response overshoot of up to 12,288 tokens; cap accounting must include reasoning without actions. With 24 episodes, that is at most approximately **1.87 million completion tokens**, plus prefill/startup. The archived aggregate throughput suggests feasibility within two hours, but six-session batches and tail utilization may be slower. An unfinished matrix is inconclusive, not permission to extend the run. Fixed seeds do not guarantee bit-identical GPU inference.

Predeclare these gates:

- **Mechanism:** control must exhibit uninspected-overwrite opportunities in at least two games; candidate must prevent the targeted overwrites and show subsequent use of the preserved feedback. Too few opportunities is inconclusive.
- **Solving:** at the common resource limits, candidate must gain **at least four completed levels net** across the 12 pairs, with positive level gains in **at least two games**, **at least +2 absolute mean score points**, and no fewer game wins. Report every pair and losses in the four comparison games.
- **Reject:** extra inspection without extra level credit; gains confined to one game; net regression; broken accounting/retention; or the screen exceeding its hard allocation. Improved prose and fewer lost frames alone do not qualify.

This is a cheap selection test, not a statistically powered claim about hidden games.

## F. Spend decision and implementation handoff

**GO for the bounded candidate and, only after the CPU gate, the two-hour screen.** The case is stronger than another generic reasoning prompt because it restores an already demonstrated observation-to-inspection path. It is not yet a demonstrated breakthrough.

If the screen passes, allocate **at most one nine-hour full 25-game × four-pass candidate evaluation**. Require at least **+2 mean score points over 47.93969**, **eight additional completed levels**, gains in at least **three games**, no fewer than **33 wins**, and completion within the original resource limit. The archived baseline comparison remains unpaired and noisy; report that limitation. Otherwise retain the submitted baseline.

Budget using the user-supplied approximately 21 hours: **2 h screen + up to 9 h full evaluation = at most 11 h**, leaving approximately **10 h** uncommitted. Quota, live rank and deadline were not independently refreshed. No workload or submission is authorized by this report itself.

Local reproducibility artifacts are isolated under [local_output/high-impact-harness](../local_output/high-impact-harness/): `replay.py`, `replay-results.json`, `summary.json`, `prototype.py`, and `prototype-results.json`. They contain no model weights or extracted transcript copies. The [independent review bundle](claude-review/README.md) adds small diagnostic source/result snapshots and exact evidence excerpts; the full replay output and archive remain ignored.

**Current handoff:** review the [V4 A+B source diff, CPU results and candidate](../interventions/transient_feedback_v4/README.md). No unread-transient latch or forced interruption was implemented. Any future score experiment must update the earlier mechanism criteria for voluntary historical retrieval and receive separate authorization.
