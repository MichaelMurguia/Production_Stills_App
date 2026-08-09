#!/usr/bin/env python
"""Build responsive WebP derivatives for the storefront's marketing stills.

The landing page shows ~88 MB of source PNGs (p01–p15, board-0001) at 150–380px
with no responsive set — every visitor pulls the full multi-megapixel files.
This generalizes the hand-built `web/-t320`/`-w1400` convention into a real
responsive set: for each source, a WebP at several widths (the browser picks by
viewport/DPR via `srcset`), plus one JPEG social card for `og:image` (crawlers
support JPEG universally, WebP unevenly). Idempotent, never upscales.

Run from the storefront dir:  python scripts/build_images.py
Commit the resulting static/img/web/*.webp and board-0001-og.jpg.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "app" / "static" / "img"
WEB = IMG / "web"

# The marketing stills the pages display. ref-*.jpg are already ~26 KB at their
# display size and need no derivatives.
SOURCES = [f"p{n:02d}" for n in range(1, 16)] + ["board-0001"]
WIDTHS = [400, 800, 1200, 1600]
WEBP_Q = 82
OG = ("board-0001", 1200, 630)  # social card: cover-cropped JPEG


def _webp(src: Image.Image, name: str, width: int) -> None:
    if width >= src.width:  # never upscale
        return
    h = round(src.height * width / src.width)
    out = WEB / f"{name}-w{width}.webp"
    src.resize((width, h), Image.LANCZOS).save(out, "WEBP", quality=WEBP_Q)


def _og_card(name: str, w: int, h: int) -> None:
    src = Image.open(IMG / f"{name}.png").convert("RGB")
    scale = max(w / src.width, h / src.height)
    resized = src.resize((round(src.width * scale), round(src.height * scale)), Image.LANCZOS)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    resized.crop((left, top, left + w, top + h)).save(WEB / f"{name}-og.jpg", "JPEG", quality=85)


def main() -> int:
    WEB.mkdir(parents=True, exist_ok=True)
    made = 0
    for name in SOURCES:
        p = IMG / f"{name}.png"
        if not p.exists():
            print(f"skip {name}: no source")
            continue
        with Image.open(p) as im:
            im = im.convert("RGB")
            for w in WIDTHS:
                _webp(im, name, w)
                made += 1
    _og_card(*OG)
    print(f"built {made} webp derivatives + {OG[0]}-og.jpg in {WEB.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
