# Independent Claude review

Prepared 28 October 2026. Review the evidence independently and challenge the recommendation in [the high-impact decision](../high-impact-harness-decision.md). GO is an unvalidated recommendation for a bounded candidate; it establishes neither improved score nor authority to spend GPU time.

## Minimal reading set

| Material | What to inspect |
| --- | --- |
| [High-impact decision](../high-impact-harness-decision.md) | One proposed level-1 unread-transient handoff, alternatives rejected, counterevidence, risks and falsification gates. This candidate is not integrated into the harness. |
| [Evidence excerpts](evidence-excerpts.md) | Exact, line-addressed TN36 and SC25 transcript excerpts; relevant source excerpts. Compare the failure and successful inspection paths. |
| [CPU result snapshot](cpu-results.json) | 100 archived sequences / 21,078 matching action endpoints; incomplete mapping exclusions; 13 manually checked losses in 10 snippets / five episodes / two games; 13 prototype protocol checks. |
| [CPU prototype](diagnostics/prototype.py), [replay diagnostic](diagnostics/replay.py) | Small copies of the investigation diagnostics, with repository-relative paths and output redirected to ignored `local_output/claude_review/`. No candidate installation, model call or GPU execution. |
| [Release notebook](../../arc-agi-3-milestone-2-solution.ipynb), [release lock](../../baselines/franzen_m2_v3/release-lock.json) | Authoritative V3 source and pins. Notebook cell index 2 contains the release patch; index 4 applies it. Do not execute the notebook. |
| [Timeout overlay](../../interventions/helper_timeout/patch.py), [builder](../../interventions/helper_timeout/build.py), [README](../../interventions/helper_timeout/README.md) | Separate existing intervention. `ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT` remains default-off; do not combine its effect with the animation hypothesis. |
| [CPU fixture](../../tests/franzen_timeout_fixture.py), [timeout tests](../../tests/test_helper_timeout.py) | Actual sandbox supervisor and selected dispatch/retention methods, with synthetic adapters and pinned local source dependencies. |

The full-validation reference is [the archived report](../../baselines/franzen_m2_v3/full-validation-report.md): mean 47.93969, 417 completed levels and 33 wins across 100 episodes. The official score 24.47 has different evaluation conditions; the animation mechanism has not been shown to explain that difference. [The earlier timeout decision](../score-intervention-decision.md) and [failure audit](../stage4e-failure-mechanism-audit.md) are background, not additional proposed changes.

## Complete source and local-only dependencies

Use these existing ignored files for complete source inspection in this checkout:

- `local_output/research_refs/franzen/ARC3-Inference/inference/agent/python_tool_sandbox.py`: `action`, `_animation_fetch`, lazy animation views and the controlled-exception/export path; approximately lines 489–735.
- `local_output/research_refs/franzen/ARC3-Inference/inference/agent/tool_agent.py`: `_summarize_step_sequence` (3711–3809) and `_run_python_tool` (locate by symbol). Check what a model actually receives after a refusal.
- `local_output/research_refs/franzen/notebook-v3.py`: `_action_verdict` (8138–8195), the stale guard (8504–8529), animation replacement (8727–8787), and released guard configuration (10199). Prefer the tracked notebook patch when an export disagrees.
- `local_output/research_refs/franzen/WRITEUP.md`, section 6: prior experiments with structured memory, context retention and verification prompts.
- `local_output/high-impact-harness/replay-results.json`: complete per-episode CPU diagnostic output, SHA-256 recorded in the result snapshot.
- `downloads/results.zip`: original evidence, approximately 2.24 GB decimal, ignored and untracked. Open selected ZIP members in place. Do not extract the entire archive or put it in Git.

The diagnostic scripts and timeout tests require the two applied source caches above. Replay additionally requires the existing local offline game environments and installed `arc-agi`/NumPy. These dependencies are available in this checkout but are not shipped in the small review bundle. A fresh Git clone can inspect the report, snippets, scripts and result snapshot; it cannot reproduce all CPU checks without those dependencies. Missing/drifted caches fail rather than download replacements. Source hashes and diagnostic-copy provenance are recorded in `cpu-results.json`.

## Questions for independent review

1. Does the exact baseline discard the earlier animation before the next model request, and is its feedback absent from the remaining observation interfaces?
2. Are the TN36 and SC25 cases meaningful lost information, or could the proposed interruption spend more inference than it saves? Account for TN36 p1 recovery and p3 later failure.
3. Does the isolated latch preserve terminal precedence, already executed actions, helpers and accurate skipped-action reporting? Full agent dispatch and the next model request remain untested for this candidate.
4. Is the proposed screen sufficiently informative within its two-hour hard limit? Endpoints, protocol checks and better inspection do not establish additional solved levels or unseen-game gains.

## Lightweight checks

Run from the repository root. These commands start no model server or Kaggle workload:

```sh
git check-ignore -v -- downloads/results.zip
git ls-files --stage -- downloads/results.zip
git diff --check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python baselines/franzen_m2_v3/verify.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_helper_timeout.py' -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/claude-review/diagnostics/prototype.py
```

Preparation checks passed: unchanged full-notebook cell sources and archived smoke hashes; 15 timeout tests; 13 isolated animation protocol checks. Timeout tests emit `ResourceWarning` messages about unclosed pipes. No full model evaluation or new GPU result was produced. The 100-episode replay result is from the earlier investigation and was checked for internal consistency here; the full replay was not repeated during preparation.

## Git boundary

`.gitignore` now contains exactly `/downloads/results.zip` as the added rule. The archive is not indexed and has no path history in the locally available refs. No staged files or staged large artifacts were present; no current indexed file or non-ignored untracked file was at least 10 MiB. The existing tracked `downloads/franzen-smoke-evidence.zip` is 256,845 bytes and is retained as baseline verification evidence.

The high-impact report, this small review bundle, timeout intervention, timeout fixture/tests, and two preceding research reports are currently untracked. They are available for local Claude review but will not appear in a remote review until explicitly included in a later commit. Nothing was staged or committed here. Ordinary `git add` excludes `results.zip`; a deliberate forced add can override the rule. Keep model weights, credentials, generated notebooks and full transcripts outside the review set. Existing `.kaggle/`, `local_output/`, `environment_files/`, recordings and baseline-generated outputs remain ignored.

The baseline and timeout intervention were preserved. This preparation adds no harness behavior. Any implementation, GPU screen or submission requires a separate instruction.
