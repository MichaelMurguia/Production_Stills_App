"""The sheet grammar — one mechanism for boards and lookbook pages.

SHEET_SYSTEM_PLAN.md (rulings R1–R8 embedded) + SHEET_SYSTEM_TECH_SPEC.md.
A sheet is the presentation artifact: masthead, blocks of slots and evidence,
canon footer, rendered by sheet_render.render_sheet. A board (stage 05) is a
sheet with the BOARD archetype — assemble.py imports this module's packing
functions so there is exactly one layout implementation.

Geometry is fractional at every level (that is what makes a size change free):
a block's `frac` is its rect within the sheet's content area, a slot's `frac`
is its rect within its block. Pixels are always derived, never stored.

R1 (type floor): fixed type (captions under images) is `frac × width` and
drives recommend(); elastic type (PALETTE / SPEC / PRINCIPLES — owns its
column, reflows) renders at `max(frac × width, floor)` and never drives it.
Floors are fixed per medium — never scaled by width.
"""
from __future__ import annotations

import hashlib
import json
from collections import namedtuple

from . import generate, paths, store

# Shared with the board renderer — the packers below were assemble.py's and
# keep its pixel grammar. assemble.py imports them from here (one library).
GUTTER = 36
LABEL_H = 46
MARGIN = 64

# Spine column share of the sheet width (lb-1b: title, thesis, elastic
# evidence live there on spined archetypes).
SPINE_W = 0.24


class SheetError(Exception):
    pass


# ------------------------------------------------------------- canon tables

BlockDef = namedtuple("BlockDef", "slots_min slots_max frac elastic")

# Closed set of twelve (plan §2). frac = authored px at the 1360-wide mocks
# ÷ 1360. Do not add a thirteenth without a designer ruling.
BLOCK_TYPES: dict[str, BlockDef] = {
    "HERO":       BlockDef(1, 1, 0.01471, False),
    "CLUSTER":    BlockDef(2, 5, 0.00882, False),
    "STRIP":      BlockDef(3, 8, 0.00625, False),
    "BEATS":      BlockDef(6, 15, 0.00662, False),
    "GRID":       BlockDef(4, 12, 0.00662, False),
    "ORTHO":      BlockDef(4, 4, 0.00588, False),
    "PALETTE":    BlockDef(0, 0, 0.00699, True),
    "MATERIAL":   BlockDef(3, 6, 0.00699, False),
    "SPEC":       BlockDef(0, 0, 0.00699, True),
    "PRINCIPLES": BlockDef(0, 0, 0.00809, True),
    "LINEUP":     BlockDef(4, 10, 0.00625, False),
    "VERSUS":     BlockDef(2, 2, 0.00772, False),
}

STYLES = ("GALLERY", "CONTACT", "NEWSPRINT", "BLUEPRINT", "PLATE", "INK")

# INK is the boards' style (R6): today's boards mat each panel on PANEL_BG
# with a label beneath, and INK is the matted dark style.
BOARD_STYLE = "INK"

# Archetype seeds (plan §3, BOARD amended per R3): a starting sequence, not a
# cage. Each entry is (type, frac rect within the content area). Elastic
# blocks on a SPINED sheet render in the spine column in block order — their
# frac is used only when the sheet has no spine.
ARCHETYPES: dict[str, dict] = {
    "BOARD": {"spine": False, "blocks": [
        ("GRID", {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0})]},
    "ART_DIRECTION": {"spine": True, "blocks": [
        ("CLUSTER", {"x": 0.0, "y": 0.0, "w": 0.32, "h": 0.42}),
        ("CLUSTER", {"x": 0.34, "y": 0.0, "w": 0.32, "h": 0.42}),
        ("CLUSTER", {"x": 0.68, "y": 0.0, "w": 0.32, "h": 0.42}),
        ("CLUSTER", {"x": 0.0, "y": 0.45, "w": 0.235, "h": 0.37}),
        ("CLUSTER", {"x": 0.255, "y": 0.45, "w": 0.235, "h": 0.37}),
        ("CLUSTER", {"x": 0.51, "y": 0.45, "w": 0.235, "h": 0.37}),
        ("CLUSTER", {"x": 0.765, "y": 0.45, "w": 0.235, "h": 0.37}),
        ("STRIP", {"x": 0.0, "y": 0.85, "w": 1.0, "h": 0.15})]},
    "SUBJECT_STUDY": {"spine": True, "blocks": [
        ("HERO", {"x": 0.0, "y": 0.0, "w": 0.55, "h": 0.52}),
        ("ORTHO", {"x": 0.58, "y": 0.0, "w": 0.42, "h": 0.52}),
        ("STRIP", {"x": 0.0, "y": 0.55, "w": 1.0, "h": 0.18}),
        ("SPEC", {"x": 0.0, "y": 0.76, "w": 0.3, "h": 0.24}),
        ("MATERIAL", {"x": 0.33, "y": 0.76, "w": 0.37, "h": 0.24}),
        ("VERSUS", {"x": 0.72, "y": 0.76, "w": 0.28, "h": 0.24})]},
    "SCENE_BOARD": {"spine": True, "blocks": [
        ("BEATS", {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.55}),
        ("STRIP", {"x": 0.0, "y": 0.58, "w": 1.0, "h": 0.13}),
        ("STRIP", {"x": 0.0, "y": 0.725, "w": 1.0, "h": 0.13}),
        ("STRIP", {"x": 0.0, "y": 0.87, "w": 1.0, "h": 0.13})]},
    "LOOK_STYLES": {"spine": False, "blocks": [
        ("CLUSTER", {"x": 0.0, "y": 0.0, "w": 0.49, "h": 0.29}),
        ("CLUSTER", {"x": 0.51, "y": 0.0, "w": 0.49, "h": 0.29}),
        ("CLUSTER", {"x": 0.0, "y": 0.31, "w": 0.49, "h": 0.29}),
        ("CLUSTER", {"x": 0.51, "y": 0.31, "w": 0.49, "h": 0.29}),
        ("PRINCIPLES", {"x": 0.0, "y": 0.62, "w": 1.0, "h": 0.16}),
        ("LINEUP", {"x": 0.0, "y": 0.8, "w": 1.0, "h": 0.2})]},
    "FACTION": {"spine": False, "blocks": [
        ("HERO", {"x": 0.0, "y": 0.0, "w": 0.32, "h": 0.45}),
        ("HERO", {"x": 0.34, "y": 0.0, "w": 0.32, "h": 0.45}),
        ("HERO", {"x": 0.68, "y": 0.0, "w": 0.32, "h": 0.45}),
        ("PRINCIPLES", {"x": 0.0, "y": 0.47, "w": 1.0, "h": 0.14}),
        ("GRID", {"x": 0.0, "y": 0.63, "w": 1.0, "h": 0.24}),
        ("PALETTE", {"x": 0.0, "y": 0.89, "w": 1.0, "h": 0.11})]},
    "LOCATION": {"spine": False, "blocks": [
        ("GRID", {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.6}),
        ("PRINCIPLES", {"x": 0.0, "y": 0.62, "w": 1.0, "h": 0.18}),
        ("PALETTE", {"x": 0.0, "y": 0.82, "w": 1.0, "h": 0.18})]},
}

