"""What the install is holding, and whether there is room for the next render.

A cloud studio is one Railway service with one volume mounted at
SCREENBOARD_HOME. Takes are never upscaled, so a 4K PNG is 20–40 MB and a
production accumulates them until each is rejected AND deleted. Nothing
measured the volume, so the first sign of a full one was a 502 from the
middle of a paid render (user 2026-08-07: region repair on
HIDDEN_REPAIR_SHOP_V001 returned "[Errno 28] No space left on device").

Two jobs here: report what is used, and refuse a write that will not fit —
before the spend, not after it. The product rule is that a gate is
readable as state before it is hit.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import paths

# A native 4K PNG runs 20–40 MB; a render also writes a thumbnail and a
# JSON record, and the encoder needs room to work. This is the floor a
# write is allowed to start from — deliberately generous, because the
# failure it prevents costs a paid generation.
RENDER_HEADROOM = 350 * 1024 * 1024

# Below this the studio says so everywhere, not only when a render is
# attempted.
LOW_WATER = 1024 * 1024 * 1024


def usage() -> dict:
    """Volume totals plus what the install's own directories hold."""
    total = used = free = 0
    try:
        du = shutil.disk_usage(paths.HOME)
        total, used, free = du.total, du.used, du.free
    except OSError:
        pass
    return {"total": total, "used": used, "free": free,
            "low": bool(total) and free < LOW_WATER,
            "breakdown": breakdown()}


def _tree_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    n = 0
    for p in root.rglob("*"):
        try:
            if p.is_file():
                n += p.stat().st_size
        except OSError:
            continue
    return n


def breakdown() -> list[dict]:
    """Per-kind totals across every production, largest first.

    Reported by KIND rather than by folder: "takes" is the answer to "what
    is filling this", and takes live under each production's boards dir.
    """
    kinds = {"Takes and boards": 0, "References": 0, "Screenplays": 0,
             "Safety copies": 0, "Everything else": 0}
    for base in _project_bases():
        data = base / "data"
        kinds["Takes and boards"] += _tree_bytes(data / "boards")
        kinds["References"] += _tree_bytes(data / "references")
        kinds["Screenplays"] += _tree_bytes(data / "screenplay")
        for z in base.glob("pre-import-*.zip"):
            try:
                kinds["Safety copies"] += z.stat().st_size
            except OSError:
                continue
        counted = (_tree_bytes(data / "boards") + _tree_bytes(data / "references")
                   + _tree_bytes(data / "screenplay"))
        kinds["Everything else"] += max(0, _tree_bytes(base) - counted)
    rows = [{"kind": k, "bytes": v} for k, v in kinds.items() if v]
    rows.sort(key=lambda r: -r["bytes"])
    return rows


def _project_bases() -> list[Path]:
    bases = []
    if (paths.HOME / "data").exists():
        bases.append(paths.HOME)          # the legacy root production
    if paths.PROJECTS_DIR.exists():
        bases += [p for p in paths.PROJECTS_DIR.iterdir()
                  if p.is_dir() and not p.name.startswith(".")]
    return bases


def free_bytes() -> int:
    try:
        return shutil.disk_usage(paths.HOME).free
    except OSError:
        return 0            # unmeasurable: never block on a guess


def human(n: int) -> str:
    for unit, size in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{n} B"


class OutOfSpace(Exception):
    """Raised BEFORE a write that cannot fit, so the caller can state the
    condition instead of failing mid-render."""


def require_room(need: int = RENDER_HEADROOM, what: str = "this render") -> None:
    """Refuse a write that will not fit. Silent when the volume cannot be
    measured — an unmeasurable disk must not block the app."""
    free = free_bytes()
    if not free:
        return
    if free < need:
        raise OutOfSpace(
            f"Not enough disk space for {what}: {human(free)} free, and a "
            f"take needs room for about {human(need)}. Nothing was "
            "generated and nothing was charged. Free space by deleting "
            "rejected takes (reject a take, then Delete), or raise this "
            "studio's volume size.")
