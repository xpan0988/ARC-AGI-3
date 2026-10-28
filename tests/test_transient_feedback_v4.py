"""CPU dispatch regressions for isolated V4 A+B; no model, server or GPU."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from franzen_v4_fixture import HarnessFixture, Game, OfflineGame, board, REVERSE
from baselines.franzen_m2_v3.prepare import ROOT, SOURCE_SHA256, source
from interventions.transient_feedback_v4.build import build, OUTPUT, source_diff
from interventions.transient_feedback_v4.patch import BASE_HASHES, NEW_FILE, apply, patched_sources


class TransientFeedbackV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="arc_v4_cpu_")
        cls.fixture = HarnessFixture(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        env = patch.dict(os.environ, {
            "ARC3_V4_TRANSIENT_FEEDBACK": "1", "ARC3_V4_ANIMATION_HISTORY": "1",
            "ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT": "0", "ARC3_ANIMATION": "1",
            "ARC3_ANIMATION_TIMELINE": "1", "ARC3_PERSISTENT_FUNCTIONS": "1",
            "ARC3_PERSISTENT_FUNCTIONS_SCOPE": "game", "ARC3_PERSISTENT_FUNCTIONS_IMPORTS": "1",
            "ARC3_PRIORITY_PACE": "0", "ARC3_NEW_CHANGED_PROMPTS": "1",
        })
        env.start()
        self.addCleanup(env.stop)

    def connect(self, scripts=(), arm="candidate"):
        return self.fixture.connect(Game(scripts), arm)

    def execute(self, agent, code):
        return self.fixture.execute(agent, code)

    def test_ordinary_noop_remains_noop_without_history(self):
        agent, session, game = self.connect([{"frames": [board()]}])
        dispatch, payload = self.execute(agent, "action('UP'); print(animation_history()['records'])")
        self.assertIn("NO-OP (executed, no change inside the board area)", payload["stdout"])
        self.assertTrue(dispatch.step_executed)
        self.assertFalse(dispatch.made_progress)
        self.assertEqual(session.history_entries[-1].result["gameplay_changed"], False)
        self.assertEqual(len(game.actions), 1)
        self.assertEqual(session._animation_history_v4.records, {})

    def test_transient_feedback_preserves_numeric_flags_and_summary(self):
        agent, session, _ = self.connect([{"frames": [board(2), board()]}])
        _, payload = self.execute(agent, "action('UP')")
        self.assertIn("ENDPOINT UNCHANGED", payload["stdout"])
        self.assertIn("2 frames, 1 transient pixels", payload["stdout"])
        self.assertNotIn("NO-OP", payload["stdout"])
        self.assertIn("ENDPOINT UNCHANGED", " ".join(agent._turn_action_trace([agent._last_action_call_result])))
        result = session.history_entries[-1].result
        self.assertTrue(result["no_op"])
        self.assertFalse(result["gameplay_changed"])
        self.assertTrue(result["executed"])
        self.assertEqual(result["animation_id"], agent._last_action_call_result["animation_id"])

    def test_multicall_retrieval_survives_overwrite_in_same_snippet(self):
        agent, session, game = self.connect([{"frames": [board(2), board()]}, {"frames": [board(3)]}])
        _, payload = self.execute(agent, """action('UP')
first_id = last_action_call_result['animation_id']
action('DOWN')
old = animation_frames(first_id)
print('old', old['action_num'], old['frames'][0].ascii.splitlines()[5][5])
print('timeline', animation_timeline(first_id)['timeline']['steps'][0]['changes'])
print('last', len(last_animation_frames))
""")
        self.assertNotIn("error", payload)
        self.assertIn("old 1 2", payload["stdout"])
        self.assertIn("0>2", payload["stdout"])
        self.assertIn("last 0", payload["stdout"])
        self.assertEqual(len(game.actions), 2)
        self.assertIsNone(session.animation_record)

    def test_action_ids_are_distinct_and_frames_match_after_later_snippets(self):
        agent, session, game = self.connect([{"frames": [board(2), board()]}, {"frames": [board(4), board()]}])
        self.execute(agent, "action('UP'); action('DOWN')")
        _, payload = self.execute(agent, """records = animation_history()['records']
