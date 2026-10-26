"""Kaggle input preflight: no model loading, installation or network calls."""
import hashlib
import json
import platform
import sys
from pathlib import Path

assert sys.version_info[:2] == (3, 12), "Released wheelhouse requires Python 3.12"
assert platform.system() == "Linux" and platform.machine() == "x86_64"
_inputs = {
    "competition": Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3"),
    "wheelhouse": Path("/kaggle/input/datasets/dfranzen/pennyroyal-v253"),
    "bundle": Path("/kaggle/input/datasets/dfranzen/taaf-kaggle-source-bundle-copy"),
    "target": Path("/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1"),
    "draft": Path("/kaggle/input/models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1"),
}
for _name, _path in _inputs.items():
    assert _path.is_dir(), f"Missing attached input {_name}: {_path}"
for _name in ("deploy_target.pkl", "benchmark_initial.pkl", "git_status.txt", "src"):
    assert (_inputs["bundle"] / _name).exists(), f"Missing source bundle member: {_name}"
for _name in ("arc_agi_3_wheels", "environment_files"):
    assert (_inputs["competition"] / _name).is_dir(), f"Missing competition member: {_name}"


def _unique(_root, _name):
    _hits = list(_root.rglob(_name))
    assert len(_hits) == 1, f"Expected one {_name}, found {_hits}"
    return _hits[0]


def _hash(_path):
    return hashlib.sha256(_path.read_bytes()).hexdigest()


_lock = _unique(_inputs["wheelhouse"], "requirements.lock")
_wheels = _unique(_inputs["wheelhouse"], "wheels")
_sglang = list(_wheels.glob("sglang-*.whl"))
assert len(_sglang) == 1 and _sglang[0].name == "sglang-0.5.19+gd00d88efc8d6-cp312-cp312-linux_x86_64.whl"
assert len(list(_wheels.glob("uv-*.whl"))) == 1
_token_map = list(_inputs["wheelhouse"].rglob("hot_tokens_64k.pt")) or list(_inputs["wheelhouse"].rglob("flash-next-64k.pt"))
assert len(_token_map) == 1
assert _hash(_token_map[0]) == "becfa41d394b86c26c632bea8f3c6ea64bbb76d7b238d8673c06afae21269f25"
assert _hash(_inputs["target"] / "tokenizer.json") == "06b9509352d2af50381ab2247e083b80d32d5c0aba91c272ca9ff729b6a0e523"
_report = {
    "python": sys.version, "inputs": {}, "wheel_count": len(list(_wheels.glob("*.whl"))),
    "lock_sha256": _hash(_lock), "sglang_wheel_sha256": _hash(_sglang[0]),
}
for _name in ("target", "draft"):
    _root = _inputs[_name]
    _index = _unique(_root, "model.safetensors.index.json")
    _mapping = json.loads(_index.read_text())["weight_map"]
    _shards = sorted(set(_mapping.values()))
    for _shard in _shards:
        _relative = Path(_shard)
        assert not _relative.is_absolute() and ".." not in _relative.parts
        assert (_index.parent / _relative).stat().st_size > 8, f"Missing/empty shard {_shard}"
    _cfg = json.loads((_index.parent / "config.json").read_text())
    _q = _cfg["quantization_config"]
    if _name == "target":
        assert len(_shards) == 38 and _q["quant_method"] == "auto-round" and _q["bits"] == 4
    else:
        assert len(_shards) == 2 and _q["quant_method"] == "compressed-tensors"
        _w = _q["config_groups"]["mtp_routed_experts"]["weights"]
        assert (_w["num_bits"], _w["group_size"], _w["symmetric"]) == (4, 32, True)
    _report["inputs"][_name] = {
        "path": str(_root), "shards": len(_shards), "index_sha256": _hash(_index),
        "config_sha256": _hash(_index.parent / "config.json"),
        "weight_bytes": sum((_index.parent / s).stat().st_size for s in _shards),
    }
_out = Path("/kaggle/working/franzen-preflight.json")
_out.parent.mkdir(parents=True, exist_ok=True)
_out.write_text(json.dumps(_report, indent=2) + "\n")
print("INPUT PREFLIGHT PASSED", json.dumps(_report, indent=2))
