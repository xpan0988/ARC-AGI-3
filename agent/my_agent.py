"""Your ARC-AGI-3 agent. This is the *only* file you should normally edit.

`scripts/build_notebook.py` splices the contents of this file into the
Kaggle submission notebook, so your local dev loop and your Kaggle
submission stay in lock-step:

    [edit my_agent.py] → [make play-local] → [make submit]

The default body below is a port of the Stochastic Goose / random_agent
sample — a known-good baseline that produces a valid submission and
proves your end-to-end pipeline works. Replace `choose_action` with your
real strategy.

Contract (enforced by the ARC-AGI-3-Agents framework):
  - Subclass `agents.agent.Agent`.
  - Class must be named `MyAgent` (the notebook's __init__.py registers it).
  - Implement `is_done(frames, latest_frame) -> bool`.
  - Implement `choose_action(frames, latest_frame) -> GameAction`.
"""
from __future__ import annotations

import random
import time
import hashlib
import json
import math
from collections import Counter, deque
from typing import Any

from arcengine import FrameData, GameAction, GameState

# When run inside the ARC-AGI-3-Agents framework (locally or on Kaggle)
# the `agents` package is on sys.path, so this import resolves.
from agents.agent import Agent


class MyAgent(Agent):
    """Picks legal actions uniformly at random. Replace with your strategy."""

    # Upper bound on actions per game; the framework also enforces global limits.
    MAX_ACTIONS = 80

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Seed per game_id so replays from the same game are reproducible but
        # different games explore independently.
        seed = int(time.time() * 1_000_000) + hash(self.game_id) % 1_000_000
        random.seed(seed)

    @property
    def name(self) -> str:
        return f"{super().name}.{self.MAX_ACTIONS}"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        # Stop once we win. Don't stop on GAME_OVER — we want to RESET and retry.
        return latest_frame.state is GameState.WIN

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        # First call or after a death → reset the level.
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return GameAction.RESET

        # ── Per-game strategy fork ───────────────────────────────────────────
        # By default every game uses the same uniformly-random strategy in the
        # `else` branch below. This `if` shows ONE example of giving a single
        # game its own heuristic: on LS20 we bias the random pick so ACTION4
        # is twice as likely as any other action. Add more `elif` branches to
        # specialize other games.
        #
        # `self.game_id` is set by the framework. It may be the short id
        # ("ls20") or include a version suffix ("ls20-9607627b"), so we
        # compare on the prefix to be safe.
        candidate_actions = [a for a in GameAction if a is not GameAction.RESET]
        if self.game_id.split("-")[0] == "ls20":
            weights = [2 if a is GameAction.ACTION4 else 1 for a in candidate_actions]
            action = random.choices(candidate_actions, weights=weights, k=1)[0]
        else:
            action = random.choice(candidate_actions)
        # ────────────────────────────────────────────────────────────────────

        if action.is_complex():
            # ACTION6 takes (x, y) coordinates on a 64×64 grid.
            action.set_data(
                {"x": random.randint(0, 63), "y": random.randint(0, 63)}
            )
            action.reasoning = {"why": "random complex action"}
        else:
            action.reasoning = f"random simple action: {action.value}"
        return action


# Stage 2 policies live in this same file because the notebook embeds only it.
# MyAgent above remains the original control, including its LS20 weighting.
def advertised_actions(frame: FrameData) -> list[GameAction]:
    """Deduplicate known advertised actions; RESET is reserved for recovery."""
    return [action for action in GameAction
            if action is not GameAction.RESET and action.value in frame.available_actions]


def prepare_action(action: GameAction, data: dict | None = None) -> GameAction:
    """Avoid carrying mutable enum data/reasoning over from another decision."""
    action.set_data(data or {})
    action.reasoning = None
    return action


class LegalRandomAgent(MyAgent):
    """Uniform advertised-action sampling, with uniform legal coordinates."""

    def choose_action(self, frames, latest_frame):
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER, GameState.WIN):
            return prepare_action(GameAction.RESET)
        choices = advertised_actions(latest_frame)
        if not choices:
            # RESET is the protocol recovery action even when not advertised.
            return prepare_action(GameAction.RESET)
        action = random.choice(choices)
        data = ({"x": random.randint(0, 63), "y": random.randint(0, 63)}
                if action.is_complex() else {})
        return prepare_action(action, data)


def observation_key(frame: FrameData, *, full_stack: bool = False) -> str:
    """Observable identity, never hidden-state identity or a progress estimate.

    Decisions use the final rendered grid, avoiding animation-path identity.
    Full-stack identity separately detects transient observable responses.
    GUID and the full-reset event flag do not identify a physical state.
    """
    payload = [frame.frame if full_stack else (frame.frame[-1] if frame.frame else []),
               frame.state.value, frame.levels_completed, frame.win_levels,
               sorted(frame.available_actions)]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()[:32]


