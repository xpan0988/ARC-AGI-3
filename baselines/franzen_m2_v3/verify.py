"""Verify a full notebook and the archived, actual Kaggle smoke; CPU/stdlib only."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from prepare import HERE, ROOT, SOURCE_SHA256, source


def verify(full_path, evidence_path):
    original_path = ROOT / "arc-agi-3-milestone-2-solution.ipynb"
    assert hashlib.sha256(original_path.read_bytes()).hexdigest() == SOURCE_SHA256
    original = json.loads(original_path.read_text())
    full = json.loads(full_path.read_text())
    assert [source(c) for c in full["cells"]] == [source(c) for c in original["cells"]]
    assert full["metadata"]["kaggle"]["dataSources"] == original["metadata"]["kaggle"]["dataSources"]
    assert full["metadata"]["kaggle"]["isInternetEnabled"] is False
    assert full["metadata"]["kaggle"]["accelerator"] == "nvidiaRtxPro6000"
    assert all(not c.get("outputs") and c.get("execution_count") is None
               for c in full["cells"] if c["cell_type"] == "code")
    with zipfile.ZipFile(evidence_path) as archive:
        post = json.loads(archive.read("franzen-postflight.json"))
        for name, meta in post["artifacts"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == meta["sha256"], name
        events = [json.loads(line) for line in archive.read(
            "ready_smoke/artifacts/ls20-9607627b_p0_events.jsonl"
        ).decode().splitlines() if line.strip()]
        calls = [json.loads(line) for line in archive.read(
            "ready_smoke/requests.jsonl"
        ).decode().splitlines() if line.strip()]
    previous = None
    transitions = []
    for event in events:
        board = event.get("board")
        if event.get("type") == "action" and event.get("action_name") != "RESET":
            assert previous and board and event.get("analysis_step") is not None
            assert len(previous) == len(board) and all(len(a) == len(b) for a, b in zip(previous, board))
            transitions.append({
                "action_num": event["action_num"], "engine_action": event["action_name"],
                "display": event["action_display"], "analysis_step": event["analysis_step"],
                "rows": len(board), "columns": len(board[0]),
                "changed_cells": sum(a != b for ar, br in zip(previous, board) for a, b in zip(ar, br)),
                "after_sha256": hashlib.sha256(json.dumps(board, separators=(",", ":")).encode()).hexdigest(),
            })
        if board:
            previous = board
    responses = [call for call in calls if call.get("event") == "response"]
    assert transitions and responses and not any(call.get("error") for call in responses)
    completion_tokens = sum(call["usage"]["completion_tokens"] for call in responses)
    assert completion_tokens > 0
    return {
        "full_source_parity": True, "archive_hashes_valid": True,
        "model_calls": len(responses), "completion_tokens": completion_tokens,
        "transitions": transitions, "parquet": post["parquet"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", type=Path, default=HERE / "generated/franzen_m2_v3_full.ipynb")
    parser.add_argument("--evidence", type=Path, default=HERE / "generated/franzen-smoke-evidence.zip")
    args = parser.parse_args()
    print(json.dumps(verify(args.full, args.evidence), indent=2))
