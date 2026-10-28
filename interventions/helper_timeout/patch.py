"""Opt-in overlay for the released Franzen V3 harness, applied before imports.

The pinned notebook and submitted artifacts remain immutable. This file is
embedded verbatim in a separate candidate notebook by build.py.
"""
from pathlib import Path
import hashlib


FLAG = "ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT"
BASE_HASHES = {
    "python_tool_sandbox.py": "c07b2dbaffdbf2a852f45c36d309146639d1c472e1ff72ce96d6369e40061ded",
    "tool_agent.py": "1a36bda19859c55e9225fb52ce33ddad5f02bb57fbb384d37177795b4dbb25fc",
}

# Only the parent supervisor may set this marker. Child final/error messages
# are explicitly reconstructed by run_sandboxed_python and cannot forward it.
TIMEOUT_BEFORE = '''                return {
                    "error": f"Tool timed out after {timeout_seconds}s",
                    "stdout": "",
                    "action_results": list(host_action_results),
                }
'''
TIMEOUT_AFTER = '''                return {
                    "error": f"Tool timed out after {timeout_seconds}s",
                    "stdout": "",
                    "action_results": list(host_action_results),
                    **({"_hard_timeout": True} if os.environ.get(
                        "ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT", ""
                    ).strip().lower() in {"1", "true", "yes", "on"} else {}),
                }
'''

RECORD_BEFORE = '''            previous = self._kept_functions
            kept = {}
'''
RECORD_AFTER = '''            previous = self._kept_functions
            # Opt-in: no export was committed by the killed child. Retain only
            # the prior source snapshot, never the child's partial definitions.
            # An exact supervisor envelope fails closed on incomplete metadata,
            # explicit exports (including []/None), or validation rejections.
            if (
                _get_env_bool("ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT", False)
                and set(sandbox_result) == {
                    "_hard_timeout", "error", "stdout", "action_results"
                }
                and sandbox_result.get("_hard_timeout") is True
                and sandbox_result.get("error") == f"Tool timed out after {self._python_timeout}s"
                and sandbox_result.get("stdout") == ""
                and isinstance(sandbox_result.get("action_results"), list)
                and all(isinstance(item, dict) for item in sandbox_result["action_results"])
            ):
                payload["function_retention"] = (
                    "Python hard timeout: kept the previous committed helper source snapshot; "
                    "new or revised definitions from this call were not committed. "
                    "Already executed actions remain executed; inspect current state before continuing. "
                    "Retained helpers may be incorrect; recheck their assumptions."
                )
                return
            kept = {}
'''


def patched_sources(sources):
    """Validate both post-release inputs before producing either replacement."""
    replacements = {}
    for name, before, after in (
        ("python_tool_sandbox.py", TIMEOUT_BEFORE, TIMEOUT_AFTER),
        ("tool_agent.py", RECORD_BEFORE, RECORD_AFTER),
    ):
        raw = sources[name]
        if hashlib.sha256(raw).hexdigest() != BASE_HASHES[name]:
            raise ValueError(f"{name}: not the pinned applied Franzen V3 source")
        text = raw.decode("utf-8")
        if text.count(before) != 1:
            raise ValueError(f"{name}: expected exactly one intervention anchor")
        text = text.replace(before, after, 1)
        compile(text, name, "exec")
        replacements[name] = text.encode("utf-8")
    return replacements


def apply(bundle_src):
    """Patch a fresh, already release-patched bundle before importing it."""
    agent_dir = Path(bundle_src) / "ARC3-Inference/inference/agent"
    replacements = patched_sources({name: (agent_dir / name).read_bytes() for name in BASE_HASHES})
    for name, raw in replacements.items():
        (agent_dir / name).write_bytes(raw)
