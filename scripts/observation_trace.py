"""Local-only synchronous observation tracing; no policy or environment changes."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy


def fingerprint(value):
    """64-bit display fingerprint, not a proof of state identity."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def snapshot(frame):
    # The vendor converter leaves action_input at its default RESET value.
    # It is not an action echo; record the actual request separately instead.
    observation = frame.model_dump(mode="json", exclude={"action_input"})
    observation["grid_fingerprint"] = fingerprint(observation["frame"])
    observation["fingerprint"] = fingerprint({
        key: observation[key] for key in
        ("frame", "state", "levels_completed", "win_levels", "available_actions")
    })
    return observation


def last_grid(observation):
    frames = observation["frame"]
    return frames[-1] if frames else None


def grid_diff(before, after):
    """Compare equal rectangular grids. Bbox is inclusive [xmin,ymin,xmax,ymax]."""
    def shape(grid):
        if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
            return None
        return [len(grid), len(grid[0])]

    before_shape, after_shape = shape(before), shape(after)
    comparable = before_shape is not None and before_shape == after_shape
    result = {"before_shape": before_shape, "after_shape": after_shape,
              "comparable": comparable, "changed_cells": None, "bbox": None}
    if comparable:
        cells = [(x, y) for y, row in enumerate(before)
                 for x, value in enumerate(row) if value != after[y][x]]
        result["changed_cells"] = len(cells)
        if cells:
            xs, ys = zip(*cells)
            result["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
    return result


def transition_diff(before, after):
    return {
        "observation_changed": before != after,
        "frames_changed": before["frame"] != after["frame"],
        "final_grid": grid_diff(last_grid(before), last_grid(after)),
    }


def traced_agent_class(base, stream, *, seed=None):
    """Wrap the two loop hooks only when explicitly requested by the runner."""
    class TracedAgent(base):
        def choose_action(self, frames, latest_frame):
            self._trace_before = snapshot(latest_frame)
            return super().choose_action(frames, latest_frame)

        def take_action(self, action):
            # GameAction members and their data/reasoning are mutable singletons.
            # Freeze them before execution (and before the next selection).
            reasoning = getattr(action, "reasoning", None)
            if reasoning is not None and not isinstance(reasoning, dict):
                reasoning = {"text": str(reasoning)}
            record = {
                "schema_version": 1, "game_id": self.game_id,
                "step": self.action_counter, "policy_seed": seed,
                "action": {"id": action.value, "name": action.name,
                           "data": deepcopy(action.action_data.model_dump(mode="json")),
                           "reasoning": deepcopy(reasoning)},
                "before": self._trace_before, "after": None, "diff": None,
                "status": "ok",
            }
            try:
                frame = super().take_action(action)
                if frame is not None:
                    record["after"] = snapshot(frame)
                    record["diff"] = transition_diff(record["before"], record["after"])
                else:
                    record["status"] = "no_observation"
            except Exception as exc:
                record["status"] = "error"
                record["error"] = {"type": type(exc).__name__, "message": str(exc)}
                raise
            finally:
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
                stream.flush()
            return frame

    # Preserve the baseline's name property, which uses the class name.
    TracedAgent.__name__ = base.__name__
    return TracedAgent
