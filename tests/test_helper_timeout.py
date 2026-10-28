"""Focused CPU regressions for the default-off helper-timeout overlay."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from baselines.franzen_m2_v3.prepare import ROOT, source
from interventions.helper_timeout.build import build
from interventions.helper_timeout.patch import (
    BASE_HASHES, FLAG, RECORD_AFTER, RECORD_BEFORE, TIMEOUT_AFTER, TIMEOUT_BEFORE,
    apply, patched_sources,
)
from franzen_timeout_fixture import FakeGame, load_agent, load_sandbox, make_agent, release_sources


HELPERS = "def inc(x):\n    return x + 1\ndef twice_inc(x):\n    return inc(x) * 2\n"
HANG = "while True:\n    pass\n"


class HelperTimeoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="arc_helper_cpu_")
        cls.originals, utilities = release_sources()
        cls.patched = patched_sources(cls.originals)
        cls.arms = {}
        for name, sources in (("baseline", cls.originals), ("candidate", cls.patched)):
            runner, retention = load_sandbox(cls.temp.name, sources["python_tool_sandbox.py"], utilities, name)
            agent_class, namespace = load_agent(sources["tool_agent.py"], runner, retention)
            cls.arms[name] = (agent_class, namespace, runner)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.environment = patch.dict(os.environ, {
            FLAG: "1", "ARC3_PERSISTENT_FUNCTIONS": "1",
            "ARC3_PERSISTENT_FUNCTIONS_SCOPE": "game",
            "ARC3_PERSISTENT_FUNCTIONS_IMPORTS": "1",
            "ARC3_PRIORITY_PACE": "0", "ARC3_ANIMATION": "0",
            "ARC3_WM_WIPE_ON_LEVEL": "1",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.path = Path(self.temp.name) / "game1/state.json"

    def agent(self, arm="candidate", transition=None):
        cls, ns, _ = self.arms[arm]
        game = FakeGame(transition)
        return make_agent(cls, ns, game, self.path), game

    def execute(self, agent, code):
        dispatch = agent._run_python_tool(self.path, {"code": code})
        return dispatch, json.loads(dispatch.content)

    def seed(self, agent):
        _, payload = self.execute(agent, HELPERS)
        self.assertNotIn("error", payload)
        self.assertEqual(set(agent._kept_functions), {"inc", "twice_inc"})
        return dict(agent._kept_functions)

    def timeout_envelope(self, **updates):
        return {"_hard_timeout": True, "error": "Tool timed out after 1s",
                "stdout": "", "action_results": [], **updates}

    def test_real_hard_timeout_preserves_committed_sources_and_dependencies(self):
        agent, game = self.agent()
        old = self.seed(agent)
        _, payload = self.execute(agent, "def inc(x):\n    return 999\ndef unfinished(x):\n    return x\n" + HANG)
        self.assertEqual(payload["error"], "Tool timed out after 1s")
        self.assertEqual(agent._kept_functions, old)
        self.assertIn("not committed", payload["function_retention"])
        self.assertIn("may be incorrect", payload["function_retention"])
        _, resumed = self.execute(agent, "print(twice_inc(2))")
        self.assertEqual(resumed["stdout"].strip(), "6")
        self.assertEqual(game.actions, [])

    def test_real_timeout_empty_bank_never_commits_new_definitions(self):
        agent, _ = self.agent()
        _, payload = self.execute(agent, "def unfinished(x):\n    return x\n" + HANG)
        self.assertEqual(agent._kept_functions, {})
        self.assertIn("hard timeout", payload["function_retention"])

    def test_real_timeout_after_actions_does_not_replay_or_rollback_state(self):
        for arm, flag in (("baseline", "1"), ("candidate", "0"), ("candidate", "1")):
            with self.subTest(arm=arm, flag=flag), patch.dict(os.environ, {FLAG: flag}):
                agent, game = self.agent(arm)
                old = self.seed(agent)
                dispatch, payload = self.execute(agent, 'action("UP")\naction("DOWN")\n' + HANG)
                self.assertEqual(game.actions, ["UP", "DOWN"])
                self.assertEqual(game.frame.step, 2)
                self.assertEqual(game.frame.grid, [[2]])
                self.assertTrue(dispatch.step_executed)
                self.assertTrue(dispatch.made_progress)
                self.assertEqual(agent._last_step_summary["executed_count"], 2)
                self.assertEqual(agent._last_action_call_result["action_num"], 2)
                self.assertEqual(agent._kept_functions, old if arm == "candidate" and flag == "1" else {})
                _, followup = self.execute(agent, "print(current_frame.step)")
                self.assertEqual(followup["stdout"].strip(), "2")
                self.assertEqual(game.actions, ["UP", "DOWN"])
                self.assertEqual(payload["error"], "Tool timed out after 1s")

    def test_default_off_matches_baseline_timeout_payload_and_clearing(self):
        payloads = []
        with patch.dict(os.environ):
            os.environ.pop(FLAG, None)
            for arm in ("baseline", "candidate"):
                agent, _ = self.agent(arm)
                self.seed(agent)
                _, payload = self.execute(agent, HANG)
                self.assertEqual(agent._kept_functions, {})
                payloads.append(payload)
            self.assertEqual(payloads[0], payloads[1])

    def test_real_supervisor_marker_is_private_and_switch_gated(self):
        runner = self.arms["candidate"][2]
        def unexpected(*args, **kwargs):
            self.fail("unexpected action execution")
        for flag in ("0", "1"):
            with self.subTest(flag=flag), patch.dict(os.environ, {FLAG: flag}):
                result = runner(code=HANG, timeout_seconds=1, initial_state={}, action_handler=unexpected)
                self.assertEqual(result.get("_hard_timeout"), True if flag == "1" else None)
                self.assertNotIn("keepable_functions", result)
        # A child-raised matching error or result dictionary is not confirmation.
        result = runner(code='result = {"_hard_timeout": True}\nraise Exception("Tool timed out after 1s")',
                        timeout_seconds=1, initial_state={}, action_handler=unexpected, kept_functions=[])
        self.assertNotIn("_hard_timeout", result)
        self.assertIn("keepable_functions", result)

    def test_explicit_empty_export_still_clears_even_with_timeout_marker(self):
        for metadata in ({"keepable_functions": []}, self.timeout_envelope(keepable_functions=[])):
            agent, _ = self.agent()
            self.seed(agent)
            payload = {}
            agent._record_retained_functions(metadata, payload)
            self.assertEqual(agent._kept_functions, {})
            self.assertNotIn("previous committed", payload.get("function_retention", ""))

    def test_successful_export_replaces_snapshot(self):
        for arm in ("baseline", "candidate"):
            agent, _ = self.agent(arm)
            self.seed(agent)
            agent._record_retained_functions({"keepable_functions": [
                {"name": "replacement", "source": "def replacement(x):\n    return x * 3"},
            ]}, {})
            self.assertEqual(set(agent._kept_functions), {"replacement"})
            _, payload = self.execute(agent, "print(replacement(4))")
            self.assertEqual(payload["stdout"].strip(), "12")

    def test_real_validation_rejection_and_python_exception_are_unchanged(self):
        observations = []
        for arm in ("baseline", "candidate"):
            agent, game = self.agent(arm)
            self.seed(agent)
            _, payload = self.execute(agent, "SECRET = 7\ndef inc(x):\n    return SECRET\nraise ValueError('ordinary error')")
            self.assertIn("error", payload)
            self.assertNotIn("inc", agent._kept_functions)
            self.assertIn("was not retained", payload["function_retention"])
            observations.append((payload, agent._kept_functions, game.actions))
        self.assertEqual(observations[0], observations[1])

    def test_incomplete_or_malformed_metadata_follows_baseline_fail_closed(self):
        timeout = self.timeout_envelope()
        variants = [
            {k: v for k, v in timeout.items() if k != key}
            for key in timeout
        ] + [
            self.timeout_envelope(_hard_timeout=1), self.timeout_envelope(_hard_timeout="true"),
            self.timeout_envelope(error="request timed out"), self.timeout_envelope(stdout="partial"),
            self.timeout_envelope(action_results=None), self.timeout_envelope(action_results=["bad"]),
            self.timeout_envelope(keepable_functions=None), self.timeout_envelope(keepable_functions=[{}]),
            self.timeout_envelope(keepable_functions="bad"), self.timeout_envelope(retention_rejected=[]),
            self.timeout_envelope(retention_rejected=[{"name": "all", "reason": "validation failure"}]),
            self.timeout_envelope(unexpected="field"),
            {"error": "Tool timed out after 1s", "stdout": "", "action_results": []},
        ]
        for metadata in variants:
            with self.subTest(metadata=metadata):
                outcomes = []
                for arm in ("baseline", "candidate"):
                    agent, _ = self.agent(arm)
                    agent._kept_functions = {"inc": "def inc(x):\n    return x + 1"}
                    payload = {}
                    original = copy.deepcopy(metadata)
                    agent._record_retained_functions(metadata, payload)
                    self.assertEqual(metadata, original)
                    self.assertEqual(agent._kept_functions, {})
                    outcomes.append(payload)
                self.assertEqual(outcomes[0], outcomes[1])

    def test_new_game_session_clears_even_after_preserved_timeout(self):
        agent, game = self.agent()
        self.seed(agent)
        self.execute(agent, HANG)
        agent._ensure_session(self.path)
        self.assertTrue(agent._kept_functions)
        agent._ensure_session(self.path.parent.parent / "game2/state.json")
        self.assertEqual(agent._kept_functions, {})
        self.assertEqual(agent._retained_clear_notice, "")
        self.assertIsNone(agent._last_step_summary)
        self.assertEqual(game.actions, [])

    def test_real_timeout_across_level_boundary_preserves_scope_semantics(self):
        for scope in ("game", "levelup", "turn"):
            with self.subTest(scope=scope), patch.dict(os.environ, {"ARC3_PERSISTENT_FUNCTIONS_SCOPE": scope}):
                agent, game = self.agent(transition="level_completed")
                old = self.seed(agent)
                dispatch, _ = self.execute(agent, 'action("UP")\n' + HANG)
                self.assertEqual(game.actions, ["UP"])
                self.assertEqual(game.frame.level, 2)
                self.assertTrue(dispatch.made_progress)
                self.assertEqual(agent._kept_functions, {} if scope == "levelup" else old)
                if scope == "game":
                    self.assertIn("Check level-specific assumptions", agent._retained_clear_notice)
                if scope == "turn":
                    agent._fixture_turn_boundary(True)
                    self.assertEqual(agent._kept_functions, old)
                    agent._fixture_turn_boundary(False)
                    self.assertEqual(agent._kept_functions, {})

    def test_reset_and_terminal_action_latches_are_unchanged(self):
        for arm in ("baseline", "candidate"):
            with self.subTest(arm=arm):
                agent, game = self.agent()
                old = self.seed(agent)
                _, payload = self.execute(agent, 'action("UP")\naction("RESET")')
                self.assertEqual(game.actions, ["UP"])
                self.assertIn("RESET must be", payload["error"])
                self.assertEqual(agent._kept_functions, old)
                self.execute(agent, 'action("RESET")')
                self.assertEqual(game.actions, ["UP", "RESET"])
                self.assertEqual(agent._kept_functions, old)  # same game, game scope
                agent, game = self.agent(transition="run_complete")
                self.seed(agent)
                dispatch, _ = self.execute(agent, 'action("UP")\naction("DOWN")')
                self.assertEqual(game.actions, ["UP"])
                self.assertTrue(agent._last_step_summary["run_complete"])
                self.assertTrue(dispatch.made_progress)

    def test_persistence_disabled_is_unchanged(self):
        with patch.dict(os.environ, {"ARC3_PERSISTENT_FUNCTIONS": "0"}):
            agent, _ = self.agent()
            agent._kept_functions = {"old": "def old():\n    return 1"}
            payload = {}
            agent._record_retained_functions(self.timeout_envelope(), payload)
            self.assertEqual(set(agent._kept_functions), {"old"})
            self.assertEqual(payload, {})

    def test_source_overlay_has_only_two_insertions_and_rejects_source_drift(self):
        self.assertEqual(self.patched["python_tool_sandbox.py"].decode().replace(TIMEOUT_AFTER, TIMEOUT_BEFORE),
                         self.originals["python_tool_sandbox.py"].decode())
        self.assertEqual(self.patched["tool_agent.py"].decode().replace(RECORD_AFTER, RECORD_BEFORE),
                         self.originals["tool_agent.py"].decode())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ARC3-Inference/inference/agent"
            target.mkdir(parents=True)
            for name, raw in self.originals.items():
                (target / name).write_bytes(raw + (b"\n" if name == "tool_agent.py" else b""))
            before = {name: (target / name).read_bytes() for name in BASE_HASHES}
            with self.assertRaises(ValueError):
                apply(directory)
            self.assertEqual({name: (target / name).read_bytes() for name in BASE_HASHES}, before)

    def test_packaged_notebook_applies_overlay_before_imports_without_touching_v3(self):
        root = ROOT / "local_output/helper_timeout"
        root.mkdir(parents=True, exist_ok=True)
        baseline = ROOT / "arc-agi-3-milestone-2-solution.ipynb"
        digest = hashlib.sha256(baseline.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=root) as directory:
            output = Path(directory) / "candidate.ipynb"
            notebook = build(baseline, output)
            original = json.loads(baseline.read_text())
            self.assertEqual([source(c) for i, c in enumerate(notebook["cells"]) if i != 5],
                             [source(c) for c in original["cells"]])
            self.assertIn('subprocess.run(["git", "apply"', source(notebook["cells"][4]))
            self.assertNotIn("os.environ[", source(notebook["cells"][5]))
            target = Path(directory) / "bundle/src/ARC3-Inference/inference/agent"
            target.mkdir(parents=True)
            for name, raw in self.originals.items():
                (target / name).write_bytes(raw)
            # Exercise the emitted cell itself, not merely valid notebook JSON.
            exec(compile(source(notebook["cells"][5]), "emitted_overlay", "exec"),
                 {"BUNDLE_DIR": Path(directory) / "bundle"})
            for name, raw in self.patched.items():
                self.assertEqual((target / name).read_bytes(), raw)
            with self.assertRaises(FileExistsError):
                build(baseline, output)
            with self.assertRaises(ValueError):
                build(baseline, baseline)
        self.assertEqual(hashlib.sha256(baseline.read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
