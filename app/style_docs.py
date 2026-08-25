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
    """Bullets, with wrapped ones kept whole.

    A continuation line silently truncated its bullet until 2026-08-22 —
    the first mechanic long enough to wrap lost its tail, and these
    bullets are copied verbatim into the Art Direction Bible and from
    there into every render prompt. An indented line under a bullet is
    part of it; anything else ends it."""
    out = []
    for ln in text.splitlines():
        t = ln.strip()
        # `---` is the document's section rule, not a bullet.
        if t.startswith(("-", "*")) and not set(t) <= {"-", "*", " "}:
            out.append(re.sub(r"^\s*[-*]\s*", "", t).strip())
        elif out and t and ln[:1] in (" ", "	"):
            out[-1] = (out[-1] + " " + t).strip()
        elif not t:
            continue
    return out


def _fenced(text: str) -> str:
    m = re.search(r"```(?:text)?\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def _avoid(prompt: str) -> list[str]:
    """The prompt's own Avoid list becomes the card's NOT fence — the
    document already states what each style is not.

    Read to the end of the PARAGRAPH, not the end of the line. Seven of
    the nine rendering styles wrap their Avoid line, and until 2026-08-22
    every one of them lost its tail: 3D Rendered Cartoon avoided "heavy
    texture" where the document says "heavy texture maps, lens dirt,
    chromatic aberration", and Photo Real never refused cartoon
    proportion at all. These become the Bible's `### Avoid` bullets and
    ride every render prompt, so the loss was silent and expensive."""
    lines = prompt.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"^\s*Avoid:?\s*(.*)$", ln, re.I)
        if not m:
            continue
        buf = [m.group(1).strip()]
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                break
            buf.append(nxt.strip())
        return [x.strip() for x in re.split(r"[,;]", " ".join(buf)) if x.strip()]
    return []


# C3 — hedges in a style's own prompt (2026-08-25).
#
# The style libraries are user-maintained prose, and their wording decides
# whether a style reaches an image at all. Nothing checked them.
#
# A hedge softens an instruction so that doing LESS still satisfies it. An
# image model settles on the safest reading that satisfies everything, and
# a hedge always makes "do less" a valid answer — so where a hedge and the
# instruction it modifies pull in opposite directions, the hedge tends to
# win. Chromatic/Operatic carried four restraint cues against one drama cue
# and rendered restrained for two days; Deep-Space carries none and is the
# only style that ever landed reliably.
#
# NOT an error. Naturalistic/Observational legitimately wants restraint,
# and a craft rule like "maintain strong value structure" is a counterweight
# doing real work. This reports; the author decides.
# Three near-misses are deliberately NOT here, because a lint that cries
# wolf is a lint nobody reads:
#   "selective focus" / "selective attention" — a technique's NAME, not a
#     softener. Only the adverb "selectively" softens an instruction.
#   "moderately wide" — a real lens specification. Flagging it would have
#     marked Deep-Space, the one style that has always landed.
#   anything inside the Avoid block — a hedge there is inverted: "avoid
#     uncontrolled background elements" asks for MORE control, not less.
_HEDGES = (
    # softeners — doing less still complies
    "selectively", "controlled", "restrained", "subtle",
    "carefully", "unforced", "sparingly", "gentle",
    # opt-outs — the model may decline and still comply. The strongest kind:
    # "unusual subject placement WHEN EMOTIONALLY MOTIVATED" is satisfied by
    # deciding the moment is not emotionally motivated.
    "when appropriate", "when emotionally motivated", "when necessary",
    "where appropriate", "if appropriate", "only when",
    # balance clauses — name a failure mode, and the safe distance is the middle
    "without becoming", "rather than becoming", "while remaining",
)


def hedges(prompt: str) -> list[dict]:
    """Every hedged line in a style's image-model prompt, with the word.

    Line-level rather than a count, because the author needs to see WHICH
    instruction was softened — a hedge on the style's defining mechanic is
    a different fact from one in its Avoid list."""
    out = []
    in_avoid = False
    for line in str(prompt or "").splitlines():
        low = line.lower().strip()
        if not low:
            continue
        if low.startswith("avoid"):
            in_avoid = True
            continue
        if low.startswith("prioritize"):
            in_avoid = False
            continue
        if in_avoid:
            continue
        found = sorted({h for h in _HEDGES if h in low})
        if found:
            out.append({"line": line.strip(), "words": found})
    return out


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
            "hedges": hedges(prompt),
            "value": value[:600],
        })
    return sorted(out, key=lambda s: s["n"])
