"""Stage 05 — judging whether a scene's approved panels are ready, and
assembling the board when they are.

Since SHEET_SYSTEM_PLAN a board is a sheet with the BOARD archetype:
the packing functions live in sheet.py (aliased below under their old
names) and the pixels come from sheet_render.render_sheet — one renderer,
so the stage-05 preview, the composer preview and the export cannot
drift. This module keeps what stage 05 is for: slot readiness, the
never-upscale gate, assembly, board records, the spec hash. Its public
signature, AssemblyError cases and /api/specs/{id}/assemble are unchanged;
the letterbox-and-flag fallback is preserved via allow_letterbox=True
(ruling R2 — sheets themselves never letterbox).
"""
from __future__ import annotations

import json

from . import generate, looks, paths, sheet, sheet_render, store

# The packing functions moved to sheet.py (SHEET_SYSTEM_PLAN §2) so boards
# and sheets share one layout implementation. Aliased under their old names
# — geometry and callers unchanged.
from .sheet import (GUTTER, LABEL_H,                 # noqa: F401
                    aspect_rects as _aspect_rects,
                    grid_rects as _grid_rects,
                    layout_rects as _layout_rects)


class AssemblyError(Exception):
    pass


def _arranged_sheet(spec_id: str) -> dict | None:
    """The spec's arranged BOARD sheet, if the user has arranged one.
    Once it exists it IS the board's layout truth (user 2026-08-13):
    the slot map reports it and assembly renders it — the packer only
    speaks for never-arranged boards."""
    if not paths.SHEETS_DIR.exists():
        return None
    for p in sorted(paths.SHEETS_DIR.glob("SH-*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        if (s.get("archetype") == "BOARD" and s.get("spec_id") == spec_id
                and s.get("arrangement")):
            return sheet.get_sheet(s["sheet_id"])
    return None


def _arranged_slot_map(spec_id: str, spec: dict, rec: dict,
                       width: int, height: int) -> dict:
    # The map mirrors the ROOM (corrected 2026-08-13): dress is additive
    # — the dressed page grows around the panel field, panel pixels and
    # verdicts are identical bare and dressed, so the raw arrangement is
    # the honest map and a look never makes the map disagree with the
    # room the user just arranged.
    cwf, chf, cxf, cyf = sheet._content_rect_fracs(rec)
    slots = []
    for b in rec.get("blocks", []):
        bf = b["frac"]
        for s in b.get("slots", []):
            if not s.get("panel_id"):
                continue
            f = s["frac"]
            ax = cxf + (bf["x"] + f["x"] * bf["w"]) * cwf
            ay = cyf + (bf["y"] + f["y"] * bf["h"]) * chf
            aw = f["w"] * bf["w"] * cwf
            ah = f["h"] * bf["h"] * chf
            cand_id = s.get("candidate_id")
            cand = generate.get_candidate(spec_id, cand_id) if cand_id else None
            have = ((int(cand.get("width") or 0), int(cand.get("height") or 0))
                    if cand else (0, 0))
            if not cand:
                status = "NO_CANDIDATE"
            elif cand.get("status") != "APPROVED":
                status = "UNAPPROVED"
            else:
                shown, need = sheet.shown_pixels(rec, b, s, have)
                status = ("TOO_SMALL" if (shown[0] + 1 < need[0]
                                          or shown[1] + 1 < need[1]) else "OK")
            panel = next((p for p in spec.get("panels", [])
                          if p.get("id") == s["panel_id"]), {})
            slots.append({
                "panel_id": s["panel_id"],
                "title": panel.get("title") or panel.get("purpose", ""),
                "x": ax, "y": ay, "w": aw, "h": ah,
                "slot_width": int(aw * width),
                "slot_height": int(ah * height),
                "status": status,
                "candidate_id": cand_id,
                "candidate_width": have[0] or None,
                "candidate_height": have[1] or None,
                "allocation_percent": None,
            })
    not_ready = [s for s in slots if s["status"] != "OK"]
    return {
        "spec_id": spec_id,
        "canvas": {"width": width, "height": height},
        "locked": store.spec_locked(spec_id),
        "board_type": str(spec.get("board_type") or "LOCATION").upper(),
        "layout_variant": "arranged",
        "derived_strip": [],
        "slots": slots,
        "ready": not not_ready,
        "assemblable": all(s["status"] in ("OK", "TOO_SMALL") for s in slots),
        "not_ready": [{"panel_id": s["panel_id"], "status": s["status"]}
                      for s in not_ready],
    }


def _assemble_arranged(spec_id: str, spec: dict, rec: dict,
                       width: int, height: int) -> dict:
    from common import stable_hash

    look = rec.get("look")
    # Dress is additive: the panel field keeps the requested width×height
    # exactly, and a look extends the page around it — so the dressed
    # sheet derives from a probe at the REQUESTED canvas, and the artifact
    # dims are whatever the dressed page came to.
    probe = dict(rec, size=[width, height], size_source="CHOSEN")
    view = looks.dressed(probe)
    # Gate at the sheet's own size, as always (the letterbox contract
    # allows smaller renders); additive dress makes dressed and bare
    # verdicts identical, so the raw record is the same gate.
    gate = sheet.readiness(rec)
    if not gate["ready"]:
        raise AssemblyError(
            "the arranged board blocks assembly: "
            + "; ".join(f"{e['kind']} {e.get('slot_id', '')}".strip()
                        for e in gate["blocked"]))
    warnings: list[str] = []
    board = sheet_render.render_sheet(view, 1.0, allow_letterbox=True,
                                      warnings=warnings)
    used: dict[str, str] = {}
    rects: dict[str, list[float]] = {}
    out_w, out_h = board.width, board.height
    cwf, chf, cxf, cyf = sheet._content_rect_fracs(view)
    for b in view.get("blocks", []):
        bf = b["frac"]
        for s in b.get("slots", []):
            if not (s.get("panel_id") and s.get("candidate_id")):
                continue
            used[s["panel_id"]] = s["candidate_id"]
            f = s["frac"]
            rects[s["panel_id"]] = [
                (cxf + (bf["x"] + f["x"] * bf["w"]) * cwf) * out_w,
                (cyf + (bf["y"] + f["y"] * bf["h"]) * chf) * out_h,
                f["w"] * bf["w"] * cwf * out_w,
                f["h"] * bf["h"] * chf * out_h,
            ]
    board_id = store.next_counter("board_counter", "BOARD")
    d = paths.BOARDS_DIR / spec_id
    d.mkdir(parents=True, exist_ok=True)
    board.save(d / f"{board_id}.png", "PNG")
    record = {
        "candidate_id": board_id,
        "kind": "assembled_board",
        "specification_id": spec_id,
        "spec_hash": stable_hash(spec),
        "panel_id": "BOARD",
        "status": "CANDIDATE",
        "width": out_w,
        "height": out_h,
        "layout_variant": "arranged",
        "look": look,
        "panels_used": used,
        "rects": rects,
        "warnings": warnings,
        "created_at": store.utcnow(),
    }
    (d / f"{board_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return record


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


def check_variant(spec: dict, variant: str | None) -> str:
    """Layout variants are presentation grammar (director's 2026-07-29
    ruling): they rearrange how approved work hangs on the canvas and are
    recorded on the board record — the spec is never touched. 'aspect'
    (the default since 2026-07-31) lays slots out at the takes' own aspect
    ratios; 'allocation' is the sheet-allocation hero grammar that was the
    old default; 'grid' is the equal-comparison grammar; 'hero:<panel>'
    leads with that panel."""
    v = (variant or "default").strip()
    if v == "default":
        return "aspect"
    if v in ("aspect", "allocation", "grid"):
        return v
    if v.startswith("hero:"):
        pid = v[5:]
        if any(p.get("id") == pid for p in spec.get("panels", [])):
            return v
        raise AssemblyError(f"unknown hero panel: {pid}")
    raise AssemblyError(f"unknown layout variant: {v}")


def check_canvas(width: int, height: int) -> None:
    """Stated bounds on the board canvas. Unchecked query values once
    allowed a 60000×60000 (~10 GB) allocation — and tiny heights make the
    aspect solver find no feasible row partition at all."""
    if not (1024 <= width <= 8192 and 576 <= height <= 8192):
        raise AssemblyError(
            f"canvas {width}×{height} is out of range — width 1024–8192, "
            "height 576–8192.")


def _variant_rects(spec: dict, alloc: dict[str, float],
                   aspects: dict[str, float], variant: str,
                   x0: int, y0: int, w: int,
                   h: int) -> dict[str, tuple[int, int, int, int]]:
    panels = spec.get("panels", [])
    btype = str(spec.get("board_type") or "LOCATION").upper()
    if btype == "LIGHTING_STUDY" or variant == "grid":
        return _grid_rects(panels, x0, y0, w, h)
    if variant == "aspect":
        # The aspect solver scores every contiguous row partition —
        # 2^(n-1) of them. Past a dozen panels that's the dashboard's hot
        # path stalling for seconds; the grid is the honest fallback.
        if len(panels) > 12:
            return _grid_rects(panels, x0, y0, w, h)
        return _aspect_rects(panels, aspects, x0, y0, w, h)
    hero_id = variant[5:] if variant.startswith("hero:") else None
    return _layout_rects(panels, alloc, x0, y0, w, h, hero_id)


def _board_frame(spec: dict, spec_id: str, width: int,
                 height: int) -> tuple[dict, tuple[int, int, int, int]]:
    """The ephemeral BOARD sheet every stage-05 surface measures against,
    and its content rect — sheet_render.content_rect is the single
    geometry authority, so preview and board never drift."""
    eph = {"sheet_id": "", "archetype": "BOARD", "style": sheet.BOARD_STYLE,
           "medium": "SCREEN", "size": [width, height],
           "size_source": "CHOSEN", "spine": False,
           "masthead": {"title": str(spec.get("subject", spec_id)),
                        "subject": "", "binding": None},
           "blocks": []}
    return eph, sheet_render.content_rect(eph, width, height)


def slot_map(spec_id: str, width: int = 3840, height: int = 2160,
             variant: str | None = None) -> dict:
    """The board's slot geometry BEFORE any pixels are spent, with a verdict
    per slot: OK, UNAPPROVED (candidates but none approved), TOO_SMALL
    (approved render smaller than its slot in both dimensions — it would
    need upscaling, which never happens), NO_CANDIDATE. Mirrors
    assemble_board's exact geometry so the preview is honest."""
    check_canvas(width, height)
    spec = store.get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    # An arranged board IS the layout truth — the map reports it, with
    # verdicts judged the way the renderer will draw it.
    arranged = _arranged_sheet(spec_id)
    if arranged is not None:
        return _arranged_slot_map(spec_id, spec, arranged, width, height)
    variant = check_variant(spec, variant)

    approved = _latest_approved_by_panel(spec_id)
    have: dict[str, dict] = {}
    for c in generate.list_candidates(spec_id):
        if c.get("candidate_id", "").startswith("CAND-"):
            have[c["panel_id"]] = c

    alloc = {lp["id"]: float(lp.get("allocation_percent", 0))
             for lp in spec.get("layout", {}).get("panels", [])}
    # The aspect variant reads each panel's take geometry — approved take
    # first, else the latest take, else 16:9 until one exists.
    aspects = {pid: int(c["width"]) / int(c["height"])
               for pid, c in {**have, **approved}.items()
               if int(c.get("width") or 0) and int(c.get("height") or 0)}

    _eph, (inner_x, inner_y, inner_w, inner_h) = _board_frame(
        spec, spec_id, width, height)
    derived = [pid for pid in ("MATERIALS", "PALETTE") if pid in approved]
    if derived:
        inner_h -= max(220, int(inner_h * 0.16)) + GUTTER

    btype = str(spec.get("board_type") or "LOCATION").upper()
    panels = spec.get("panels", [])
    rects = _variant_rects(spec, alloc, aspects, variant,
                           inner_x, inner_y, inner_w, inner_h)

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
            # Cover-crop policy: filling the slot needs BOTH dimensions at
            # native size — a shortfall in either means letterboxing.
            status = "TOO_SMALL" if (cw < rw or ch < img_h) else "OK"
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
        "layout_variant": variant,
        "derived_strip": derived,
        "slots": slots,
        "ready": not not_ready,
        "assemblable": all(s["status"] in ("OK", "TOO_SMALL") for s in slots),
        "not_ready": [{"panel_id": s["panel_id"], "status": s["status"]}
                      for s in not_ready],
    }


def assemble_board(spec_id: str, width: int = 3840, height: int = 2160,
                   variant: str | None = None) -> dict:
    from common import stable_hash

    check_canvas(width, height)
    spec = store.get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    if not store.spec_locked(spec_id):
        raise AssemblyError(f"{spec_id} is not approved; only locked specs can assemble.")
    # An arranged board assembles AS ARRANGED (user 2026-08-13): the
    # sheet renders at the requested canvas — fractional geometry makes
    # the size free — gated on the sheet's own readiness (which covers
    # pixels and approval; deliberately benched panels don't block).
    arranged = _arranged_sheet(spec_id)
    if arranged is not None:
        return _assemble_arranged(spec_id, spec, arranged, width, height)
    variant = check_variant(spec, variant)

    approved = _latest_approved_by_panel(spec_id)
    missing = [p["id"] for p in spec.get("panels", []) if p["id"] not in approved]
    if missing:
        raise AssemblyError(
            "every panel needs an APPROVED candidate before assembly; missing: "
            + ", ".join(missing))

    alloc = {lp["id"]: float(lp.get("allocation_percent", 0))
             for lp in spec.get("layout", {}).get("panels", [])}
    aspects = {pid: int(c["width"]) / int(c["height"])
               for pid, c in approved.items()
               if int(c.get("width") or 0) and int(c.get("height") or 0)}

    eph, (cx, cy, cw, ch) = _board_frame(spec, spec_id, width, height)
    sub = "  ·  ".join(x for x in [
        _slug(spec), spec_id, str(spec.get("mode", "")),
        "BOARD CANDIDATE — UNAPPROVED"] if x)
    eph["masthead"]["subject"] = sub

    # Approved derived strips (palette / materials) reserve a bottom band.
    derived = [(pid, approved[pid]) for pid in ("MATERIALS", "PALETTE")
               if pid in approved]
    inner_h = ch
    strip_h = 0
    if derived:
        strip_h = max(220, int(inner_h * 0.16))
        inner_h -= strip_h + GUTTER

    rects = _variant_rects(spec, alloc, aspects, variant, cx, cy, cw, inner_h)

    # The board as a sheet: one layout block carrying every panel slot at
    # its packed rect, plus the derived band. Fractions are derived from
    # the same rects the record states, so the click-through frames and
    # the pixels agree.
    used: dict[str, str] = {}
    main = {"block_id": "B-0001", "type": "GRID", "heading": None,
            "caption": None,
            "frac": {"x": 0.0, "y": 0.0, "w": 1.0, "h": inner_h / ch},
            "slots": []}
    for panel in spec["panels"]:
        pid = panel["id"]
        cand = approved[pid]
        used[pid] = cand["candidate_id"]
        if generate.candidate_image_path(spec_id, cand["candidate_id"]) is None:
            raise AssemblyError(f"image file missing for {cand['candidate_id']}")
        rx, ry, rw, rh = rects[pid]
        main["slots"].append({
            "slot_id": f"S{len(main['slots']) + 1}",
            "spec_id": spec_id, "candidate_id": cand["candidate_id"],
            "panel_id": pid,
            "label": f"{pid} — {panel.get('title') or panel.get('purpose', '')}",
            "frac": {"x": (rx - cx) / cw, "y": (ry - cy) / inner_h,
                     "w": rw / cw, "h": rh / inner_h},
            "crop": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "rotate": 0.0},
            "annotation": None})
    eph["blocks"].append(main)

    if derived:
        strip_labels = {
            "MATERIALS": "MATERIALS — DERIVED FROM APPROVED PANELS",
            "PALETTE": "PALETTE — SAMPLED FROM APPROVED PANELS",
        }
        sy = cy + inner_h + GUTTER
        strip = {"block_id": "B-0002", "type": "STRIP", "heading": None,
                 "caption": None,
                 "frac": {"x": 0.0, "y": (sy - cy) / ch, "w": 1.0,
                          "h": strip_h / ch},
                 "slots": []}
        n = len(derived)
        for i, (pid, cand) in enumerate(derived):
            used[pid] = cand["candidate_id"]
            strip["slots"].append({
                "slot_id": f"S{i + 1}",
                "spec_id": spec_id, "candidate_id": cand["candidate_id"],
                "panel_id": pid, "label": strip_labels.get(pid, pid),
                "frac": {"x": i / n, "y": 0.0,
                         "w": 1 / n - (0.012 if n > 1 else 0), "h": 1.0},
                "crop": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0,
                         "rotate": 0.0},
                "annotation": None})
        eph["blocks"].append(strip)

    warnings: list[str] = []
    board = sheet_render.render_sheet(eph, 1.0, allow_letterbox=True,
                                      warnings=warnings)

    board_id = store.next_counter("board_counter", "BOARD")

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
        "layout_variant": variant,
        "panels_used": used,
        # The structural layout (user ruling 2026-08-02): the board page
        # keeps panels as individual images in these frames — click-through
        # to the uncropped take — and the composite PNG becomes the export.
        "rects": {pid: list(r) for pid, r in rects.items()},
        "warnings": warnings,
        "created_at": store.utcnow(),
    }
    (d / f"{board_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record
