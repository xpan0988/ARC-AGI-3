"""Render a JSONL trace as before/after PNG pairs (including every subframe)."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.observation_trace import grid_diff, last_grid

# Fixed categorical palette, not a claim about the engine's display colors.
PALETTE = (
    "#000000", "#0074D9", "#FF4136", "#2ECC40",
    "#FFDC00", "#AAAAAA", "#F012BE", "#FF851B",
    "#7FDBFF", "#870C25", "#FFFFFF", "#6B4C9A",
    "#8B5A2B", "#008080", "#B8D346", "#E6B8D7",
)


def cell_color(value):
    if 0 <= value < len(PALETTE):
        return PALETTE[value]
    return "#" + hashlib.sha256(str(value).encode("ascii")).hexdigest()[:6]


def render_pair(record, before, after, subframe, output, scale=6):
    """Nearest-neighbor cells; cyan/black inset borders preserve cell interiors."""
    values = sorted({v for grid in (before, after) if grid for row in grid for v in row})
    colors = [cell_color(v).lower() for v in values]
    if len(set(colors)) != len(colors):
        raise ValueError("Palette collision: cannot display distinct values faithfully")
    grids = (before, after)
    width = max([64, *(len(row) for grid in grids if grid for row in grid)]) * scale
    height = max([64, *(len(grid) for grid in grids if grid)]) * scale
    diff = grid_diff(before, after)
    legend_rows = (len(values) + 7) // 8
    canvas = Image.new("RGB", (max(820, width * 2 + 36), height + 126 + 22 * legend_rows), "#eeeeee")
    draw = ImageDraw.Draw(canvas)
    action = record["action"]
    draw.text((12, 8), f'{record["game_id"]} | step {record["step"]} | {action["name"]} {json.dumps(action["data"])}', fill="black")
    after_obs = record["after"]
    state = after_obs["state"] if after_obs else record["status"]
    levels = after_obs["levels_completed"] if after_obs else "?"
    draw.text((12, 26), f'{record["before"]["state"]} -> {state} | levels completed: {record["before"]["levels_completed"]} -> {levels}', fill="black")
    draw.text((12, 44), f'after subframe {subframe} | changed cells: {diff["changed_cells"]} | bbox: {diff["bbox"]}', fill="black")
    draw.text((12, 62), "Cyan/black outlines = changed cells; null count = empty or unequal grid shapes", fill="black")
    for panel, grid in enumerate(grids):
        ox, oy = 12 + panel * (width + 12), 106
        label = "before (last prior frame)" if subframe <= 1 else "previous subframe"
        draw.text((ox, 86), label if panel == 0 else "after", fill="black")
        if not grid:
            draw.text((ox, oy), "No frame returned", fill="black")
            continue
        for y, row in enumerate(grid):
            for x, value in enumerate(row):
                left, top = ox + x * scale, oy + y * scale
                box = (left, top, left + scale - 1, top + scale - 1)
                draw.rectangle(box, fill=cell_color(value))
                if diff["comparable"] and before[y][x] != after[y][x]:
                    draw.rectangle(box, outline="black")
                    draw.rectangle((left + 1, top + 1, left + scale - 2, top + scale - 2), outline="#00ffff")
    for index, value in enumerate(values):
        x, y = 12 + (index % 8) * 100, height + 116 + (index // 8) * 22
        draw.rectangle((x, y, x + 14, y + 14), fill=cell_color(value), outline="black")
        draw.text((x + 20, y + 1), str(value), fill="black")
    canvas.save(output)


def render_trace(path, *, scale=6, limit=None):
    output = path.parent / f"{path.stem}-images"
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    with (gzip.open(path, "rt") if path.suffix == ".gz" else path.open()) as stream:
        for index, line in enumerate(stream):
            if limit is not None and index >= limit:
                break
            record = json.loads(line)
            previous = last_grid(record["before"])
            frames = record["after"]["frame"] if record["after"] else []
            for subframe, grid in enumerate(frames or [None], 1):
                target = output / f'{record["step"]:05d}-{subframe:03d}.png'
                render_pair(record, previous, grid, subframe, target, scale)
                previous = grid
                count += 1
    return output, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--scale", type=int, default=6, help="Pixels per cell, at least 5")
    parser.add_argument("--limit", type=int, help="Render only the first N transitions")
    args = parser.parse_args()
    if args.scale < 5 or (args.limit is not None and args.limit < 1):
        parser.error("--scale must be >= 5 and --limit must be >= 1")
    path = args.trace.resolve()
    if not path.is_relative_to((ROOT / "local_output").resolve()):
        parser.error("Keep traces and generated images under gitignored local_output/")
    output, count = render_trace(path, scale=args.scale, limit=args.limit)
    print(f"Wrote {count} PNGs to {output}")


if __name__ == "__main__":
    main()