for r in records:
    x = animation_frames(r['animation_id'])
    print(r['action_num'], x['action_num'], x['frames'][0].ascii.splitlines()[5][5])
print(animation_frames('not-a-real-id')['error'])
""")
        self.assertIn("1 1 2", payload["stdout"])
        self.assertIn("2 2 4", payload["stdout"])
        self.assertIn("unavailable", payload["stdout"])
        self.assertEqual(len(game.actions), 2)  # queries are not gameplay
        ids = list(session._animation_history_v4.records)
        self.assertEqual(len(set(ids)), 2)

    def test_record_limit_evicts_oldest_without_fallback(self):
        agent, session, game = self.connect([{"frames": [board(i), board()]} for i in range(1, 7)])
        _, payload = self.execute(agent, """action('UP')
old_id = last_action_call_result['animation_id']
for i in range(5): action('DOWN')
print([r['action_num'] for r in animation_history()['records']])
print(animation_frames(old_id)['error'])
""")
        self.assertIn("[3, 4, 5, 6]", payload["stdout"])
        self.assertIn("unavailable", payload["stdout"])
        history = session._animation_history_v4
        self.assertEqual(len(history.records), 4)
        self.assertEqual(history.evicted, 2)
        self.assertEqual(len(game.actions), 6)

    def test_long_animations_have_explicit_truncation_and_original_indices(self):
        chain = [board(1 + i % 14, 64) for i in range(99)] + [board(0, 64)]
        agent, session, _ = self.connect([{"frames": chain}])
        _, payload = self.execute(agent, """action('UP')
