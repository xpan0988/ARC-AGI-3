"""Focused tests; synthetic observations never inspect game implementation files."""
import io
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from scripts.play_local import load_my_agent_class
from arcengine import FrameData, FrameDataRaw, GameAction, GameState
from scripts.build_notebook import build, AGENT_SRC
from scripts.observation_trace import grid_diff, snapshot, traced_agent_class, transition_diff
from scripts.visualize_trace import cell_color, render_trace

MyAgent = load_my_agent_class()


def raw(value=0, state=GameState.NOT_FINISHED, levels=0):
    frame = FrameDataRaw(game_id="test-version", state=state,
                         levels_completed=levels, win_levels=2,
                         available_actions=[1, 6], guid="test-guid")
    frame.frame = [np.full((2, 3), value, dtype=int)]
    return frame


class FakeEnv:
    def __init__(self, responses=None):
        self.observation_space = raw()
        self.responses = iter(responses) if responses is not None else None
        self.calls = []

    def step(self, action, data, reasoning):
        self.calls.append((action.value, dict(data), reasoning))
        response = next(self.responses) if self.responses is not None else raw(len(self.calls) % 16)
        self.observation_space = response
        return response


def agent_for(cls, env):
    return cls(card_id="test", game_id="test", agent_name="test",
               ROOT_URL="http://localhost", record=False, arc_env=env)


