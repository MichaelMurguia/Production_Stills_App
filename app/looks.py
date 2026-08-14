"""Board looks — presentation presets for arranged BOARD sheets.

A look is a sheet-level property ({"key", "options"}) that survives every
arrangement commit (set_arrangement replaces blocks, never siblings).
Dress is PURE DERIVATION: dressed() returns an ephemeral sheet — paint
style swapped, bands/columns reserved inside the content area, stored
panel blocks uniformly rescaled into what remains (the arrangement stays
the only layout truth), and a separate `dress` list whose data is
resolved from canon AT DERIVATION TIME (always current, no staleness
bookkeeping). Render, readiness, export and assemble all consume
dressed() — one derivation, no drift (the display_window pattern).

Dress is NOT blocks: the twelve-type canon stays closed, readiness never
judges dress imagery, and _validate never sees it.

User rulings (2026-08-13): annotations are canon-first (a narrative
"polish" verb comes later); looks show in previews and export only —
the arrange room stays the neutral INK working surface.
"""
from __future__ import annotations

import copy

from . import sheet, store, wizard

GAP = 0.015          # breathing space between dress regions
MAX_SWATCHES = 24
MAX_MATERIALS = 8

LOOKS: dict[str, dict] = {
    "ART_BOARD": {
        "label": "Art Board",
        "style": "ART_BOARD",
        "annotations": "hand",
        "options": {
            "palette_strip": {"label": "Palette swatches", "default": True},
            "materials": {"label": "Material callouts", "default": False},
            "atmosphere": {"label": "Atmosphere strip", "default": True},
        },
    },
    "TECH_DESIGN": {
        "label": "Tech Design",
        "style": "TECH_DESIGN",
        "annotations": "callout",
        "options": {
            "spec_table": {"label": "Spec table", "default": True},
            "materials": {"label": "Material chips", "default": True},
            "palette": {"label": "Palette row", "default": True},
            "profile": {"label": "Profile paragraph", "default": False},
        },
    },
}


def catalog() -> list[dict]:
    """The picker's vocabulary: key, label, and option table."""
    return [{"key": k, "label": v["label"],
             "options": {n: {"label": m["label"], "default": m["default"]}
                         for n, m in v["options"].items()}}
            for k, v in LOOKS.items()]


def resolved_options(key: str, options: dict | None) -> dict:
    look = LOOKS[key]
    opts = options or {}
    unknown = sorted(set(opts) - set(look["options"]))
    if unknown:
        raise sheet.SheetError(
            f"{key} has no option: {', '.join(unknown)}")
    return {n: bool(opts.get(n, m["default"]))
            for n, m in look["options"].items()}


def set_look(sheet_id: str, key: str | None, options: dict | None = None) -> dict:
    """Persist (or clear) a board's look. The single validation door."""
    rec = sheet._require(sheet_id)
    if rec.get("archetype") != "BOARD":
        raise sheet.SheetError("a look applies to BOARD sheets only")
    if key is None or key == "":
        rec.pop("look", None)
        return sheet.save_sheet(rec)
    if key not in LOOKS:
        raise sheet.SheetError(
            f"unknown look: {key} (have {', '.join(sorted(LOOKS))})")
    rec["look"] = {"key": key, "options": resolved_options(key, options)}
    return sheet.save_sheet(rec)


# ------------------------------------------------------------ canon pulls

def _swatches() -> list[dict]:
    """Every live swatch across the production's design languages, in
    reference order — {language, name, hex, hero}."""
    live, _dead = wizard.swatches_in_play(None)
    out = []
    for language in live:
        for sw in live[language]:
            out.append({"language": language, "name": sw.get("name", ""),
                        "hex": sw.get("hex", ""),
                        "hero": bool(sw.get("hero"))})
    return out[:MAX_SWATCHES]


def _materials() -> list[dict]:
    out = []
    for r in store.list_references():
        if store.role_head(r.get("role", "")) != "MATERIAL_REFERENCE":
            continue
        if r.get("status") == "REJECTED":
            continue
        label = (r.get("notes") or "").split("·")[0].strip() or r["id"]
        out.append({"id": r["id"], "file": r.get("file", ""),
                    "label": label[:28]})
    return out[:MAX_MATERIALS]


