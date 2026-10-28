"""Build a separate default-off candidate; never execute a notebook or server."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from baselines.franzen_m2_v3.prepare import ROOT, SOURCE_SHA256, source, validate_python


HERE = Path(__file__).resolve().parent


def build(source_path, output_path):
    raw = Path(source_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Reference differs from released V3; refusing to build")
    output_path = Path(output_path).resolve()
    # Candidate output must never overwrite a baseline, release or user file.
    allowed_root = (ROOT / "local_output/helper_timeout").resolve()
    if not output_path.is_relative_to(allowed_root) or output_path.suffix != ".ipynb":
        raise ValueError(f"Candidate output must be a new .ipynb under {allowed_root}")
    notebook = copy.deepcopy(json.loads(raw))
    assert len(notebook["cells"]) == 23
    original_sources = [source(c) for c in notebook["cells"]]
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            validate_python(cell, index)
            cell["outputs"] = []
            cell["execution_count"] = None
        cell["metadata"] = {
            k: v for k, v in cell.get("metadata", {}).items()
            if k not in {"execution", "papermill"}
        }
    notebook["metadata"] = {
        k: notebook["metadata"][k] for k in ("kaggle", "kernelspec", "language_info")
    }
    notebook["metadata"]["kaggle"].update(
        accelerator="nvidiaRtxPro6000", isGpuEnabled=True, isInternetEnabled=False
    )
    overlay = (
        "# Helper-timeout candidate, default OFF. No change to V3 cell sources.\n"
        "# Install after the released git patch, before importing the bundle.\n"
        + (HERE / "patch.py").read_text()
        + "\napply(BUNDLE_DIR / 'src')\n"
    )
    compile(overlay, "helper_timeout_overlay", "exec")
    notebook["cells"].insert(5, {
        "cell_type": "code", "source": overlay, "metadata": {},
        "outputs": [], "execution_count": None,
    })
    assert [source(c) for i, c in enumerate(notebook["cells"]) if i != 5] == original_sources
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x") as handle:
        handle.write(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
    return notebook


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "arc-agi-3-milestone-2-solution.ipynb")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "local_output/helper_timeout/candidate.ipynb")
    args = parser.parse_args()
    build(args.source, args.output)
    print(f"Built default-off candidate: {args.output}")
