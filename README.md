# ARC Prize 2026 — Local Dev Starter

**Go from zero to your first Kaggle submission in about 10 minutes, without
ever opening the Kaggle notebook editor.**

This is a starter kit for the [ARC Prize 2026 — ARC-AGI-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
competition. You'll edit one Python file on your laptop, see it actually play
the real game environments locally, and push it to Kaggle as a submission with
a single command.

No Docker. No `submission.json` to hand-write. No copy-pasting between your
editor and a notebook.

---

## What you need before you start

- **Python 3.12** (the competition's `arc-agi` package requires it)
  - macOS: `brew install python@3.12`
  - Ubuntu: `sudo apt install python3.12 python3.12-venv`
  - Windows: install from [python.org](https://www.python.org/downloads/)
- **git** (to clone the official agent framework)
- **A Kaggle account** with the competition rules accepted
  ([accept here](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules))

That's it. No GPU required for the starter agent.

---

## Quick start

```bash
# 1.  Clone this repo and step in
git clone https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter.git
cd ARC-AGI-3-Kaggle-Starter

# 2.  Drop your Kaggle API token (kaggle.com → Settings → Create New Token)
#     into the project-local .kaggle/ folder (NOT your home directory)
mkdir -p .kaggle && echo "KGAT_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" > .kaggle/access_token
chmod 600 .kaggle/access_token

# 3.  One-time setup: venv, dependencies, framework
make setup

# 4.  Open agent/my_agent.py to see the random-action starter, then edit
#     it to make a better submission. This is the only file you change.

# 5.  Run it locally against every game in the competition (takes seconds)
make play-local

# 6.  Push it to Kaggle as a submission notebook
make submit

# 7.  Watch the run
make status

# 8.  When status shows "complete", open the notebook on kaggle.com,
#     find your kernel, click "Submit to Competition" in the top
#     right, and pick `submission.parquet` from the Output File
#     dropdown. That's one of your 5 daily submissions.
```

That's the entire loop. Steps 4–7 are what you'll repeat as you iterate;
step 8 is the deliberate moment when you spend a daily submission.

---

## The one file you edit: `agent/my_agent.py`

This is the only file you normally touch. It defines a class called `MyAgent`
with two methods:

```python
class MyAgent(Agent):
    def is_done(self, frames, latest_frame) -> bool:
        """Return True when your agent wants to stop playing."""
        ...

    def choose_action(self, frames, latest_frame) -> GameAction:
        """Look at the game state and return the next action."""
        ...
```

The starter version picks random actions — a baseline that proves your whole
pipeline works end-to-end. Replace the body of `choose_action` with your
strategy. Everything else (Kaggle plumbing, submission file format, game
orchestration) is handled for you.

---

## What happens when you run `make submit`

The competition is a *code* competition: you submit a notebook, Kaggle runs it
twice.

```diagram
   make submit
       │
       ▼
   ┌─────────────────────────────────────┐
   │  Kaggle Phase A: Save & Run All     │
   │  ─ Runs your notebook in their      │
   │    real environment                 │
   │  ─ Validates that your code         │
   │    executes without errors          │
   │  ─ make status shows "complete"     │
   └─────────────────┬───────────────────┘
                     │
                     │  You click "Submit to Competition"
                     │  on the kernel page
                     ▼
   ┌─────────────────────────────────────┐
   │  Kaggle Phase B: Competition Rerun  │
   │  ─ Your agent actually plays the    │
   │    hidden game set                  │
   │  ─ Your leaderboard score appears   │
   └─────────────────────────────────────┘
```

`make submit` builds and uploads the notebook (Phase A). After
`make status` reports `complete`, open the kernel on kaggle.com and click
**"Submit to Competition"** to enter Phase B and get a leaderboard score.

> **You only get 5 official submissions per day**, so it pays to be
> confident before you submit: get `make play-local` passing, then submit.

> **Heads up:** Before your first `make submit`, open
> [`notebooks/kernel-metadata.json`](notebooks/kernel-metadata.json) and
> replace `REPLACE_WITH_YOUR_USERNAME` with your Kaggle handle. The Makefile
> will refuse to push until you do.

### Choosing an accelerator

The notebook is generated with a **T4 GPU** by default (matches Kaggle's
sample submission). To change it, open
[`scripts/build_notebook.py`](scripts/build_notebook.py) and edit **one
line** near the top:

```python
ACCELERATOR = "t4"     # change "t4" to one of: cpu, t4, p100, rtx6000
```

Then re-run `make submit`. That's it — both the notebook metadata and
[`notebooks/kernel-metadata.json`](notebooks/kernel-metadata.json) get
updated automatically.

| Value | Hardware | When to use |
|---|---|---|
| `"cpu"` | No GPU | The random starter, or any non-ML agent |
| `"t4"` | Nvidia T4 ×2 | **Default.** Small models, fast iteration |
| `"p100"` | Nvidia P100 | Single big-memory GPU |
| `"rtx6000"` | Nvidia RTX 6000 (`g4-standard-48`) | Heavy ML; **ARC-AGI-3 exclusive**, burns GPU quota faster |

RTX 6000 is reserved for ARC-AGI-3 notebooks only — don't use it for early
iteration. All accelerated Kaggle sessions have internet disabled, which is
already the default in this kit.

---

## All the commands

### Local observation tracing (Stage 1)

Tracing is opt-in and leaves the random policy and submission agent unchanged:

```bash
.venv/bin/python scripts/play_local.py --game ls20,vc33 --max-steps 50 --seed 42 --trace
# Use the run directory printed above:
.venv/bin/python scripts/visualize_trace.py local_output/traces/run-XXXX/ls20.jsonl
.venv/bin/python scripts/visualize_trace.py local_output/traces/run-XXXX/vc33.jsonl
.venv/bin/python -m unittest discover -s tests -v
ARC_LOCAL_INTEGRATION=1 OPERATION_MODE=offline .venv/bin/python -m unittest discover -s tests -v
make verify-local
make notebook                       # Builds locally; does not submit
```

JSONL and PNGs stay under gitignored `local_output/`. Each run gets a new
directory; each game gets one JSONL file. Images are written beside the trace
in `<game>-images/`. Open any PNG with Preview; `--limit 10` renders only the
first ten transitions. `--scale 8` changes the integer cell size (minimum 5).
Pillow is already installed by the local `arc-agi` dependency tree.

Without `--trace`, the runner uses the original class and loop, imports no
tracer or image code, performs no snapshots/diffs/hashes, and creates no trace
directory. `--seed` is separately opt-in: it seeds Python's policy RNG after
agent initialization using `"<seed>:<short-game-id>"`. Default seeding remains
unchanged. Repeatability requires the same engine, game versions, and run
settings; this does not promise identical runs on Kaggle.
The opt-in integration test runs both cached games with and without tracing,
compares seeded requests and observations, and independently checks cell
counts/bounding boxes with NumPy. Normal arcade startup can request an anonymous
API key even with cached games; use `OPERATION_MODE=offline` before the play or
verify command when network access is unavailable and games are already cached.

#### Actual interfaces and transition semantics

Inspected locally with `arc-agi 0.9.9` and `arcengine 0.9.3`:

- `FrameData.frame` is `list[list[list[int]]]`: ordered rendered frames,
  then rows (`y`), then columns (`x`). One action can return multiple animation
  frames. The local raw interface is `FrameDataRaw`, whose `frame` property is
  a list of NumPy arrays stored privately; `model_dump()` alone omits those
  grids. The vendor agent converts them with `tolist()`.
- Public metadata: `game_id`, `state`, `levels_completed`, `win_levels`,
  `guid`, `full_reset`, `available_actions`, and `action_input`. There is no
  public current-level index in `FrameData`; do not infer one from the score.
  States are `NOT_PLAYED`, `NOT_FINISHED`, `GAME_OVER`, and `WIN`.
- `GameAction` IDs are RESET=0 and ACTION1–ACTION7=1–7. Only ACTION6 is
  complex: `x` and `y` are integers from 0 through 63. All action-data models
  also contain `game_id` (default empty). Reasoning is attached to mutable
  enum members; the framework wraps string reasoning as `{"text": ...}`
  before `env.step(action, data=..., reasoning=...)`.
- `arc.make()` initializes the local environment with a reset before the
  agent loop. The first trace's `before` is the observation actually passed
  to `choose_action`, not the synthetic empty `agent.frames[0]`. That setup
  reset is not counted as an agent action. Each record's `after` is the
  result returned by `take_action`; ordinarily it equals the next `before`.
- The vendor conversion **drops `action_input`**, leaving a misleading default
  RESET. Traces omit that field and capture the actual outgoing action/data
  before execution. Full arrays and public metadata are snapshotted before
  policy selection and after execution, avoiding mutable enum/frame aliasing.
- The baseline resets on `NOT_PLAYED` or `GAME_OVER`, continues across level
  completions, and stops on `WIN`. Generic engine reset handling normally
  resets the current level after actions have been taken; zero-action and
  post-win resets are full resets. `ONLY_RESET_LEVELS=true` changes that
  behavior. The trace records `full_reset` and progress without guessing.
- Existing baseline quirks are preserved: LS20 biases ACTION4; the policy
  samples all non-RESET enum actions, **not** just `available_actions`.
  The vendor loop uses `action_counter <= MAX_ACTIONS`, so a requested cap of
  50 normally executes 51 actions, with trace steps 0–50. The runner takes
  `min(MyAgent.MAX_ACTIONS, --max-steps)`, so larger requested caps still
  respect the agent's current cap of 80. The baseline's time/hash seed is not
  reproducible across runs despite its source comment; use local `--seed`.

#### Trace schema and differences

Each JSONL line is a complete interaction (`schema_version: 1`): `game_id`
(requested short ID), zero-based `step`, optional `policy_seed`, `action`
(`id`, `name`, `data`, normalized `reasoning`), `before`, `after`, `diff`, and
`status`. Snapshots retain the versioned public `game_id`. Errors are recorded
with `after: null`, an error type/message, and then re-raised; no next
observation is invented. A rejected frame can have `status: no_observation`.

- `diff.observation_changed`: any captured observation or metadata changed.
- `diff.frames_changed`: full ordered frame stacks differ, including length.
- `diff.final_grid`: compares only the last frame before/after the action.
  It contains `[rows, columns]` shapes, `comparable`, `changed_cells`, and an
  inclusive `[xmin, ymin, xmax, ymax]` bounding box. No changes means count 0
  and bbox null. Missing, empty, ragged, or differently sized grids mean
  count/bbox null and `comparable: false`, not zero changes. Intermediate
  animation can change even when the final-grid count is zero.
- `grid_fingerprint` hashes the complete ordered frame stack; `fingerprint`
  also includes state, levels completed, win levels, and available actions.
  Both use the first 16 hex characters of SHA-256 over sorted-key compact JSON.
  The latter excludes GUID and the reset-event flag to help detect repeated
  observations across resets. These are observable-state hints, not proof
  of identical hidden state; collisions are possible.

#### Images and stable colors

Each `00000-001.png` is an action/subframe comparison. The left panel starts
with the prior observation's last grid; subsequent panels compare the
previous animation subframe. The right panel shows the new subframe. All
returned subframes are rendered, preserving row/column coordinates and
integer-sized square cells with no interpolation. Cyan borders with a black
outer edge mark changed cells in both panels while preserving their interior
colors. Header text identifies action parameters, step, state/progress, and
the **pair-specific** diff; metadata describes the whole action response,
since intermediate state metadata is not exposed. Legends label cell values.

This is a categorical debugging palette, not an engine-renderer palette:

| Value | Hex | Value | Hex |
|---|---|---|---|
| 0 | `#000000` | 8 | `#7FDBFF` |
| 1 | `#0074D9` | 9 | `#870C25` |
| 2 | `#FF4136` | 10 | `#FFFFFF` |
| 3 | `#2ECC40` | 11 | `#6B4C9A` |
| 4 | `#FFDC00` | 12 | `#8B5A2B` |
| 5 | `#AAAAAA` | 13 | `#008080` |
| 6 | `#F012BE` | 14 | `#B8D346` |
| 7 | `#FF851B` | 15 | `#E6B8D7` |

Other integers use the first six SHA-256 hex characters of their decimal ASCII
representation. The renderer rejects color collisions within a comparison
instead of silently merging values. Raw integers always remain in JSONL.
Traces duplicate before/after arrays for simple inspection, so long runs can
grow large; image generation is a separate command with no play-loop cost.

#### Submission isolation

`scripts/build_notebook.py` embeds only `agent/my_agent.py` as source in a
`%%writefile /tmp/my_agent.py` cell. The notebook installs offline competition
wheels, copies the competition-provided framework at runtime, registers
`MyAgent`, and runs the gateway path (or writes a dummy parquet outside a
competition rerun). Local scripts, tests, traces, images, and the local vendor
checkout are not bundled. Local tests and notebook generation do not qualify
an actual Kaggle gateway run or hidden-game behavior.
Stage 2 adds an optional policy selector to the embedded source; all three
policies and their helpers remain in that same file, with `original` default.

Stage 1 local verification: both LS20 and VC33 completed the normal smoke run
and the seed-42 traced run (51 actions each, zero levels, aggregate score 0.0).
All 102 saved transitions passed independent ordering, fingerprint, cell-count,
and bounding-box checks. The 102 generated PNGs included inspected examples
from both games. Ten tests passed with real-game integration enabled, and
`make notebook` passed. Reset/death/win transitions and multi-frame responses
were covered with synthetic fixtures; the sampled real runs did not reach
those states. No Kaggle execution or submission was performed.

### Active exploration and memory baselines (Stage 2)

Three independently selectable policies share the official agent loop:

- `original`: the unchanged starter control, including its LS20 bias and
  sampling beyond advertised actions.
- `legal`: uniformly samples advertised known non-reset actions; ACTION6
  coordinates are uniform in 0–63. RESET is used for death/not-played recovery
  or when no usable action is advertised. WIN stops the loop.
- `memory`: legal actions plus per-game transition/visit memory, under-tested
  action preference, no-effect penalties, short-cycle avoidance, and 10%
  legal-random exploration. ACTION6 uses 64 spatial bins for coverage, with
  uniform coordinates within each bin. No new game-ID-specific rules.

```bash
OPERATION_MODE=offline make play-local GAME=ls20 POLICY=memory
OPERATION_MODE=offline .venv/bin/python scripts/play_local.py \
  --game ls20,vc33 --policy legal --seed 42 --trace
make notebook POLICY=memory             # Local build only
make notebook                           # Restore default original-policy artifact

# Full paired experiment on all cached games, with exact equal action budgets:
OPERATION_MODE=offline .venv/bin/python scripts/evaluate_policies.py \
  --seeds 0,1,2 --actions 256 --replicates 2
# Small reproducibility check:
OPERATION_MODE=offline .venv/bin/python scripts/evaluate_policies.py \
  --games ls20,vc33 --seeds 0 --actions 32 --replicates 2
```

The experiment prints a fresh `local_output/experiments/stage2-*` directory
containing a version/seed/source-hash manifest, compressed Stage 1 JSONL traces,
memory transition records, per-run JSON/CSV, and aggregate/per-game Markdown.
It fixes the public environment seed and NumPy global RNG seed at 0 per run;
the policy seeds vary independently. The simpler local runner's `--seed`
continues to seed the policy RNG only.
`visualize_trace.py` accepts both `.jsonl` and `.jsonl.gz` without changing the
Stage 1 schema. Runtime includes tracing and compression; initialization and
post-run analysis are excluded. Only replicate 0 contributes to outcome tables;
subsequent replicates verify full normalized traces, excluding only GUIDs.

The evaluator is offline and evaluates **all cached games**, not necessarily
all public games. To populate the cache via the official wrapper first:

```bash
.venv/bin/python scripts/play_local.py --list
.venv/bin/python scripts/play_local.py --max-steps 0
```

The latter initializes each catalog game and takes one action under the
existing runner's inclusive cap. No environment implementation source needs
to be read. See [the Stage 2 experiment report](docs/stage2-exploration.md) for
the fixed policy design, metric definitions, comparative results and limits.

### Workflow commands

| Command | What it does |
|---|---|
| `make setup` | One-time install: Python venv, `arc-agi`, `kaggle` CLI, clones the framework |
| `make play-local` | Runs your agent against every game in the dataset, locally |
| `make play-local GAME=ls20` | Same, but only one game (faster while debugging) |
| `make verify-local` | 30-second smoke test on two games |
| `make list-games` | Print every game id available |
| `make pull-sample` | Download the official sample agent for reference |
| `make notebook` | Build the Kaggle notebook from your agent (no push) |
| `make submit` | Build the notebook **and** push it to Kaggle |
| `make status` | Check the status of your most recent Kaggle run |
| `make clean` | Remove the venv, downloads, and generated notebook |

---

## Why this setup, instead of editing in the Kaggle notebook?

Three reasons:

1. **Iteration speed.** Editing in your normal IDE, then `make play-local`,
   gives you a real-game-engine feedback loop in seconds. The Kaggle editor's
   loop is *minutes* per change.
2. **No environment surprises.** The local `arc-agi` PyPI package hosts the
   same game engine the Kaggle gateway runs. If it works locally, it works on
   Kaggle.
3. **Your code stays in git.** Notebooks are awful for diffs and code review.
   Here your real work lives in [`agent/my_agent.py`](agent/my_agent.py); the
   notebook is just an auto-generated deployment artifact.

---

## Project layout

```
.
├── agent/
│   └── my_agent.py             ★ The file you edit
├── scripts/
│   ├── play_local.py           Runs your agent against real games
│   ├── build_notebook.py       Packages your agent into a Kaggle notebook
│   └── slim_framework.py       Trims framework deps so install is light
├── notebooks/
│   ├── kernel-metadata.json    Edit once: your Kaggle username
│   └── submission.ipynb        Auto-generated, never edit by hand
├── vendor/                     Cloned framework (gitignored)
├── .venv/                      Python 3.12 venv (gitignored)
├── .kaggle/                    Your project-local Kaggle token (gitignored)
└── Makefile
```

---

## Troubleshooting

**`make setup` fails: `python3.12: command not found`**
Install Python 3.12 — the `arc-agi` package requires it. macOS:
`brew install python@3.12`.

**`make submit` says "edit kernel-metadata.json"**
You haven't replaced `REPLACE_WITH_YOUR_USERNAME` in
[`notebooks/kernel-metadata.json`](notebooks/kernel-metadata.json) yet.

**`make submit` says `401 Unauthorized`**
Your Kaggle token is missing or invalid. Generate a fresh one from your
[Kaggle Settings page](https://www.kaggle.com/settings) and overwrite
`.kaggle/access_token`.

**`make play-local` says "Could not create environment"**
Your machine couldn't reach the ARC-AGI API to download the game source on
first run. Check your internet, then try again — once downloaded, games are
cached in `environment_files/` and you're fully offline.

**My local score is 0.0**
That's expected for the random starter agent. Your job is to make it
non-zero. 🙂

---

## Where to go next

- Read the [ARC-AGI-3 docs](https://docs.arcprize.org/) to understand the
  benchmark.
- `make pull-sample` to study Kaggle's reference agent (the same one
  currently sitting on the leaderboard).
- The competition's [discussion forum](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion)
  for community Q&A.

Good luck. Looking forward to seeing what you build.