r = animation_history()['records'][0]
x = animation_frames(r['animation_id'])
t = animation_timeline(r['animation_id'])
print(r['original_frames'], r['retained_frames'], r['truncated'], r['truncation_reason'])
print(x['frame_indices'][0], x['frame_indices'][-1], len(x['frames']))
print(t['timeline']['steps'][-1]['step'])
""")
        self.assertNotIn("error", payload)
        self.assertIn("100 16 True frame_limit", payload["stdout"])
        # Pre-action board is index 0; all 100 original engine frames are counted.
        self.assertIn("6 100 16", payload["stdout"])
        history = session._animation_history_v4
        self.assertLessEqual(history.bytes, self.fixture.history.MAX_TOTAL_BYTES)
        self.assertTrue(all(len(raw) <= self.fixture.history.MAX_RECORD_BYTES for raw in history.records.values()))

    def test_memory_bound_at_capacity_and_unsupported_grids_are_reported(self):
        frames = [board(1 + i % 14, 64) for i in range(30)] + [board(0, 64)]
        agent, session, _ = self.connect([{"frames": frames} for _ in range(8)])
        self.execute(agent, "for i in range(8): action('UP')")
        history = session._animation_history_v4
        self.assertEqual(len(history.records), 4)
        self.assertLessEqual(history.bytes, 1024 * 1024)
        self.assertEqual(history.bytes, sum(map(len, history.records.values())))
        # Storage rejects oversized frames without retaining their raw grids.
        item = {"action_num": 99, "level": 1, "action_name": "ACTION1", "action_display": "UP"}
        record = {"chain": [board(0, 65), board(1, 65), board(0, 65)], "summary": {"transient_pixels": 1}}
        animation_id = history.observe(item, record, 1)
        data = history.query("history_frames", animation_id, self.fixture.animation['build_animation_frames'],
                             self.fixture.animation['build_animation_view'])
        self.assertTrue(data["truncated"])
        self.assertIn("unsupported_grid", data["truncation_reason"])
        self.assertEqual(data["frames"], [])

    def test_explicit_reset_invalidates_old_ids(self):
        agent, session, _ = self.connect([{"frames": [board(2), board()]}, {"frames": [board()]}])
        self.execute(agent, "action('UP')")
        old = next(iter(session._animation_history_v4.records))
        _, payload = self.execute(agent, f"action('RESET'); print(animation_history()['records']); print(animation_frames({old!r})['error'])")
        self.assertIn("[]", payload["stdout"])
        self.assertIn("unavailable", payload["stdout"])
        self.assertEqual(session._animation_history_v4.bytes, 0)

    def test_level_transition_clears_and_retains_terminal_semantics(self):
        agent, session, game = self.connect([{"frames": [board(2), board()]},
                                              {"frames": [board(3)], "levels": 1, "level_completed": True}])
        self.execute(agent, "action('UP')")
        _, payload = self.execute(agent, "action('DOWN'); print(animation_history()['records']); action('UP')")
        self.assertIn("[]", payload["stdout"])
        self.assertIn("TerminalStateActionError", payload["error"])
        self.assertEqual(len(game.actions), 2)
        self.assertEqual(session._animation_history_v4.level, 2)

    def test_death_and_auto_reset_clear_history_but_preserve_last_animation(self):
        agent, session, _ = self.connect([{"frames": [board(2), board()]},
                                          {"frames": [board(3), board()], "game_over": True},
                                          {"frames": [board()]}])
        self.execute(agent, "action('UP'); action('DOWN')")
        self.assertEqual(session._animation_history_v4.records, {})
        last = copy.deepcopy(session.animation_record)
        session._execute_auto_reset()
        self.assertEqual(session._animation_history_v4.records, {})
        self.assertEqual(session.animation_record, last)  # existing fatal-animation behavior

    def test_new_game_rejects_previous_game_id(self):
        agent, session, _ = self.connect([{"frames": [board(2), board()]}])
        self.execute(agent, "action('UP')")
        old = next(iter(session._animation_history_v4.records))
        other, other_session, _ = self.fixture.connect(Game([{"frames": [board(4), board()]}]), session_name="other")
        _, payload = self.execute(other, f"action('UP'); print(animation_frames({old!r})['error'])")
        self.assertIn("unavailable", payload["stdout"])
        self.assertNotEqual(session._animation_history_v4.scope, other_session._animation_history_v4.scope)

    def test_persistent_change_is_unchanged_and_transient_feedback_can_coexist(self):
        agent, session, _ = self.connect([{"frames": [board(1), board(2), board(1)]}])
        dispatch, payload = self.execute(agent, "action('UP'); print(animation_history()['records'][0]['action_num'])")
        self.assertIn("-> effect", payload["stdout"])
        self.assertTrue(dispatch.made_progress)
        self.assertTrue(session.history_entries[-1].result["gameplay_changed"])

    def test_existing_batch_execution_and_early_stop_are_identical(self):
        observations = []
        for arm in ['baseline', 'candidate']:
            agent, session, game = self.connect([{"frames": [board(1)]}, {"frames": [board(2), board(1)]}], arm)
            _, payload = self.execute(agent, "action(['UP','DOWN','LEFT'])")
            observations.append((game.actions, agent._last_action_call_result))
            self.assertEqual(len(game.actions), 2)
            self.assertTrue(agent._last_action_call_result["stopped_early"])
            self.assertEqual(agent._last_action_call_result["stop_reason"], "no_op_action")
            if arm == 'candidate':
                self.assertIn("ENDPOINT UNCHANGED", agent._last_action_call_result["stop_detail"])
                self.assertEqual(len(session._animation_history_v4.records), 1)
        self.assertEqual(observations[0][0], observations[1][0])
        for key in ["no_op", "gameplay_changed", "gameplay_changed_per_action", "executed_count", "skipped_actions"]:
            self.assertEqual(observations[0][1][key], observations[1][1][key], key)

    def test_earlier_animation_inside_one_batch_remains_retrievable(self):
        agent, session, game = self.connect([{"frames": [board(2), board(1)]}, {"frames": [board(3)]}])
        _, payload = self.execute(agent, """action(['UP','DOWN'])
