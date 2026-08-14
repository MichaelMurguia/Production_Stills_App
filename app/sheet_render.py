"""One renderer for preview and export (SHEET_SYSTEM_PLAN §10).

render_sheet serves the composer preview at a small scale and the export at
full scale, so preview and output cannot drift. All type comes from
caption_frac × pixel width — no constants. Images cover-crop exactly as the
board always has; **no upscaling, ever**. A sheet does not letterbox as a
fallback (export is gated on pixels first, so a shortfall here raises) —
the one exception is the stage-05 assemble path, which keeps its shipped
letterbox-and-flag contract via allow_letterbox=True (ruling R2).

Style ink lives here (and under .sheet[data-style] in CSS for the DOM
shell), never in :root — sheet ink is not an app token (plan §4).
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import generate, paths, sheet as sheet_mod, store

PRINT_DPI = sheet_mod.PRINT_DPI

# Masthead type as fractions of sheet width (authored at the 1360 mocks).
TITLE_FRAC = 0.025
SUB_FRAC = 0.00885
FOOTER_FRAC = 0.00625


class RenderShortfall(sheet_mod.SheetError):
    """A slot could not be filled without upscaling. Export is gated on
    pixels before rendering, so reaching this outside the board's
    letterbox path is a bug — it raises rather than degrading silently."""


# ------------------------------------------------------------------- styles
# A style declares surface, edge and voice — never layout, size or content
# (§4). INK is the boards' style (R6): matted panels on a near-black ground;
# its ground deliberately replaces the old warm charcoal #2a2723.

STYLE_INK: dict[str, dict] = {
    "GALLERY": {"paper": (239, 233, 221), "inset": (228, 221, 208),
                "ink": (31, 29, 25), "dim": (110, 105, 96),
                "edge": "matted", "voice": "serif", "accent": None},
    "CONTACT": {"paper": (23, 24, 26), "inset": None,
                "ink": (232, 229, 221), "dim": (150, 148, 140),
                "edge": "flush", "voice": "mono", "accent": None,
                "keyline": (60, 62, 66)},
    "NEWSPRINT": {"paper": (217, 212, 200), "inset": None,
                  "ink": (26, 24, 20), "dim": (100, 96, 88),
                  "edge": "bleed", "voice": "slab", "accent": None},
    "BLUEPRINT": {"paper": (28, 79, 124), "inset": None,
                  "ink": (238, 243, 248), "dim": (170, 190, 210),
                  "edge": "flush", "voice": "mono", "accent": None,
                  "keyline": (238, 243, 248), "grid": (44, 96, 142)},
    "PLATE": {"paper": (251, 251, 249), "inset": None,
              "ink": (30, 30, 28), "dim": (120, 118, 112),
              "edge": "flush", "voice": "sans", "accent": None},
    "INK": {"paper": (19, 20, 24), "inset": (226, 221, 208),
            "ink": (232, 229, 221), "dim": (154, 151, 143),
            "edge": "matted", "voice": "mono",
            "accent": (216, 162, 74), "mat": (52, 48, 43)},
    # Look styles (2026-08-13): rendered by ephemeral dressed() sheets
    # only — deliberately NOT in sheet.STYLES, so no stored sheet can
    # adopt them. Ink values are design-review parameters (defaults).
    "ART_BOARD": {"paper": (236, 228, 210), "ink": (40, 34, 26),
                  "dim": (122, 110, 92), "edge": "matted",
                  "mat": (222, 212, 192), "voice": "serif",
                  "accent": (166, 118, 58), "hand_ink": (58, 48, 92)},
    "TECH_DESIGN": {"paper": (16, 18, 22), "ink": (226, 230, 235),
                    "dim": (128, 136, 146), "edge": "flush",
                    "keyline": (70, 78, 88), "voice": "mono",
                    "accent": (94, 160, 208), "grid": (26, 30, 36)},
}

# Bundled OFL faces render FIRST (app/fonts/, license beside each) so
# typography is identical on every install — the old Windows-only paths
# meant Linux tenants silently fell back to PIL's default bitmap font
# (found 2026-08-13). Windows paths remain as a fallback for stripped
# checkouts; load_default() is the last resort. "hand" is the Art Board
# annotation voice (Caveat) — sheet-render typography, not app chrome.
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_VOICES = {
    "serif": [str(_FONTS_DIR / "ebgaramond" / "EBGaramond.ttf"),
              "C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/times.ttf"],
    "mono": [str(_FONTS_DIR / "ibmplexmono" / "IBMPlexMono-Regular.ttf"),
             "C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"],
    "slab": [str(_FONTS_DIR / "zillaslab" / "ZillaSlab-Regular.ttf"),
             "C:/Windows/Fonts/rockb.ttf", "C:/Windows/Fonts/bahnschrift.ttf"],
    "sans": [str(_FONTS_DIR / "inter" / "Inter.ttf"),
             "C:/Windows/Fonts/bahnschrift.ttf",
             "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"],
    "hand": [str(_FONTS_DIR / "caveat" / "Caveat.ttf"),
             "C:/Windows/Fonts/segoepr.ttf"],
}
_SANS_BOLD = [str(_FONTS_DIR / "inter" / "Inter.ttf"),
              "C:/Windows/Fonts/bahnschrift.ttf",
              "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]


def _font(voice: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _VOICES.get(voice, []) + _SANS_BOLD:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, max(6, int(size)))
            except OSError:
                continue
    return ImageFont.load_default()


def _mat_color(style: dict) -> tuple:
    """The panel mat behind an image on a matted style; a hair off the
    paper on flush styles so an unfilled area still reads as a surface."""
    if style.get("mat"):
        return style["mat"]
    p = style["paper"]
    delta = -8 if sum(p) > 380 else 12
    return tuple(max(0, min(255, c + delta)) for c in p)


# ----------------------------------------------------------------- geometry

def pixel_size(sheet: dict, scale: float = 1.0) -> tuple[int, int]:
    w, h = sheet["size"]
    if sheet["medium"] == "PRINT":
        return (int(round(w * PRINT_DPI * scale)),
                int(round(h * PRINT_DPI * scale)))
    return (int(round(w * scale)), int(round(h * scale)))


def content_rect(sheet: dict, W: int, H: int) -> tuple[int, int, int, int]:
    """The block area in px — the single geometry authority: slot_map and
    assemble_board use this too, so the stage-05 preview stays honest."""
    cw, ch, cx, cy = sheet_mod._content_rect_fracs(sheet)
    return (int(cx * W), int(cy * H), int(cw * W), int(ch * H))


def _floor_px(sheet: dict, W: int) -> float:
    L = sheet_mod.LADDERS[sheet["medium"]]
    nominal = (sheet["size"][0] * PRINT_DPI if sheet["medium"] == "PRINT"
               else sheet["size"][0])
    scale = W / max(1, nominal)
    if sheet["medium"] == "PRINT":
        return L["floor"] / 72.0 * PRINT_DPI * scale
    return L["floor"] * scale


def _type_px(sheet: dict, block: dict | None, frac: float, W: int) -> int:
    """frac × width, elastic blocks growing to the floor (R1)."""
    size = frac * W
    if block is not None and sheet_mod.BLOCK_TYPES[block["type"]].elastic:
        size = max(size, _floor_px(sheet, W))
    return max(6, int(round(size)))


# ------------------------------------------------------------ image placing

def _prepare_source(img_path: Path, crop: dict | None,
                    aspect: float | None = None) -> Image.Image:
    im = Image.open(img_path).convert("RGB")
    c = crop or {}
    rot = float(c.get("rotate", 0.0) or 0.0)
    if rot:
        # The frame never rotates — the image rotates inside it; the fill
        # this needs is charged to the crop budget like any other zoom.
        im = im.rotate(-rot, resample=Image.BICUBIC, expand=True)
    if aspect:
        # The crop is framing intent (2026-08-13): draw the slot-aspect
        # window derived from it — the same window readiness judged.
        c = sheet_mod.display_window(c, aspect, im.width, im.height)
    x = float(c.get("x", 0.0)); y = float(c.get("y", 0.0))
    w = float(c.get("w", 1.0)); h = float(c.get("h", 1.0))
    if (x, y, w, h) != (0.0, 0.0, 1.0, 1.0):
        box = (int(x * im.width), int(y * im.height),
               max(int(x * im.width) + 1, int((x + w) * im.width)),
               max(int(y * im.height) + 1, int((y + h) * im.height)))
        im = im.crop(box)
    return im


def _place_image(canvas: Image.Image, draw: ImageDraw.ImageDraw,
                 img_path: Path, rect: tuple[int, int, int, int],
                 crop: dict | None, style: dict, allow_letterbox: bool,
                 warnings: list[str], label: str, cand_id: str) -> None:
    rx, ry, rw, rh = rect
    draw.rectangle([rx, ry, rx + rw - 1, ry + rh - 1], fill=_mat_color(style))
    if style.get("keyline"):
        draw.rectangle([rx, ry, rx + rw - 1, ry + rh - 1],
                       outline=style["keyline"], width=1)
    with _prepare_source(img_path, crop, rw / max(rh, 1)) as im:
        orig_w, orig_h = im.size
        # Cover-crop: scale DOWN to cover the slot, crop the overflow,
        # center. No upscaling, ever.
        cover = max(rw / im.width, rh / im.height)
        if cover <= 1.0:
            nw = max(rw, round(im.width * cover))
            nh = max(rh, round(im.height * cover))
            im = im.resize((nw, nh), Image.LANCZOS)
            left = (nw - rw) // 2
            top = (nh - rh) // 2
            im = im.crop((left, top, left + rw, top + rh))
        elif allow_letterbox:
            fit = min(rw / im.width, rh / im.height, 1.0)
            if fit < 1.0:
                im = im.resize((max(1, int(im.width * fit)),
                                max(1, int(im.height * fit))), Image.LANCZOS)
            warnings.append(
                f"{label}: {cand_id} ({orig_w}x{orig_h}) cannot fill "
                f"its {rw}x{rh} slot without upscaling — letterboxed; "
                "regenerate at a larger size for full quality")
        else:
            raise RenderShortfall(
                f"{label or cand_id}: {orig_w}x{orig_h} cannot fill its "
                f"{rw}x{rh} slot without upscaling — export is gated on "
                "pixels, so reaching render this short is a bug")
        ox = rx + (rw - im.width) // 2
        oy = ry + (rh - im.height) // 2
        canvas.paste(im, (ox, oy))


# ------------------------------------------------------------ block drawing

def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines: list[str] = []
    for raw in str(text).splitlines():
        words, cur = raw.split(), ""
        if not words:
            lines.append("")
        for wd in words:
            probe = (cur + " " + wd).strip()
            if draw.textlength(probe, font=font) <= max_w or not cur:
                cur = probe
            else:
                lines.append(cur)
                cur = wd
        if words:
            lines.append(cur)
    return lines


def _draw_text_block(draw, sheet, block, rect, style, W) -> None:
    """Elastic evidence (SPEC / PRINCIPLES) and any prose: heading line in
    ink, body in dim, at max(frac × width, floor)."""
    rx, ry, rw, rh = rect
    size = _type_px(sheet, block, sheet_mod.BLOCK_TYPES[block["type"]].frac, W)
    head_f = _font("mono", int(size * 0.85))
    body_f = _font(style["voice"], size)
    y = ry
    heading = (block.get("heading") or {}).get("text", "")
    if heading:
        draw.text((rx, y), heading.upper(), font=head_f, fill=style["dim"])
        y += int(size * 1.7)
    body = (block.get("caption") or {}).get("text", "")
    for line in _wrap(draw, body, body_f, rw):
        if y > ry + rh - size:
            break
        draw.text((rx, y), line, font=body_f, fill=style["ink"])
        y += int(size * 1.55)


def _draw_palette_block(draw, sheet, block, rect, style, W) -> None:
    """A palette group as ramps: the resolved binding's ordered swatches —
    the order is the ruling; a sheet may not reorder them."""
    rx, ry, rw, rh = rect
    size = _type_px(sheet, block, sheet_mod.BLOCK_TYPES["PALETTE"].frac, W)
    label_f = _font("mono", int(size * 0.85))
    text = (block.get("caption") or {}).get("text", "")
    lines = [l for l in text.splitlines() if l.strip()]
    y = ry
    if lines:
        draw.text((rx, y), lines[0].upper(), font=label_f, fill=style["dim"])
        y += int(size * 1.8)
    swatches = []
    for line in lines[1:]:
        part = line.split(None, 1)
        if part and part[0].startswith("#") and len(part[0]) == 7:
            try:
                hx = part[0][1:]
                swatches.append(((int(hx[0:2], 16), int(hx[2:4], 16),
                                  int(hx[4:6], 16)),
                                 part[1] if len(part) > 1 else ""))
            except ValueError:
                continue
    if not swatches:
        return
    cell_h = max(8, int(size * 1.6))
    cell_w = rw // len(swatches)
    for i, (rgb, _name) in enumerate(swatches):
        draw.rectangle([rx + i * cell_w, y,
                        rx + (i + 1) * cell_w - 2, y + cell_h], fill=rgb)


def _draw_slot_block(canvas, draw, sheet, block, rect, style, W,
                     allow_letterbox, warnings, annotations,
                     manifest: list | None = None,
                     image_tier: str = "full") -> None:
    rx, ry, rw, rh = rect
    cap_frac = sheet_mod.BLOCK_TYPES[block["type"]].frac
    cap_px = _type_px(sheet, None, cap_frac, W)
    head_f = _font("mono", cap_px)
    cap_f = _font(style["voice"], cap_px)
    y = ry
    heading = (block.get("heading") or {}).get("text", "")
    if heading:
        draw.text((rx, y), heading.splitlines()[0].upper(), font=head_f,
                  fill=style["ink"])
        y += int(cap_px * 1.9)
    caption = (block.get("caption") or {}).get("text", "")
    cap_lines = _wrap(draw, caption, cap_f, rw)[:4] if caption else []
    cap_h = int(len(cap_lines) * cap_px * 1.55) + (int(cap_px * 0.8)
                                                   if cap_lines else 0)
    inner_h = rh - (y - ry) - cap_h
    inset = (style.get("inset") if block["type"] in ("ORTHO", "SPEC")
             else None)
    if inset:
        draw.rectangle([rx, y, rx + rw - 1, y + inner_h - 1], fill=inset)

    # Geometry is computed once and declared (canon pass R2): the drawer
    # emits the rects it drew; the composer overlay consumes them and
    # measures nothing. `image` is the slot band the slot fracs address —
    # its origin/size invert a dragged rect back to a model frac exactly.
    entry = None
    if manifest is not None:
        entry = {"block_id": block["block_id"], "type": block["type"],
                 "outer": [rx, ry, rw, rh],
                 "image": [rx, y, rw, inner_h], "slots": []}
        manifest.append(entry)

    label_px = cap_px
    for s in block.get("slots", []):
        f = s["frac"]
        sx = rx + int(f["x"] * rw)
        sy = y + int(f["y"] * inner_h)
        sw_ = max(1, int(f["w"] * rw))
        sh_ = max(1, int(f["h"] * inner_h))
        if entry is not None:
            entry["slots"].append({"slot_id": s["slot_id"],
                                   "rect": [sx, sy, sw_, sh_],
                                   "filled": bool(s.get("candidate_id"))})
        label = str(s.get("label") or "")
        band = int(label_px * 1.5) + 8 if label else 0
        img_h = max(1, sh_ - band)
        img_path = None
        if s.get("candidate_id") and s.get("spec_id"):
            if image_tier != "full":
                # Preview-scale renders read display derivatives (md) —
                # export and assemble always render from the source.
                img_path = generate.candidate_variant_path(
                    s["spec_id"], s["candidate_id"], image_tier)
            else:
                img_path = generate.candidate_image_path(s["spec_id"],
                                                         s["candidate_id"])
        if img_path:
            _place_image(canvas, draw, img_path, (sx, sy, sw_, img_h),
                         s.get("crop"), style, allow_letterbox, warnings,
                         label or s.get("panel_id") or s["slot_id"],
                         s["candidate_id"])
        else:
            draw.rectangle([sx, sy, sx + sw_ - 1, sy + img_h - 1],
                           fill=_mat_color(style))
        if label:
            draw.text((sx, sy + img_h + 6), label.upper(),
                      font=cap_f, fill=style["ink"])
        # Tech Design panel marks: keyline + corner registration ticks +
        # panel id — presentation only, the fracs never move.
        if sheet.get("dress_panel_marks"):
            line = style.get("keyline") or style["dim"]
            draw.rectangle([sx, sy, sx + sw_ - 1, sy + img_h - 1],
                           outline=line, width=1)
            tick = max(6, W // 300)
            for tx, ty, dx, dy in ((sx, sy, 1, 1), (sx + sw_ - 1, sy, -1, 1),
                                   (sx, sy + img_h - 1, 1, -1),
                                   (sx + sw_ - 1, sy + img_h - 1, -1, -1)):
                draw.line([(tx, ty), (tx + dx * tick, ty)], fill=line, width=1)
                draw.line([(tx, ty), (tx, ty + dy * tick)], fill=line, width=1)
            pid = str(s.get("panel_id") or "")
            if pid:
                pf = _font("mono", max(7, int(cap_px * 0.8)))
                pw_ = draw.textlength(pid.upper(), font=pf)
                draw.text((sx + sw_ - pw_ - 6, sy + 5), pid.upper(),
                          font=pf, fill=style["ink"])
        ann = s.get("annotation")
        mode = sheet.get("dress_annotations")
        if ann and mode == "hand" and str(ann.get("text") or "").strip():
            # Art Board hand notes: the annotation text itself, written
            # on the image in the hand voice — no badge, no KEY entry.
            # A paper-colored halo keeps the script legible on any take.
            hf = _font("hand", max(14, int(cap_px * 2.0)))
            note = str(ann["text"])[:60]
            halo = style["paper"]
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                           (-1, -1), (1, 1), (-1, 1), (1, -1)):
                draw.text((sx + 10 + ox, sy + 8 + oy), note, font=hf,
                          fill=halo)
            draw.text((sx + 10, sy + 8), note, font=hf,
                      fill=style.get("hand_ink", style["ink"]))
        elif ann and ann.get("n"):
            r = max(8, int(cap_px * 0.9))
            draw.ellipse([sx + 6, sy + 6, sx + 6 + 2 * r, sy + 6 + 2 * r],
                         fill=style["ink"])
            draw.text((sx + 6 + r, sy + 6 + r), str(ann["n"]),
                      font=_font("mono", r), fill=style["paper"], anchor="mm")
            annotations.append((ann["n"], ann.get("text", "")))

    cy0 = y + inner_h + int(cap_px * 0.8)
    for line in cap_lines:
        draw.text((rx, cy0), line, font=cap_f, fill=style["dim"])
        cy0 += int(cap_px * 1.55)


# --------------------------------------------------------------- dress
# Look dress (2026-08-13): presentation elements derived by looks.dressed
# around the arranged panel blocks. Dress paints only its reserved
# regions; it is never blocks, never judged by readiness, never stored.

def _draw_swatch_strip(draw, rect, style, W, swatches, compact=False):
    rx, ry, rw, rh = rect
    if not swatches:
        return
    n = len(swatches)
    gap = 2
    cell_w = max(6, (rw - gap * (n - 1)) // n)
    label_px = max(7, int(FOOTER_FRAC * W))
    label_f = _font("mono", label_px)
    label_h = 0 if compact else int(label_px * 2.9)
    cell_h = max(8, rh - label_h)
    x = rx
    for sw in swatches:
        hx = str(sw.get("hex") or "")
        try:
            rgb = tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))
        except (ValueError, IndexError):
            continue
        draw.rectangle([x, ry, x + cell_w - 1, ry + cell_h - 1], fill=rgb)
        if compact and style.get("keyline"):
            # A swatch near the paper's own value vanishes without an
            # edge (VOID BLACK on Tech Design, user export 2026-08-13).
            draw.rectangle([x, ry, x + cell_w - 1, ry + cell_h - 1],
                           outline=style["keyline"], width=1)
        if sw.get("hero"):
            draw.rectangle([x, ry, x + cell_w - 1, ry + cell_h - 1],
                           outline=style["ink"], width=max(1, W // 1600))
        if compact:
            lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            fill = (20, 20, 20) if lum > 140 else (235, 235, 235)
            draw.text((x + 3, ry + cell_h - label_px - 3), hx.upper(),
                      font=label_f, fill=fill)
        else:
            # Labels stay inside their own cell — neighboring names were
            # colliding on swatch-heavy boards (user export, 2026-08-13).
            room = cell_w - 6
            name = str(sw.get("name") or "").upper()
            clipped = name
            while clipped and draw.textlength(
                    clipped + ("…" if clipped != name else ""),
                    font=label_f) > room:
                clipped = clipped[:-1]
            if clipped:
                draw.text((x, ry + cell_h + 4),
                          clipped + ("…" if clipped != name else ""),
                          font=label_f, fill=style["ink"])
            if draw.textlength(hx.upper(), font=label_f) <= room:
                draw.text((x, ry + cell_h + 4 + int(label_px * 1.3)),
                          hx.upper(), font=label_f, fill=style["dim"])
        x += cell_w + gap


def _draw_material_chips(canvas, draw, rect, style, W, refs, warnings):
    """Square reference chips, downscale-only: a source smaller than its
    chip is SKIPPED with a warning — dress never upscales and never
    gates (it is presentation, not a slot)."""
    rx, ry, rw, rh = rect
    if not refs:
        return
    label_px = max(7, int(FOOTER_FRAC * W))
    label_f = _font("mono", label_px)
    label_h = int(label_px * 1.6)
    chip = max(8, rh - label_h)
    gap = max(4, W // 480)
    x = rx
    for r in refs:
        if x + chip > rx + rw:
            break
        path = store.reference_image_path(str(r.get("id") or ""), "md")
        drawn = False
        if path:
            try:
                with Image.open(path) as im:
                    im = im.convert("RGB")
                    if im.width >= chip and im.height >= chip:
                        cover = chip / min(im.width, im.height)
                        nw = max(chip, round(im.width * cover))
                        nh = max(chip, round(im.height * cover))
                        im = im.resize((nw, nh), Image.LANCZOS)
                        left = (nw - chip) // 2
                        top = (nh - chip) // 2
                        im = im.crop((left, top, left + chip, top + chip))
                        canvas.paste(im, (x, ry))
                        drawn = True
                    else:
                        warnings.append(
                            f"material chip {r.get('id')}: source smaller "
                            f"than its {chip}px chip — skipped, never "
                            "upscaled")
            except OSError:
                pass
        if not drawn:
            continue
        if style.get("keyline"):
            draw.rectangle([x, ry, x + chip - 1, ry + chip - 1],
                           outline=style["keyline"], width=1)
        draw.text((x, ry + chip + 3),
                  str(r.get("label") or r.get("id") or "")[:16].upper(),
                  font=label_f, fill=style["dim"])
        x += chip + gap


def _draw_spec_table(draw, rect, style, W, rows):
    rx, ry, rw, rh = rect
    if not rows:
        return
    px = max(7, int(FOOTER_FRAC * W * 1.1))
    key_f = _font("mono", px)
    row_h = int(px * 2.1)
    key_w = int(rw * 0.42)
    y = ry
    for k, v in rows:
        if y + row_h > ry + rh:
            break
        draw.line([(rx, y + row_h - 2), (rx + rw, y + row_h - 2)],
                  fill=style.get("keyline") or style["dim"], width=1)
        draw.text((rx, y + int(px * 0.4)), str(k).upper()[:18], font=key_f,
                  fill=style["dim"])
        val = str(v)
        while val and draw.textlength(val + "…", font=key_f) > rw - key_w:
            val = val[:-1]
        draw.text((rx + key_w, y + int(px * 0.4)),
                  val + ("…" if val != str(v) else ""), font=key_f,
                  fill=style["ink"])
        y += row_h


def _draw_atmosphere(draw, rect, style, W, text):
    rx, ry, rw, rh = rect
    if not text:
        return
    px = max(8, int(SUB_FRAC * W))
    f = _font("mono", px)
    if style.get("accent"):
        draw.line([(rx, ry), (rx + rw, ry)], fill=style["accent"],
                  width=max(1, W // 1600))
    line = str(text).upper()
    while line and draw.textlength(line + "…", font=f) > rw:
        line = line[:-1]
    draw.text((rx, ry + max(4, int(px * 0.6))),
              line + ("…" if line != str(text).upper() else ""),
              font=f, fill=style["dim"])


def _draw_profile(draw, rect, style, W, text):
    rx, ry, rw, rh = rect
    if not text:
        return
    px = max(8, int(SUB_FRAC * W))
    f = _font(style["voice"], px)
    y = ry
    for line in _wrap(draw, str(text), f, rw):
        if y + px * 1.55 > ry + rh:
            break
        draw.text((rx, y), line, font=f, fill=style["dim"])
        y += int(px * 1.55)


def _draw_dress(canvas, draw, sheet, style, W, cx, cy, cw, ch, warnings):
    for d in sheet.get("dress", []) or []:
        f = d.get("frac") or {}
        rect = (cx + int(f.get("x", 0) * cw), cy + int(f.get("y", 0) * ch),
                max(1, int(f.get("w", 0) * cw)),
                max(1, int(f.get("h", 0) * ch)))
        data = d.get("data") or {}
        kind = d.get("kind")
        if kind == "SWATCH_STRIP":
            _draw_swatch_strip(draw, rect, style, W,
                               data.get("swatches") or [],
                               compact=bool(data.get("compact")))
        elif kind == "MATERIAL_CHIPS":
            _draw_material_chips(canvas, draw, rect, style, W,
                                 data.get("refs") or [], warnings)
        elif kind == "SPEC_TABLE":
            _draw_spec_table(draw, rect, style, W, data.get("rows") or [])
        elif kind == "ATMOSPHERE":
            _draw_atmosphere(draw, rect, style, W, data.get("text", ""))
        elif kind == "PROFILE":
            _draw_profile(draw, rect, style, W, data.get("text", ""))


# -------------------------------------------------------------- the renderer

def render_sheet(sheet: dict, scale: float = 1.0, *,
                 allow_letterbox: bool = False,
                 warnings: list[str] | None = None,
                 manifest: list | None = None,
                 image_tier: str = "full") -> Image.Image:
    """The sheet as ink on paper. Composer overlays are app chrome and are
    drawn in the DOM — nothing here marks selection, snapping or state."""
    style = STYLE_INK.get(sheet.get("style"))
    if style is None:
        raise sheet_mod.SheetError(f"unknown style: {sheet.get('style')}")
    warnings = warnings if warnings is not None else []
    W, H = pixel_size(sheet, scale)
    if W < 16 or H < 16:
        raise sheet_mod.SheetError(f"render size {W}×{H} is too small")
    canvas = Image.new("RGB", (W, H), style["paper"])
    draw = ImageDraw.Draw(canvas)

    if style.get("grid"):
        step = max(24, W // 48)
        for gx in range(0, W, step):
            draw.line([(gx, 0), (gx, H)], fill=style["grid"], width=1)
        for gy in range(0, H, step):
            draw.line([(0, gy), (W, gy)], fill=style["grid"], width=1)

    cx, cy, cw, ch = content_rect(sheet, W, H)
    mx = int(0.047 * W)
    my = cy if not sheet.get("spine") else int(0.047 * W * (H / W) * 0)
    title_px = max(10, int(TITLE_FRAC * W))
    sub_px = max(7, int(SUB_FRAC * W))
    title_f = _font("serif" if style["voice"] == "serif" else "sans",
                    title_px)
    sub_f = _font("mono", sub_px)
    mh = sheet.get("masthead") or {}

    annotations: list[tuple[int, str]] = []

    if sheet.get("spine"):
        # Spine column: masthead + elastic blocks, top to bottom. Elastic
        # type owns its column and reflows (R1) — this is that column.
        sx0, sw_ = mx, int(sheet_mod.SPINE_W * W) - mx
        yy = int(0.06 * H)
        for line in _wrap(draw, str(mh.get("title", "")).upper(), title_f,
                          sw_):
            draw.text((sx0, yy), line, font=title_f, fill=style["ink"])
            yy += int(title_px * 1.12)
        if mh.get("subject"):
            yy += int(sub_px * 0.8)
            draw.text((sx0, yy), str(mh["subject"]).upper(), font=sub_f,
                      fill=style["dim"])
            yy += int(sub_px * 1.6)
        if style.get("accent"):
            draw.line([(sx0, yy + 4), (sx0 + sw_, yy + 4)],
                      fill=style["accent"], width=max(2, W // 1200))
        yy += int(sub_px * 2.5)
        for b in sheet.get("blocks", []):
            if not sheet_mod.BLOCK_TYPES[b["type"]].elastic:
                continue
            rest_h = H - yy - int(0.05 * H)
            if rest_h <= 0:
                break
            band = min(rest_h, int(0.22 * H))
            if b["type"] == "PALETTE":
                _draw_palette_block(draw, sheet, b, (sx0, yy, sw_, band),
                                    style, W)
            else:
                _draw_text_block(draw, sheet, b, (sx0, yy, sw_, band),
                                 style, W)
            yy += band + int(0.02 * H)
    else:
        yy = int(0.035 * H)
        draw.text((mx, yy), str(mh.get("title", "")).upper(), font=title_f,
                  fill=style["ink"])
        yy += int(title_px * 1.2)
        subject_bits = [str(mh.get("subject") or "").upper()]
        tagline = (sheet.get("dress_masthead") or {}).get("tagline", "")
        if tagline:
            subject_bits.append(str(tagline))
        subject_line = "  ·  ".join(x for x in subject_bits if x)
        if subject_line:
            draw.text((mx, yy), subject_line, font=sub_f,
                      fill=style["dim"])
        if style.get("accent"):
            ry_ = cy - int(sub_px * 1.2)
            draw.line([(mx, ry_), (W - mx, ry_)], fill=style["accent"],
                      width=max(2, W // 1200))

    for b in sheet.get("blocks", []):
        elastic = sheet_mod.BLOCK_TYPES[b["type"]].elastic
        if elastic and sheet.get("spine"):
            continue  # rendered in the spine above
        f = b["frac"]
        rect = (cx + int(f["x"] * cw), cy + int(f["y"] * ch),
                max(1, int(f["w"] * cw)), max(1, int(f["h"] * ch)))
        if elastic:
            if b["type"] == "PALETTE":
                _draw_palette_block(draw, sheet, b, rect, style, W)
            else:
                _draw_text_block(draw, sheet, b, rect, style, W)
        else:
            _draw_slot_block(canvas, draw, sheet, b, rect, style, W,
                             allow_letterbox, warnings, annotations,
                             manifest, image_tier)

    _draw_dress(canvas, draw, sheet, style, W, cx, cy, cw, ch, warnings)

    # Canon footer: the sheet states what it is, in mono. The KEY lists
    # annotations in order — they claim no band and force no reflow.
    foot_px = max(7, int(FOOTER_FRAC * W))
    foot_f = _font("mono", foot_px)
    unit = sheet_mod.LADDERS[sheet["medium"]]["unit"]
    left = " · ".join(x for x in [
        str(sheet.get("sheet_id") or ""), str(sheet.get("archetype", "")),
        f"{sheet['size'][0]}×{sheet['size'][1]} {unit}".upper(),
        str(sheet.get("style", ""))] if x)
    draw.text((mx, H - int(foot_px * 2.4)), left, font=foot_f,
              fill=style["dim"])
    if annotations:
        key = "KEY  " + "   ".join(
            f"{n} — {t}" for n, t in sorted(annotations, key=lambda a: a[0]))
        kw = draw.textlength(key, font=foot_f)
        draw.text((W - mx - kw, H - int(foot_px * 2.4)), key, font=foot_f,
                  fill=style["dim"])
    return canvas


# ------------------------------------------------------------------- export

def export_sheet(sheet_id: str, fmt: str = "png") -> Path:
    """Full-size export, gated on readiness — both failure kinds must be
    clear before a pixel is spent (§7). The gate judges the DRESSED sheet:
    a look shrinks the panel area, and what ships is what is judged."""
    from . import looks
    rec = sheet_mod.get_sheet(sheet_id)
    if rec is None:
        raise KeyError(sheet_id)
    view = looks.dressed(rec)
    gate = sheet_mod.readiness(view)
    if not gate["ready"]:
        raise sheet_mod.SheetError(
            "export is blocked: " + json.dumps(gate["blocked"]))
    if fmt not in ("png", "pdf"):
        raise sheet_mod.SheetError("format must be png or pdf")
    img = render_sheet(view, 1.0)
    out_dir = sheet_mod.sheet_export_dir(sheet_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{sheet_id}.{fmt}"
    if fmt == "png":
        img.save(out, "PNG")
    else:
        img.save(out, "PDF", resolution=PRINT_DPI)
    return out


# export_lookbook removed 2026-08-12: the Lookbook surface was rolled back
# (user); export_sheet above remains the one export door, serving the
# stage-05 arrange room.
