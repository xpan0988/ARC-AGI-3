"""Bounded, offline, paired policy experiment using Stage 1 JSONL tracing.

Defaults: every cached public game, three seeds, exactly 256 actions, two
replicates. Downloads are deliberately outside the measured experiment.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import platform
import random
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.play_local import OperationMode, arc_agi, load_my_agent_class
from scripts.observation_trace import fingerprint, traced_agent_class
from arcengine import GameAction

POLICIES = ("original", "legal", "memory")


def decision_fingerprint(observation):
    return fingerprint({**{k: observation[k] for k in
                           ("state", "levels_completed", "win_levels", "available_actions")},
                        "frame": observation["frame"][-1:]})


def measure_trace(path):
    """Stream metrics from saved public observations, independently of policy memory."""
    seen, decision_seen = set(), set()
    digest = hashlib.sha256()
    result = dict(actions=0, repeats=0, decision_repeats=0, no_change=0,
                  no_frame_change=0, resets=0, deaths=0, unadvertised=0,
                  multi_frame_responses=0, levels_completed=0, final_levels=0,
                  won=False, progress_events=[])
    previous = None
    with gzip.open(path, "rt") as stream:
        for record in map(json.loads, stream):
            if record["status"] != "ok" or record["step"] != result["actions"]:
                raise ValueError(f"Unsuccessful or out-of-order trace in {path}")
            before, after = record["before"], record["after"]
            if previous is not None and previous != before:
                raise ValueError(f"Observation discontinuity in {path}")
            if previous is None:
                seen.add(before["fingerprint"])
                decision_seen.add(decision_fingerprint(before))
                result["levels_completed"] = before["levels_completed"]
            result["actions"] += 1
            result["repeats"] += after["fingerprint"] in seen
            result["decision_repeats"] += decision_fingerprint(after) in decision_seen
            seen.add(after["fingerprint"])
            decision_seen.add(decision_fingerprint(after))
            result["no_change"] += not record["diff"]["observation_changed"]
            result["no_frame_change"] += not record["diff"]["frames_changed"]
            result["resets"] += record["action"]["id"] == 0
            result["unadvertised"] += record["action"]["id"] != 0 and record["action"]["id"] not in before["available_actions"]
            result["deaths"] += after["state"] == "GAME_OVER" and before["state"] != "GAME_OVER"
            result["multi_frame_responses"] += len(after["frame"]) > 1
            result["levels_completed"] = max(result["levels_completed"], after["levels_completed"])
            result["final_levels"] = after["levels_completed"]
            result["won"] |= after["state"] == "WIN"
            if after["levels_completed"] > before["levels_completed"] or after["state"] == "WIN":
                result["progress_events"].append({"step": record["step"], "action": record["action"],
                                                  "before_levels": before["levels_completed"],
                                                  "after_levels": after["levels_completed"],
                                                  "state": after["state"]})
            previous = after
            # Only per-environment GUID is nondeterministic. All actual actions,
            # arrays, metadata, fingerprints and differences enter the digest.
            normalized = {**record, "before": {k: v for k, v in before.items() if k != "guid"},
                          "after": {k: v for k, v in after.items() if k != "guid"}}
            digest.update(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode())
            digest.update(b"\n")
    result.update(unique_observations=len(seen), unique_decision_observations=len(decision_seen),
                  trace_digest=digest.hexdigest())
    return result


def run_one(arcade, game, policy, seed, budget, replicate, output):
    path = output / f"{game}_{policy}_seed{seed}_rep{replicate}.jsonl.gz"
    # Match fresh-process enum state and Stage 1's seed convention.
    for action in GameAction:
        action.set_data({})
        action.reasoning = None
    # The public wrapper's seed does not seed NumPy's process-global RNG.
    # Fix it before every environment construction, independently of policy.
    np.random.seed(0)
    random.seed(f"{seed}:{game.split('-')[0]}")
    env = arcade.make(game, seed=0)
    if env is None or env.observation_space is None:
        raise RuntimeError(f"Could not initialize {game}")
    with gzip.open(path, "wt", compresslevel=1) as stream:
        cls = traced_agent_class(load_my_agent_class(policy), stream, seed=seed)
        agent = cls(card_id="stage2", game_id=game.split("-")[0],
                    agent_name=f"stage2.{policy}", ROOT_URL="http://localhost",
                    record=False, arc_env=env)
        # Vendor uses <=. The experimental budget is exact and common to all
        # policies, independently of the unchanged local runner's cap semantics.
        agent.MAX_ACTIONS = budget - 1
        random.seed(f"{seed}:{game.split('-')[0]}")
        start = time.perf_counter()
        agent.main()
        runtime = time.perf_counter() - start
    metrics = measure_trace(path)
    if metrics["actions"] != agent.action_counter:
        raise ValueError("Trace and agent action counts disagree")
    if policy != "original" and metrics["unadvertised"]:
        raise ValueError("Legal policy executed an unadvertised action")
    if hasattr(agent, "memory"):
        memory_path = path.with_suffix("").with_suffix(".memory.json")
        memory_path.write_text(json.dumps({"episodes": agent.memory.episode,
                                           "cycles": agent.memory.cycles,
                                           "transitions": agent.memory.transitions}))
        if len(agent.memory.transitions) != metrics["actions"]:
            raise ValueError("Memory missed an action response")
    return dict(game_id=game, policy=policy, seed=seed, replicate=replicate,
                runtime_s=runtime, trace=path.name, status="ok", **metrics)


def aggregate(rows):
    result = []
    for policy in POLICIES:
        group = [r for r in rows if r["policy"] == policy and r["replicate"] == 0 and r["status"] == "ok"]
        actions = sum(r["actions"] for r in group)
        result.append(dict(policy=policy, runs=len(group),
                           wins=sum(r["won"] for r in group),
                           games_won=len({r["game_id"] for r in group if r["won"]}),
                           levels=sum(r["levels_completed"] for r in group),
                           games_with_progress=len({r["game_id"] for r in group if r["levels_completed"]}),
                           actions=actions,
                           repeat_rate=sum(r["repeats"] for r in group) / max(1, actions),
                           no_change_rate=sum(r["no_change"] for r in group) / max(1, actions),
                           mean_unique=sum(r["unique_observations"] for r in group) / max(1, len(group)),
                           runtime_s=sum(r["runtime_s"] for r in group)))
    return result


def write_results(rows, output, manifest):
    (output / "results.json").write_text(json.dumps(rows, indent=2))
    fields = sorted({key for row in rows for key in row} - {"progress_events"})
    with (output / "per_game.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["game_id"], row["policy"], row["seed"])].append(row)
    checked = [key for key, group in groups.items() if len(group) == manifest["replicates"]
               and len(group) > 1 and all(r["status"] == "ok" for r in group)]
    mismatches = [key for key in checked if len({r["trace_digest"] for r in groups[key]}) != 1]
    summary = {"comparison": aggregate(rows), "replication_groups_checked": len(checked),
               "replication_mismatches": mismatches,
               "failed_runs": [r for r in rows if r["status"] != "ok"]}
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    lines = ["# Policy comparison", "", "Only replicate 0 contributes to outcomes; subsequent replicates check determinism.", "",
             "| Policy | Runs | Wins | Levels (sum of per-run maxima) | Actions | Repeated | No change | Mean unique | Runtime s |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in summary["comparison"]:
        lines.append(f'| {r["policy"]} | {r["runs"]} | {r["wins"]} | {r["levels"]} | {r["actions"]} | {r["repeat_rate"]:.1%} | {r["no_change_rate"]:.1%} | {r["mean_unique"]:.1f} | {r["runtime_s"]:.2f} |')
    lines += ["", "## Per-game breakdown", "", "Means across policy seeds; levels list is in seed order.", "",
              "| Game | Policy | Levels | Wins | Mean actions | Repeated | No change | Mean unique | Runtime s |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for game in manifest["games"]:
        for policy in POLICIES:
            group = sorted([r for r in rows if r["game_id"] == game and r["policy"] == policy
                            and r["replicate"] == 0 and r["status"] == "ok"], key=lambda r: r["seed"])
            if not group:
                continue
            n, actions = len(group), sum(r["actions"] for r in group)
            lines.append(f'| {game} | {policy} | {", ".join(str(r["levels_completed"]) for r in group)} | {sum(r["won"] for r in group)} | {actions/n:.1f} | {sum(r["repeats"] for r in group)/max(1, actions):.1%} | {sum(r["no_change"] for r in group)/max(1, actions):.1%} | {sum(r["unique_observations"] for r in group)/n:.1f} | {sum(r["runtime_s"] for r in group):.2f} |')
    lines += ["", f'Replication: {len(checked)} groups checked; {len(mismatches)} mismatched; {len(summary["failed_runs"])} failed runs.', ""]
    (output / "comparison.md").write_text("\n".join(lines))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", help="Comma-separated IDs; default all cached games")
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--actions", type=int, default=256)
    parser.add_argument("--replicates", type=int, default=2)
    args = parser.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    if args.actions < 1 or args.replicates < 1 or not seeds or len(seeds) != len(set(seeds)):
        parser.error("Positive action/replicate budgets and unique seeds are required")
    logging.basicConfig(level=logging.ERROR)
    arcade = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE,
                            environments_dir=str(ROOT / "environment_files"))
    available = sorted(e.game_id for e in arcade.get_environments())
    wanted = args.games.split(",") if args.games else available
    games = sorted({g for g in available if g in wanted or g.split("-")[0] in wanted})
    if not games or any(not any(g == w or g.split("-")[0] == w for g in games) for w in wanted):
        parser.error("Requested games are not cached; use the official local runner to cache them first")
    root = ROOT / "local_output" / "experiments"
    root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="stage2-", dir=root))
    manifest = {"games": games, "policies": POLICIES, "seeds": seeds, "actions": args.actions,
                "environment_seed": 0, "numpy_seed": 0, "replicates": args.replicates,
                "python": platform.python_version(), "platform": platform.platform(),
                "packages": {p: version(p) for p in ("arc-agi", "arcengine", "numpy", "pillow")},
                "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in [ROOT / "agent/my_agent.py", Path(__file__),
                                            ROOT / "scripts/observation_trace.py"]},
                "vendor_revision": subprocess.check_output(["git", "-C", str(ROOT / "vendor/ARC-AGI-3-Agents"), "rev-parse", "HEAD"], text=True).strip(),
                "runtime_scope": "agent.main including policy, environment, tracing and gzip; excludes setup and trace analysis"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Experiment directory: {output}", flush=True)
    rows = []
    for replicate in range(args.replicates):
        for game in games:
            for seed in seeds:
                # Rotate policy order to reduce systematic warm-cache timing bias.
                order = POLICIES[(seed + replicate) % 3:] + POLICIES[:(seed + replicate) % 3]
                for policy in order:
                    try:
                        row = run_one(arcade, game, policy, seed, args.actions, replicate, output)
                    except Exception as exc:
                        row = dict(game_id=game, policy=policy, seed=seed, replicate=replicate,
                                   status="error", error=f"{type(exc).__name__}: {exc}")
                    rows.append(row)
                    with (output / "runs.jsonl").open("a") as stream:
                        stream.write(json.dumps(row) + "\n")
                    print(f'{len(rows)}: {game} {policy} seed={seed} rep={replicate}: {row["status"]} levels={row.get("levels_completed", "?")}', flush=True)
    summary = write_results(rows, output, manifest)
    print(json.dumps(summary, indent=2))
    if summary["failed_runs"] or summary["replication_mismatches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