class TraceTests(unittest.TestCase):
    def test_cell_counts_and_inclusive_bbox(self):
        self.assertEqual(grid_diff([[1, 2, 3], [4, 5, 6]], [[1, 9, 3], [8, 5, 6]]),
                         {"before_shape": [2, 3], "after_shape": [2, 3],
                          "comparable": True, "changed_cells": 2, "bbox": [0, 0, 1, 1]})
        self.assertEqual(grid_diff([[1]], [[1]])["changed_cells"], 0)
        for before, after in [(None, [[1]]), ([], []), ([[1]], [[1, 2]]), ([[1], []], [[2], []])]:
            self.assertIsNone(grid_diff(before, after)["changed_cells"])

    def test_metadata_and_animation_changes_with_same_final_grid(self):
        before = snapshot(FrameData(frame=[[[1]]]))
        after = snapshot(FrameData(frame=[[[2]], [[1]]], levels_completed=1))
        diff = transition_diff(before, after)
        self.assertTrue(diff["observation_changed"])
        self.assertTrue(diff["frames_changed"])
        self.assertEqual(diff["final_grid"]["changed_cells"], 0)
        self.assertNotEqual(before["fingerprint"], after["fingerprint"])
        self.assertEqual(snapshot(FrameData(frame=[[[1]]], guid="another"))["fingerprint"], before["fingerprint"])

    def test_real_loop_pairs_actions_reset_and_win(self):
        death = raw(2, GameState.GAME_OVER)
        restart = raw(3)
        restart.full_reset = False
        win = raw(4, GameState.WIN, 2)
        win.frame.insert(0, np.full((2, 3), 5))
        env, stream = FakeEnv([death, restart, win]), io.StringIO()
        agent = agent_for(traced_agent_class(MyAgent, stream), env)
        agent.main()
        records = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual(len(records), 3)  # Stops on WIN, resets after GAME_OVER.
        self.assertEqual([r["step"] for r in records], [0, 1, 2])
        self.assertEqual(records[1]["action"]["name"], "RESET")
        self.assertEqual(records[0]["before"]["frame"], [[[0] * 3] * 2])
        self.assertEqual(records[0]["before"]["state"], "NOT_FINISHED")
        self.assertEqual(records[0]["after"], records[1]["before"])
        self.assertEqual(records[1]["after"], records[2]["before"])
        self.assertEqual(len(records[2]["after"]["frame"]), 2)
        self.assertEqual(records[2]["after"]["levels_completed"], 2)
        self.assertEqual([r["action"]["id"] for r in records], [c[0] for c in env.calls])
        self.assertNotIn("action_input", records[0]["after"])

    def test_tracing_preserves_seeded_baseline(self):
        runs = []
        for enabled in (False, True):
            for action in GameAction:
                action.set_data({})
                action.reasoning = None
            stream, env = io.StringIO(), FakeEnv()
            cls = traced_agent_class(MyAgent, stream) if enabled else MyAgent
            agent = agent_for(cls, env)
            agent.MAX_ACTIONS = 30
            random.seed(123)
            agent.main()
            runs.append((env.calls, [snapshot(f) for f in agent.frames], agent.name))
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(len(runs[0][0]), 31)  # Preserve vendor <= cap behavior.

    def test_mutable_action_snapshot_and_exception(self):
        class MutatingEnv(FakeEnv):
            def step(self, action, data, reasoning):
                action.set_data({"x": 63, "y": 63})
                raise RuntimeError("test failure")

        stream = io.StringIO()
        agent = agent_for(traced_agent_class(MyAgent, stream), MutatingEnv())
        agent.choose_action(agent.frames, FrameData(frame=[[[0]]]))
        GameAction.ACTION6.set_data({"x": 2, "y": 3})
        with self.assertRaisesRegex(RuntimeError, "test failure"):
            agent.take_action(GameAction.ACTION6)
        record = json.loads(stream.getvalue())
        self.assertEqual(record["action"]["data"]["x"], 2)
        self.assertEqual(record["status"], "error")
        self.assertIsNone(record["after"])

    def test_missing_environment_response_is_not_fabricated(self):
        stream = io.StringIO()
        agent = agent_for(traced_agent_class(MyAgent, stream), FakeEnv([None]))
        with self.assertRaisesRegex(ValueError, "None frame data"):
            agent.main()
        self.assertEqual(json.loads(stream.getvalue())["status"], "error")

    def test_png_retains_cells_highlights_and_all_subframes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.jsonl"
            path.write_text(json.dumps({
                "game_id": "test", "step": 0, "status": "ok",
                "action": {"name": "ACTION6", "data": {"x": 0, "y": 0}},
                "before": snapshot(FrameData(frame=[[[0, 1]]])),
                "after": snapshot(FrameData(frame=[[[2, 1]], [[2, 3]]])),
            }) + "\n")
            output, count = render_trace(path)
            self.assertEqual(count, 2)
            with Image.open(output / "00000-001.png") as image:
                self.assertEqual(image.getpixel((15, 109)), (0, 0, 0))
                self.assertEqual(image.getpixel((411, 109)), (255, 65, 54))
                self.assertEqual(image.getpixel((409, 107)), (0, 255, 255))
            self.assertEqual(len({cell_color(n) for n in range(16)}), 16)
            # Empty observations are still renderable, with no invented grid.
            record = json.loads(path.read_text())
            record["before"]["frame"] = []
            record["after"]["frame"] = []
            path.write_text(json.dumps(record) + "\n")
            self.assertEqual(render_trace(path)[1], 1)

    def test_disabled_runner_does_not_import_tracer(self):
        import builtins
        from scripts import play_local
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "scripts.observation_trace":
                raise AssertionError("Disabled tracing imported its implementation")
            return original_import(name, *args, **kwargs)

        with patch("sys.argv", ["play_local.py", "--game", "test", "--max-steps", "1"]), \
             patch.object(play_local.arc_agi, "Arcade") as arcade, \
             patch("builtins.__import__", side_effect=guarded_import):
            arcade.return_value.get_environments.return_value = [type("Info", (), {"game_id": "test"})()]
            arcade.return_value.make.return_value = FakeEnv()
            play_local.main()

    def test_notebook_embeds_only_original_agent(self):
        notebook = build()
        self.assertEqual(notebook["cells"][2]["source"], "%%writefile /tmp/my_agent.py\n" + AGENT_SRC.read_text())
        text = json.dumps(notebook)
        self.assertNotIn("observation_trace", text)
        self.assertNotIn("visualize_trace", text)
        self.assertEqual(notebook["nbformat"], 4)


if __name__ == "__main__":
    unittest.main()