# One rule, two media (plan §6, R1). Floors are FIXED — scaling the screen
# floor with width cancels width out of the inequality and defeats the
# ladder (tech spec appendix A).
LADDERS = {
    "PRINT": {"ratio": (3, 2),
              "rungs": [(12, 8), (18, 12), (24, 16), (36, 24)],
              "unit": "in", "floor": 12.0},   # points, fixed
    "SCREEN": {"ratio": (16, 9),
               "rungs": [(1920, 1080), (2560, 1440),
                         (3840, 2160), (5120, 2880)],
               "unit": "px", "floor": 24.0},  # px, fixed
}

PRINT_DPI = 300

BINDING_KINDS = ("SUBJECT", "PANEL", "PALETTE_GROUP", "MATERIAL_ANCHOR",
                 "SCREENPLAY", "JUDGING_NOTE", "SPEC_FIELD")

# The R4 swap note carried by the STRIP that /arrange builds from a board's
# derived MATERIALS/PALETTE takes.
DERIVED_SWAP_NOTE = ("RENDERED AS PANELS · THE PALETTE BLOCK CAN DRAW THESE "
                     "FROM STAGE 02")


# ------------------------------------------------- packing (from assemble.py)
# Moved verbatim (behaviour gate: tests/test_assemble_layout.py passes
# unchanged with assemble.py aliasing these). Pixel-space; the composer's
# fractional grammar seeds fracs from simpler splitters below.

