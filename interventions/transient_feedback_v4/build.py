"""Build V4 A+B and its exact source diff; never execute the notebook."""
import argparse
import copy
import difflib
import hashlib
import json
from pathlib import Path

from baselines.franzen_m2_v3.prepare import ROOT, SOURCE_SHA256, source, validate_python
from interventions.transient_feedback_v4.patch import BASE_HASHES, patched_sources

HERE = Path(__file__).resolve().parent
CACHE = ROOT / "local_output/research_refs/franzen/ARC3-Inference/inference"
OUTPUT = ROOT / "local_output/transient_feedback_v4"


def release_sources():
    raw = (ROOT / "arc-agi-3-milestone-2-solution.ipynb").read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Reference differs from released V3")
    sources = {name: (CACHE / name).read_bytes() for name in BASE_HASHES}
    # patched_sources checks every full-file pin before generating anything.
    patched_sources(sources)
    return sources


def source_diff(original, replacements):
    return "".join("".join(difflib.unified_diff(
        original.get(name, b"").decode().splitlines(keepends=True),
        raw.decode().splitlines(keepends=True),
        fromfile=f"a/ARC3-Inference/inference/{name}" if name in original else "/dev/null",
        tofile=f"b/ARC3-Inference/inference/{name}",
    )) for name, raw in replacements.items())


def build(output_path=OUTPUT / "candidate.ipynb", *, feedback=True, history=True):
    output_path = Path(output_path).resolve()
    if not output_path.is_relative_to(OUTPUT.resolve()) or output_path.suffix != ".ipynb":
        raise ValueError(f"Output must be a new .ipynb under {OUTPUT}")
    # Exclusive artifact paths protect existing baseline and candidate outputs.
    paths = [output_path, output_path.with_suffix(".manifest.json"), output_path.with_suffix(".patch")]
    if any(path.exists() for path in paths):
        raise FileExistsError("Candidate or companion artifact already exists")
    sources = release_sources()
    replacements = patched_sources(sources)
    original = json.loads((ROOT / "arc-agi-3-milestone-2-solution.ipynb").read_bytes())
    notebook = copy.deepcopy(original)
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            validate_python(cell, index)
            cell.update(outputs=[], execution_count=None)
        cell["metadata"] = {k: v for k, v in cell.get("metadata", {}).items()
                            if k not in {"execution", "papermill"}}
    notebook["metadata"] = {k: notebook["metadata"][k]
                            for k in ("kaggle", "kernelspec", "language_info")}
    notebook["metadata"]["kaggle"].update(
        accelerator="nvidiaRtxPro6000", isGpuEnabled=True, isInternetEnabled=False)
    overlay = (
        "# Isolated V4: after V3 patch/setup, before bundle imports.\n"
        + (HERE / "patch.py").read_text()
        + f"\napply(BUNDLE_DIR / 'src', history_source={(HERE / 'history.py').read_text()!r})\n"
        + "import os\n"
        + f"os.environ['ARC3_V4_TRANSIENT_FEEDBACK'] = {str(int(feedback))!r}\n"
        + f"os.environ['ARC3_V4_ANIMATION_HISTORY'] = {str(int(history))!r}\n"
        + "os.environ['ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT'] = '0'\n"
    )
    compile(overlay, "v4_overlay", "exec")
    notebook["cells"].insert(5, {"cell_type": "code", "source": overlay,
                               "metadata": {}, "outputs": [], "execution_count": None})
    assert [source(c) for i, c in enumerate(notebook["cells"]) if i != 5] == [source(c) for c in original["cells"]]
    raw = (json.dumps(notebook, indent=1, ensure_ascii=False) + "\n").encode()
    diff = source_diff(sources, replacements)
    manifest = {
        "candidate": "Franzen V4 transient feedback A+B", "v3_sha256": SOURCE_SHA256,
        "v3_cell_sources_unchanged": True, "overlay_cell_index": 5,
        "flags": {"ARC3_V4_TRANSIENT_FEEDBACK": bool(feedback),
                  "ARC3_V4_ANIMATION_HISTORY": bool(history),
                  "ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT": False},
        "baseline_sha256": BASE_HASHES,
        "candidate_source_sha256": {name: hashlib.sha256(value).hexdigest() for name, value in replacements.items()},
        "notebook_sha256": hashlib.sha256(raw).hexdigest(),
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
        "scope": "Built only; no GPU, model, or Kaggle execution",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for path, content in zip(paths, [raw, (json.dumps(manifest, indent=2) + "\n").encode(), diff.encode()]):
        with path.open("xb") as handle:
            handle.write(content)
    return notebook, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT / "candidate.ipynb")
    parser.add_argument("--feedback", type=int, choices=(0, 1), default=1)
    parser.add_argument("--history", type=int, choices=(0, 1), default=1)
    args = parser.parse_args()
    _, manifest = build(args.output, feedback=bool(args.feedback), history=bool(args.history))
    print(json.dumps({"output": str(args.output), **manifest}, indent=2))
