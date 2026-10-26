"""Opt-in parity checks against cached games through public interfaces only."""
import io
import json
import os
import random
import unittest
from copy import deepcopy

import numpy as np

from scripts.play_local import ROOT, arc_agi, OperationMode, load_my_agent_class
from arcengine import GameAction
from scripts.observation_trace import snapshot, traced_agent_class


@unittest.skipUnless(os.getenv("ARC_LOCAL_INTEGRATION") == "1",
                     "Set ARC_LOCAL_INTEGRATION=1 to run cached real games")
class LocalIntegrationTests(unittest.TestCase):
    def test_ls20_vc33_trace_parity_and_diffs(self):
        arcade = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE,
                                environments_dir=str(ROOT / "environment_files"))
        base = load_my_agent_class()
        for game_id in ("ls20", "vc33"):
            with self.subTest(game=game_id):
                runs = []
                for enabled in (False, True):
                    # Enum members persist in-process, unlike fresh CLI runs.
                    for action in GameAction:
                        action.set_data({})
                        action.reasoning = None
                    env = arcade.make(game_id)
                    self.assertIsNotNone(env, "Cache the requested game first")
                    requests = []
                    real_step = env.step

                    def step(action, data, reasoning):
                        requests.append(deepcopy((action.value, data, reasoning)))
                        response = real_step(action, data=data, reasoning=reasoning)
                        self.assertEqual(response.action_input.id.value, action.value)
                        self.assertEqual(response.action_input.data, data)
                        return response

                    env.step = step
                    stream = io.StringIO()
                    cls = traced_agent_class(base, stream, seed=42) if enabled else base
                    agent = cls(card_id="test", game_id=game_id, agent_name="test",
                                ROOT_URL="http://localhost", record=False, arc_env=env)
                    agent.MAX_ACTIONS = 50
                    random.seed(f"42:{game_id}")
                    agent.main()
                    frames = [snapshot(frame) for frame in agent.frames[1:]]
                    runs.append((requests, [{k: v for k, v in f.items() if k != "guid"} for f in frames]))
                    if not enabled:
                        continue
                    records = [json.loads(line) for line in stream.getvalue().splitlines()]
                    self.assertEqual(len(records), agent.action_counter)
                    for index, record in enumerate(records):
                        self.assertEqual(record["step"], index)
                        self.assertEqual(record["status"], "ok")
                        self.assertEqual(record["after"], frames[index])
                        self.assertEqual(record["action"]["id"], requests[index][0])
                        self.assertEqual(record["action"]["data"], requests[index][1])
                        self.assertEqual(record["action"]["reasoning"], requests[index][2])
                        if index:
                            self.assertEqual(record["before"], records[index - 1]["after"])
                        before, after = record["before"]["frame"], record["after"]["frame"]
                        self.assertEqual(record["diff"]["frames_changed"], before != after)
                        self.assertEqual(record["diff"]["observation_changed"], record["before"] != record["after"])
                        if before and after and np.shape(before[-1]) == np.shape(after[-1]):
                            ys, xs = np.where(np.asarray(before[-1]) != np.asarray(after[-1]))
                            expected_bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None
                            self.assertEqual(record["diff"]["final_grid"]["changed_cells"], len(xs))
                            self.assertEqual(record["diff"]["final_grid"]["bbox"], expected_bbox)
                self.assertEqual(runs[0], runs[1], "Tracing altered seeded actions or observations")
