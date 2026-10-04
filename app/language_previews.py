"""A picture on every design-language card, before any panel exists.

User, 2026-10-04, looking at seven cards that each said "Examples will
appear here from your panels": "This section needs to auto generate images
once an art direction bible is created. Before that, it should make
thumbnail renderings based on 'Best Guess'."

So each design language has ONE thumbnail, rendered from one of two bases:

- BEST GUESS, before the Bible exists — what the screenplay read said the
  language looks like, under the production's style anchors and period.
- FROM THE BIBLE, once the Bible exists — that language's own Bible
  section and materials, under the Bible's global sections.

What spends, and when, is decided HERE and nowhere else (one rule; the
client only asks). A thumbnail is DUE when it is missing, or when the
Bible now exists and the thumbnail is still a guess — the upgrade the user
asked for. A Bible edit that changes a language's section makes its
thumbnail OUTDATED, which is stated and offered, never spent on its own:
editing a document must not bill seven renders per keystroke-save.

A thumbnail is not a reference. It is never approved, never attached to a
render, and lives in its own folder, so it can only ever be looked at.
An approved panel in the language still takes the card over — a real
example beats a guess.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
from pathlib import Path

from . import bible, generate, paths, store

ASPECT = "3:2"   # the card is 1.586:1 and crops to cover
SIZE = "1K"      # a thumbnail: the cheapest size every engine offers

_busy: set[str] = set()
_busy_lock = threading.Lock()


class PreviewError(Exception):
    pass


def _dir() -> Path:
    return paths.DATA / "language_previews"


def slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", str(name or "")).strip("-").lower()
    return s[:60]


def _languages() -> list[dict]:
    a = store.load_wizard_analysis() or {}
    out, seen = [], set()
    for w in a.get("design_worlds") or []:
        name = str(w.get("name", "")).strip()
        s = slug(name)
        if name and s and s not in seen:
            seen.add(s)
            out.append(w)
    return out


def _bible_section(name: str, text: str) -> str:
    """The language's own Bible section plus its materials, or "" when the
    Bible has no section for it (a language confirmed after the draft)."""
    sections = bible.parse_sections(text)
    key = next((k for k in sections if k.casefold() == name.casefold()), None)
    if not key or not sections[key].strip():
        return ""
    return bible.render_context("", design_languages=[key], scene_lessons=[])


def _anchors() -> str:
    a = store.interview_answers()
    rows = [(label, " ".join(str(a.get(k, "")).split()))
            for k, label in (("texture", "WORLD TEXTURE"),
                             ("light", "CINEMATOGRAPHY"),
                             ("medium", "RENDERING STYLE"))]
    return "\n".join(f"{label}: {v}" for label, v in rows if v)


def basis(world: dict) -> dict:
    """What this language's thumbnail is rendered FROM, right now.

    `kind` is "bible", "guess", or "" when there is nothing to render from
    — a name alone would be the engine's invention, not this production's.
    `key` changes exactly when the picture should."""
    name = str(world.get("name", "")).strip()
    text = bible.load_text()
    if text.strip():
        section = _bible_section(name, text)
        if section:
            src = section
            kind = "bible"
        else:
            kind, src = "guess", ""
    else:
        kind, src = "guess", ""
    if kind == "guess":
        words = " ".join(str(world.get("description", "")).split())
        if not words:
            return {"kind": "", "key": "", "source": ""}
        kws = [str(k).strip() for k in (world.get("keywords") or []) if str(k).strip()]
        src = words + (("\nKeywords: " + ", ".join(kws)) if kws else "")
        src += ("\n" + _anchors()) if _anchors() else ""
    period = generate.production_period()
    key = hashlib.sha256(json.dumps(
        {"kind": kind, "name": name, "source": src, "period": period},
        sort_keys=True).encode("utf-8")).hexdigest()
    return {"kind": kind, "key": key, "source": src}


def _prompt(world: dict, b: dict) -> str:
    name = str(world.get("name", "")).strip()
    project = paths._project_name(paths._project_base(paths.ACTIVE_PROJECT),
                                  "this production")
    lead = ("A first impression from the screenplay, before the Art Direction "
            "Bible exists. Stay inside what the description supports."
            if b["kind"] == "guess" else
            "Render it exactly as the Art Direction Bible below describes it.")
    parts = [
        f"DESIGN LANGUAGE STUDY — {name.upper()} — {project}",
        "",
        "One establishing concept frame that shows what this design language "
        "looks like: its architecture, vehicles, objects, costume and "
        "materials, in its own environment. A look-development thumbnail "
        "for a film's art department, not a story moment.",
        lead,
        "",
        "THE DESIGN LANGUAGE" if b["kind"] == "guess" else "ART DIRECTION",
        b["source"],
    ]
    period = generate.production_period()
    if period:
        parts += ["", f"PERIOD: {period}. Nothing in frame may postdate it."]
    parts += ["", "No text, lettering, labels, logos or borders anywhere in the image."]
    return "\n".join(parts)


def _record_path(s: str) -> Path:
    return _dir() / f"{paths.safe_id(s)}.json"


def image_path(s: str) -> Path:
    return _dir() / f"{paths.safe_id(s)}.png"


def _read_record(s: str) -> dict:
    try:
        return json.loads(_record_path(s).read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        return {}


def state(world: dict, b: dict | None = None) -> dict:
    """One card's thumbnail, and whether it is DUE — the only place that
    decides a render should be spent without anyone asking."""
    name = str(world.get("name", "")).strip()
    s = slug(name)
    b = b or basis(world)
    rec = _read_record(s)
    have = bool(rec) and image_path(s).exists()
    if not have:
        st = "missing"
    elif rec.get("key") == b["key"]:
        st = "current"
    else:
        st = "outdated"
    due = bool(b["kind"]) and (
        st == "missing" or (b["kind"] == "bible" and rec.get("basis") == "guess"))
    with _busy_lock:
        busy = s in _busy
    return {
        "name": name, "slug": s,
        "state": st, "due": due and not busy, "rendering": busy,
        "basis": rec.get("basis", "") if have else "",
        "next_basis": b["kind"],
        "url": (f"/api/design-languages/previews/{s}.png?v={rec.get('key', '')[:12]}"
                if have else ""),
    }


def engine() -> str:
    """The image engine a thumbnail renders on: the studio's preferred one
    when it can run, otherwise the first that can. "" when none can."""
    cap = generate.capability()["image"]
    usable = list(cap.get("engines") or [])
    if not usable:
        return ""
    pref = generate.preferred_provider()
    return pref if pref in usable else usable[0]


def status() -> dict:
    return {"engine": engine(),
            "size": SIZE,
            "languages": [state(w) for w in _languages()]}


def render(name: str) -> dict:
    """Render one language's thumbnail now. Spends one image call."""
    world = next((w for w in _languages()
                  if str(w.get("name", "")).strip().casefold()
                  == str(name or "").strip().casefold()), None)
    if world is None:
        raise KeyError(name)
    b = basis(world)
    if not b["kind"]:
        raise PreviewError(
            f"{world['name']} has no description and no Bible section yet — "
            "a thumbnail from a name alone would be invented, not read.")
    provider = engine()
    if not provider:
        raise PreviewError("Connect an image model to render design-language "
                           "thumbnails — Settings → AI & engines.")
    s = slug(world["name"])
    with _busy_lock:
        if s in _busy:
            raise PreviewError(f"{world['name']} is already rendering.")
        _busy.add(s)
    try:
        prompt = _prompt(world, b)
        generate._require_prompt_fits(provider, prompt)
        refs = store.auto_style_references([world["name"]])
        from . import palette_plate
        refs = palette_plate.collapse(refs)[:generate.MAX_REFERENCE_IMAGES]
        ref_paths = generate._reference_image_paths(refs)
        _dir().mkdir(parents=True, exist_ok=True)
        # A private temp file per render, moved into place only once the
        # picture exists: two renders can never share, or delete, one
        # another's output, and a failed render leaves the last good
        # thumbnail standing.
        fd, tmp = tempfile.mkstemp(prefix=f".{s}-", suffix=".png", dir=_dir())
        os.close(fd)
        tmp_p = Path(tmp)
        try:
            generate.render_to(provider, prompt, ref_paths, SIZE, ASPECT, tmp_p)
            if not tmp_p.exists() or tmp_p.stat().st_size == 0:
                raise PreviewError(f"{provider} returned no image.")
            os.replace(tmp_p, image_path(s))
        finally:
            tmp_p.unlink(missing_ok=True)
        store._atomic_write_json(_record_path(s), {
            "name": world["name"], "basis": b["kind"], "key": b["key"],
            "provider": provider, "size": SIZE, "aspect_ratio": ASPECT,
            "prompt": prompt,
            "references": [r.get("id", "palette-plate") for r in refs],
            "rendered_at": store.utcnow(),
        })
    finally:
        with _busy_lock:
            _busy.discard(s)
    return state(world, b)
