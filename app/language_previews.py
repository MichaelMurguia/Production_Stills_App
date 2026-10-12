"""A picture on every design-language and environment card, before any
panel exists.

User, 2026-10-04, looking at seven cards that each said "Examples will
appear here from your panels": "This section needs to auto generate images
once an art direction bible is created. Before that, it should make
thumbnail renderings based on 'Best Guess'." Later the same day: "be
economical with image generation by rendering only small thumbnails at
first", and environments joined languages.

Each card has ONE thumbnail, rendered from one of two bases:

- BEST GUESS, when the Bible doesn't cover it yet — what the screenplay
  read said, under the production's style anchors and period.
- FROM THE BIBLE, once the Bible covers it — its own Bible entry under the
  Bible's global sections.

What spends, and when, is decided HERE and nowhere else (one rule). A
thumbnail is DUE when it is missing, or when the Bible now covers it and
it is still a guess. A Bible edit makes it OUTDATED, which is stated and
offered, never spent on its own.

A thumbnail is not a reference. It is never approved, never attached to a
render, and lives in its own folder, so it can only ever be looked at.
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

ASPECT = "3:2"      # the cards are landscape and crop to cover
QUALITY = "medium"  # OpenAI only; a thumbnail does not need "high"

KINDS = {
    "language": {"field": "design_worlds", "words": "description",
                 "prefix": "", "label": "DESIGN LANGUAGE STUDY",
                 "brief": ("One establishing concept frame that shows what this "
                           "design language looks like: its architecture, "
                           "vehicles, objects, costume and materials, in its own "
                           "environment.")},
    "environment": {"field": "environments", "words": "notes",
                    "prefix": "env-", "label": "ENVIRONMENT STUDY",
                    "brief": ("One wide establishing concept frame of this "
                              "environment: its landscape or architecture, its "
                              "light and its atmosphere. No character in focus.")},
}

_busy: set[str] = set()
_busy_lock = threading.Lock()


class PreviewError(Exception):
    pass


def _dir() -> Path:
    return paths.DATA / "language_previews"


def slug(name: str, kind: str = "language") -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", str(name or "")).strip("-").lower()[:60]
    return (KINDS[kind]["prefix"] + s) if s else ""


def _items(kind: str) -> list[dict]:
    a = store.load_wizard_analysis() or {}
    out, seen = [], set()
    for w in a.get(KINDS[kind]["field"]) or []:
        name = str(w.get("name", "")).strip()
        s = slug(name, kind)
        if name and s and s not in seen:
            seen.add(s)
            out.append(w)
    return out


def _bible_entry(name: str, kind: str, text: str) -> str:
    """The Bible's own words for this card, under its global sections, or
    "" when the Bible has no entry for it."""
    sections = bible.parse_sections(text)
    if kind == "language":
        key = next((k for k in sections if k.casefold() == name.casefold()), None)
        if not key or not sections[key].strip():
            return ""
        return bible.render_context("", design_languages=[key], scene_lessons=[])
    envs = bible.parse_sections(sections.get(bible.ENVIRONMENTS_SECTION, ""), level=3)
    key = next((k for k in envs if k.casefold() == name.casefold()), None)
    if not key or not envs[key].strip():
        return ""
    base = bible.render_context("", design_languages=[], scene_lessons=[])
    return (base + "\n\n" if base else "") + f"ENVIRONMENT — {key}\n{envs[key].strip()}"


def _anchors() -> str:
    a = store.interview_answers()
    rows = [(label, " ".join(str(a.get(k, "")).split()))
            for k, label in (("texture", "WORLD TEXTURE"),
                             ("light", "CINEMATOGRAPHY"),
                             ("medium", "RENDERING STYLE"))]
    return "\n".join(f"{label}: {v}" for label, v in rows if v)


def basis(item: dict, kind: str = "language") -> dict:
    """What this card's thumbnail is rendered FROM, right now.

    `kind` is "bible", "guess", or "" when there is nothing to render from
    — a name alone would be the engine's invention, not this production's.
    `key` changes exactly when the picture should."""
    name = str(item.get("name", "")).strip()
    text = bible.load_text()
    src = _bible_entry(name, kind, text) if text.strip() else ""
    which = "bible" if src else "guess"
    if which == "guess":
        words = " ".join(str(item.get(KINDS[kind]["words"], "")).split())
        if not words:
            return {"kind": "", "key": "", "source": ""}
        kws = [str(k).strip() for k in (item.get("keywords") or []) if str(k).strip()]
        locs = [str(x).strip() for x in (item.get("locations") or []) if str(x).strip()]
        src = words
        if kws:
            src += "\nKeywords: " + ", ".join(kws)
        if locs:
            src += "\nLocations: " + "; ".join(locs[:8])
        if _anchors():
            src += "\n" + _anchors()
    period = generate.production_period()
    key = hashlib.sha256(json.dumps(
        {"kind": which, "card": kind, "name": name, "source": src, "period": period},
        sort_keys=True).encode("utf-8")).hexdigest()
    return {"kind": which, "key": key, "source": src}


def _prompt(item: dict, b: dict, kind: str) -> str:
    name = str(item.get("name", "")).strip()
    project = paths._project_name(paths._project_base(paths.ACTIVE_PROJECT),
                                  "this production")
    lead = ("A first impression from the screenplay, before the Art Direction "
            "Bible covers it. Stay inside what the description supports."
            if b["kind"] == "guess" else
            "Render it exactly as the Art Direction Bible below describes it.")
    parts = [
        f"{KINDS[kind]['label']} — {name.upper()} — {project}",
        "",
        KINDS[kind]["brief"] + " A look-development thumbnail for a film's "
        "art department, not a story moment.",
        lead,
        "",
        "WHAT THE SCREENPLAY SAYS" if b["kind"] == "guess" else "ART DIRECTION",
        b["source"],
    ]
    period = generate.production_period()
    if period:
        parts += ["", f"PERIOD: {period}. Nothing in frame may postdate it."]
    parts += ["", "No text, lettering, labels, logos or borders anywhere in the image."]
    return "\n".join(parts)


def _record_path(s: str, base: Path | None = None) -> Path:
    return (base or _dir()) / f"{paths.safe_id(s)}.json"


def image_path(s: str, base: Path | None = None) -> Path:
    return (base or _dir()) / f"{paths.safe_id(s)}.png"


def _read_record(s: str) -> dict:
    try:
        return json.loads(_record_path(s).read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        return {}


def state(item: dict, kind: str = "language", b: dict | None = None) -> dict:
    """One card's thumbnail, and whether it is DUE — the only place that
    decides a render should be spent without anyone asking."""
    name = str(item.get("name", "")).strip()
    s = slug(name, kind)
    b = b or basis(item, kind)
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
        "name": name, "slug": s, "kind": kind,
        "state": st, "due": due and not busy, "rendering": busy,
        "basis": rec.get("basis", "") if have else "",
        "next_basis": b["kind"],
        "url": (f"/api/design-languages/previews/{s}.png?v={rec.get('key', '')[:12]}"
                if have else ""),
    }


def engine() -> str:
    return generate.image_engine()


def status() -> dict:
    eng = engine()
    return {"engine": eng,
            "size": generate.thumb_size(eng) if eng else "",
            "languages": [state(w, "language") for w in _items("language")],
            "environments": [state(e, "environment") for e in _items("environment")]}


def due(kind: str) -> list[str]:
    return [st["name"] for st in (state(i, kind) for i in _items(kind)) if st["due"]]


def render(name: str, kind: str = "language") -> dict:
    """Render one card's thumbnail now. Spends one small image call."""
    if kind not in KINDS:
        raise KeyError(kind)
    item = next((w for w in _items(kind)
                 if str(w.get("name", "")).strip().casefold()
                 == str(name or "").strip().casefold()), None)
    if item is None:
        raise KeyError(name)
    b = basis(item, kind)
    if not b["kind"]:
        raise PreviewError(
            f"{item['name']} has no description and no Bible entry yet — "
            "a thumbnail from a name alone would be invented, not read.")
    provider = engine()
    if not provider:
        raise PreviewError("Connect an image model to render thumbnails — "
                           "Settings → AI & engines.")
    s = slug(item["name"], kind)
    with _busy_lock:
        if s in _busy:
            raise PreviewError(f"{item['name']} is already rendering.")
        _busy.add(s)
    # The folder is fixed NOW: a production switched mid-render must not
    # receive this production's picture.
    base = _dir()
    size = generate.thumb_size(provider)
    try:
        prompt = _prompt(item, b, kind)
        generate._require_prompt_fits(provider, prompt)
        langs = [item["name"]] if kind == "language" else []
        refs = store.auto_style_references(langs)
        from . import palette_plate
        refs = palette_plate.collapse(refs)[:generate.MAX_REFERENCE_IMAGES]
        ref_paths = generate._reference_image_paths(refs)
        base.mkdir(parents=True, exist_ok=True)
        # A private temp file per render, moved into place only once the
        # picture exists: two renders can never share, or delete, one
        # another's output, and a failed render leaves the last good
        # thumbnail standing.
        fd, tmp = tempfile.mkstemp(prefix=f".{s}-", suffix=".png", dir=base)
        os.close(fd)
        tmp_p = Path(tmp)
        try:
            generate.render_to(provider, prompt, ref_paths, size, ASPECT, tmp_p,
                               quality=QUALITY)
            if not tmp_p.exists() or tmp_p.stat().st_size == 0:
                raise PreviewError(f"{provider} returned no image.")
            os.replace(tmp_p, image_path(s, base))
        finally:
            tmp_p.unlink(missing_ok=True)
        store._atomic_write_json(_record_path(s, base), {
            "name": item["name"], "kind": kind, "basis": b["kind"], "key": b["key"],
            "provider": provider, "size": size, "aspect_ratio": ASPECT,
            "quality": QUALITY if provider == "openai" else "",
            "prompt": prompt,
            "references": [r.get("id", "palette-plate") for r in refs],
            "rendered_at": store.utcnow(),
        })
    finally:
        with _busy_lock:
            _busy.discard(s)
    return state(item, kind, b)
