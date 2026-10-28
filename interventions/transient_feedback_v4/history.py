"""Bounded V4 observations; no game actions, model calls, or execution guards."""
import json
import os
import uuid

FEEDBACK_FLAG = "ARC3_V4_TRANSIENT_FEEDBACK"
HISTORY_FLAG = "ARC3_V4_ANIMATION_HISTORY"
MAX_RECORDS = 4
MAX_FRAMES = 16  # post-action frames; one additional pre-action board
MAX_RECORD_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 1024 * 1024
MAX_SIDE = 64


def enabled(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def transient_verdict(item):
    animation = item.get("animation") or {}
    if (enabled(FEEDBACK_FLAG) and item.get("executed")
            and item.get("gameplay_changed") is False
            and animation.get("transient_pixels", 0) > 0):
        return (
            "ENDPOINT UNCHANGED (executed; intermediate animation: "
            f"{animation.get('frames', '?')} frames, "
            f"{animation['transient_pixels']} transient pixels)"
        )
    return None


GUIDANCE = (
    " Historical transient animations: animation_history()['records'] lists up to "
    "4 retained records with animation_id, action_num, level and truncation metadata. "
    "animation_frames(animation_id) returns a dict with FrameView objects in ['frames']; "
    "animation_timeline(animation_id) returns ['timeline']. Check ['truncated'] and "
    "['frame_indices'] (original animation indices). Old IDs expire on eviction, RESET, "
    "death or level change. Missing IDs return an explicit error, never another action. "
    "last_animation_frames and last_animation_timeline still mean only the last action."
)


class AnimationHistory:
    """At most four JSON byte strings, each <=256 KiB and total <=1 MiB.

    Serialized storage avoids retaining references to the unbounded raw chain.
    Fixed dimensions/frame counts bound encoding, decoding and response size.
    """
    def __init__(self):
        self.scope = uuid.uuid4().hex
        self.serial = 0
        self.records = {}
        self.bytes = 0
        self.evicted = 0
        self.level = None

    def clear(self, level):
        self.records.clear()
        self.bytes = 0
        self.level = level

    def observe(self, payload, record, previous_level):
        level = payload.get("level")
        boundary = (payload.get("action_name") == "RESET"
                    or level != previous_level
                    or any(payload.get(k) for k in
                           ("level_completed", "game_over", "run_complete", "done")))
        if boundary or (self.level is not None and self.level != level):
            self.clear(level)
        self.level = level
        if boundary or not record or not (record.get("summary") or {}).get("transient_pixels"):
            return None
        chain = record.get("chain") or ()
        total = max(0, len(chain) - 1)
        if total < 2:
            return None
        # Uniform deterministic sampling includes both endpoints and marks gaps.
        indices = (list(range(total + 1)) if total <= MAX_FRAMES else
                   sorted({i * total // MAX_FRAMES for i in range(MAX_FRAMES + 1)}))
        grids = []
        reason = "frame_limit" if total > MAX_FRAMES else None
        for index in indices:
            grid = chain[index]
            if (not grid or len(grid) > MAX_SIDE
                    or any(not row or len(row) > MAX_SIDE for row in grid)
                    or any(type(c) is not int or not 0 <= c <= 15 for row in grid for c in row)):
                grids = []
                indices = []
                reason = "unsupported_grid (requires <=64x64 ARC palette)"
                break
            grids.append([list(row) for row in grid])
        self.serial += 1
        animation_id = f"{self.scope}:{self.serial}:{payload['action_num']}"
        data = {
            "animation_id": animation_id, "action_num": payload["action_num"],
            "level": level, "action": str(payload.get("action_display") or "")[:128],
            "original_frames": total, "retained_frames": max(0, len(grids) - 1),
            "frame_indices": indices[1:], "truncated": bool(reason),
            "truncation_reason": reason, "chain": grids,
        }
        encoded = json.dumps(data, separators=(",", ":")).encode()
        if len(encoded) > MAX_RECORD_BYTES:
            # Fail visibly, retaining only metadata rather than exceeding a cap.
            data.update(chain=[], frame_indices=[], retained_frames=0,
                        truncated=True, truncation_reason="byte_limit")
            encoded = json.dumps(data, separators=(",", ":")).encode()
        while self.records and (len(self.records) >= MAX_RECORDS
                                or self.bytes + len(encoded) > MAX_TOTAL_BYTES):
            oldest = next(iter(self.records))
            self.bytes -= len(self.records.pop(oldest))
            self.evicted += 1
        self.records[animation_id] = encoded
        self.bytes += len(encoded)
        return animation_id

    def query(self, kind, animation_id, build_frames, build_timeline):
        if kind == "history":
            return {
                "records": [self._metadata(json.loads(raw)) for raw in self.records.values()],
                "max_records": MAX_RECORDS, "max_frames": MAX_FRAMES,
                "stored_bytes": self.bytes, "max_bytes": MAX_TOTAL_BYTES,
                "evicted_records": self.evicted, "level": self.level,
            }
        if not isinstance(animation_id, str) or animation_id not in self.records:
            return {"error": "Animation ID unavailable (evicted, cleared, or another game).",
                    "animation_id": animation_id}
        data = json.loads(self.records[animation_id])
        metadata = self._metadata(data)
        record = {"chain": data["chain"], "step": data["action_num"],
                  "level": data["level"], "action_display": data["action"]}
        if kind == "history_frames":
            return {**metadata, "frames": build_frames(record)}
        if kind == "history_timeline":
            timeline = build_timeline(record)
            original = [0] + data["frame_indices"]
            for step in timeline.get("steps", []):
                position = step["step"]
                step["from_frame_index"] = original[position - 1]
                step["step"] = original[position]
            return {**metadata, "timeline": timeline}
        return {"error": "Unknown historical animation query.", "animation_id": animation_id}

    @staticmethod
    def _metadata(data):
        return {key: value for key, value in data.items() if key != "chain"}


def history_for(session):
    history = getattr(session, "_animation_history_v4", None)
    if history is None:
        history = AnimationHistory()
        session._animation_history_v4 = history
    return history
