# Preserve committed helpers on hard timeout

Implemented as a separate, **default-off** candidate. No submitted notebook,
baseline builder, cached upstream source, action path, or deadline is edited.

The source of truth is the tracked, SHA-pinned
`arc-agi-3-milestone-2-solution.ipynb`. Its cell 2 writes Franzen's release patch;
cell 4 copies the Kaggle source bundle and applies it. The existing isolated
builder, `baselines/franzen_m2_v3/prepare.py`, preserves all 23 released cells.
The starter `scripts/build_notebook.py` is a different pipeline and is unused.

`build.py` preserves those same 23 cell sources and inserts one overlay cell
immediately after release patch application, before bundled modules are imported.
The overlay embeds `patch.py` verbatim. It checks full hashes of the two expected
post-release files, checks unique anchors, compiles both replacements, then writes
only to that fresh working bundle. Unexpected input fails before either write.
These pins identify the locally inspected applied sources; the full mounted
Kaggle bundle has not been imported in this CPU validation.

## Switch and behavior

`ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT` is unset by default. Unset, `0`, invalid
values, or disabled function persistence preserve V3 retention behavior.
When explicitly enabled with `1` (also `true`, `yes`, `on`), the parent sandbox
supervisor adds a private marker **only** in its hard-deadline kill branch.
Child final/error messages cannot forward that marker.

The host accepts only that exact timeout envelope, with the expected error,
empty stdout, and dictionary action records. Missing/malformed metadata,
explicit exports (including `[]` or `None`), validation-rejection metadata,
and every other error follow the original recorder. The sole new branch keeps
the existing source bank and returns a notice: partial definitions were not
committed, already executed actions remain executed, and old helpers can be
wrong. Existing session/level/turn boundaries still clear according to scope.

No process locals, partial new functions, or state are restored; no action is
replayed. The marker is internal and does not change the action/result path.

Build without executing:

```sh
.venv/bin/python -m interventions.helper_timeout.build
```

Output: `local_output/helper_timeout/candidate.ipynb` (gitignored; creation is
exclusive, so an existing output is never overwritten). Generation enables no
runtime switch and starts no Kaggle session. A later authorized experiment can
set the flag in the **candidate's** customization hook before tool calls; the
original submitted notebook must remain untouched. Both A/B arms can use this
same artifact with the flag explicitly `0` versus `1` for the entire episode.

## CPU checks

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_helper_timeout.py' -v
```

The 15 tests run actual supervisor/bootstrap subprocesses and the release's
retention collector/restorer, with real host dispatch, retention, session and
level-boundary methods extracted from verified applied source. The exact turn
boundary block runs without entering the model loop. Game/file serialization,
action-name mapping and output display use small fixtures; segmentation raises
if invoked. This is not a complete upstream import or gateway/game evaluation.

Tests require the existing two source caches under
`local_output/research_refs/franzen/ARC3-Inference/inference/agent/`. They check
their hashes and every release-patch post-image hunk before execution. Retention
and frame-diff utility sources come directly from new-file hunks in the tracked
notebook. Missing/drifted fixtures fail rather than silently skip or download.

Results, unchanged baseline verification, risks and the A/B decision are in
[the decision report](../../docs/score-intervention-decision.md#6-实施与-cpu-验证2026-10-28).
