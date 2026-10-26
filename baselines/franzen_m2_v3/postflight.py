"""Run in the Kaggle smoke notebook after gameplay; archive small evidence only."""
import hashlib
import importlib.metadata
import json
import subprocess
import time
import zipfile
from pathlib import Path

_work = Path("/kaggle/working")
_report = {
    "scope": "bounded offline smoke; no competition score",
    "finished_epoch": time.time(),
    "notebook_start_epoch": globals().get("NOTEBOOK_START_TIME"),
    "gameplay_start_epoch": globals().get("smoke_start"),
    "versions": {}, "source_sha256": {}, "artifacts": {},
}
for _package in ("arc-agi", "arcengine", "numpy", "pandas", "pyarrow"):
    try:
        _report["versions"][_package] = importlib.metadata.version(_package)
    except importlib.metadata.PackageNotFoundError:
        _report["versions"][_package] = None
_report["gpu"] = subprocess.check_output(
    ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader"], text=True
).strip()
_source = Path("/kaggle/taaf-kaggle-source-share/src")
for _path in sorted(_source.rglob("*.py")):
    if ".git" not in _path.parts and "__pycache__" not in _path.parts:
        _report["source_sha256"][str(_path.relative_to(_source))] = hashlib.sha256(_path.read_bytes()).hexdigest()
for _path in sorted(_work.rglob("*")):
    if _path.is_file() and _path.suffix in {".json", ".jsonl", ".txt", ".log", ".parquet"}:
        _report["artifacts"][str(_path.relative_to(_work))] = {
            "bytes": _path.stat().st_size,
            "sha256": hashlib.sha256(_path.read_bytes()).hexdigest(),
        }
_parquet = _work / "submission.parquet"
if _parquet.exists():
    import pandas as pd
    _table = pd.read_parquet(_parquet)
    assert list(_table.columns) == ["row_id", "game_id", "end_of_game", "score"]
    _report["parquet"] = {
        "rows": len(_table), "dtypes": {k: str(v) for k, v in _table.dtypes.items()},
        "placeholder_only": True,
    }
_path = _work / "franzen-postflight.json"
_path.write_text(json.dumps(_report, indent=2) + "\n")
with zipfile.ZipFile(_work / "franzen-smoke-evidence.zip", "w", zipfile.ZIP_DEFLATED) as _archive:
    for _name in [*_report["artifacts"], "franzen-postflight.json"]:
        _archive.write(_work / _name, _name)
print("POSTFLIGHT", json.dumps({k: v for k, v in _report.items() if k != "source_sha256"}, indent=2))
