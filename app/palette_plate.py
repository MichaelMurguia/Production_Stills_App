"""One palette, one reference image.

A palette is a SWATCH OF COLOURS — a single thing (user ruling
2026-08-15, and the same reading as canon's "a set that means something
as a set renders as one object"). Attaching it colour by colour spent one
of the render's fourteen reference slots per swatch: a panel with one
subject group ticked reported thirteen subject references and sat over
the cap, because an eight-colour design language had quietly taken eight
slots.

So the swatches are drawn into ONE plate — a labelled strip, hero band
first, the rest ordered light to dark exactly as the app's own ramps are
— and that plate is what rides. The composite is cached on the hexes it
contains, so it is drawn once and reused until the palette changes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import paths, store, wizard

# The strip is read by an image model, not a person: big flat fields of
# colour with the hex printed under each, no gradients, nothing to
# mistake for subject matter.
CELL_W = 240
CELL_H = 420
LABEL_H = 74
PAD = 24
BG = (18, 20, 23)
INK = (236, 238, 240)


def _luma(hx: str) -> float:
    h = hx.lstrip("#")
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return 0.0
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _rgb(hx: str) -> tuple[int, int, int]:
    h = hx.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def swatch_rows(refs: list[dict]) -> list[dict]:
    """The parsed, ordered swatches of the given COLOR_PALETTE references.

    Hero first, then light to dark with ties broken on the hex, so the
    plate matches the ramp the user picked it from — a reference that
    reorders itself between viewings is a different reference."""
    rows = []
    for r in refs:
        sw = wizard.parse_swatch_notes(r.get("notes", ""))
        if not sw.get("hex"):
            continue
        rows.append({"id": r.get("id", ""), "hex": sw["hex"],
                     "pair_hex": sw.get("pair_hex"), "name": sw.get("name", ""),
                     "language": sw.get("language", ""), "hero": sw.get("hero")})
    rows.sort(key=lambda s: (not s["hero"], -_luma(s["hex"]), s["hex"]))
    return rows


def plate_path(refs: list[dict]) -> Path | None:
    """Draw (or reuse) the one plate for these swatches. None when none of
    them parse to a colour — a palette with nothing to show attaches
    nothing rather than a blank image."""
    rows = swatch_rows(refs)
    if not rows:
        return None
    key = hashlib.sha256(
        "|".join(f"{s['hex']}/{s['pair_hex'] or ''}/{s['name']}" for s in rows)
        .encode("utf-8")).hexdigest()[:16]
    # Read the path at CALL time: paths.* are rebound on project switch,
    # and a plate cached into another production's folder would leak one
    # film's palette into another's renders.
    out = paths.REF_THUMBS / f"palette-{key}.png"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)

    from PIL import Image, ImageDraw

    w = PAD * 2 + CELL_W * len(rows)
    h = PAD * 2 + CELL_H + LABEL_H
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    font = _font(26)
    small = _font(20)
    for i, s in enumerate(rows):
        x = PAD + i * CELL_W
        # A value/key pair is ONE swatch, so it takes one cell split in two.
        if s["pair_hex"]:
            d.rectangle([x, PAD, x + CELL_W - 8, PAD + CELL_H // 2],
                        fill=_rgb(s["hex"]))
            d.rectangle([x, PAD + CELL_H // 2, x + CELL_W - 8, PAD + CELL_H],
                        fill=_rgb(s["pair_hex"]))
        else:
            d.rectangle([x, PAD, x + CELL_W - 8, PAD + CELL_H],
                        fill=_rgb(s["hex"]))
        ty = PAD + CELL_H + 10
        d.text((x, ty), (s["name"] or "").upper()[:22], font=font, fill=INK)
        d.text((x, ty + 32), s["hex"].upper()
               + (f" / {s['pair_hex'].upper()}" if s["pair_hex"] else ""),
               font=small, fill=(154, 161, 168))
    img.save(out, "PNG")
    return out


def _font(px: int):
    from PIL import ImageFont
    for name in ("cour.ttf", "consola.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def collapse(refs: list[dict]) -> list[dict]:
    """Replace every COLOR_PALETTE reference in `refs` with ONE synthetic
    reference carrying the composite plate, in the position the first
    swatch held. Non-palette references pass through untouched, in order.

    The synthetic record carries `_plate` — the path to attach — because
    it has no library row of its own: it is a rendering OF references, not
    a reference someone approved."""
    swatches = [r for r in refs
                if store.role_head(r.get("role", "")) == "COLOR_PALETTE"]
    if len(swatches) <= 1:
        return list(refs)
    plate = plate_path(swatches)
    if plate is None:
        # Nothing parsed to a colour, so there is nothing to composite.
        # Pass them through untouched: attaching a swatch whose notes are
        # unreadable is a small wrong; silently dropping a reference the
        # user attached is a large one.
        return list(refs)
    langs = []
    for s in swatch_rows(swatches):
        if s["language"] and s["language"] not in langs:
            langs.append(s["language"])
    label = " + ".join(langs) if langs else "PALETTE"
    synth = {
        "id": "PALETTE",
        "role": f"COLOR_PALETTE — {label}",
        "status": "APPROVED",
        "notes": f"{len(swatches)} swatches on one plate · "
                 + " · ".join(s["hex"].upper() for s in swatch_rows(swatches)),
        "_plate": str(plate),
        "_from": [r.get("id", "") for r in swatches],
    }
    out, placed = [], False
    for r in refs:
        if r in swatches:
            if not placed:
                out.append(synth)
                placed = True
            continue
        out.append(r)
    return out