r = animation_history()['records'][0]
print('batch earlier', r['action_num'], animation_frames(r['animation_id'])['frames'][0].ascii.splitlines()[5][5])
print('last', len(last_animation_frames))
""")
        self.assertNotIn('error', payload)
        self.assertEqual(len(game.actions), 2)
        self.assertIn('batch earlier 1 2', payload['stdout'])
        self.assertIn('last 0', payload['stdout'])

    def test_last_animation_interfaces_match_baseline_and_aliases_refresh(self):
        outputs = []
        for arm in ['baseline', 'candidate']:
            agent, session, _ = self.connect([{"frames": [board(2), board()]}, {"frames": [board(4), board()]}], arm)
            _, payload = self.execute(agent, """alias = last_animation_frames
action('UP')
print('first', alias[0].ascii.splitlines()[5][5], dict(last_animation_timeline)['frames'])
action('DOWN')
print('second', alias[0].ascii.splitlines()[5][5], dict(last_animation_timeline)['frames'])
""")
            self.assertNotIn("error", payload)
            outputs.append([s for s in payload['stdout'].splitlines() if not s.startswith('[action]')])
        self.assertEqual(outputs, [['first 2 2', 'second 4 2']] * 2)

    def test_existing_timeline_disable_switch_is_preserved(self):
        with patch.dict(os.environ, {'ARC3_ANIMATION_TIMELINE': '0'}):
            agent, _, _ = self.connect([{'frames': [board(2), board()]}])
            _, payload = self.execute(agent, """action('UP')