def grid_rects(panels: list[dict], x0: int, y0: int, w: int,
               h: int) -> dict[str, tuple[int, int, int, int]]:
    """Uniform grid — the right grammar for study series: every panel equal,
    comparison is the point."""
    n = len(panels)
    cols = min(4, max(1, n if n <= 4 else (3 if n <= 9 else 4)))
    rows = -(-n // cols)
    cw = (w - GUTTER * (cols - 1)) // cols
    ch = (h - GUTTER * (rows - 1)) // rows
    rects = {}
    for i, p in enumerate(panels):
        r, c = divmod(i, cols)
        rects[p["id"]] = (x0 + c * (cw + GUTTER), y0 + r * (ch + GUTTER), cw, ch)
    return rects


def layout_rects(panels: list[dict], alloc: dict[str, float],
                 x0: int, y0: int, w: int, h: int,
                 hero_id: str | None = None) -> dict[str, tuple[int, int, int, int]]:
    """Hero panel takes the left region, remaining panels stack on the right
    with heights proportional to their layout allocation. hero_id overrides
    which panel leads — layout is presentation grammar, not canon."""
    ordered = sorted(panels, key=lambda p: -(alloc.get(p["id"], 0) or 0))
    if hero_id:
        ordered = ([p for p in ordered if p["id"] == hero_id]
                   + [p for p in ordered if p["id"] != hero_id])
    rects: dict[str, tuple[int, int, int, int]] = {}
    if len(ordered) == 1:
        rects[ordered[0]["id"]] = (x0, y0, w, h)
        return rects

    hero = ordered[0]
    hero_share = (alloc.get(hero["id"], 50) or 50) / 100.0
    hero_w = int(w * min(max(hero_share, 0.45), 0.68))
    rects[hero["id"]] = (x0, y0, hero_w, h)

    rest = ordered[1:]
    rx = x0 + hero_w + GUTTER
    rw = w - hero_w - GUTTER
    total = sum(alloc.get(p["id"], 0) or 0 for p in rest) or len(rest)
    ry = y0
    remaining_h = h - GUTTER * (len(rest) - 1)
    for i, p in enumerate(rest):
        share = (alloc.get(p["id"], 0) or (total / len(rest))) / total
        ph = int(remaining_h * share) if i < len(rest) - 1 else (y0 + h - ry)
        rects[p["id"]] = (rx, ry, rw, ph)
        ry += ph + GUTTER
    return rects


def aspect_rects(panels: list[dict], aspects: dict[str, float],
                 x0: int, y0: int, w: int,
                 h: int) -> dict[str, tuple[int, int, int, int]]:
    """Aspect-first layout (director's ruling 2026-07-31): slot geometry
    derives from the takes' OWN aspect ratios — justified rows in panel
    order, like a photo wall. Priority order: aspect ratio first, scale
    second, crop last. Every contiguous partition of the panels into rows
    is scored; within a row, native aspects fix the widths, and the
    partition whose natural stacked height best fills the canvas wins.
    The residual mismatch (canvas height / natural height) is the ONLY
    aspect deviation, it is uniform across every panel, and the cover-crop
    step absorbs it — so the crop is as small as the canvas allows."""
    import math
    n = len(panels)
    if n == 0:
        return {}
    a = [max(0.1, min(10.0, aspects.get(p["id"]) or 16 / 9)) for p in panels]

    best = None  # (cost, rows, f)
    for bits in range(1 << (n - 1)):
        rows, start = [], 0
        for i in range(n - 1):
            if bits >> i & 1:
                rows.append(range(start, i + 1))
                start = i + 1
        rows.append(range(start, n))
        k = len(rows)
        avail = h - GUTTER * (k - 1) - LABEL_H * k
        if avail <= 0:
            continue
        natural = sum((w - GUTTER * (len(r) - 1)) / sum(a[i] for i in r)
                      for r in rows)
        f = avail / natural
        # |log f| is the uniform crop each panel pays; the tiny row-count
        # term only breaks ties toward calmer walls.
        cost = abs(math.log(f)) + 0.01 * k
        if best is None or cost < best[0]:
            best = (cost, rows, f)

    _, rows, f = best
    rects: dict[str, tuple[int, int, int, int]] = {}
    y = float(y0)
    for r in rows:
        wr = w - GUTTER * (len(r) - 1)
        sum_a = sum(a[i] for i in r)
        row_h = (wr / sum_a) * f
        x = float(x0)
        for j, i in enumerate(r):
            wi = wr * (a[i] / sum_a)
            if j == len(r) - 1:
                wi = x0 + w - x  # absorb rounding drift
            rects[panels[i]["id"]] = (round(x), round(y), round(wi),
                                      round(row_h) + LABEL_H)
            x += wi + GUTTER
        y += row_h + LABEL_H + GUTTER
    return rects


# ------------------------------------------------------------ type and size

def type_size(frac: float, medium: str, width: float) -> float:
    """PRINT -> points; SCREEN -> px. width is inches (print) or px (screen)."""
    return frac * width * 72 if medium == "PRINT" else frac * width


def rendered_size(block: dict, medium: str, width: float) -> float:
    """Elastic type grows to the floor and takes the vertical room; fixed
    type cannot grow without colliding, so it renders at its fraction."""
    bd = BLOCK_TYPES[block["type"]]
    s = type_size(bd.frac, medium, width)
    return max(s, LADDERS[medium]["floor"]) if bd.elastic else s


def slot_pixel_need(sheet: dict, block: dict, slot: dict) -> tuple[int, int]:
    """Source pixels this slot needs at the sheet's size. Print renders at
    300 dpi. A crop keeps a fraction of the source, so cropping divides the
    pixels a candidate has — the need scales by 1/crop."""
    w, h = sheet["size"]
    if sheet["medium"] == "PRINT":
        px_w, px_h = w * PRINT_DPI, h * PRINT_DPI
    else:
        px_w, px_h = w, h
    cw, ch, _, _ = _content_rect_fracs(sheet)
    need_w = px_w * cw * block["frac"]["w"] * slot["frac"]["w"]
    need_h = px_h * ch * block["frac"]["h"] * slot["frac"]["h"]
    crop = slot.get("crop") or {}
    need_w /= max(float(crop.get("w", 1.0)) or 1.0, 1e-6)
    need_h /= max(float(crop.get("h", 1.0)) or 1.0, 1e-6)
    return (int(round(need_w)), int(round(need_h)))


def _content_rect_fracs(sheet: dict) -> tuple[float, float, float, float]:
    """(w_frac, h_frac, x_frac, y_frac) of the content area within the full
    sheet: inside margins, right of the spine when one exists, below the
    masthead band on spineless sheets (spined sheets carry the masthead in
    the spine). Mirrored by sheet_render — keep the two in step."""
    w, h = sheet["size"]
    aspect = w / h if h else 1.0
    mx = 0.047  # margin as a fraction of width (64/1360 at the mock scale)
    my = mx * aspect / (16 / 9)
    if sheet.get("spine"):
        x0 = SPINE_W + mx
        y0 = my
    else:
        x0 = mx
        y0 = my + 0.11  # masthead band
    return (1.0 - x0 - mx, 1.0 - y0 - my, x0, y0)


def _candidate_dims(slot: dict) -> tuple[int, int]:
    sid, cid = slot.get("spec_id"), slot.get("candidate_id")
    if not sid or not cid:
        return (0, 0)
    rec = generate.get_candidate(sid, cid)
    if not rec:
        return (0, 0)
    return (int(rec.get("width") or 0), int(rec.get("height") or 0))


def _iter_slots(sheet: dict):
    for b in sheet.get("blocks", []):
        for s in b.get("slots", []):
            yield b, s


def _any_slot_short(sheet: dict, size: tuple[int, int]) -> bool:
    probe = dict(sheet, size=list(size))
    for b, s in _iter_slots(probe):
        if not s.get("candidate_id"):
            continue  # empty slots gate export, not the recommendation
        have = _candidate_dims(s)
        need = slot_pixel_need(probe, b, s)
        if have[0] < need[0] or have[1] < need[1]:
            return True
    return False


def recommend(sheet: dict) -> tuple[int, int]:
    """Smallest rung where every FIXED block's type clears the floor and
    every filled slot clears its pixels. Elastic blocks never drive this —
    they grow to the floor and reflow (R1). Falls back to the top rung."""
    L = LADDERS[sheet["medium"]]
    fixed = [b for b in sheet.get("blocks", [])
             if not BLOCK_TYPES[b["type"]].elastic]
    worst = min((BLOCK_TYPES[b["type"]].frac for b in fixed), default=None)
    for w, h in L["rungs"]:
        if worst is not None and type_size(worst, sheet["medium"], w) < L["floor"]:
            continue
        if _any_slot_short(sheet, (w, h)):
            continue
        return (w, h)
    return tuple(L["rungs"][-1])


def readiness(sheet: dict) -> dict:
    """The export gate (plan §7): one list, two kinds. TYPE_FLOOR when a
    fixed block's type would set under the medium's floor at the sheet's
    size; SLOT_PIXELS when a slot's candidate is short of the pixels its
    rendered size needs (an empty slot is short of everything: have [0,0]).
    Stage 05's TOO_SMALL maps onto SLOT_PIXELS at this boundary only (R5)."""
    L = LADDERS[sheet["medium"]]
    width = sheet["size"][0]
    blocked: list[dict] = []
    for b in sheet.get("blocks", []):
        bd = BLOCK_TYPES[b["type"]]
        if bd.elastic:
            continue
        size = type_size(bd.frac, sheet["medium"], width)
        if size < L["floor"]:
            blocked.append({"kind": "TYPE_FLOOR", "block_id": b["block_id"],
                            "size": round(size, 1), "floor": L["floor"]})
    for b, s in _iter_slots(sheet):
        need = slot_pixel_need(sheet, b, s)
        have = _candidate_dims(s) if s.get("candidate_id") else (0, 0)
        if have[0] < need[0] or have[1] < need[1]:
            blocked.append({"kind": "SLOT_PIXELS", "block_id": b["block_id"],
                            "slot_id": s["slot_id"],
                            "have": list(have), "need": list(need)})
        # A take rejected or reverted after placement blocks export here —
        # slots hold approved takes only, and the gate must say so before
        # a pixel is spent. (A vanished candidate reads as (0,0) above.)
        if s.get("candidate_id") and s.get("spec_id"):
            rec = generate.get_candidate(s["spec_id"], s["candidate_id"])
            if rec is not None and rec.get("status") != "APPROVED":
                blocked.append({"kind": "SLOT_APPROVAL",
                                "block_id": b["block_id"],
                                "slot_id": s["slot_id"],
                                "candidate_id": s["candidate_id"]})
    return {"ready": not blocked, "blocked": blocked}


# ------------------------------------------------------------- caption model

def _hash_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_binding(binding: dict) -> str:
    """The caption's text as its source currently states it. Raises
    SheetError for an unknown kind; a missing source resolves to '' (which
    reads as STALE against any real bound_hash — the source is gone)."""
    kind = str(binding.get("kind", ""))
    if kind not in BINDING_KINDS:
        raise SheetError(f"unknown binding kind: {kind}")
    if kind == "SUBJECT":
        s = store.get_subject(str(binding.get("id", "")))
        if not s:
            return ""
        head = " — ".join(x for x in [s.get("name", ""), s.get("subtitle", "")] if x)
        return "\n".join([head] + [str(t) for t in s.get("traits", []) if t])
    if kind == "PANEL":
        spec = store.get_spec(str(binding.get("id", "")))
        if not spec:
            return ""
        pid = str(binding.get("panel", ""))
        p = next((p for p in spec.get("panels", []) if p.get("id") == pid), None)
        if not p:
            return ""
        return str(p.get("title") or p.get("purpose") or "")
    if kind == "SPEC_FIELD":
        spec = store.get_spec(str(binding.get("id", "")))
        if not spec:
            return ""
        v = spec.get(str(binding.get("field", "")), "")
        return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    if kind == "PALETTE_GROUP":
        # A stage-02 palette group IS a design language's swatches, in
        # reference order — the order is the ruling (palette-groups canon);
        # a sheet may not reorder them.
        from . import wizard
        live, _dead = wizard.swatches_in_play([str(binding.get("id", ""))])
        sw = live.get(str(binding.get("id", "")), [])
        return "\n".join([str(binding.get("id", ""))]
                         + [f"{p['hex']} {p['name']}".strip() for p in sw])
    if kind == "MATERIAL_ANCHOR":
        role = str(binding.get("role", ""))
        refs = [r for r in store.list_references()
                if r.get("role", "") == role and r.get("status") != "REJECTED"]
        return "\n".join(f"{r['id']} {r.get('file', '')}".strip() for r in refs)
    if kind == "SCREENPLAY":
        # The binding quotes a line; it resolves while the screenplay still
        # contains it and to '' (stale) once the line is rewritten.
        quote = str(binding.get("quote", ""))
        text = store.screenplay_text_cached()
        return quote if quote and quote in text else ""
    # JUDGING_NOTE — the note carried on a take's record.
    rec = generate.get_candidate(str(binding.get("id", "")),
                                 str(binding.get("candidate", "")))
    return str((rec or {}).get("model_notes") or (rec or {}).get("notes") or "")


def _caption_state(cap: dict) -> str:
    """BOUND / AUTHORED / STALE, computed live — never persisted by a read.
    A stale binding offers exactly two acts (take the new line / keep and
    author); silently rewriting approved work is the failure this exists to
    prevent (plan §8)."""
    if not cap:
        return "AUTHORED"
    if cap.get("state") == "AUTHORED" or not cap.get("binding"):
        return "AUTHORED"
    current = resolve_binding(cap["binding"])
    return "BOUND" if _hash_text(current) == cap.get("bound_hash") else "STALE"


# ---------------------------------------------------------------- sheet CRUD

def _sheet_path(sheet_id: str):
    return paths.SHEETS_DIR / f"{paths.safe_id(sheet_id)}.json"


def sheet_export_dir(sheet_id: str):
    return paths.SHEETS_DIR / paths.safe_id(sheet_id) / "export"


def _seed_slots(btype: str, n: int | None = None) -> list[dict]:
    """Default slot fracs for a fresh block — simple splits the composer
    then refines by drag. Deterministic; block-relative."""
    bd = BLOCK_TYPES[btype]
    # An explicit n may sit under the minimum — valid when every slot is
    # filled (see _validate); the max is a hard ceiling either way.
    n = bd.slots_min if n is None else max(1, min(bd.slots_max, n))
    slots: list[dict] = []
    if n == 0:
        return slots

    def add(x, y, w, h):
        slots.append({"slot_id": f"S{len(slots) + 1}", "spec_id": None,
                      "candidate_id": None,
                      "frac": {"x": round(x, 4), "y": round(y, 4),
                               "w": round(w, 4), "h": round(h, 4)},
                      "crop": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0,
                               "rotate": 0.0},
                      "annotation": None})

    if btype == "HERO":
        add(0, 0, 1, 1)
    elif btype == "CLUSTER":
        # Hero-left, the rest stacked right (the allocation grammar).
        add(0, 0, 0.62, 1)
        rest = n - 1
        for i in range(rest):
            add(0.65, i / rest, 0.35, 1 / rest - (0.02 if rest > 1 else 0))
    elif btype == "VERSUS":
        add(0, 0, 0.49, 1)
        add(0.51, 0, 0.49, 1)
    elif btype in ("STRIP", "LINEUP", "MATERIAL"):
        for i in range(n):
            add(i / n, 0, 1 / n - (0.012 if n > 1 else 0), 1)
    else:  # GRID, ORTHO, BEATS — uniform grid
        cols = 2 if btype == "ORTHO" else min(5, max(2, -(-n // 3)))
        rows = -(-n // cols)
        for i in range(n):
            r, c = divmod(i, cols)
            add(c / cols, r / rows, 1 / cols - 0.012, 1 / rows - 0.02)
    return slots


def _new_block(sheet: dict, btype: str, frac: dict | None = None) -> dict:
    if btype not in BLOCK_TYPES:
        raise SheetError(f"unknown block type: {btype}")
    n = 1 + max((int(b["block_id"].split("-")[1]) for b in sheet["blocks"]),
                default=0)
    if frac is None:
        bottom = max((b["frac"]["y"] + b["frac"]["h"]
                      for b in sheet["blocks"]), default=0.0)
        y = min(bottom + 0.02, 0.85)
        frac = {"x": 0.0, "y": round(y, 4), "w": 1.0,
                "h": round(min(0.3, 1.0 - y), 4)}
    return {"block_id": f"B-{n:04d}", "type": btype, "frac": dict(frac),
            "heading": None, "caption": None, "slots": _seed_slots(btype)}


def create_sheet(archetype: str, style: str, medium: str,
                 spec_id: str | None = None, title: str = "",
                 subject: str = "") -> dict:
    if archetype not in ARCHETYPES:
        raise SheetError(f"unknown archetype: {archetype}")
    if style not in STYLES:
        raise SheetError(f"unknown style: {style}")
    if medium not in LADDERS:
        raise SheetError(f"medium must be one of {sorted(LADDERS)}")
    seed = ARCHETYPES[archetype]
    sheet = {
        "sheet_id": store.next_counter("sheet_counter", "SH"),
        "archetype": archetype,
        "style": style,
        "medium": medium,
        "size": list(LADDERS[medium]["rungs"][0]),
        "size_source": "RECOMMENDED",
        "spec_id": spec_id,
        "masthead": {"title": title, "subject": subject, "binding": None},
        "spine": bool(seed["spine"]),
        "blocks": [],
        "rev": 0,
        "created_at": store.utcnow(),
        "updated_at": store.utcnow(),
    }
    for btype, frac in seed["blocks"]:
        sheet["blocks"].append(_new_block(sheet, btype, frac))
    return save_sheet(sheet)


def _validate(sheet: dict) -> None:
    if sheet.get("style") not in STYLES:
        raise SheetError(f"unknown style: {sheet.get('style')}")
    if sheet.get("archetype") not in ARCHETYPES:
        raise SheetError(f"unknown archetype: {sheet.get('archetype')}")
    if sheet.get("medium") not in LADDERS:
        raise SheetError(f"unknown medium: {sheet.get('medium')}")
    if sheet.get("size_source") not in ("RECOMMENDED", "CHOSEN"):
        raise SheetError("size_source must be RECOMMENDED or CHOSEN")
    for b in sheet.get("blocks", []):
        bd = BLOCK_TYPES.get(b.get("type"))
        if bd is None:
            raise SheetError(f"unknown block type: {b.get('type')}")
        slots = b.get("slots", [])
        nslots = len(slots)
        if nslots > bd.slots_max:
            raise SheetError(
                f"{b.get('block_id')}: {b['type']} holds at most "
                f"{bd.slots_max} slots, not {nslots}")
        # The minimum stops skeletal empty layouts; a block whose every
        # slot is filled is valid at any count — an arranged two-panel
        # board is a real board, and the R4 strip carries exactly the
        # takes that exist. A panel-bound block (every slot names its
        # panel) is likewise exempt: its census comes from the spec's
        # panel list, not a layout choice, and an unapproved panel
        # arranges as an empty slot.
        filled = nslots > 0 and all(s.get("candidate_id") for s in slots)
        panel_bound = nslots > 0 and all(s.get("panel_id") for s in slots)
        if (not bd.elastic and nslots < bd.slots_min
                and not filled and not panel_bound):
            raise SheetError(
                f"{b.get('block_id')}: {b['type']} holds at least "
                f"{bd.slots_min} slots, not {nslots}")
        for rect in ([b.get("frac", {})]
                     + [s.get("frac", {}) for s in b.get("slots", [])]
                     + [s.get("crop", {}) for s in b.get("slots", [])
                        if s.get("crop")]):
            for k in ("x", "y", "w", "h"):
                v = float(rect.get(k, 0))
                if not (0.0 <= v <= 1.0):
                    raise SheetError(
                        f"{b.get('block_id')}: frac {k}={v} out of [0, 1]")


def save_sheet(sheet: dict) -> dict:
    """Validate, follow a RECOMMENDED size silently (that is what
    recommended means), bump rev, write atomically."""
    _validate(sheet)
    if sheet.get("size_source") == "RECOMMENDED":
        sheet["size"] = list(recommend(sheet))
    sheet["rev"] = int(sheet.get("rev", 0)) + 1
    sheet["updated_at"] = store.utcnow()
    store._atomic_write_json(_sheet_path(sheet["sheet_id"]), sheet)
    return sheet


def get_sheet(sheet_id: str) -> dict | None:
    p = _sheet_path(sheet_id)
    if not p.exists():
        return None
    sheet = json.loads(p.read_text(encoding="utf-8"))
    # Staleness sweep — computed on read, never persisted by a read.
    for b in sheet.get("blocks", []):
        for key in ("heading", "caption"):
            cap = b.get(key)
            if cap:
                cap["state"] = _caption_state(cap)
    mh = sheet.get("masthead") or {}
    if mh.get("binding"):
        mh["state"] = ("BOUND" if _hash_text(resolve_binding(mh["binding"]))
                       == mh.get("bound_hash") else "STALE")
    return sheet


def list_sheets() -> list[dict]:
    if not paths.SHEETS_DIR.exists():
        return []
    out = []
    for p in sorted(paths.SHEETS_DIR.glob("SH-*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        out.append({"sheet_id": s["sheet_id"], "archetype": s["archetype"],
                    "style": s["style"], "medium": s["medium"],
                    "size": s["size"], "spec_id": s.get("spec_id"),
                    "title": (s.get("masthead") or {}).get("title", ""),
                    "blocks": len(s.get("blocks", [])),
                    "updated_at": s.get("updated_at", "")})
    return out


def delete_sheet(sheet_id: str) -> None:
    p = _sheet_path(sheet_id)
    if not p.exists():
        raise KeyError(sheet_id)
    p.unlink()


# ----------------------------------------------------------------- block ops

def _require(sheet_id: str) -> dict:
    sheet = get_sheet(sheet_id)
    if sheet is None:
        raise KeyError(sheet_id)
    return sheet


def _block(sheet: dict, block_id: str) -> dict:
    b = next((b for b in sheet["blocks"] if b["block_id"] == block_id), None)
    if b is None:
        raise KeyError(block_id)
    return b


def add_block(sheet_id: str, btype: str, index: int | None = None) -> dict:
    sheet = _require(sheet_id)
    block = _new_block(sheet, btype)
    if index is None:
        sheet["blocks"].append(block)
    else:
        sheet["blocks"].insert(max(0, min(index, len(sheet["blocks"]))), block)
    return save_sheet(sheet)


def remove_block(sheet_id: str, block_id: str) -> dict:
    sheet = _require(sheet_id)
    _block(sheet, block_id)  # KeyError if absent
    sheet["blocks"] = [b for b in sheet["blocks"] if b["block_id"] != block_id]
    return save_sheet(sheet)


def set_slot(sheet_id: str, block_id: str, slot_id: str, patch: dict) -> dict:
    """Patch a slot: candidate (spec_id + candidate_id), frac, crop,
    annotation. Every drag saves — there is no session and no save button
    (plan §5). Over-budget crops are allowed and kept: the slot turns
    short in readiness(), exactly as a small render does."""
    sheet = _require(sheet_id)
    b = _block(sheet, block_id)
    s = next((s for s in b["slots"] if s["slot_id"] == slot_id), None)
    if s is None:
        raise KeyError(slot_id)
    for key in ("spec_id", "candidate_id"):
        if key in patch:
            s[key] = patch[key]
    if s.get("candidate_id") and s.get("spec_id"):
        cand = generate.get_candidate(s["spec_id"], s["candidate_id"])
        if cand is None:
            raise SheetError(f"unknown candidate {s['candidate_id']} "
                             f"on {s['spec_id']}")
        # Slots hold approved takes only — the fill tray offers nothing
        # else, and this door must not be wider than the tray.
        if cand.get("status") != "APPROVED":
            raise SheetError(f"{s['candidate_id']} is not approved; "
                             "slots hold approved takes only")
    for key in ("frac", "crop"):
        if key in patch and patch[key] is not None:
            s[key] = {k: float(v) for k, v in patch[key].items()}
    if "annotation" in patch:
        s["annotation"] = patch["annotation"]
    return save_sheet(sheet)


def add_slot(sheet_id: str, block_id: str) -> dict:
    sheet = _require(sheet_id)
    b = _block(sheet, block_id)
    bd = BLOCK_TYPES[b["type"]]
    if len(b["slots"]) >= bd.slots_max:
        raise SheetError(f"{b['type']} holds at most {bd.slots_max} slots")
    b["slots"] = _merge_reseed(b, len(b["slots"]) + 1)
    return save_sheet(sheet)


def remove_slot(sheet_id: str, block_id: str, slot_id: str) -> dict:
    sheet = _require(sheet_id)
    b = _block(sheet, block_id)
    bd = BLOCK_TYPES[b["type"]]
    if len(b["slots"]) <= bd.slots_min:
        raise SheetError(f"{b['type']} holds at least {bd.slots_min} slots")
    if not any(s["slot_id"] == slot_id for s in b["slots"]):
        raise KeyError(slot_id)
    b["slots"] = [s for s in b["slots"] if s["slot_id"] != slot_id]
    return save_sheet(sheet)


def _merge_reseed(block: dict, n: int) -> list[dict]:
    """Grow a block to n slots: fresh geometry, existing fills carried in
    order."""
    fresh = _seed_slots(block["type"], n)
    for old, new in zip(block["slots"], fresh):
        for key in ("spec_id", "candidate_id", "crop", "annotation"):
            new[key] = old.get(key)
    return fresh


# ------------------------------------------------------------------ captions

def set_caption(sheet_id: str, block_id: str, text: str | None = None,
                binding: dict | None = None, slot: str = "",
                which: str = "caption") -> dict:
    """Author a caption (text) or bind it (binding) — exactly one of the
    two. which: 'caption' | 'heading'."""
    if (text is None) == (binding is None):
        raise SheetError("caption takes text OR binding, exactly one")
    if which not in ("caption", "heading"):
        raise SheetError(f"unknown caption field: {which}")
    sheet = _require(sheet_id)
    b = _block(sheet, block_id)
    if binding is not None:
        resolved = resolve_binding(binding)
        b[which] = {"text": resolved, "binding": binding,
                    "bound_hash": _hash_text(resolved), "state": "BOUND"}
    else:
        b[which] = {"text": str(text), "state": "AUTHORED"}
    return save_sheet(sheet)


def resolve_caption(sheet_id: str, block_id: str, action: str,
                    which: str = "caption") -> dict:
    """The two acts on a STALE binding: 'rebind' takes the new line (new
    hash); 'author' keeps the text and freezes it. Never auto-adopt; the
    source is never written."""
    if action not in ("rebind", "author"):
        raise SheetError("action must be 'rebind' or 'author'")
    sheet = _require(sheet_id)
    b = _block(sheet, block_id)
    cap = b.get(which)
    if not cap:
        raise KeyError(which)
    if action == "rebind":
        if not cap.get("binding"):
            raise SheetError("caption has no binding to rebind")
        resolved = resolve_binding(cap["binding"])
        cap.update(text=resolved, bound_hash=_hash_text(resolved),
                   state="BOUND")
    else:
        cap.pop("binding", None)
        cap.pop("bound_hash", None)
        cap["state"] = "AUTHORED"
    return save_sheet(sheet)


# ------------------------------------------------------------------- arrange

def arrange_board(spec_id: str) -> dict:
    """Stage 05's one new door (plan §9): idempotent — a spec has at most
    one BOARD sheet, created on first call from the spec's current slot
    map. Readiness travels with the candidates; the composer never grows a
    second opinion about whether a panel is big enough."""
    from . import assemble  # function-level: assemble imports our packers

    for p in (sorted(paths.SHEETS_DIR.glob("SH-*.json"))
              if paths.SHEETS_DIR.exists() else []):
        s = json.loads(p.read_text(encoding="utf-8"))
        if s.get("archetype") == "BOARD" and s.get("spec_id") == spec_id:
            return get_sheet(s["sheet_id"])

    # "The spec's current slot map": the layout the user last assembled
    # under, read from the latest board record — default when none exists.
    variant = None
    bdir = paths.BOARDS_DIR / paths.safe_id(spec_id)
    if bdir.exists():
        boards = sorted(bdir.glob("BOARD-*.json"))
        if boards:
            rec = json.loads(boards[-1].read_text(encoding="utf-8"))
            variant = rec.get("layout_variant")
    sm = assemble.slot_map(spec_id, variant=variant)
    spec = store.get_spec(spec_id) or {}
    variant = sm["layout_variant"]

    sheet = create_sheet("BOARD", BOARD_STYLE, "SCREEN", spec_id=spec_id,
                         title=str(spec.get("subject", spec_id)),
                         subject=assemble._slug(spec))
    sheet["masthead"]["binding"] = {"kind": "SPEC_FIELD", "id": spec_id,
                                    "field": "subject"}
    sheet["masthead"]["bound_hash"] = _hash_text(
        resolve_binding(sheet["masthead"]["binding"]))
    sheet["blocks"] = []

    hero_id = variant[5:] if variant.startswith("hero:") else None
    layout_type = "CLUSTER" if variant == "allocation" else "GRID"
    slots = [s for s in sm["slots"] if s["panel_id"] != hero_id]
    hero = next((s for s in sm["slots"] if s["panel_id"] == hero_id), None)

    def bbox(entries):
        x0 = min(e["x"] for e in entries)
        y0 = min(e["y"] for e in entries)
        x1 = max(e["x"] + e["w"] for e in entries)
        y1 = max(e["y"] + e["h"] for e in entries)
        return x0, y0, x1 - x0, y1 - y0

    all_box = bbox(sm["slots"])

    def block_from(entries, btype):
        bx, by, bw, bh = bbox(entries)
        block = _new_block(sheet, btype, {
            "x": round((bx - all_box[0]) / all_box[2], 4),
            "y": round((by - all_box[1]) / all_box[3], 4),
            "w": round(bw / all_box[2], 4), "h": round(bh / all_box[3], 4)})
        block["slots"] = []
        for e in entries:
            # Only approved takes ride into the sheet (OK / TOO_SMALL both
            # mean approved); an UNAPPROVED panel arranges as an empty
            # slot, which readiness() blocks until it is filled.
            approved_take = (e.get("candidate_id")
                             if e.get("status") in ("OK", "TOO_SMALL")
                             else None)
            block["slots"].append({
                "slot_id": f"S{len(block['slots']) + 1}",
                "spec_id": spec_id, "candidate_id": approved_take,
                "panel_id": e["panel_id"],
                "frac": {"x": round((e["x"] - bx) / bw, 4),
                         "y": round((e["y"] - by) / bh, 4),
                         "w": round(e["w"] / bw, 4),
                         "h": round(e["h"] / bh, 4)},
                "crop": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0,
                         "rotate": 0.0},
                "annotation": None})
        return block

    if hero is not None:
        sheet["blocks"].append(block_from([hero], "HERO"))
    if slots:
        # The block caps are hard for hand-authored sheets; an arranged
        # board honors them by chunking reading-order runs into as many
        # balanced blocks as the count needs (a 6-panel allocation board
        # is two CLUSTERs of three, not a 422). Slot fracs are relative
        # to each block's own bounding box, so chunking never moves a
        # panel — the rendered geometry is identical.
        cap = BLOCK_TYPES[layout_type].slots_max
        ordered = sorted(slots, key=lambda e: (e["y"], e["x"]))
        groups = -(-len(ordered) // cap)
        size = -(-len(ordered) // groups)
        for i in range(0, len(ordered), size):
            sheet["blocks"].append(block_from(ordered[i:i + size],
                                              layout_type))

    # R4: existing MATERIALS / PALETTE renders are takes, not evidence
    # blocks — they travel as a trailing STRIP naming the swap. Nothing is
    # dropped, and nothing is left for the user to diagnose.
    derived = []
    approved = assemble._latest_approved_by_panel(spec_id)
    for pid in sm.get("derived_strip", []):
        cand = approved.get(pid)
        if cand:
            derived.append((pid, cand))
    if derived:
        strip = _new_block(sheet, "STRIP",
                           {"x": 0.0, "y": 0.86, "w": 1.0, "h": 0.14})
        strip["slots"] = _seed_slots("STRIP", len(derived))
        for (pid, cand), s in zip(derived, strip["slots"]):
            s.update(spec_id=spec_id, candidate_id=cand["candidate_id"],
                     panel_id=pid)
        strip["caption"] = {"text": DERIVED_SWAP_NOTE, "state": "AUTHORED"}
        sheet["blocks"].append(strip)

    return save_sheet(sheet)


# ---------------------------------------------------------- arrangement
# The arrange room's board physics (user 2026-08-12, prototyped in the
# Reflow Lab): the room edits a rows -> columns -> stacked-cells
# structure with linked-edge resizing, split-docking, claim arrows and a
# bench. THIS is where that structure becomes slot geometry — the server
# owns the mapping (R2: geometry computed once); the client's live math
# during a gesture is feedback only, never stored.

def set_arrangement(sheet_id: str, arrangement: dict) -> dict:
    """Replace a BOARD sheet's blocks from an arrangement structure:
    {rows: [{h, cols: [{w, cells: [{id, h}]}]}], bench: [panel ids]}.
    Fractions renormalize server-side; every placed cell keeps its
    panel's carried take, crop and annotation; benched panels simply
    have no slot (a layout decision — the takes are untouched)."""
    sheet = _require(sheet_id)
    if sheet.get("archetype") != "BOARD":
        raise SheetError("an arrangement applies to BOARD sheets only")
    rows = arrangement.get("rows") or []
    bench = [str(b) for b in (arrangement.get("bench") or [])]
    spec_id = str(sheet.get("spec_id") or "")
    spec = store.get_spec(spec_id) or {}
    known = ({p["id"] for p in spec.get("panels", [])}
             | {"MATERIALS", "PALETTE"})
    carried: dict[str, dict] = {}
    for _b, s in _iter_slots(sheet):
        if s.get("panel_id"):
            carried[s["panel_id"]] = s
            known.add(s["panel_id"])

    ids: list[str] = []
    for row in rows:
        for col in (row.get("cols") or []):
            for cell in (col.get("cells") or []):
                ids.append(str(cell.get("id", "")))
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise SheetError(f"panel placed twice: {', '.join(dupes)}")
    unknown = sorted({i for i in ids + bench if i not in known})
    if unknown:
        raise SheetError(f"unknown panel: {', '.join(unknown)}")
    if not ids:
        raise SheetError("an arrangement needs at least one placed panel")

    from . import assemble
    approved = assemble._latest_approved_by_panel(spec_id) if spec_id else {}

    def slot_for(pid: str, frac: dict) -> dict:
        # A panel-bound slot follows the panel's LATEST approved take —
        # the same rule the slot map and assemble live by. Pinning the
        # placed candidate froze boards on stale takes: a fresh 4K
        # approval left the board judging the old render SHORT forever
        # (user-hit 2026-08-13). The carried id only fills in when no
        # approval exists (e.g. it lost approval after placement — the
        # SLOT_APPROVAL gate then states it).
        old = carried.get(pid) or {}
        cand = ((approved.get(pid) or {}).get("candidate_id")
                or old.get("candidate_id"))
        return {"slot_id": "", "spec_id": old.get("spec_id") or spec_id,
                "candidate_id": cand, "panel_id": pid, "frac": frac,
                "crop": old.get("crop") or {"x": 0.0, "y": 0.0, "w": 1.0,
                                            "h": 1.0, "rotate": 0.0},
                "annotation": old.get("annotation")}

    # Gutter (user 2026-08-13, from the prototype's tuning): a sheet-level
    # breathing space in SHEET pixels, baked into the stored fracs so the
    # renderer and every export honor it without knowing it exists.
    W, H = sheet["size"][0], sheet["size"][1]
    if sheet.get("medium") == "PRINT":
        W, H = W * 300, H * 300
    gutter = arrangement.get("gutter")
    cap = min(W, H) // 5  # breathing space, never a layout of its own
    gutter = 36 if gutter is None else max(0, min(cap, int(gutter)))
    gx, gy = gutter / W, gutter / H

    hsum = sum(float(r.get("h", 0)) for r in rows) or 1.0
    blocks: list[dict] = []
    y = 0.0
    norm_rows = []
    for row in rows:
        rh = float(row.get("h", 0)) / hsum
        cols = row.get("cols") or []
        wsum = sum(float(c.get("w", 0)) for c in cols) or 1.0
        slots: list[dict] = []   # carries ABSOLUTE fracs until chunking
        norm_cols = []
        x = 0.0
        for col in cols:
            cw = float(col.get("w", 0)) / wsum
            cells = col.get("cells") or []
            csum = sum(float(k.get("h", 0)) for k in cells) or 1.0
            norm_cells = []
            cy = 0.0
            for cell in cells:
                ch = float(cell.get("h", 0)) / csum
                pid = str(cell.get("id"))
                ax = x + gx / 2
                ay = y + rh * cy + gy / 2
                aw = max(cw - gx, 0.01)
                ah = max(rh * ch - gy, 0.01)
                slots.append(slot_for(pid, {
                    "x": ax, "y": ay, "w": aw, "h": ah}))
                norm_cells.append({"id": pid, "h": round(ch, 4)})
                cy += ch
            norm_cols.append({"w": round(cw, 4), "cells": norm_cells})
            x += cw
        # The GRID cap is hard for hand-authored sheets; a row that holds
        # more chunks into same-band blocks (geometry preserved, exactly
        # as arrange_board chunks).
        cap = BLOCK_TYPES["GRID"].slots_max
        pieces = [slots[i:i + cap] for i in range(0, len(slots), cap)] or [[]]
        for piece in pieces:
            if not piece:
                continue
            bx = min(s["frac"]["x"] for s in piece)
            by = min(s["frac"]["y"] for s in piece)
            bxe = max(s["frac"]["x"] + s["frac"]["w"] for s in piece)
            bye = max(s["frac"]["y"] + s["frac"]["h"] for s in piece)
            bw = max(bxe - bx, 1e-6)
            bh = max(bye - by, 1e-6)
            block = _new_block(sheet, "GRID", {
                "x": round(bx, 4), "y": round(by, 4),
                "w": round(bw, 4), "h": round(bh, 4)})
            block["slots"] = []
            for s in piece:
                f = s["frac"]
                s = dict(s, slot_id=f"S{len(block['slots']) + 1}",
                         frac={"x": round((f["x"] - bx) / bw, 4),
                               "y": round((f["y"] - by) / bh, 4),
                               "w": round(f["w"] / bw, 4),
                               "h": round(f["h"] / bh, 4)})
                block["slots"].append(s)
            blocks.append(block)
        norm_rows.append({"h": round(rh, 4), "cols": norm_cols})
        y += rh
    sheet["blocks"] = blocks
    sheet["arrangement"] = {"rows": norm_rows, "bench": bench,
                            "gutter": gutter}
    return save_sheet(sheet)


def derive_arrangement(sheet: dict) -> dict:
    """A BOARD sheet that predates arrangements gets one inferred from
    its slot geometry by guillotine slicing: full-width horizontal gaps
    cut rows, full-height vertical gaps cut columns, horizontal gaps cut
    stacked cells. Everything the packers and the old composer produced
    slices cleanly at depth three; anything deeper degrades to one
    column per remaining rect (approximate, never lossy of panels)."""
    rects = []
    for b in sheet.get("blocks", []):
        bf = b.get("frac", {})
        for s in b.get("slots", []):
            if not s.get("panel_id"):
                continue
            f = s["frac"]
            rects.append({"id": s["panel_id"],
                          "x": bf["x"] + f["x"] * bf["w"],
                          "y": bf["y"] + f["y"] * bf["h"],
                          "w": f["w"] * bf["w"], "h": f["h"] * bf["h"]})

    def cuts(rs, axis):
        lo = min(r[axis] for r in rs)
        hi = max(r[axis] + r["w" if axis == "x" else "h"] for r in rs)
        edges = sorted({round(r[axis] + (r["w" if axis == "x" else "h"]), 4)
                        for r in rs} - {round(hi, 4)})
        out = []
        for e in edges:
            if all(r[axis] + 1e-4 >= e or
                   r[axis] + (r["w"] if axis == "x" else r["h"]) <= e + 1e-4
                   for r in rs):
                out.append(e)
        return [lo] + out + [hi]

    def between(rs, axis, a, b):
        key = "w" if axis == "x" else "h"
        return [r for r in rs if r[axis] + r[key] / 2 > a
                and r[axis] + r[key] / 2 < b]

    rows_out = []
    if not rects:
        return {"rows": [], "bench": [], "gutter": 36}
    ys = cuts(rects, "y")
    for yi in range(len(ys) - 1):
        band = between(rects, "y", ys[yi], ys[yi + 1])
        if not band:
            continue
        cols_out = []
        xs = cuts(band, "x")
        for xi in range(len(xs) - 1):
            colr = between(band, "x", xs[xi], xs[xi + 1])
            if not colr:
                continue
            colr.sort(key=lambda r: r["y"])
            total = sum(r["h"] for r in colr) or 1.0
            cols_out.append({"w": round(xs[xi + 1] - xs[xi], 4),
                             "cells": [{"id": r["id"],
                                        "h": round(r["h"] / total, 4)}
                                       for r in colr]})
        rows_out.append({"h": round(ys[yi + 1] - ys[yi], 4),
                         "cols": cols_out})
    return {"rows": rows_out, "bench": [], "gutter": 36}


# ------------------------------------------------------------- fill tray

def fill_candidates() -> list[dict]:
    """The arrange room's fill tray: every APPROVED candidate across the
    production, `placed_in` naming the sheets already holding it. Reuses
    generate.list_candidates per spec — no second index. (Formerly
    lookbook_candidates; the Lookbook surface was rolled back 2026-08-12
    and the tray now serves the stage-05 arrange room.)"""
    placed: dict[str, list[str]] = {}
    for meta in list_sheets():
        full = get_sheet(meta["sheet_id"]) or {}
        for _b, s in _iter_slots(full):
            if s.get("candidate_id"):
                placed.setdefault(s["candidate_id"], []).append(
                    meta["sheet_id"])
    out = []
    for spec_meta in store.list_specs():
        sid = spec_meta.get("specification_id")
        if not sid:
            continue
        for c in generate.list_candidates(sid):
            if (c.get("status") == "APPROVED"
                    and str(c.get("candidate_id", "")).startswith("CAND-")):
                out.append({"spec_id": sid,
                            "candidate_id": c["candidate_id"],
                            "panel_id": c.get("panel_id", ""),
                            "width": c.get("width"), "height": c.get("height"),
                            "placed_in": placed.get(c["candidate_id"], [])})
    return out
