import gzip
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.play_local import load_my_agent_class
from scripts.build_notebook import build
from scripts.evaluate_policies import aggregate, measure_trace, run_one, write_results
from scripts.observation_trace import traced_agent_class
from scripts.visualize_trace import render_trace
from arcengine import FrameData, GameAction, GameState
from test_observation_trace import FakeEnv, agent_for, raw


class ExplorationTests(unittest.TestCase):
    def test_legal_random_obeys_advertisement_and_coordinates(self):
        agent = agent_for(load_my_agent_class("legal"), FakeEnv())
        frame = FrameData(state=GameState.NOT_FINISHED, available_actions=[2, 6, 6, 999])
        random.seed(7)
        for _ in range(100):
            action = agent.choose_action([], frame)
            self.assertIn(action.value, (2, 6))
            action.validate_data(action.action_data.model_dump())
            if action.is_complex():
                self.assertTrue(0 <= action.action_data.x <= 63)
                self.assertTrue(0 <= action.action_data.y <= 63)
        for state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self.assertIs(agent.choose_action([], FrameData(state=state)), GameAction.RESET)
        self.assertIs(agent.choose_action([], FrameData(state=GameState.NOT_FINISHED)), GameAction.RESET)
        self.assertTrue(agent.is_done([], FrameData(state=GameState.WIN)))

    def test_memory_records_final_win_and_death_reset_boundary(self):
        stream = io.StringIO()
        cls = traced_agent_class(load_my_agent_class("memory"), stream)
        agent = agent_for(cls, FakeEnv([raw(1, GameState.GAME_OVER), raw(0), raw(2, GameState.WIN, 1)]))
        random.seed(10)
        agent.main()
        transitions = agent.memory.transitions
        self.assertEqual(len(transitions), 3)
        self.assertEqual(transitions[1]["action_id"], 0)
        self.assertEqual(transitions[-1]["state"], "WIN")
        self.assertEqual(transitions[-1]["levels_delta"], 1)
        self.assertGreater(transitions[1]["episode"], transitions[0]["episode"])
        self.assertEqual(len(json.loads(stream.getvalue().splitlines()[-1])["after"]["frame"]), 1)

    def test_memory_noops_cycles_and_under_tested_action_preference(self):
        agent = agent_for(load_my_agent_class("memory"), FakeEnv())
        frame = FrameData(frame=[[[1]]], state=GameState.NOT_FINISHED, available_actions=[1, 2])
        agent.choose_action([], frame)
        source = agent._memory_before
        for _ in range(4):
            agent.memory.observe(source, 1, {}, frame)
        self.assertEqual(agent.memory.repeated_states, 4)
        self.assertEqual(agent.memory.cycles, 4)
        self.assertTrue(agent.memory.transitions[-1]["action_cycle"])
        self.assertTrue(agent.memory.transitions[-1]["unchanged"])
        self.assertGreater(agent.memory.score(source[0], 0, (2,)), agent.memory.score(source[0], 0, (1,)))

    def test_multiframe_change_is_not_progress_and_final_grid_identity_is_stable(self):
        agent = agent_for(load_my_agent_class("memory"), FakeEnv())
        before = FrameData(frame=[[[1]]], state=GameState.NOT_FINISHED, available_actions=[1])
        agent.choose_action([], before)
        after = FrameData(frame=[[[2]], [[1]]], state=GameState.NOT_FINISHED, available_actions=[1])
        agent.memory.observe(agent._memory_before, 1, {}, after)
        record = agent.memory.transitions[-1]
        self.assertFalse(record["unchanged"])
        self.assertTrue(record["endpoint_unchanged"])
        self.assertEqual(record["levels_delta"], 0)
        self.assertEqual(record["frame_count"], 2)
        self.assertEqual(len(agent.memory.visits), 1)

    def test_memory_is_per_game_and_retains_learning_across_reset(self):
        cls = load_my_agent_class("memory")
        first, second = agent_for(cls, FakeEnv()), agent_for(cls, FakeEnv())
        before = FrameData(frame=[[[0]]], state=GameState.NOT_FINISHED, available_actions=[1])
        first.choose_action([], before)
        first.memory.observe(first._memory_before, 1, {}, before)
        first.memory.observe(first._memory_before, 0, {}, FrameData(frame=[[[0]]], full_reset=True))
        self.assertEqual(len(second.memory.visits), 0)
        self.assertEqual(first.memory.state_actions[(first._memory_before[0], (1,))]["attempts"], 1)
        self.assertEqual(len(first.memory.recent_pairs), 0)

    def test_memory_coordinate_bins_preserve_exact_request_and_legality(self):
        agent = agent_for(load_my_agent_class("memory"), FakeEnv())
        frame = FrameData(frame=[[[0]]], state=GameState.NOT_FINISHED, available_actions=[6])
        random.seed(9)
        bins = set()
        for _ in range(80):
            action = agent.choose_action([], frame)
            self.assertEqual(action.value, 6)
            data = action.action_data.model_dump()
            action.validate_data(data)
            agent.memory.observe(agent._memory_before, 6, data, frame)
            record = agent.memory.transitions[-1]
            self.assertEqual(record["data"], data)
            bins.add(record["bucket"])
        self.assertGreaterEqual(len(bins), 60)

    def test_notebook_policies_are_self_contained_and_run_official_loop(self):
        for policy in ("original", "legal", "memory"):
            with self.subTest(policy=policy):
                source = build(policy)["cells"][2]["source"].split("\n", 1)[1]
                namespace = {"__name__": "bundled_agent"}
                exec(compile(source, "bundled_agent.py", "exec"), namespace)
                agent = agent_for(namespace["MyAgent"], FakeEnv())
                agent.MAX_ACTIONS = 2
                agent.main()
                self.assertEqual(agent.action_counter, 3)
                self.assertEqual(namespace["MyAgent"].__name__, "MyAgent")
                self.assertNotIn("from scripts", source)

    def test_trace_metrics_gzip_render_and_replication(self):
        class Arcade:
            def make(self, game, seed):
                # Same visible state on every step: no novelty/progress.
                return FakeEnv([raw(0), raw(0), raw(0)])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [run_one(Arcade(), "test-version", "memory", 3, 3, rep, root) for rep in (0, 1)]
            self.assertEqual(rows[0]["trace_digest"], rows[1]["trace_digest"])
            self.assertEqual(rows[0]["repeats"], 3)
            self.assertEqual(rows[0]["unique_observations"], 1)
            self.assertEqual(rows[0]["no_change"], 3)
            self.assertEqual(rows[0]["levels_completed"], 0)
            self.assertEqual(render_trace(root / rows[0]["trace"], limit=1)[1], 1)
            summary = write_results(rows, root, {"replicates": 2, "games": ["test-version"]})
            self.assertEqual(summary["replication_groups_checked"], 1)
            self.assertEqual(summary["replication_mismatches"], [])
            self.assertEqual(aggregate(rows)[2]["runs"], 1)
            # Broken order must not silently become a successful experiment.
            path = root / rows[0]["trace"]
            with gzip.open(path, "rt") as stream:
                record = json.loads(stream.readline())
            record["step"] = 4
            with gzip.open(path, "wt") as stream:
                stream.write(json.dumps(record) + "\n")
            with self.assertRaises(ValueError):
                measure_trace(path)

    def test_evaluator_isolates_numpy_seed_between_runs(self):
        class Arcade:
            def make(self, game, seed):
                return FakeEnv([raw(int(np.random.randint(0, 16))) for _ in range(3)])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = run_one(Arcade(), "test-version", "original", 1, 3, 0, root)
            np.random.seed(9876)
            np.random.randint(0, 16, size=100)
            second = run_one(Arcade(), "test-version", "original", 1, 3, 1, root)
            self.assertEqual(first["trace_digest"], second["trace_digest"])
