"""Display-tier image derivatives — the smallest image that still looks crisp.

Renders are native 4K PNGs (20–40 MB) kept as the archival truth, but the app
shows them almost everywhere at a fraction of that size. This module builds
small, cached WebP derivatives so the raw file is served only where full
resolution is actually consumed (the lightbox at 100%, the crop/repair pixel
tools). Everything is DISPLAY-ONLY: a derivative never feeds a render engine
(so `store.RENDER_SAFE_FORMATS` does not apply) and never feeds a size gate
(that reads the record's real width/height, never a served file).

Two tiers plus the untouched source:
  thumb — grid cards, filmstrips, rails, chips (any site shown <=~256px CSS)
  md    — the staged hero, board drill-ins, board-frame slots (mid displays)
  full  — the source PNG, served as-is
Edges are chosen to stay crisp at 2x DPR (thumb covers 2x256, md covers 2x800).
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

# (max_edge_px, webp_quality). "full" is intentionally absent — it is the
# source file, returned untouched by the callers.
VARIANTS: dict[str, tuple[int, int]] = {"thumb": (512, 80), "md": (1600, 82)}

# Building a variant decodes a 20–40 MB 4K PNG, resizes and re-encodes it — ~0.3s
# for a thumb, ~0.8s for md, and a transient ~50–100 MB of RAM. A cold board
# fires dozens at once; unbounded that saturated a tenant's CPU and could OOM it
# (user 2026-08-09). This caps how many run concurrently across every request
# thread and the boot warmer, so a burst queues instead of storming. The cached
# fast path never touches it.
_BUILD_SEMAPHORE = threading.Semaphore(
    max(1, int(os.environ.get("SCREENBOARD_VARIANT_CONCURRENCY", "2"))))


def _fresh(cache: Path, src: Path) -> bool:
    return cache.exists() and cache.stat().st_mtime >= src.stat().st_mtime


def variant_path(src: Path, cache: Path, max_edge: int, quality: int) -> Path:
    """A cached WebP derivative of `src` at `cache`, built on demand.

    Rebuilds when the source is newer than the cache (mtime guard); never
    upscales; caps concurrent builds; and on ANY failure returns `src` rather
    than raising, so a display request degrades to the full image instead of a
    404. Safe to call eagerly (warm the cache at write time) or lazily (first
    request)."""
    try:
        if _fresh(cache, src):
            return cache
        with _BUILD_SEMAPHORE:
            # Another thread may have built it while we waited for the permit —
            # dozens of tiles can ask for the same file at once on a cold board.
            if _fresh(cache, src):
                return cache
            from PIL import Image
            cache.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                im = im.convert("RGB")
                if max(im.size) > max_edge:               # thumbnail never upscales,
                    im.thumbnail((max_edge, max_edge), Image.LANCZOS)  # but be explicit
                im.save(cache, "WEBP", quality=quality)
        return cache
    except Exception:
        return src


def warm(src: Path, cache_for) -> None:
    """Best-effort pre-build of every tier for `src`. `cache_for(size)` maps a
    tier name to its cache Path. Never raises — warming is an optimization, and
    the lazy path in `variant_path` is the backstop."""
    for size, (edge, quality) in VARIANTS.items():
        variant_path(src, cache_for(size), edge, quality)
