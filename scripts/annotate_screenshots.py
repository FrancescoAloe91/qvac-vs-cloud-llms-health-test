#!/usr/bin/env python3
"""Add a header bar to existing benchmark screenshots (cases 1–5).

Does not crop the original image — prepends a dark banner with case title and
cloud model versions used for the comparison.

Usage:
  pip install pillow   # once, inside .venv
  python scripts/annotate_screenshots.py
  python scripts/annotate_screenshots.py --manifest assets/screenshots/manifest.json

Edit tier labels in data/cloud_tiers.json or in the manifest before running.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "assets" / "screenshots" / "manifest.json"
DEFAULT_TIERS = PROJECT_ROOT / "data" / "cloud_tiers.json"
OUT_DIR = PROJECT_ROOT / "assets" / "screenshots" / "annotated"

BG = (14, 17, 23)
TEXT = (226, 232, 240)
ACCENT = (0, 208, 156)
MUTED = (148, 163, 184)


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(path_str: str) -> Path:
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return p


def _header_lines(case_title: str, tiers: dict) -> list[str]:
    return [
        case_title,
        f"ChatGPT: {tiers.get('chatgpt', '—')}",
        f"Claude: {tiers.get('claude', '—')}",
        f"Gemini: {tiers.get('gemini', '—')}",
        f"QVAC: {tiers.get('qvac', '—')}",
    ]


def annotate_image(src: Path, dst: Path, lines: list[str], header_h: int = 118) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Install Pillow first: pip install pillow", file=sys.stderr)
        sys.exit(1)

    img = Image.open(src).convert("RGB")
    w, h = img.size
    canvas = Image.new("RGB", (w, h + header_h), BG)
    canvas.paste(img, (0, header_h))

    draw = ImageDraw.Draw(canvas)
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
        font_body = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    except OSError:
        font_title = ImageFont.load_default()
        font_body = font_title

    y = 14
    draw.text((18, y), lines[0], fill=ACCENT, font=font_title)
    y += 30
    for line in lines[1:]:
        draw.text((18, y), line, fill=TEXT, font=font_body)
        y += 18
    draw.line([(12, header_h - 6), (w - 12, header_h - 6)], fill=MUTED, width=1)

    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, quality=95)
    print(f"Wrote {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add tier header bars to benchmark screenshots")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    sys.path.insert(0, str(PROJECT_ROOT))
    from lib.cloud_tiers import effective_tier_labels, load_tier_labels

    manifest = _load_json(args.manifest)
    base = manifest.get("tier_labels") or load_tier_labels()
    tiers = effective_tier_labels(base)
    images = manifest.get("images") or []
    if not images:
        print(f"No images in {args.manifest}", file=sys.stderr)
        sys.exit(1)

    for entry in images:
        src = _resolve(entry["file"])
        if not src.is_file():
            print(f"Skip missing: {src}", file=sys.stderr)
            continue
        case_title = entry.get("case") or entry.get("title") or src.stem
        out_name = entry.get("out") or f"{src.stem}_header.png"
        dst = args.out / out_name
        annotate_image(src, dst, _header_lines(case_title, tiers))


if __name__ == "__main__":
    main()
