"""CPU adapters around exact V3/V4 host, agent and sandbox methods.

No analyzer/model loop is imported. File/display adapters and TAAF game objects
are replaced; action dispatch, per-action animation capture, batch rules,
animation queries, subprocess protocol and retention execute production source.
"""
import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import arcengine

from franzen_timeout_fixture import load_agent, load_module, load_sandbox, make_agent, release_sources as old_sources
from interventions.transient_feedback_v4.build import release_sources
from interventions.transient_feedback_v4.patch import patched_sources, NEW_FILE

COLORS = "0123456789abcdef"
NAMES = {"UP": "ACTION1", "DOWN": "ACTION2", "LEFT": "ACTION3", "RIGHT": "ACTION4",
         "SPACE": "ACTION5", "MOUSE": "ACTION6", "UNDO": "ACTION7", "RESET": "RESET"}
REVERSE = {value: key for key, value in NAMES.items()}
VALID = list(NAMES)


def ascii_grid(grid):
    return "\n".join("".join(COLORS[int(c)] for c in row) for row in grid)


class Frame:
    def __init__(self, grid, step=0, level=1):
        self.grid, self.step, self.level = grid, step, level
        self.ascii = ascii_grid(grid)
        self.shape = (len(grid), max(map(len, grid), default=0))


class Entry:
    def __init__(self, action, frame, result):
        self.action, self.frame, self.result = action, frame, result


def board(color=0, side=12):
    grid = [[0] * side for _ in range(side)]
    grid[5][5] = color
    return tuple(map(tuple, grid))


class Game:
    def __init__(self, scripts=()):
        self.scripts = iter(scripts)
        self.actions = []
        self.game_run = SimpleNamespace(history=[])
        self.number_of_levels = 7
        self.current_state = self.state([board()])

    def state(self, frames, levels=0, won_level=False, terminal=False):
        return SimpleNamespace(
            frame=SimpleNamespace(data=frames[-1]), levels_completed=levels,
            just_won_level=won_level, won=False,
            raw=SimpleNamespace(frame=frames, state=(arcengine.GameState.GAME_OVER if terminal
                                                     else arcengine.GameState.NOT_FINISHED)),
            available_actions=[action.value for action in arcengine.GameAction])

    def execute_action(self, action, **kwargs):
        self.actions.append((action.id.name, dict(action.data)))
        self.game_run.history.append(action)
        spec = next(self.scripts, {})
        before = self.current_state
        frames = spec.get("frames", [board(1 + len(self.actions) % 14)])
        self.current_state = self.state(frames, spec.get("levels", before.levels_completed),
                                        spec.get("level_completed", False), spec.get("game_over", False))
        return self.current_state


class OfflineGame(Game):
    """TAAF-shaped adapter over actual installed offline ARC environments."""
    def __init__(self, env, levels):
        super().__init__()
        self.env = env
        self.number_of_levels = levels
        self.current_state = self.convert(env.observation_space)

    def convert(self, raw):
        return SimpleNamespace(frame=SimpleNamespace(data=raw.frame[-1]), raw=raw,
                               levels_completed=raw.levels_completed,
                               just_won_level=(raw.levels_completed > getattr(self, "completed", raw.levels_completed)),
                               won=raw.state == arcengine.GameState.WIN,
                               available_actions=[action.value for action in arcengine.GameAction])

    def execute_action(self, action, **kwargs):
        self.completed = self.current_state.levels_completed
        raw = self.env.step(action.id, action.data)
        self.actions.append((action.id.name, dict(action.data)))
        self.game_run.history.append(action)
        self.current_state = self.convert(raw)
        return self.current_state


