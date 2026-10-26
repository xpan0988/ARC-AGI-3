"""Build isolated notebooks from the hash-pinned Kaggle Version 3; never run them."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE_SHA256 = "589eaf393f416effe925c6830fc00fcdc0d6da91193b29ff0029282cbd6ee96e"


def source(cell):
    value = cell["source"]
    return value if isinstance(value, str) else "".join(value)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_python(cell, index):
    code = source(cell)
    if code.startswith("%%writefile "):
        assert index == 2 and code.startswith("%%writefile /kaggle/harness-changes.patch\n")
        return
    lines = ["pass" if line.startswith("!") else line for line in code.splitlines()]
    compile("\n".join(lines), f"notebook_cell_{index}", "exec", ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)


def build(source_path, output_dir):
    raw = source_path.read_bytes()
    if sha(raw) != SOURCE_SHA256:
        raise ValueError("Reference notebook differs from released Version 3; refusing to build")
    original = json.loads(raw)
    assert original["nbformat"] == 4 and len(original["cells"]) == 23
    notebook = copy.deepcopy(original)
    notebook["metadata"] = {
        key: copy.deepcopy(original["metadata"][key])
        for key in ("kaggle", "kernelspec", "language_info")
    }
    notebook["metadata"]["kaggle"].update(
        accelerator="nvidiaRtxPro6000", isGpuEnabled=True, isInternetEnabled=False
    )
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            validate_python(cell, i)
            cell["outputs"] = []
            cell["execution_count"] = None
        cell["metadata"] = {
            key: value for key, value in cell.get("metadata", {}).items()
            if key not in {"execution", "papermill"}
        }
    assert [source(c) for c in notebook["cells"]] == [source(c) for c in original["cells"]]
    smoke = copy.deepcopy(notebook)
    smoke["cells"][16]["source"] = source(smoke["cells"][16]) + "\n\n" + (HERE / "smoke_overrides.py").read_text()
    run = source(smoke["cells"][20])
    anchor = "# Outside a real submission, stop ~10 min before the wall-clock budget for a graceful exit."
    assert run.count(anchor) == 1
    run = run.replace(anchor, (
        "# Smoke only: cold mounted-input reads may exceed the release's startup wait.\n"
        "ready_deadline = time.monotonic() + 15 * 60\n"
        "while time.monotonic() < ready_deadline:\n"
        "    if proc.poll() is not None:\n"
        "        raise RuntimeError('Released SGLang server exited during startup')\n"
        "    try:\n"
        "        with urlopen('http://127.0.0.1:8001/health', timeout=5) as response:\n"
        "            if response.status == 200:\n"
        "                break\n"
        "    except Exception:\n"
        "        pass\n"
        "    time.sleep(5)\n"
        "else:\n"
        "    raise RuntimeError('Cold smoke startup exceeded its additional 15-minute allowance')\n\n"
        "# Smoke scope only: same solver, one ls20 episode, at most four actions.\n"
        "assert not TRUE_SUBMISSION, 'Smoke notebook cannot be submitted'\n"
        "bm.games = [g for g in bm.games if g.env_name.startswith('ls20')]\n"
        "assert len(bm.games) == 1, 'Expected one ls20 game'\n\n" + anchor
    ))
    run = run.replace("soft_end = None", "soft_end = datetime.now() + timedelta(minutes=8)")
    run = run.replace("if not TRUE_SUBMISSION:\n    budget =", "if False:  # preserve smoke deadline\n    budget =")
    smoke["cells"][20]["source"] = run
    smoke["cells"].insert(2, {
        "cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
        "source": (HERE / "preflight.py").read_text(),
    })
    for index in (16, 20):
        validate_python({"source": source(smoke["cells"][index + 1])}, index)
    output_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, value in (("full", notebook), ("smoke", smoke)):
        path = output_dir / f"franzen_m2_v3_{name}.ipynb"
        data = (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode()
        path.write_bytes(data)
        hashes[path.name] = sha(data)
    manifest = {
        "reference": "dfranzen/arc-agi-3-milestone-2-solution",
        "script_version_id": 354920985, "notebook_version": 3,
        "source_sha256": SOURCE_SHA256,
        "reference_repository_commit": "10882e332d883af3e61616df8c8a17d03a328a75",
        "duck_base_commit": "7652836056c59e044f093e3c13ed7438c814169e",
        "runtime_base_commit": "d00d88efc8d6281b12be4f4073126aec95038c55",
        "inputs": original["metadata"]["kaggle"]["dataSources"],
        "cell_source_sha256": [sha(source(c).encode()) for c in original["cells"]],
        "generated_sha256": hashes, "full_source_cells_unchanged": True,
        "smoke_changes": "preflight plus scope/deadline/action caps; not a score comparison",
    }
    (output_dir / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"output_dir": str(output_dir), **hashes}, indent=2))
    return notebook, smoke, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "arc-agi-3-milestone-2-solution.ipynb")
    parser.add_argument("--output", type=Path, default=HERE / "generated")
    args = parser.parse_args()
    build(args.source, args.output)
