"""CPU fixture: real V3 sandbox/retention code, fake game and display adapters.

No model client, benchmark, GPU, or game implementation is loaded. Cached
post-patch files are verified against both pins and notebook patch hunks before
use. New utility files are reconstructed directly from that notebook patch.
"""
import ast
import copy
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace

from baselines.franzen_m2_v3.prepare import ROOT, SOURCE_SHA256, source
from interventions.helper_timeout.patch import BASE_HASHES


def release_sources():
    raw = (ROOT / "arc-agi-3-milestone-2-solution.ipynb").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    notebook = json.loads(raw)
    blocks = {}
    for block in source(notebook["cells"][2]).split("diff --git ")[1:]:
        path = block.splitlines()[0].split()[1][2:]
        blocks[path] = block
    originals = {}
    for name, digest in BASE_HASHES.items():
        raw = (ROOT / "local_output/research_refs/franzen/ARC3-Inference/inference/agent" / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        lines = raw.decode().splitlines()
        block = blocks["ARC3-Inference/inference/agent/" + name]
        # Every release patch post-image must occur at its declared line.
        for hunk in re.split(r"(?m)^@@ ", block)[1:]:
            header, *body = hunk.splitlines()
            match = re.match(r"-\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", header)
            assert match, header
            post = [line[1:] for line in body if line.startswith((" ", "+"))]
            start, count = int(match[1]) - 1, int(match[2] or 1)
            assert len(post) == count and lines[start:start + count] == post, name
        originals[name] = raw
    utilities = {}
    for name in ("retained_functions", "frame_diff"):
        block = blocks[f"ARC3-Inference/inference/utils/{name}.py"]
        assert "new file mode" in block
        utilities[name] = "\n".join(
            line[1:] for line in block.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ) + "\n"
        compile(utilities[name], name, "exec")
    return originals, utilities


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_sandbox(directory, raw, utilities, tag):
    """Run the actual supervisor/bootstrap; segmentation is deliberately unused."""
    directory = Path(directory)
    modules = {}
    for name, text in {**utilities, "segmentation": (
        "def segment_layer(*args, **kwargs):\n"
        "    raise AssertionError('Segmentation is outside this CPU fixture')\n"
    )}.items():
        path = directory / f"{tag}_{name}.py"
        path.write_text(text)
        modules[name] = load_module(f"{tag}_{name}", path)
    # Only import adapters differ. Subprocess, pipe protocol, source collection,
    # process kill and host action handling all execute their original bodies.
    tree = ast.parse(raw.decode())
    tree.body = [n for n in tree.body if not (
        isinstance(n, ast.ImportFrom) and (n.module or "").startswith("inference.")
    )]
    ns = {
        "__name__": f"{tag}_sandbox",
        "_segmentation": modules["segmentation"],
        "_frame_diff_module": modules["frame_diff"],
        "_retained_functions": modules["retained_functions"],
        "ARC_COLOR_CHARS": "0123456789abcdef",
    }
    exec(compile(tree, f"{tag}_python_tool_sandbox.py", "exec"), ns)
    return ns["run_sandboxed_python"], modules["retained_functions"]


def load_agent(raw, runner, retention):
    """Execute real dispatch/retention/lifecycle methods, with runtime adapters."""
    tree = ast.parse(raw.decode())
    functions = {
        "_get_env_bool", "_get_env_int", "_persistent_functions", "_persistent_functions_scope",
        "_normalize_valid_actions", "_terminal_action_reason", "_terminal_action_stop_detail",
        "_animation_enabled", "_animation_timeline_enabled", "_empty_world_model",
        "_ascii_frame_view_payload", "_ascii_history_view_payload", "_to_ascii_frame_view",
        "_priority_action_count",
    }
    methods = {
        "_ensure_session", "_retained_sources", "_record_retained_functions",
        "_retained_function_context", "_run_python_tool", "_normalize_python_actions",
        "_compact_action_result", "_summarize_step_sequence", "_turn_action_trace",
        "_update_summarized_knowledge_from_step_summary",
    }
    body = [n for n in tree.body if getattr(n, "name", "") in functions | {
        "_AsciiFrameView", "_ToolDispatchResult",
    }]
    original_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ToolAgent")
    selected_class = copy.deepcopy(original_class)
    selected_class.body = [n for n in selected_class.body if getattr(n, "name", "") in methods]
    # Exercise the unchanged turn-scope block without entering the model loop.
    turn_block = next(n for n in ast.walk(original_class) if isinstance(n, ast.If)
                      and ast.unparse(n.test) == "not resuming_after_yield and _persistent_functions_scope() == 'turn'")
    turn_method = ast.parse("def _fixture_turn_boundary(self, resuming_after_yield): pass").body[0]
    turn_method.body = [copy.deepcopy(turn_block)]
    selected_class.body.append(turn_method)
    body.append(selected_class)
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)] + body, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {
        "__name__": "franzen_cpu_fixture", "os": os, "json": json, "re": re,
        "dataclass": dataclass, "Path": Path, "run_sandboxed_python": runner,
        "function_signature": retention.function_signature,
        "to_engine_action": lambda name: name,
        "to_model_action": lambda name: name,
        "reset_exposed": lambda: True,
        "_WM_WIPE_ON_GAME_OVER": False,
        "_new_noop_wording": lambda: False,
    }
    # dataclasses consult the module namespace only for string annotations.
    mod = ModuleType(ns["__name__"])
    mod.__dict__.update(ns)
    sys.modules[ns["__name__"]] = mod
    exec(compile(module, "franzen_v3_selected_methods", "exec"), mod.__dict__)
    return mod.ToolAgent, mod.__dict__


class FakeGame:
    """Small state machine, not an ARC game or scoring implementation."""
    def __init__(self, transition=None):
        self.frame = SimpleNamespace(grid=[[0]], ascii="0", step=0, level=1, shape=(1, 1))
        self.history = []
        self.actions = []
        self.transition = transition

    def step(self, arguments):
        names = [a["action"] for a in arguments["actions"]]
        self.actions.extend(names)
        self.frame.step += len(names)
        self.frame.grid = [[self.frame.step]]
        self.frame.ascii = str(self.frame.step)
        result = {
            "executed": True, "executed_count": len(names), "requested_count": len(names),
            "executed_actions": names, "action_num": self.frame.step,
            "level": self.frame.level, "valid_actions": ["UP", "DOWN", "RESET"],
            "board_changed": True, "gameplay_changed": True,
            "state": "NOT_FINISHED", "score": 0,
        }
        if self.transition:
            result[self.transition] = True
            if self.transition == "level_completed":
                self.frame.level += 1
                result["level"] = self.frame.level
        self.history.append(SimpleNamespace(action=" ".join(names), frame=copy.deepcopy(self.frame), result=result))
        return result


def make_agent(cls, ns, game, state_path):
    agent = object.__new__(cls)
    agent._session_runtime_dir = None
    agent._kept_functions = {}
    agent._retained_clear_notice = ""
    agent._python_timeout = 1
    agent._current_valid_actions = ["UP", "DOWN", "RESET"]
    agent._noop_repeat_guard = None
    agent._repeat_state_seen = set()
    agent._step_env_callback = game.step
    # File serialization and output formatting are fixture adapters; no network.
    ns["load_runtime_state"] = lambda path: (game.frame, game.history)
    agent._render_tool_payload = lambda payload, **kwargs: json.dumps(payload)
    agent._ensure_session(state_path)
    return agent