print('last timeline', dict(last_animation_timeline))
r = animation_history()['records'][0]
print('history timeline', animation_timeline(r['animation_id'])['timeline']['frames'])
""")
            self.assertNotIn('error', payload)
            self.assertIn('last timeline {}', payload['stdout'])
            self.assertIn('history timeline 2', payload['stdout'])

    def test_terminal_feedback_precedence_matches_v3(self):
        for key in ['game_over', 'run_complete', 'done', 'level_completed']:
            item = {'executed': True, 'gameplay_changed': False,
                    'animation': {'frames': 7, 'transient_pixels': 256}, key: True}
            baseline = self.fixture.arms['baseline'][2]['_action_verdict'](item)
            candidate = self.fixture.arms['candidate'][2]['_action_verdict'](item)
            self.assertEqual(baseline, candidate)

    def test_helpers_and_ordinary_python_error_preserve_exports_and_actions(self):
        agent, session, game = self.connect([{"frames": [board(2), board()]}])
        _, payload = self.execute(agent, "def helper(): return 7\naction('UP'); raise ValueError('ordinary')")
        self.assertIn("ordinary", payload["error"])
        self.assertIn("helper", agent._kept_functions)
        _, resumed = self.execute(agent, "print(helper()); print(len(animation_history()['records']))")
        self.assertEqual(resumed["stdout"], "7\n1\n")
        self.assertEqual(len(game.actions), 1)

    def test_flags_are_independent_and_default_off(self):
        for feedback, history in [("1", "0"), ("0", "1"), ("0", "0"), (None, None)]:
            with self.subTest(feedback=feedback, history=history), patch.dict(os.environ):
                for key, value in [("ARC3_V4_TRANSIENT_FEEDBACK", feedback), ("ARC3_V4_ANIMATION_HISTORY", history)]:
                    if value is None: os.environ.pop(key, None)
                    else: os.environ[key] = value
                agent, session, _ = self.connect([{"frames": [board(2), board()]}])
                _, payload = self.execute(agent, "action('UP'); print('history_api', 'animation_history' in dir())")
                self.assertEqual("ENDPOINT UNCHANGED" in payload["stdout"], feedback == "1")
                self.assertIn(f"history_api {history == '1'}", payload["stdout"])
                self.assertEqual(hasattr(session, '_animation_history_v4'), history == '1')

    def test_both_flags_off_equal_baseline_payloads_helpers_and_actions(self):
        for code in ["action('UP'); action('DOWN'); print(current_frame.ascii)",
                     "action(['UP','DOWN','LEFT'])",
                     "def helper(): return 7\naction('UP'); raise ValueError('ordinary')"]:
            observations = []
            with self.subTest(code=code), patch.dict(os.environ, {"ARC3_V4_TRANSIENT_FEEDBACK": "0", "ARC3_V4_ANIMATION_HISTORY": "0"}):
                for arm in ['baseline', 'candidate']:
                    agent, session, game = self.connect([{"frames": [board(2), board()]}, {"frames": [board(3)]}], arm)
                    dispatch, payload = self.execute(agent, code)
                    observations.append((payload, game.actions, agent._kept_functions, agent._last_step_summary,
                                         dispatch.step_executed, dispatch.made_progress))
                self.assertEqual(observations[0], observations[1])

    def test_tool_guidance_exposes_retrieval_and_flag_off_prompt_matches(self):
        baseline_prompt = self.fixture.arms['baseline'][1]['_build_system_prompt'](tool_output_tokens=3072)
        candidate_builder = self.fixture.arms['candidate'][1]['_build_system_prompt']
        prompt = candidate_builder(tool_output_tokens=3072)
        self.assertIn("animation_history()['records']", prompt)
        self.assertIn("animation_frames(animation_id)", prompt)
        with patch.dict(os.environ, {"ARC3_V4_TRANSIENT_FEEDBACK": "0", "ARC3_V4_ANIMATION_HISTORY": "0"}):
            self.assertEqual(baseline_prompt, candidate_builder(tool_output_tokens=3072))

    def test_pins_reject_drift_before_writing_and_diff_roundtrip(self):
        original = self.fixture.original
        for key in BASE_HASHES:
            drift = dict(original); drift[key] += b'\n'
            with self.assertRaises(ValueError): patched_sources(drift)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'ARC3-Inference/inference'
            for name, raw in original.items():
                (target/name).parent.mkdir(parents=True, exist_ok=True); (target/name).write_bytes(raw)
            (target/'utils').mkdir()
            drift = target/'agent/tool_agent.py'
            drift.write_bytes(drift.read_bytes() + b'\n')
            before = {name: (target/name).read_bytes() for name in original}
            with self.assertRaises(ValueError): apply(directory)
            self.assertEqual({name: (target/name).read_bytes() for name in original}, before)
            drift.write_bytes(original['agent/tool_agent.py'])
            apply(directory)
            for name, raw in self.fixture.candidate.items(): self.assertEqual((target/name).read_bytes(), raw)
            with self.assertRaises(ValueError): apply(directory)
        diff = source_diff(original, self.fixture.candidate)
        self.assertIn('ENDPOINT UNCHANGED', diff)
        self.assertNotIn('_hard_timeout', diff)

    def test_builder_preserves_v3_cells_reproducible_and_combined_flags_enabled(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        baseline = ROOT/'arc-agi-3-milestone-2-solution.ipynb'
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            output = Path(directory)/'one.ipynb'
            notebook, manifest = build(output)
            original = json.loads(baseline.read_bytes())
            self.assertEqual([source(c) for i,c in enumerate(notebook['cells']) if i != 5], [source(c) for c in original['cells']])
            for key in ['ARC3_V4_TRANSIENT_FEEDBACK', 'ARC3_V4_ANIMATION_HISTORY']: self.assertTrue(manifest['flags'][key])
            self.assertFalse(manifest['flags']['ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT'])
            other = Path(directory)/'two.ipynb'; build(other)
            self.assertEqual(output.read_bytes(), other.read_bytes())
            control = Path(directory)/'control.ipynb'; _, off = build(control, feedback=False, history=False)
            self.assertFalse(any(off['flags'].values()))
            target = Path(directory)/'bundle/src/ARC3-Inference/inference'
            for name, raw in self.fixture.original.items():
                (target/name).parent.mkdir(parents=True,exist_ok=True); (target/name).write_bytes(raw)
            (target/'utils').mkdir()
            with patch.dict(os.environ):
                exec(compile(source(notebook['cells'][5]), 'emitted_v4_cell', 'exec'), {'BUNDLE_DIR':Path(directory)/'bundle'})
                self.assertEqual(os.environ['ARC3_V4_ANIMATION_HISTORY'], '1')
                self.assertEqual(os.environ['ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT'], '0')
            for name, raw in self.fixture.candidate.items(): self.assertEqual((target/name).read_bytes(), raw)
            with self.assertRaises(FileExistsError): build(output)
            with self.assertRaises(ValueError): build(baseline)
        self.assertEqual(hashlib.sha256(baseline.read_bytes()).hexdigest(), SOURCE_SHA256)

    def test_real_tn36_sc25_prefixes_recover_earlier_transient_records(self):
        env = patch.dict(os.environ, {'OPERATION_MODE': 'offline', 'ONLY_RESET_LEVELS': 'true',
                                     'MPLCONFIGDIR': str(Path(self.temp.name)/'mpl')})
        env.start()
        self.addCleanup(env.stop)
        import arc_agi
        arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE,
                                environments_dir=str(ROOT/'environment_files'),
                                recordings_dir=str(Path(self.temp.name)/'recordings'))
        with zipfile.ZipFile(ROOT/'downloads/results.zip') as archive:
            benchmark = json.loads(archive.read('benchmark.json'))
            event_boards = {}
            for episode in ['tn36-ef4dde99_p0', 'sc25-635fd71a_p3']:
                event_boards[episode] = [e['board'] for e in
                    (json.loads(line) for line in archive.open('artifacts/'+episode+'_events.jsonl'))
                    if e.get('type') == 'action']
        for prefix, pass_index, count, target_action, frames, pixels, levels in [
            ('tn36', 0, 6, 5, 7, 256, 7), ('sc25', 3, 38, 36, 5, 36, 6)]:
            with self.subTest(game=prefix):
                runs = [r for r in benchmark['game_runs'] if r['game_id'].startswith(prefix)]
                run = next(r for r in runs if Path(r['solver_analysis_html']).stem.endswith(f'_p{pass_index}'))
                game = OfflineGame(arcade.make(run['game_id']), levels)
                agent, session, _ = self.fixture.connect(game, session_name=prefix)
                actions=[]
                for h in run['history'][:count]:
                    item=h['action']; data=item.get('data') or {}; action={'action':REVERSE[item['id']]}
                    if item['id']=='ACTION6': action.update(row=data['y'],col=data['x'])
                    actions.append(action)
                code='\n'.join(f'action([{a!r}])' for a in actions)
                code+=f"\nr = next(r for r in animation_history()['records'] if r['action_num'] == {target_action})\nx = animation_frames(r['animation_id'])\nprint('recovered', r['action_num'], len(x['frames']), x['truncated'])\nprint(animation_timeline(r['animation_id'])['timeline']['frames'])"
                _, payload = self.execute(agent,code)
                self.assertNotIn('error',payload)
                self.assertEqual(len(game.actions),count)
                self.assertIn(f'recovered {target_action} {frames} False',payload['stdout'])
                result=session.history_entries[target_action-1].result
                self.assertEqual(result['animation']['transient_pixels'],pixels)
                self.assertIn('ENDPOINT UNCHANGED',payload['stdout'])
                episode = Path(run['solver_analysis_html']).stem
                self.assertEqual([[list(row) for row in entry.frame.grid] for entry in session.history_entries],
                                 event_boards[episode][:count])


if __name__ == '__main__':
    unittest.main()
