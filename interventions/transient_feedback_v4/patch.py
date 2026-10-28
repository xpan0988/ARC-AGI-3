"""Install A+B only into a fresh, SHA-pinned, already V3-patched bundle."""
import hashlib
from pathlib import Path

BASE_HASHES = {
    "framework/solver.py": "42b4794f0447e071ba118194c64d009f7fa59df0b84f3d9c35da4dd215824c52",
    "agent/tool_agent.py": "1a36bda19859c55e9225fb52ce33ddad5f02bb57fbb384d37177795b4dbb25fc",
    "agent/python_tool_sandbox.py": "c07b2dbaffdbf2a852f45c36d309146639d1c472e1ff72ce96d6369e40061ded",
}
NEW_FILE = "utils/animation_history_v4.py"
IMPORTS = '''from inference.utils.animation_history_v4 import (
    HISTORY_FLAG as _V4_HISTORY_FLAG, enabled as _v4_enabled,
    transient_verdict as _v4_transient_verdict, history_for as _v4_history_for,
    GUIDANCE as _V4_ANIMATION_GUIDANCE,
)
'''


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"Expected one V3 anchor: {before[:90]!r}")
    return text.replace(before, after, 1)


def patched_sources(sources, history_source=None):
    for name, digest in BASE_HASHES.items():
        if hashlib.sha256(sources[name]).hexdigest() != digest:
            raise ValueError(f"{name}: not the pinned applied V3 source")
    if history_source is None:
        history_source = Path(__file__).with_name("history.py").read_text()
    solver = sources["framework/solver.py"].decode()
    solver = replace_once(solver, "def _action_verdict(item: dict) -> str:\n",
                          IMPORTS + "from inference.utils.animation import build_animation_frames, build_animation_view\n\n\ndef _action_verdict(item: dict) -> str:\n")
    solver = replace_once(solver, '    if changed is False:\n        return (',
                          '    if changed is False:\n        return _v4_transient_verdict(item) or (')
    solver = replace_once(solver, '        previous_completed = int(self.game.current_state.levels_completed)\n',
                          '        previous_completed = int(self.game.current_state.levels_completed)\n'
                          '        v4_previous_level = _level_number(self.game) if _v4_enabled(_V4_HISTORY_FLAG) else None\n')
    solver = replace_once(solver, '        payload["automatic"] = automatic\n',
                          '        payload["automatic"] = automatic\n'
                          '        if _v4_enabled(_V4_HISTORY_FLAG):\n'
                          '            animation_id = _v4_history_for(self).observe(\n'
                          '                payload, self.animation_record if animation_summary else None, v4_previous_level)\n'
                          '            if animation_id is not None:\n'
                          '                payload["animation_id"] = animation_id\n')
    solver = replace_once(solver, '            "animation", "automatic",\n',
                          '            "animation", "automatic", "animation_id",\n')
    solver = replace_once(solver, '        if str(arguments.get("query") or "").strip() == "animation":\n',
                          '        if str(arguments.get("query") or "").strip() == "animation":\n'
                          '            if _v4_enabled(_V4_HISTORY_FLAG) and arguments.get("history") is True:\n'
                          '                return {"executed": False, "query": "animation", "history":\n'
                          '                    _v4_history_for(self).query(arguments.get("kind"), arguments.get("animation_id"),\n'
                          '                                                build_animation_frames, build_animation_view)}\n')
    solver = replace_once(solver, '        self.write_viewer_payload()\n        return final_payload\n',
                          '''        if stop_reason == "no_op_action" and _v4_transient_verdict(executed_payloads[-1]):
            final_payload["stop_detail"] = (
                f"Action {len(executed_payloads)} of {batch_size}: "
                + _v4_transient_verdict(executed_payloads[-1])
                + f". Remaining actions {final_payload.get('skipped_actions', [])!r} were SKIPPED "
                  "under the existing batch no-op rule. Inspect the animation; "
                  "an unchanged endpoint does not mean nothing happened."
            )
        self.write_viewer_payload()
        return final_payload
''')
    agent = sources["agent/tool_agent.py"].decode()
    agent = replace_once(agent, 'log = logging.getLogger(__name__)\n', IMPORTS + '\nlog = logging.getLogger(__name__)\n')
    agent = replace_once(agent, '                verdict = (\n                    "NO-OP (executed, no change inside the board area)"',
                         '                verdict = _v4_transient_verdict(item) or (\n                    "NO-OP (executed, no change inside the board area)"')
    agent = replace_once(agent, '        prompt += ANIMATION_ADDENDUM\n',
                         '        prompt += ANIMATION_ADDENDUM\n        if _v4_enabled(_V4_HISTORY_FLAG):\n            prompt += _V4_ANIMATION_GUIDANCE\n')
    agent = replace_once(agent, '                "current_frame": current_frame_payload,\n',
                         '                **({"animation_history_enabled": True} if _v4_enabled(_V4_HISTORY_FLAG) else {}),\n'
                         '                "current_frame": current_frame_payload,\n')
    agent = replace_once(agent, '            raw = self._step_env_callback({"query": "animation"})\n',
                         '''            if (_v4_enabled(_V4_HISTORY_FLAG) and request.get("kind") in
                    {"history", "history_frames", "history_timeline"}):
                raw = self._step_env_callback({"query": "animation", "history": True,
                    "kind": request["kind"], "animation_id": request.get("animation_id")})
                return raw.get("history", {}) if isinstance(raw, dict) else {}
            raw = self._step_env_callback({"query": "animation"})
''')
    agent = replace_once(agent, '"action_echo", "animation"):', '"action_echo", "animation", "animation_id"):')
    sandbox = sources["agent/python_tool_sandbox.py"].decode()
    sandbox = replace_once(sandbox, '''        def _animation_fetch(kind):
            _send({"type": "animation", "request": {"kind": kind}})
''', '''        def _animation_fetch(kind, animation_id=None):
            request = {"kind": kind}
            if animation_id is not None:
                request["animation_id"] = animation_id
            _send({"type": "animation", "request": request})
''')
    sandbox = replace_once(sandbox, '            payload = reply.get("animation")\n',
                           '''            payload = reply.get("animation")
            if kind in {"history", "history_frames", "history_timeline"}:
                payload = dict(payload or {})
                if kind == "history_frames":
                    payload["frames"] = [FrameView(**item) for item in payload.get("frames", [])]
                return payload
''')
    sandbox = replace_once(sandbox, '        _refresh_state(initial.get("state") or {})\n',
                           '''        if (initial.get("animation_enabled")
                and (initial.get("state") or {}).get("animation_history_enabled")):
            runtime_globals["animation_history"] = lambda: _animation_fetch("history")
            runtime_globals["animation_frames"] = lambda animation_id: _animation_fetch("history_frames", animation_id)
            runtime_globals["animation_timeline"] = lambda animation_id: _animation_fetch("history_timeline", animation_id)

        _refresh_state(initial.get("state") or {})
''')
    result = {"framework/solver.py": solver.encode(), "agent/tool_agent.py": agent.encode(),
              "agent/python_tool_sandbox.py": sandbox.encode(), NEW_FILE: history_source.encode()}
    for name, raw in result.items():
        compile(raw, name, "exec")
    return result


def apply(bundle_src, history_source=None):
    root = Path(bundle_src) / "ARC3-Inference/inference"
    if (root / NEW_FILE).exists():
        raise ValueError("V4 history module already exists; expected a fresh V3 bundle")
    if not (root / NEW_FILE).parent.is_dir():
        raise ValueError("Missing V3 utilities directory; refusing an incomplete bundle")
    result = patched_sources({name: (root / name).read_bytes() for name in BASE_HASHES}, history_source)
    for name, raw in result.items():
        (root / name).write_bytes(raw)