def _atmosphere_text(spec: dict) -> str:
    """Place and hour only — the render intent already reads as the
    masthead tagline, and a board must never say one thing twice
    (user-visible duplication, 2026-08-13)."""
    s = spec.get("setting") or {}
    place = " ".join(x for x in [str(s.get("int_ext", "")).strip(),
                                 str(s.get("location", "")).strip()] if x)
    parts = [p for p in [place, str(s.get("time_of_day", "")).strip().upper()]
             if p]
    return "  ·  ".join(parts)


def _spec_rows(rec: dict, spec: dict) -> list[tuple[str, str]]:
    s = spec.get("setting") or {}
    rows = [
        ("BOARD TYPE", str(spec.get("board_type", "")).upper()),
        ("SETTING", " ".join(x for x in [str(s.get("int_ext", "")),
                                         str(s.get("location", ""))] if x)),
        ("TIME", str(s.get("time_of_day", "")).upper()),
        ("MODE", str(spec.get("mode", ""))),
        ("SIZE", f"{rec['size'][0]} × {rec['size'][1]}"),
    ]
    for p in (spec.get("panels") or [])[:10]:
        rows.append((str(p.get("id", "")),
                     f"{str(p.get('scale', '') or '—')} · "
                     f"{str(p.get('title') or p.get('purpose', ''))[:34]}"))
    return [(k, v) for k, v in rows if v and v.strip(" ·")]


# ------------------------------------------------------------- derivation

