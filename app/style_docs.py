"""Anchor style libraries, read from documents rather than hardcoded.

The 2026-08-16 ruling that made cinematography document-backed said why:
"the document is the source of truth and the one the user maintains, so
editing it updates the app and there is never a second list to keep in
step." That was written about one anchor and applies to all of them.

Until 2026-08-22 it WAS one anchor. World texture and rendering style were
arrays in `app.js` — five and nine options, each carrying a one-line
description and a prompt fragment of about sixty characters. The deepest
world texture said, in full:

    weathered surfaces, patina, sun-bleach and oxidation, repairs visible

against 1,210 characters for a cinematography grammar. Adding a texture
meant editing the client. They were exactly the second list that ruling
was written against (user, 2026-08-22).

So the parser moved here and all three anchors read the same shape:

    # n. Name — Subtitle
    ## Key Question / ## Description / ## Operating Principle
    ## Visual Mechanics      (bullets)
    ## Image-Model Prompt    (fenced; may carry its own Avoid list)
    ## Reference Films       (bullets, optional — texture and rendering
                              have no film canon and omit it)

`value` is what actually rides a prompt, and is deliberately NOT the full
image-model prompt: per the cinematography document's own Usage Note,
generation leans on the mechanics and the operating principle rather than
asking a model to imitate a named work. One rule, three libraries.
"""
from __future__ import annotations

import re

from . import paths

_HEAD = re.compile(r"^#\s+(\d+)\.\s+(.+?)\s+[—-]\s+(.+?)\s*$", re.M)

# doc stem -> (filename, key prefix, the noun the directive uses)
LIBRARIES = {
    "cinematography": ("CINEMATOGRAPHY_STYLES.md", "cine-", "cinematography"),
    "texture": ("WORLD_TEXTURE_STYLES.md", "tex-", "world texture"),
    "rendering": ("RENDERING_STYLES.md", "rend-", "rendering style"),
}


def doc_path(lib: str):
    return paths.ROOT / "docs" / LIBRARIES[lib][0]


def slug(lib: str, name: str) -> str:
    return LIBRARIES[lib][1] + re.sub(r"[^a-z0-9]+", "-",
                                      str(name).lower()).strip("-")


def _flat(text: str) -> str:
    """Prose from a hand-wrapped document is one paragraph, not five lines.
    The fenced image-model prompt is NOT run through this — its line
    structure is authored."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _subsections(body: str) -> dict[str, str]:
    out, cur = {}, None
    for ln in body.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            cur = m.group(1).strip()
            out[cur] = ""
        elif cur is not None:
            out[cur] += ln + "\n"
    return {k: v.strip() for k, v in out.items()}


def _bullets(text: str) -> list[str]:
    out = []
    for ln in text.splitlines():
        t = ln.strip()
        # `---` is the document's section rule, not a bullet.
        if not t.startswith(("-", "*")) or set(t) <= {"-", "*", " "}:
            continue
        out.append(re.sub(r"^\s*[-*]\s*", "", t).strip())
    return out


def _fenced(text: str) -> str:
    m = re.search(r"```(?:text)?\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def _avoid(prompt: str) -> list[str]:
    """The prompt's own Avoid list becomes the card's NOT fence — the
    document already states what each style is not."""
    m = re.search(r"^\s*Avoid:?\s*(.+)$", prompt, re.M | re.I)
    if not m:
        return []
    return [x.strip() for x in re.split(r"[,;]", m.group(1)) if x.strip()]


def styles(lib: str) -> list[dict]:
    """Every style the named document defines, in its own order.

    A style the document drops disappears from the picker; a style it
    gains appears there. A missing document is not an error — it is an
    empty library, and the caller states that rather than inventing one.
    """
    noun = LIBRARIES[lib][2]
    p = doc_path(lib)
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    heads = list(_HEAD.finditer(text))
    out = []
    for i, m in enumerate(heads):
        body = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        sub = _subsections(body)
        name, subtitle = m.group(2).strip(), m.group(3).strip()
        prompt = _fenced(sub.get("Image-Model Prompt", ""))
        mechanics = _bullets(sub.get("Visual Mechanics", ""))
        principle = _flat(sub.get("Operating Principle", ""))
        mechanics = [_flat(x) for x in mechanics]
        value = "; ".join(x.rstrip(".") for x in
                          [f"{name} {noun} — {subtitle.lower()}",
                           principle.rstrip(".")] + mechanics[:6] if x)
        out.append({
            "n": int(m.group(1)), "key": slug(lib, name), "name": name,
            "subtitle": _flat(subtitle),
            "question": _flat(sub.get("Key Question", "")),
            "description": _flat(sub.get("Description", "")),
            "principle": principle,
            "mechanics": mechanics,
            "films": _bullets(sub.get("Reference Films", "")),
            "avoid": _avoid(prompt),
            "prompt": prompt,
            "value": value[:600],
        })
    return sorted(out, key=lambda s: s["n"])