class HarnessFixture:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.original = release_sources()
        self.candidate = patched_sources(self.original)
        _, self.utilities = old_sources()  # verifies original release hunks, reconstructs utilities
        self.animation = self.load_animation()
        path = self.directory / "history_v4.py"
        path.write_bytes(self.candidate[NEW_FILE])
        self.history = load_module("v4_history_cpu", path)
        self.arms = {name: self.load_arm(sources, name) for name, sources in
                     (("baseline", self.original), ("candidate", self.candidate))}

    def load_animation(self):
        from baselines.franzen_m2_v3.prepare import ROOT, source
        notebook = json.loads((ROOT / "arc-agi-3-milestone-2-solution.ipynb").read_text())
        block = next(b for b in source(notebook["cells"][2]).split("diff --git ")[1:]
                     if b.startswith("a/ARC3-Inference/inference/utils/animation.py "))
        text = "\n".join(line[1:] for line in block.splitlines()
                          if line.startswith("+") and not line.startswith("+++"))
        text = text.replace("from inference.utils.grid_utils import ARC_COLOR_CHARS, format_grid_ascii",
                            "# Color/display adapter supplied by CPU fixture")
        ns = {"ARC_COLOR_CHARS": COLORS, "format_grid_ascii": ascii_grid}
        exec(compile(text, "release_animation.py", "exec"), ns)
        return ns

    def load_arm(self, sources, tag):
        runner, retention = load_sandbox(self.directory, sources["agent/python_tool_sandbox.py"], self.utilities, tag)
        cls, ns = load_agent(sources["agent/tool_agent.py"], runner, retention)
        shared = {"_V4_HISTORY_FLAG": self.history.HISTORY_FLAG, "_v4_enabled": self.history.enabled,
                  "_v4_history_for": self.history.history_for, "_v4_transient_verdict": self.history.transient_verdict,
                  "_V4_ANIMATION_GUIDANCE": self.history.GUIDANCE,
                  "to_engine_action": lambda name: NAMES.get(str(name), str(name)),
                  "to_model_action": lambda name: REVERSE.get(str(name), str(name)),
                  "build_animation_frames": self.animation["build_animation_frames"],
                  "build_animation_view": self.animation["build_animation_view"]}
        ns.update(shared)
        agent_tree = ast.parse(sources["agent/tool_agent.py"].decode())
        agent_class = next(n for n in agent_tree.body if getattr(n, "name", "") == "ToolAgent")
        dispatch = copy.deepcopy(next(n for n in agent_class.body if getattr(n, "name", "") == "_dispatch_tool"))
        prompt = copy.deepcopy(next(n for n in agent_tree.body if getattr(n, "name", "") == "_build_system_prompt"))
        dispatch_module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                                          dispatch, prompt], type_ignores=[])
        exec(compile(ast.fix_missing_locations(dispatch_module), f"{tag}_dispatch_prompt", "exec"), ns)
        cls._dispatch_tool = ns["_dispatch_tool"]
        from baselines.franzen_m2_v3.prepare import ROOT
        prompts = ast.parse((ROOT / "local_output/research_refs/franzen/ARC3-Inference/inference/agent/prompts.py").read_text())
        prompts.body = [node for node in prompts.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
        ns["ARC_COLOR_LEGEND"] = COLORS
        exec(compile(prompts, "release_prompt_constants", "exec"), ns)
        ns.update({"current_grid_image_enabled": lambda: False, "_explain_gameplay_changed": lambda: True,
                   "_memory_sections_disabled": lambda: True, "_prefer_tool_calls": lambda: True,
                   "_level_transfer_guidance_enabled": lambda: False, "undo_exposure_mode": lambda: "on",
                   "_AUTO_FRAME_DIFF": False, "_DIFF_IMAGE": False})
        tree = ast.parse(sources["framework/solver.py"].decode())
        functions = {"_action_verdict", "_build_action_echo", "_build_action_trace", "_interior_gameplay_changed",
                     "_animation_chain", "_grid_from_state", "_level_number", "_engine_action_names",
                     "_model_mouse_action_data", "_format_action_display", "_is_engine_game_over", "_is_run_complete",
                     "_guard_action_data", "_stale_repeat", "_stale_detail", "_guards_active", "_analyzer_reported_tokens"}
        methods = {"_execute_action", "step_env", "_execute_auto_reset", "_normalize_actions", "_error_payload",
                   "_terminal_payload", "action_count", "current_frame"}
        host = copy.deepcopy(next(n for n in tree.body if getattr(n, "name", "") == "_HarnessGameSession"))
        host.decorator_list = []
        host.body = [n for n in host.body if getattr(n, "name", "") in methods]
        module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
                           + [n for n in tree.body if getattr(n, "name", "") in functions] + [host], type_ignores=[])
        ast.fix_missing_locations(module)
        host_ns = {**shared, "arcengine": arcengine, "Any": object, "copy": copy, "Frame": Frame, "HistoryEntry": Entry,
                   "NEW_NOOP_WORDING": True, "ACTION_ECHO": True, "STALE_STATE_BLOCK": True, "GUARDS_FROM_LEVEL": 2,
                   "BATCH_NOOP_BLOCK": True, "NOOP_GUARD_BORDER_WIDTH": 4, "ANIMATION_ENABLED": True,
                   "_BLOCKED_VERDICTS": {}, "reset_exposed": lambda: True,
                   "to_model_actions": lambda names: [REVERSE.get(n, n) for n in names],
                   "collapse_frames": self.animation["collapse_frames"], "normalize_frames": self.animation["normalize_frames"],
                   "summarize_animation": self.animation["summarize_animation"]}
        exec(compile(module, f"{tag}_solver_methods", "exec"), host_ns)
        return cls, ns, host_ns

    def connect(self, game=None, arm="candidate", session_name="game"):
        game = game or Game()
        cls, ns, host_ns = self.arms[arm]
        session = object.__new__(host_ns["_HarnessGameSession"])
        session.game, session.analyzer = game, SimpleNamespace(generated_tokens=0)
        session.token_baseline = 0
        session.history_entries, session.animation_record = [], None
        session.should_stop = lambda: False
        session.timing_payload = lambda: {}
        session.write_runtime_state = lambda: None
        session.write_viewer_payload = lambda: None
        session._append_action_viewer_event = lambda *a: None
        state_path = self.directory / session_name / "state.json"
        # make_agent's initial file adapter is replaced with this host session.
        agent = make_agent(cls, ns, SimpleNamespace(step=session.step_env), state_path)
        agent._python_timeout = 5
        agent._step_env_callback = session.step_env
        agent._current_valid_actions = VALID
        ns["load_runtime_state"] = lambda path: (session.current_frame(), session.history_entries)
        return agent, session, game

    @staticmethod
    def execute(agent, code):
        dispatch = agent._dispatch_tool(Path(agent._session_runtime_dir) / "state.json", "python", {"code": code})
        return dispatch, json.loads(dispatch.content)
