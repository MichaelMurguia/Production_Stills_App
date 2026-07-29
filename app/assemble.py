from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import generate, paths, store

# Board grammar defaults — warm neutral ground, production-wall hierarchy.
BG = (42, 39, 35)
PANEL_BG = (52, 48, 43)
INK = (232, 229, 221)
INK_DIM = (154, 151, 143)
ACCENT = (216, 162, 74)

MARGIN = 64
GUTTER = 36
HEADER_H = 150
LABEL_H = 46

FONT_CANDIDATES = [
    "C:/Windows/Fonts/bahnschrift.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


class AssemblyError(Exception):
    pass


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _latest_approved_by_panel(spec_id: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for c in generate.list_candidates(spec_id):
        if c.get("status") == "APPROVED" and c.get("candidate_id", "").startswith("CAND-"):
            out[c["panel_id"]] = c  # list is sorted by id; last approved wins
    return out


def _slug(spec: dict) -> str:
    """The header's setting line — slugline discipline carried onto the board."""
    btype = str(spec.get("board_type") or "LOCATION").upper()
    if btype == "ASSET":
        return "ASSET BOARD"
    if btype == "MASTER":
        return "MASTER BOARD"
    s = spec.get("setting") or {}
    place = f"{s.get('int_ext', '')}. {s.get('location', '')}".strip(". ").strip()
    tod = str(s.get("time_of_day", "")).strip().upper()
    slug = " — ".join(x for x in [place, tod] if x)
    if btype == "LIGHTING_STUDY":
        return f"LIGHTING STUDY · {slug}" if slug else "LIGHTING STUDY"
    return slug


def _grid_rects(panels: list[dict], x0: int, y0: int, w: int,
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


def _layout_rects(panels: list[dict], alloc: dict[str, float],
                  x0: int, y0: int, w: int, h: int) -> dict[str, tuple[int, int, int, int]]:
    """Hero panel takes the left region, remaining panels stack on the right
    with heights proportional to their layout allocation."""
    ordered = sorted(panels, key=lambda p: -(alloc.get(p["id"], 0) or 0))
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


def slot_map(spec_id: str, width: int = 3840, height: int = 2160) -> dict:
    """The board's slot geometry BEFORE any pixels are spent, with a verdict
    per slot: OK, UNAPPROVED (candidates but none approved), TOO_SMALL
    (approved render smaller than its slot in both dimensions — it would
    need upscaling, which never happens), NO_CANDIDATE. Mirrors
    assemble_board's exact geometry so the preview is honest."""
    spec = store.get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)

    approved = _latest_approved_by_panel(spec_id)
    have: dict[str, dict] = {}
    for c in generate.list_candidates(spec_id):
        if c.get("candidate_id", "").startswith("CAND-"):
            have[c["panel_id"]] = c

    alloc = {lp["id"]: float(lp.get("allocation_percent", 0))
             for lp in spec.get("layout", {}).get("panels", [])}

    inner_x = MARGIN
    inner_y = HEADER_H + MARGIN
    inner_w = width - 2 * MARGIN
    inner_h = height - inner_y - MARGIN
    derived = [pid for pid in ("MATERIALS", "PALETTE") if pid in approved]
    if derived:
        inner_h -= max(220, int(inner_h * 0.16)) + GUTTER

    btype = str(spec.get("board_type") or "LOCATION").upper()
    panels = spec.get("panels", [])
    if btype == "LIGHTING_STUDY":
        rects = _grid_rects(panels, inner_x, inner_y, inner_w, inner_h)
    else:
        rects = _layout_rects(panels, alloc, inner_x, inner_y, inner_w, inner_h)

    slots = []
    for panel in panels:
        pid = panel["id"]
        rx, ry, rw, rh = rects[pid]
        img_h = rh - LABEL_H
        cand = approved.get(pid)
        status = "NO_CANDIDATE"
        cw = ch = None
        cand_id = None
        if cand:
            cand_id = cand["candidate_id"]
            cw = int(cand.get("width") or 0)
            ch = int(cand.get("height") or 0)
            status = "TOO_SMALL" if (cw < rw and ch < img_h) else "OK"
        elif pid in have:
            cand_id = have[pid]["candidate_id"]
            status = "UNAPPROVED"
        slots.append({
            "panel_id": pid,
            "title": panel.get("title") or panel.get("purpose", ""),
            "x": rx / width, "y": ry / height,
            "w": rw / width, "h": img_h / height,
            "slot_width": rw, "slot_height": img_h,
            "status": status,
            "candidate_id": cand_id,
            "candidate_width": cw, "candidate_height": ch,
            "allocation_percent": alloc.get(pid),
        })

    not_ready = [s for s in slots if s["status"] != "OK"]
    return {
        "spec_id": spec_id,
        "canvas": {"width": width, "height": height},
        "locked": store.spec_locked(spec_id),
        "board_type": btype,
        "derived_strip": derived,
        "slots": slots,
        "ready": not not_ready,
        "assemblable": all(s["status"] in ("OK", "TOO_SMALL") for s in slots),
        "not_ready": [{"panel_id": s["panel_id"], "status": s["status"]}
                      for s in not_ready],
    }


def assemble_board(spec_id: str, width: int = 3840, height: int = 2160) -> dict:
    from common import stable_hash

    spec = store.get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    if not store.spec_locked(spec_id):
        raise AssemblyError(f"{spec_id} is not approved; only locked specs can assemble.")

    approved = _latest_approved_by_panel(spec_id)
    missing = [p["id"] for p in spec.get("panels", []) if p["id"] not in approved]
    if missing:
        raise AssemblyError(
            "every panel needs an APPROVED candidate before assembly; missing: "
            + ", ".join(missing))

    alloc = {lp["id"]: float(lp.get("allocation_percent", 0))
             for lp in spec.get("layout", {}).get("panels", [])}

    board = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(board)

    title_font = _font(64)
    sub_font = _font(26)
    label_font = _font(28)

    # Header — board title in the Master Board presentation grammar.
    draw.text((MARGIN, MARGIN - 10), str(spec.get("subject", spec_id)).upper(),
              font=title_font, fill=INK)
    slug = _slug(spec)
    sub = "  ·  ".join(x for x in [
        slug, spec_id, str(spec.get("mode", "")), "BOARD CANDIDATE — UNAPPROVED"] if x)
    draw.text((MARGIN, MARGIN + 72), sub, font=sub_font, fill=INK_DIM)
    draw.line([(MARGIN, HEADER_H + MARGIN - 24), (width - MARGIN, HEADER_H + MARGIN - 24)],
              fill=ACCENT, width=3)

    inner_x = MARGIN
    inner_y = HEADER_H + MARGIN
    inner_w = width - 2 * MARGIN
    inner_h = height - inner_y - MARGIN

    # Approved derived strips (palette / materials) reserve a bottom band.
    derived = [(pid, approved[pid]) for pid in ("MATERIALS", "PALETTE") if pid in approved]
    strip_h = 0
    if derived:
        strip_h = max(220, int(inner_h * 0.16))
        inner_h -= strip_h + GUTTER

    btype = str(spec.get("board_type") or "LOCATION").upper()
    if btype == "LIGHTING_STUDY":
        rects = _grid_rects(spec["panels"], inner_x, inner_y, inner_w, inner_h)
    else:
        rects = _layout_rects(spec["panels"], alloc, inner_x, inner_y, inner_w, inner_h)

    warnings = []
    used: dict[str, str] = {}
    for panel in spec["panels"]:
        pid = panel["id"]
        rx, ry, rw, rh = rects[pid]
        img_h = rh - LABEL_H
        cand = approved[pid]
        used[pid] = cand["candidate_id"]
        img_path = generate.candidate_image_path(spec_id, cand["candidate_id"])
        if img_path is None:
            raise AssemblyError(f"image file missing for {cand['candidate_id']}")

        draw.rectangle([rx, ry, rx + rw, ry + img_h], fill=PANEL_BG)
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            # No upscaling, ever: scale factor is capped at 1.0. A panel render
            # smaller than its slot is centered and flagged for regeneration.
            scale = min(rw / im.width, img_h / im.height, 1.0)
            if scale < 1.0:
                im = im.resize((max(1, int(im.width * scale)),
                                max(1, int(im.height * scale))), Image.LANCZOS)
            elif rw > im.width and img_h > im.height:
                warnings.append(
                    f"{pid}: {cand['candidate_id']} ({im.width}x{im.height}) is smaller than "
                    f"its {rw}x{img_h} slot — regenerate at a larger size for full quality")
            ox = rx + (rw - im.width) // 2
            oy = ry + (img_h - im.height) // 2
            board.paste(im, (ox, oy))

        label = f"{pid} — {panel.get('title') or panel.get('purpose', '')}"
        draw.text((rx, ry + img_h + 10), label.upper(), font=label_font, fill=INK)

    # Derived strips band: materials and palette, drawn from the board's own
    # approved imagery. Same no-upscaling rule as every panel.
    if derived:
        sy = inner_y + inner_h + GUTTER
        cell_h = strip_h - LABEL_H
        sx = inner_x
        strip_labels = {
            "MATERIALS": "MATERIALS — DERIVED FROM APPROVED PANELS",
            "PALETTE": "PALETTE — SAMPLED FROM APPROVED PANELS",
        }
        for pid, cand in derived:
            used[pid] = cand["candidate_id"]
            img_path = generate.candidate_image_path(spec_id, cand["candidate_id"])
            if img_path is None:
                warnings.append(f"{pid}: image file missing for {cand['candidate_id']}")
                continue
            with Image.open(img_path) as im:
                im = im.convert("RGB")
                scale = min(cell_h / im.height, (inner_x + inner_w - sx) / im.width, 1.0)
                if scale < 1.0:
                    im = im.resize((max(1, int(im.width * scale)),
                                    max(1, int(im.height * scale))), Image.LANCZOS)
                draw.rectangle([sx, sy, sx + im.width, sy + cell_h], fill=PANEL_BG)
                board.paste(im, (sx, sy + (cell_h - im.height) // 2))
                draw.text((sx, sy + cell_h + 8), strip_labels.get(pid, pid),
                          font=label_font, fill=INK_DIM)
                sx += im.width + GUTTER
            if sx >= inner_x + inner_w:
                break

    state = store.load_app_state()
    state["board_counter"] = int(state.get("board_counter", 0)) + 1
    board_id = f"BOARD-{state['board_counter']:04d}"
    store.save_app_state(state)

    d = paths.BOARDS_DIR / spec_id
    d.mkdir(parents=True, exist_ok=True)
    img_path = d / f"{board_id}.png"
    board.save(img_path, "PNG")

    record = {
        "candidate_id": board_id,
        "kind": "assembled_board",
        "specification_id": spec_id,
        "spec_hash": stable_hash(spec),
        "panel_id": "BOARD",
        "status": "CANDIDATE",
        "width": width,
        "height": height,
        "panels_used": used,
        "warnings": warnings,
        "created_at": store.utcnow(),
    }
    (d / f"{board_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record
