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

GAP = 0.015          # breathing space between reserved dress regions
MAX_RESERVED = 0.35  # dress may never eat more than a third of the board
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
    s = spec.get("setting") or {}
    place = " ".join(x for x in [str(s.get("int_ext", "")).strip(),
                                 str(s.get("location", "")).strip()] if x)
    parts = [p for p in [place, str(s.get("time_of_day", "")).strip().upper(),
                         str(spec.get("render_intent", "")).strip()] if p]
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
    sheet has no look — today's pipeline byte-identical."""
    out = copy.deepcopy(rec or {})
    key = (out.get("look") or {}).get("key")
    if key not in LOOKS:
        return out
    look = LOOKS[key]
    opts = resolved_options(key, (out.get("look") or {}).get("options"))
    spec_id = str(out.get("spec_id") or "")
    spec = store.get_spec(spec_id) or {}

    bands: list[tuple[str, float]] = []
    col_w = 0.0
    if key == "ART_BOARD":
        if opts["palette_strip"] or opts["materials"]:
            bands.append(("PALETTE_BAND", 0.08))
        if opts["atmosphere"]:
            bands.append(("ATMOSPHERE", 0.045))
    elif key == "TECH_DESIGN":
        if opts["spec_table"] or opts["profile"]:
            col_w = 0.16
        if opts["materials"] or opts["palette"]:
            bands.append(("TECH_BAND", 0.07))

    reserved = min(sum(h for _, h in bands) + GAP * len(bands), MAX_RESERVED)
    keep_w = 1.0 - (col_w + GAP if col_w else 0.0)
    keep_h = 1.0 - reserved

    for b in out.get("blocks", []):
        f = b["frac"]
        f["x"] = round(f["x"] * keep_w, 4)
        f["w"] = round(f["w"] * keep_w, 4)
        f["y"] = round(f["y"] * keep_h, 4)
        f["h"] = round(f["h"] * keep_h, 4)

    dress: list[dict] = []
    cursor = keep_h
    for kind, h in bands:
        cursor += GAP
        frac = {"x": 0.0, "y": round(cursor, 4),
                "w": round(keep_w, 4), "h": round(h, 4)}
        cursor += h
        if kind == "PALETTE_BAND":
            sw = _swatches() if opts.get("palette_strip") else []
            mats = _materials() if opts.get("materials") else []
            if sw and mats:
                half = round(keep_w / 2 - GAP / 2, 4)
                dress.append({"kind": "SWATCH_STRIP",
                              "frac": {**frac, "w": half},
                              "data": {"swatches": sw}})
                dress.append({"kind": "MATERIAL_CHIPS",
                              "frac": {**frac, "x": round(half + GAP, 4),
                                       "w": half},
                              "data": {"refs": mats}})
            elif sw:
                dress.append({"kind": "SWATCH_STRIP", "frac": frac,
                              "data": {"swatches": sw}})
            elif mats:
                dress.append({"kind": "MATERIAL_CHIPS", "frac": frac,
                              "data": {"refs": mats}})
        elif kind == "ATMOSPHERE":
            text = _atmosphere_text(spec)
            if text:
                dress.append({"kind": "ATMOSPHERE", "frac": frac,
                              "data": {"text": text}})
        elif kind == "TECH_BAND":
            mats = _materials() if opts.get("materials") else []
            sw = _swatches() if opts.get("palette") else []
            if mats and sw:
                half = round(keep_w / 2 - GAP / 2, 4)
                dress.append({"kind": "MATERIAL_CHIPS",
                              "frac": {**frac, "w": half},
                              "data": {"refs": mats}})
                dress.append({"kind": "SWATCH_STRIP",
                              "frac": {**frac, "x": round(half + GAP, 4),
                                       "w": half},
                              "data": {"swatches": sw, "compact": True}})
            elif mats:
                dress.append({"kind": "MATERIAL_CHIPS", "frac": frac,
                              "data": {"refs": mats}})
            elif sw:
                dress.append({"kind": "SWATCH_STRIP", "frac": frac,
                              "data": {"swatches": sw, "compact": True}})

    if col_w:
        cx = round(keep_w + GAP, 4)
        table_h = 0.6 if opts.get("profile") else 1.0
        if opts.get("spec_table"):
            dress.append({"kind": "SPEC_TABLE",
                          "frac": {"x": cx, "y": 0.0, "w": col_w,
                                   "h": round(table_h, 4)},
                          "data": {"rows": _spec_rows(out, spec)}})
        if opts.get("profile"):
            profile = str(spec.get("scene", "") or "").strip()
            if profile:
                dress.append({"kind": "PROFILE",
                              "frac": {"x": cx, "y": 0.62, "w": col_w,
                                       "h": 0.38},
                              "data": {"text": profile}})

    out["style"] = look["style"]
    out["dress"] = dress
    out["dress_annotations"] = look["annotations"]
    out["dress_panel_marks"] = key == "TECH_DESIGN"
    if key == "ART_BOARD":
        tagline = str(spec.get("render_intent", "") or "").strip()
    else:
        tagline = "  ·  ".join(x for x in [spec_id,
                                           str(spec.get("mode", ""))] if x)
    out["dress_masthead"] = {"tagline": tagline}
    return out
