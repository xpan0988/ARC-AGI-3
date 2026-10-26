# Franzen Milestone 2 Version 3 baseline

This is an isolated reproduction path for [Daniel Franzen's released notebook](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution), **Version 3 / script version 354920985**. It does not use or modify the starter agent builder. Measured execution evidence and hashes are recorded in `run-record.json`.

**27 October 2026 status: one approved full validation is RUNNING.** [Version 3 / script version 362506200](https://www.kaggle.com/code/panxiyuan/franzen-m2-v3-baseline?scriptVersionId=362506200) was created with **Save & Run All** at 00:25:08 AEDT. Immediately before saving, the editor export was byte-identical to the verified Version 2 candidate (SHA-256 `f8e3bf0065a198e6508f738546941d67454eeac74236f244a4de9ee9dc51f4fc`); all 23 released sources and five inputs are preserved. The server became ready after 511 seconds and the benchmark started at elapsed 568 seconds, with GPU memory 91.1/95.6 GiB. Completion, nine-hour compliance, final game results and post-run quota remain pending. See `full-validation-run.json` for this execution and its 30-minute completion checks. A second full run and competition submission are not authorized.

The [saved smoke, Version 1](https://www.kaggle.com/code/panxiyuan/franzen-m2-v3-baseline?scriptVersionId=362494227), ran offline on RTX PRO 6000: one RESET plus three model-generated UP actions, 6,881 generated tokens over seven model calls, and a 47-second ready-server episode. All three returned 64×64 frames differ by 52 cells. The four-action cap ended the episode at zero completed levels; this is an initialization test, not a performance result.

The [full candidate, Version 2](https://www.kaggle.com/code/panxiyuan/franzen-m2-v3-baseline?scriptVersionId=362495586), was saved **without execution** and is the exact source of the running Version 3. Its downloaded export matches all 23 released cell sources, retains all five input versions, and has no stale outputs. The earlier interactive smoke session was stopped; quota changed from 30h to **29h29m available before the full run**. No official submission or leaderboard result exists.

Cold input reads were substantially slower than the author's run: 1,190 seconds for weight loading and 1,370 seconds for server startup. The first episode expired with a warm-up RESET and zero generated tokens; the successful episode reused the loaded server. Notebook execution through postflight took 25m28s; total charged GPU usage including startup/export was approximately **31 minutes**. Quick Save's displayed 13-second/zero-second runtimes describe snapshot packaging, not model execution. Nine-hour completion and hidden-game behavior remain unverified.

## Build locally

From `/Users/xiyuanpan/ARC-AGI-3`:

```bash
python3.12 baselines/franzen_m2_v3/prepare.py
python3.12 baselines/franzen_m2_v3/verify.py
```

The input is the existing root-level `arc-agi-3-milestone-2-solution.ipynb`, pinned by SHA-256. No weights, packages, or network resources are downloaded. Outputs are:

- `generated/franzen_m2_v3_full.ipynb`: all 23 released cell sources unchanged; saved execution outputs removed; GPU metadata corrected to RTX PRO 6000 with internet disabled.
- `generated/franzen_m2_v3_smoke.ipynb`: the same harness with an input preflight, one `ls20` episode, one pass, four-action cap and eight-minute gameplay limit. These execution limits are never included in the full notebook.
- `generated/source-manifest.json`: source and output hashes, each original cell hash, and exact exported Kaggle input version IDs.

`generated/` is gitignored. `release-lock.json` records runtime and mounted model metadata hashes. The existing notebook builders and original/legal/memory policy selection remain separate.

The verifier requires the downloaded `generated/franzen-smoke-evidence.zip`. It checks the actual saved artifact hashes, model response tokens, action/observation transitions, and reference source parity; it runs without model dependencies. The local evidence is in `generated/evidence/ready_smoke/`, with the executed notebook in `generated/executed-smoke.ipynb` and the round-tripped full candidate in `generated/kaggle-full-candidate.ipynb`. Input preflight, offline installation, inference and the parquet schema were verified on Kaggle. Local validation also passed 18 Stage 1/2 tests (one opt-in integration test skipped) and all three existing starter notebook builds.

The generated smoke waits for server health before starting its gameplay clock, with an additional 15-minute cold-start allowance after the released launcher returns. This is smoke-only orchestration. The full notebook remains byte-identical at the cell-source level to the release.

## Exact release configuration

| Component | Released setting |
|---|---|
| Target | Intel Qwen3.8-Flash-Next W4A16 AutoRound INT4; BF16 PLE table offloaded to host RAM; Kaggle Transformers V1 |
| Draft | Albucino MTP routed experts, compressed-tensors symmetric INT4 group32; two shards; Kaggle Transformers V1 |
| Speculation | NEXTN, three steps, top-k 1, four draft tokens, acceptance thresholds 1.0/1.0, pinned 64k FR-Spec token map |
| Runtime | Pennyroyal 2.5.3; SGLang `0.5.19+gd00d88efc8d6`, Torch `2.13.0+cu130`, CUDA toolkit `13.0.88`; bundled custom wheel |
| Hardware | One RTX PRO 6000 Blackwell Server Edition, approximately 95.6 GiB VRAM; approximately 177 GiB host RAM |
| Server | 139,264-token context; BF16 activations, FP8 E4M3 KV; static memory fraction .96; ten requests; 8,192-token prefill chunks; 16,384 prefill-token limit |
| Cache | Mamba extra-buffer strategy, 60 cache states, 64-token tracking; longest-prefix scheduling; sparse prefill checkpoints and final-unlock LRU patch |
| Harness | 131,072 context; 12,288 max output; 59,392-token drain; 150 assistant turns / 30-turn drain; preserve reasoning history |
| Sampling | Temperature .7, top-p .95, top-k 20; thinking enabled |
| Scheduling | Ten active streams; released progress/cache priority and tail fade; 120 game tasks in competition mode |
| Gameplay | Released prompts, perception, animation/difference tools, persistent functions and execution guards; no new exploration heuristics |
| Full scope | Four passes over 25 demo games in ordinary execution; one pass over gateway games in an actual submission; competition budget 532 minutes after setup |

Do not replace the patched wheel with stock SGLang. It includes low-M GEMM, speculative memory accounting, Marlin scale compatibility, prefix retention, and bounded checkpoint prefetch changes. Do not reapply those patches. The notebook applies its separate harness patch to the attached original Tufa source bundle.

The author's saved demonstration run used about **93.4–94.5 / 95.6 GiB VRAM**, up to about **125 GiB / 177 GiB RAM**, and finished in **8h21m48s** including setup. This is the author's execution, not our measured full-run result. Its displayed notebook competition score is **33.68**; it does not establish the author's latest team score or our future score.

The release does not set a fixed server seed and uses stochastic sampling. Reproduction means pinned source, artifacts and configuration; identical trajectories or scores are not guaranteed. Preserve the automatically selected server seed from `serve.log` in the run record.

## Kaggle inputs and environment

Copy the exact released version. Retain all five attached inputs and their selected versions:

1. Competition `arc-prize-2026-arc-agi-3` (source ID 133468).
2. Dataset `dfranzen/pennyroyal-v253` (offline wheels, requirements lock and token map).
3. Dataset `dfranzen/taaf-kaggle-source-bundle-copy` (original sources, benchmark and deployment pickles).
4. Model `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1`.
5. Model `dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1`.

The exported dataset version IDs are **20092813 and 20134793**; model instance version IDs are **1007514 and 1007009**. Preserve the exported manifest association; do not silently update inputs. Exact mounted paths are in `preflight.py`. No model weights belong on the Mac: the attached target/draft weight files total approximately **185.34 GB decimal**.

Session options: **GPU RTX Pro 6000**, **Internet off**, **Pin to original environment (2026-05-27)**. The installed runtime needs Linux x86-64 / Python 3.12. Both `pip --no-index` and bundled `uv` offline installation are used; no external model API is required. The OpenAI-compatible endpoint is a local SGLang server at `127.0.0.1:8001`.

## Smoke and full-run procedure

The private smoke copy uses the same released model/launcher. Browser file import was unavailable because Chrome extension file access was disabled; equivalent bounded smoke cells were entered through the editor. The executed smoke notebook must be archived separately from the generated smoke variant; their source bytes are not assumed equal.

Before a full run, inspect the smoke record for input checks, successful server health, at least one **model-generated non-RESET action**, its resulting frame, absence of inference errors, and a stopped GPU session. A RESET alone is insufficient.

After readiness is confirmed with the user:

1. Open a pristine Version 3 copy, or import `generated/franzen_m2_v3_full.ipynb`. Verify all five inputs and session options above. Do not run the bounded smoke notebook as a submission.
2. Open the [prepared editor](https://www.kaggle.com/code/panxiyuan/franzen-m2-v3-baseline/edit). Use **Save Version → Save & Run All** for the full ordinary notebook execution. Allow approximately **8.5–9 GPU hours** given the observed cold startup; the demo run is a separate expense from the later competition rerun. The full concurrency/throughput and nine-hour limit still need this validation. Current machine availability is not guaranteed by remaining quota.
3. Check that the saved version finishes successfully, with no cell traceback, and offers `/kaggle/working/submission.parquet` in Outputs. Record Kaggle notebook ID/version, start/end/duration, input versions and source hashes.
4. After explicit submission approval, choose **Submit to Competition**, select **ARC Prize 2026 – ARC-AGI-3**, the completed notebook version, and **`submission.parquet`**. Kaggle reruns the code with its competition gateway and `KAGGLE_IS_COMPETITION_RERUN` set.
5. Confirm successful evaluation in the competition **Submissions** tab; record the returned public leaderboard score and any reported runtime. Leave score unset until that result exists.

The ordinary offline notebook writes a **one-row placeholder parquet** with `row_id`, `game_id`, `end_of_game`, `score`. It is a format/commit artifact, not evidence of competition performance. During official evaluation, the competition gateway records actual actions and generates the real submission artifact. Do not edit or substitute fabricated scores.

## Licenses and attribution

The [Franzen notebook/repository](https://github.com/da-fr/arc-agi-3-solution/tree/10882e332d883af3e61616df8c8a17d03a328a75) is Apache-2.0. Retain Daniel Franzen's attribution and credit Jeroen Cottaar / Tufa Labs for Duck. Also retain notices from John Pezzulli, Mamy Ratsimbazafy, Gabriel Olympie and bundled dependencies; the inference stack contains separately licensed components.

The [Intel](https://huggingface.co/Intel/Qwen3.8-Flash-Next-W4A16-AutoRound) and [Albucino](https://huggingface.co/albucino/Qwen3.8-Flash-Next-W4A16-FP8PLE) model cards identify **Qwen Community License 1.0**, not Apache-2.0. Preserve its copyright/permission notice; it includes additional commercial service conditions. Use the attached released quantizations and retain their notices rather than relabeling model weights under the harness license. [Model license](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE).