def action_bucket(action: GameAction, data: dict) -> tuple:
    # Coordinates remain exact in transition records. Only exploration counts
    # share an 8x8 spatial bin; this assumes no game-specific action semantics.
    if action.is_complex():
        return (action.value, data["x"] // 8, data["y"] // 8)
    return (action.value,)


class ExplorationMemory:
    """Per-agent/per-game memory, retained across deaths but not across games."""

    def __init__(self):
        self.visits = Counter()
        self.state_actions = {}
        self.level_actions = {}
        self.transitions = []
        self.recent_states = deque(maxlen=12)
        self.recent_pairs = deque(maxlen=12)
        self.episode = 0
        self.repeated_states = 0
        self.cycles = 0

    @staticmethod
    def new_stats():
        return {"attempts": 0, "unchanged": 0, "endpoint_unchanged": 0,
                "outcomes": Counter()}

    def start(self, frame):
        key = observation_key(frame)
        self.visits[key] += 1
        self.recent_states.append(key)

    def score(self, state, level, bucket):
        local = self.state_actions.get((state, bucket), self.new_stats())
        general = self.level_actions.get((level, bucket), self.new_stats())
        # Under-tested local actions get priority; level-wide evidence remains
        # useful when counters/animation make every exact grid look new.
        evidence = local if local["attempts"] else general
        count = evidence["attempts"]
        novelty = sum(n / (1 + self.visits[d]) for d, n in evidence["outcomes"].items()) / max(1, count)
        return (2 / math.sqrt(1 + local["attempts"])
                + 1 / math.sqrt(1 + general["attempts"])
                + novelty
                - 2 * evidence["endpoint_unchanged"] / (1 + count)
                - self.recent_pairs.count((state, bucket)))

    def observe(self, before, action_id, data, after):
        source, source_full, level = before
        target = observation_key(after)
        bucket = action_bucket(GameAction.from_id(action_id), data)
        unchanged = source_full == observation_key(after, full_stack=True)
        endpoint_unchanged = source == target
        repeated = self.visits[target] > 0
        cycle = target in self.recent_states
        action_cycle = (source, bucket) in self.recent_pairs and cycle
        self.repeated_states += repeated
        self.cycles += cycle
        self.visits[target] += 1
        for table, key in ((self.state_actions, (source, bucket)),
                           (self.level_actions, (level, bucket))):
            stats = table.setdefault(key, self.new_stats())
            stats["attempts"] += 1
            stats["unchanged"] += unchanged
            stats["endpoint_unchanged"] += endpoint_unchanged
            stats["outcomes"][target] += 1
        self.transitions.append({
            "episode": self.episode, "source": source, "target": target,
            "action_id": action_id, "data": dict(data), "bucket": bucket,
            "unchanged": unchanged, "endpoint_unchanged": endpoint_unchanged,
            "repeated": repeated, "cycle": cycle, "action_cycle": action_cycle,
            "frame_count": len(after.frame), "levels_delta": after.levels_completed - level,
            "state": after.state.value, "full_reset": after.full_reset,
        })
        boundary = (action_id == GameAction.RESET.value or after.full_reset
                    or after.levels_completed != level or after.state == GameState.GAME_OVER)
        if boundary:
            self.episode += 1
            self.recent_states.clear()
            self.recent_pairs.clear()
        else:
            self.recent_pairs.append((source, bucket))
        self.recent_states.append(target)


class MemoryAgent(LegalRandomAgent):
    """Small action-coverage heuristic; novelty is evidence, not game reward."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory = ExplorationMemory()

    def choose_action(self, frames, latest_frame):
        key = observation_key(latest_frame)
        if not self.memory.visits:
            self.memory.start(latest_frame)
        self._memory_before = (key, observation_key(latest_frame, full_stack=True),
                               latest_frame.levels_completed)
        choices = advertised_actions(latest_frame)
        if latest_frame.state != GameState.NOT_FINISHED or not choices:
            return prepare_action(GameAction.RESET)
        # Fixed 10% legal-random exploration prevents learned penalties from
        # permanently excluding actions with delayed or context-specific effects.
        if random.random() < 0.1:
            return super().choose_action(frames, latest_frame)
        candidates = []
        for action in choices:
            buckets = [(action.value, x, y) for x in range(8) for y in range(8)] if action.is_complex() else [(action.value,)]
            for bucket in buckets:
                score = self.memory.score(key, latest_frame.levels_completed, bucket)
                candidates.append((score, action, bucket))
        best = max(item[0] for item in candidates)
        tied = [item for item in candidates if item[0] == best]
        # Equal scores break ties by action family first; ACTION6 having 64
        # coordinate bins must not give it 64 lottery tickets at initialization.
        action = random.choice(list(dict.fromkeys(item[1] for item in tied)))
        _, _, bucket = random.choice([item for item in tied if item[1] is action])
        data = ({"x": bucket[1] * 8 + random.randrange(8),
                 "y": bucket[2] * 8 + random.randrange(8)} if action.is_complex() else {})
        return prepare_action(action, data)

    def take_action(self, action):
        # Capture the actual request before enum mutation or the next decision.
        action_id, data = action.value, action.action_data.model_dump()
        frame = super().take_action(action)
        if frame is not None:
            # Update here rather than at the next decision, so WIN, death and
            # the final budget-limited response are included in memory.
            self.memory.observe(self._memory_before, action_id, data, frame)
        return frame


POLICIES = {"original": MyAgent, "legal": LegalRandomAgent, "memory": MemoryAgent}
