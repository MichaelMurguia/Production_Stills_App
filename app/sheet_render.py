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
}

_VOICES = {
    "serif": ["C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/times.ttf"],
    "mono": ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"],
    "slab": ["C:/Windows/Fonts/rockb.ttf", "C:/Windows/Fonts/bahnschrift.ttf"],
    "sans": ["C:/Windows/Fonts/bahnschrift.ttf",
             "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"],
}
_SANS_BOLD = ["C:/Windows/Fonts/bahnschrift.ttf",
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

def _prepare_source(img_path: Path, crop: dict | None) -> Image.Image:
    im = Image.open(img_path).convert("RGB")
    c = crop or {}
    rot = float(c.get("rotate", 0.0) or 0.0)
    if rot:
        # The frame never rotates — the image rotates inside it; the fill
        # this needs is charged to the crop budget like any other zoom.
        im = im.rotate(-rot, resample=Image.BICUBIC, expand=True)
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
    with _prepare_source(img_path, crop) as im:
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
                     manifest: list | None = None) -> None:
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
        ann = s.get("annotation")
        if ann and ann.get("n"):
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


# -------------------------------------------------------------- the renderer

def render_sheet(sheet: dict, scale: float = 1.0, *,
                 allow_letterbox: bool = False,
                 warnings: list[str] | None = None,
                 manifest: list | None = None) -> Image.Image:
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
        if mh.get("subject"):
            draw.text((mx, yy), str(mh["subject"]).upper(), font=sub_f,
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
                             manifest)

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
    clear before a pixel is spent (§7)."""
    rec = sheet_mod.get_sheet(sheet_id)
    if rec is None:
        raise KeyError(sheet_id)
    gate = sheet_mod.readiness(rec)
    if not gate["ready"]:
        raise sheet_mod.SheetError(
            "export is blocked: " + json.dumps(gate["blocked"]))
    if fmt not in ("png", "pdf"):
        raise sheet_mod.SheetError("format must be png or pdf")
    img = render_sheet(rec, 1.0)
    out_dir = sheet_mod.sheet_export_dir(sheet_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{sheet_id}.{fmt}"
    if fmt == "png":
        img.save(out, "PNG")
    else:
        img.save(out, "PDF", resolution=PRINT_DPI)
    return out


def export_lookbook(lb_id: str) -> Path:
    """Multi-page PDF, one page per sheet at that sheet's own size — sheets
    in one lookbook may differ in size; each page carries its own box."""
    lb = sheet_mod.get_lookbook(lb_id)
    if lb is None:
        raise KeyError(lb_id)
    if not lb.get("sheets"):
        raise sheet_mod.SheetError("the lookbook has no sheets to export")
    pages: list[Image.Image] = []
    for sid in lb["sheets"]:
        rec = sheet_mod.get_sheet(sid)
        if rec is None:
            continue
        gate = sheet_mod.readiness(rec)
        if not gate["ready"]:
            raise sheet_mod.SheetError(
                f"{sid} blocks the export: " + json.dumps(gate["blocked"]))
        pages.append(render_sheet(rec, 1.0))
    out_dir = paths.LOOKBOOKS_DIR / paths.safe_id(lb_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{lb_id}.pdf"
    pages[0].save(out, "PDF", resolution=PRINT_DPI, save_all=True,
                  append_images=pages[1:])
    return out