def dressed(rec: dict) -> dict:
    """The ephemeral presentation sheet. Identity (deep copy) when the
    sheet has no look — today's pipeline byte-identical.

    Dress is ADDITIVE (corrected 2026-08-13, user: exported panels were
    cropped differently than arranged): the page GROWS to hold the dress
    bands/column and the panel field keeps its exact arranged pixels —
    the original carve-and-rescale warped every slot's aspect, and since
    a crop is framing intent, the display window re-derived differently
    on export than in the room. With additive dress the arranged
    geometry, the crops, and every pixel verdict are identical bare and
    dressed."""
    out = copy.deepcopy(rec or {})
    key = (out.get("look") or {}).get("key")
    if key not in LOOKS:
        return out
    look = LOOKS[key]
    opts = resolved_options(key, (out.get("look") or {}).get("options"))
    spec_id = str(out.get("spec_id") or "")
    # The unit's current truth — a board sheet's spec_id is the BASE, and
    # reading it via get_spec would silently serve R1 (2026-08-13).
    spec = store.resolve_spec_current(spec_id) or {}

    W, H = float(out["size"][0]), float(out["size"][1])
    cwf, chf, _, _ = sheet._content_rect_fracs(out)
    CW, CH = cwf * W, chf * H  # the arranged panel field, in sheet units

    # Resolve the data FIRST — a band with nothing to say claims no page.
    bands: list[tuple[str, float, list[dict]]] = []  # kind, height, elements
    col: list[dict] = []
    col_w = 0.0
    if key == "ART_BOARD":
        sw = _swatches() if opts["palette_strip"] else []
        mats = _materials() if opts["materials"] else []
        if sw and mats:
            bands.append(("PALETTE_BAND", 0.08 * CH, [
                {"kind": "SWATCH_STRIP", "span": (0.0, 0.5 - GAP / 2),
                 "data": {"swatches": sw}},
                {"kind": "MATERIAL_CHIPS", "span": (0.5 + GAP / 2,
                                                    0.5 - GAP / 2),
                 "data": {"refs": mats}}]))
        elif sw:
            bands.append(("PALETTE_BAND", 0.08 * CH, [
                {"kind": "SWATCH_STRIP", "span": (0.0, 1.0),
                 "data": {"swatches": sw}}]))
        elif mats:
            bands.append(("PALETTE_BAND", 0.08 * CH, [
                {"kind": "MATERIAL_CHIPS", "span": (0.0, 1.0),
                 "data": {"refs": mats}}]))
        text = _atmosphere_text(spec) if opts["atmosphere"] else ""
        if text:
            bands.append(("ATMOSPHERE", 0.045 * CH, [
                {"kind": "ATMOSPHERE", "span": (0.0, 1.0),
                 "data": {"text": text}}]))
    elif key == "TECH_DESIGN":
        rows = _spec_rows(out, spec) if opts["spec_table"] else []
        profile = (str(spec.get("scene", "") or "").strip()
                   if opts["profile"] else "")
        if rows or profile:
            col_w = 0.16 * CW
            if rows:
                col.append({"kind": "SPEC_TABLE",
                            "vspan": (0.0, 0.6 if profile else 1.0),
                            "data": {"rows": rows}})
            if profile:
                col.append({"kind": "PROFILE", "vspan": (0.62, 0.38),
                            "data": {"text": profile}})
        mats = _materials() if opts["materials"] else []
        sw = _swatches() if opts["palette"] else []
        if mats and sw:
            bands.append(("TECH_BAND", 0.07 * CH, [
                {"kind": "MATERIAL_CHIPS", "span": (0.0, 0.5 - GAP / 2),
                 "data": {"refs": mats}},
                {"kind": "SWATCH_STRIP", "span": (0.5 + GAP / 2,
                                                  0.5 - GAP / 2),
                 "data": {"swatches": sw, "compact": True}}]))
        elif mats:
            bands.append(("TECH_BAND", 0.07 * CH, [
                {"kind": "MATERIAL_CHIPS", "span": (0.0, 1.0),
                 "data": {"refs": mats}}]))
        elif sw:
            bands.append(("TECH_BAND", 0.07 * CH, [
                {"kind": "SWATCH_STRIP", "span": (0.0, 1.0),
                 "data": {"swatches": sw, "compact": True}}]))

    gap_y = GAP * CH
    gap_x = GAP * CW
    extra_h = sum(h + gap_y for _, h, _ in bands)
    extra_w = (col_w + gap_x) if col_w else 0.0

    out["style"] = look["style"]
    out["dress_annotations"] = look["annotations"]
    out["dress_panel_marks"] = key == "TECH_DESIGN"
    if key == "ART_BOARD":
        tagline = str(spec.get("render_intent", "") or "").strip()
    else:
        tagline = "  ·  ".join(x for x in [spec_id,
                                           str(spec.get("mode", ""))] if x)
    out["dress_masthead"] = {"tagline": tagline}
    if not extra_h and not extra_w:
        out["dress"] = []
        return out

    # Grow the page until the new content rect holds the old panel field
    # plus the dress exactly. The margins mix W- and H-terms, so solve by
    # fixed point — it converges in a few steps and survives any future
    # margin change without a second copy of the constants.
    W2, H2 = W + extra_w, H + extra_h
    for _ in range(6):
        probe = dict(out, size=[W2, H2])
        cw2f, ch2f, _, _ = sheet._content_rect_fracs(probe)
        W2 += (CW + extra_w) - cw2f * W2
        H2 += (CH + extra_h) - ch2f * H2
    if out.get("medium") == "PRINT":
        out["size"] = [round(W2, 2), round(H2, 2)]
    else:
        out["size"] = [int(round(W2)), int(round(H2))]
    cw2f, ch2f, _, _ = sheet._content_rect_fracs(out)
    CW2, CH2 = cw2f * out["size"][0], ch2f * out["size"][1]

    # Panels keep their exact arranged pixels, anchored at the content
    # origin — only the denominators changed.
    sx, sy = CW / CW2, CH / CH2
    for b in out.get("blocks", []):
        f = b["frac"]
        f["x"] = round(f["x"] * sx, 6)
        f["w"] = round(f["w"] * sx, 6)
        f["y"] = round(f["y"] * sy, 6)
        f["h"] = round(f["h"] * sy, 6)

    dress: list[dict] = []
    cursor = CH  # sheet units below the panel field, inside content
    for _kind, h, els in bands:
        cursor += gap_y
        for el in els:
            x0, wf = el["span"]
            dress.append({"kind": el["kind"],
                          "frac": {"x": round(x0 * CW / CW2, 6),
                                   "y": round(cursor / CH2, 6),
                                   "w": round(wf * CW / CW2, 6),
                                   "h": round(h / CH2, 6)},
                          "data": el["data"]})
        cursor += h
    if col_w:
        cx = (CW + gap_x) / CW2
        for el in col:
            y0, hf = el["vspan"]
            dress.append({"kind": el["kind"],
                          "frac": {"x": round(cx, 6), "y": round(y0, 6),
                                   "w": round(col_w / CW2, 6),
                                   "h": round(hf, 6)},
                          "data": el["data"]})
    out["dress"] = dress
    return out
