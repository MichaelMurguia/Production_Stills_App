"""Art Direction Bible ingestion — project-agnostic.

The bible (context/01_ART_DIRECTION_BIBLE.md) is the single authoritative
source of rendering language for whatever film/project this app instance
serves. This module parses it into sections and assembles the subset that
applies to one panel.

Section model (by ## heading):
- SYSTEM sections have fixed meanings (visual identity, rendering language,
  lighting, characters, materials, scene lessons, drift rule, …).
- Every OTHER ## section is a DESIGN LANGUAGE block — a faction, world, or
  technology family with its own look. Authors add as many as the project
  needs; nothing is hardcoded per-project.
- "Core Material Language" ### subsections attach to the design block whose
  name they share (substring match either direction).
- A design block may declare its own inference keywords with a line like
  "Keywords: cabin, workshop, mining" — otherwise its title words are used.

Selection: specs can carry explicit `design_languages` / `scene_lessons`
lists (the governed path). When absent, keyword inference against the
panel's text decides, falling back to the FIRST design block in the bible
(author convention: put the project's default human world first).
"""
from __future__ import annotations

import re

from . import paths

GLOBAL_SECTIONS = [
    "Overall Visual Identity",
    "Rendering Language",
    "Lighting Language",
    "Character Presentation",
]

MATERIALS_SECTION = "Core Material Language"
SCENE_LESSONS_SECTION = "Current Locked Scene-Specific Lessons"
# Environments ride the level-3 mechanism (### entries under this container,
# like materials and lessons) — a top-level section would be swallowed by
# the every-other-##-is-a-design-language rule. Gap 6, Correction 2.
ENVIRONMENTS_SECTION = "Environments"

SYSTEM_SECTIONS = set(GLOBAL_SECTIONS) | {
    "Status",
    "Technology Families",          # container heading, no body of its own
    "Design Languages",             # alternative container heading
    MATERIALS_SECTION,
    ENVIRONMENTS_SECTION,
    "Composition Rules",
    "Production Board Presentation",
    SCENE_LESSONS_SECTION,
    "Drift Prevention Rule",
}

NEWLINE = chr(10)

_STOPWORDS = {"the", "and", "for", "with", "current", "locked", "scene",
              "specific", "lessons", "technology", "design", "language",
              "family", "families"}


def load_text() -> str:
    p = paths.BIBLE
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def save_text(text: str) -> None:
    paths.BIBLE.parent.mkdir(parents=True, exist_ok=True)
    paths.BIBLE.write_text(text.rstrip() + "\n", encoding="utf-8")


def parse_sections(text: str, level: int = 2) -> dict[str, str]:
    """Split markdown into {heading: body} at the given heading level.
    Bodies keep their own deeper subsections; '---' rules are dropped."""
    marker = "#" * level + " "
    sections: dict[str, str] = {}
    name = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith(marker):
            if name is not None:
                sections[name] = "\n".join(buf).strip()
            name = line[len(marker):].strip()
            buf = []
        elif name is not None:
            buf.append("" if line.strip() == "---" else line)
    if name is not None:
        sections[name] = "\n".join(buf).strip()
    return {k: re.sub(r"\n{3,}", "\n\n", v).strip() for k, v in sections.items()}


def _title_words(title: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return [w for w in words if len(w) >= 3 and w not in _STOPWORDS]


def _section_keywords(title: str, body: str) -> list[str]:
    m = re.search(r"^\s*\*{0,2}(?:Keywords|Triggers)\*{0,2}\s*:\s*(.+)$",
                  body, re.MULTILINE | re.IGNORECASE)
    if m:
        return [k.strip().lower() for k in m.group(1).split(",") if k.strip()]
    return _title_words(title)


def design_language_names(sections: dict[str, str] | None = None) -> list[str]:
    if sections is None:
        sections = parse_sections(load_text())
    return [n for n, body in sections.items()
            if n not in SYSTEM_SECTIONS and body.strip()]


def atmospheres() -> list[str]:
    """The approved atmosphere studies named in the Lighting Language section —
    the governed vocabulary for time-of-day / atmosphere choices."""
    body = parse_sections(load_text()).get("Lighting Language", "")
    out: list[str] = []
    collecting = False
    for line in body.splitlines():
        stripped = line.strip()
        if not collecting:
            if "atmosphere studies" in stripped.lower():
                collecting = True
            continue
        if stripped.startswith("- "):
            out.append(stripped[2:].strip())
        elif stripped:
            break
    return out


def sections_catalog() -> dict:
    """What the bible offers for explicit selection — drives the spec editor
    checkboxes and the wizard. Generic: derived entirely from the file."""
    text = load_text()
    sections = parse_sections(text)
    lessons = [t for t, b in parse_sections(
        sections.get(SCENE_LESSONS_SECTION, ""), level=3).items() if b.strip()]
    environments = [t for t, b in parse_sections(
        sections.get(ENVIRONMENTS_SECTION, ""), level=3).items() if b.strip()]
    return {
        "exists": bool(text.strip()),
        "design_languages": design_language_names(sections),
        "environments": environments,
        "scene_lessons": lessons,
        "atmospheres": atmospheres(),
    }


def infer_selection(haystack: str) -> dict:
    """Legacy keyword inference — used when a spec has no explicit selection."""
    sections = parse_sections(load_text())
    hay = haystack.lower()
    design = [n for n in design_language_names(sections)
              if any(k in hay for k in _section_keywords(n, sections[n]))]
    if not design:
        names = design_language_names(sections)
        design = names[:1]  # first block = the project's default world
    lessons = [t for t, b in parse_sections(
        sections.get(SCENE_LESSONS_SECTION, ""), level=3).items()
        if b.strip() and any(k in hay for k in _section_keywords(t, b))]
    return {"design_languages": design, "scene_lessons": lessons}


def _strip_keywords(body: str) -> str:
    """Keywords/Triggers lines are selection metadata, not art direction —
    they never reach a prompt."""
    return re.sub(r"^\s*\*{0,2}(?:Keywords|Triggers)\*{0,2}\s*:.*$\n?", "",
                  body, flags=re.MULTILINE | re.IGNORECASE).strip()


def _block(title: str, body: str) -> str:
    body = _strip_keywords(body)
    return f"{title.upper()}\n{body}" if body else ""


def render_context(haystack: str,
                   design_languages: list[str] | None = None,
                   scene_lessons: list[str] | None = None,
                   environments: list[str] | None = None) -> str:
    """Assemble the bible subset for one panel.

    `design_languages` / `scene_lessons`: explicit selections from the spec
    (the governed path). None means fall back to keyword inference against
    `haystack` (the panel's searchable text). `environments` is explicit
    only — no inference; a sheet without one simply carries none. Its block
    lands between languages and lessons, before the prompt's SETTING lines,
    so the sheet's own atmosphere wins ties (Gap 6 ruling §3)."""
    text = load_text()
    if not text:
        return ""
    sections = parse_sections(text)

    if design_languages is None or scene_lessons is None:
        inferred = infer_selection(haystack)
        if design_languages is None:
            design_languages = inferred["design_languages"]
        if scene_lessons is None:
            scene_lessons = inferred["scene_lessons"]

    parts: list[str] = ["VISUAL STYLE — locked art direction from the Art Direction Bible. "
                        "Non-negotiable; it overrides model defaults."]

    for name in GLOBAL_SECTIONS:
        if sections.get(name):
            parts.append(_block(name, sections[name]))

    materials = parse_sections(sections.get(MATERIALS_SECTION, ""), level=3)
    for name in design_languages:
        body = sections.get(name, "")
        mat = next((m for t, m in materials.items()
                    if t.lower() in name.lower() or name.lower() in t.lower()
                    or any(w in _title_words(name) for w in _title_words(t))), "")
        if mat:
            body = f"{body}\n\nMaterials:\n{mat}" if body else mat
        if body:
            parts.append(_block(f"{name} — design language", body))

    envs = parse_sections(sections.get(ENVIRONMENTS_SECTION, ""), level=3)
    for name in (environments or []):
        body = next((b for t, b in envs.items() if t.lower() == name.lower()), "")
        if body:
            parts.append(_block(f"{name} — environment", body))

    lessons = parse_sections(sections.get(SCENE_LESSONS_SECTION, ""), level=3)
    for title in scene_lessons:
        if lessons.get(title):
            parts.append(_block(f"Locked lessons — {title}", lessons[title]))

    return "\n\n".join(p for p in parts if p)


# ------------------------------------------- the rendering anchor, kept
# ONE question — "what medium do the panels render in?" — and until
# 2026-08-22 it had two answers. The rendering-style ANCHOR is the
# director's decision. The bible's `Rendering Language` section is a
# transcription of that decision, written once by the drafter and then
# frozen. Nothing kept them in step, and the bible is the half that
# reaches a render: `render_context` carries Rendering Language into
# every panel prompt, and into the Model Test's entire brief.
#
# What that cost (user-hit 2026-08-22, proven from the install): the
# bible was written at 16:17 saying Production Painting — "the brush left
# visible… Avoid: photographic detail". The anchor was changed to Photo
# Real at 18:04. The Model Test ran at 18:06 and returned an oil painting.
# The engine rendered exactly what it was sent.
#
# The section IS the style's document entry — its mechanics as Required,
# its avoid-list as Avoid — so it can be rebuilt from the anchor exactly,
# for free, with no model call. It is derived now and kept derived: the
# anchor is upstream of the bible the way the design system is upstream
# of the CSS.

_RL_TITLE = "Rendering Language"


def rendering_section(entry: dict) -> str:
    """The Rendering Language body for one rendering-style entry.

    Deliberately fuller than the drafter's version, which saw only the
    six mechanics that fit inside an anchor answer's 600 characters.
    Nothing here is a summary — the document entry is the source."""
    name = str(entry.get("name") or "").strip()
    sub = str(entry.get("subtitle") or "").strip().lower()
    req = [f"{name} rendering style" + (f" — {sub}." if sub else ".")]
    principle = str(entry.get("principle") or "").strip()
    if principle:
        req.append(principle.rstrip(".") + ".")
    for m in entry.get("mechanics") or []:
        t = str(m).strip().rstrip(".")
        if t:
            req.append(t + ".")
    avoid = [str(a).strip().rstrip(".") for a in (entry.get("avoid") or []) if str(a).strip()]
    lines = ["### Required"] + [f"- {x}" for x in req]
    if avoid:
        lines += ["", "### Avoid"] + [f"- {a[:1].upper() + a[1:]}." for a in avoid]
    return NEWLINE.join(lines)


def replace_section(text: str, title: str, body: str) -> str:
    """Swap ONE `## ` section's body, leaving every other byte alone.

    Rewriting the whole document through parse_sections would reflow the
    parts it does not own, and this is a document the director edits."""
    marker = "## " + title
    out, i, lines = [], 0, text.splitlines()
    while i < len(lines):
        if lines[i].strip() == marker:
            out.append(lines[i])
            out.append(body)
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return NEWLINE.join(out).rstrip() + NEWLINE


def stated_style(text: str = "") -> str:
    """Which rendering style the bible's own section NAMES.

    The first Required bullet reads `<Name> rendering style — <subtitle>`,
    which both the drafter's template and `rendering_section` produce. A
    bible that names none simply has no stated style, and a document that
    states nothing can never be contradicted."""
    body = parse_sections(text or load_text()).get(_RL_TITLE, "")
    m = re.search(r"^\s*[-*]\s*(.+?)\s+rendering style\b", body, re.M | re.I)
    return m.group(1).strip() if m else ""


def medium_entry(answer: str = None) -> dict:
    """The rendering-style document entry the anchor answer names."""
    from . import store, style_docs
    if answer is None:
        answer = store.interview_answers().get("medium", "")
    a = " ".join(str(answer or "").split())
    if not a:
        return {}
    entries = style_docs.styles("rendering")
    for e in entries:                       # the picker's own verbatim value
        if a == " ".join(str(e.get("value") or "").split()):
            return e
    low = a.lower()
    for e in entries:                       # or it simply names one
        n = str(e.get("name") or "").strip().lower()
        if n and low.startswith(n):
            return e
    return {}


def sync_rendering_language(answer: str = None) -> dict:
    """Rebuild the section when the anchor names a DIFFERENT style.

    Only on a genuine contradiction. A director who hand-tuned bullets
    within Photo Real still has a section naming Photo Real, and nothing
    is touched. A section naming Production Painting under a Photo Real
    anchor is wrong by definition, and is rebuilt.

    It runs — it is not offered (user ruling on migrations). There is no
    judgement here for a person to make: the anchor is the decision and
    the section is its transcription."""
    from . import store
    text = load_text()
    if not text.strip() or ("## " + _RL_TITLE) not in text:
        return {"changed": False, "reason": "no bible"}
    entry = medium_entry(answer)
    if not entry:
        return {"changed": False, "reason": "no rendering style chosen"}
    stated, want = stated_style(text), str(entry.get("name") or "").strip()
    if stated.lower() == want.lower():
        return {"changed": False, "reason": "already agrees", "style": want}
    save_text(replace_section(text, _RL_TITLE, rendering_section(entry)))
    state = store.load_app_state()
    state["bible_rev"] = int(state.get("bible_rev", 0)) + 1
    store.save_app_state(state)
    return {"changed": True, "from": stated or "(unstated)", "to": want,
            "rev": state["bible_rev"]}


def medium_conflict() -> str:
    """One sentence naming both sides, or "" when they agree.

    What a render refuses on. It outlives a failed sync: an anchor naming
    a style the library does not carry cannot be rebuilt from, and that is
    precisely when the contradiction would otherwise ride silently."""
    entry = medium_entry()
    if not entry:
        return ""
    stated, want = stated_style(), str(entry.get("name") or "").strip()
    if not stated or stated.lower() == want.lower():
        return ""
    return (f"the Art Direction Bible's Rendering Language says {stated}, "
            f"and the board rendering style is {want}")


def drift_prevention() -> str:
    return parse_sections(load_text()).get("Drift Prevention Rule", "")


# ------------------------------------------------------------- house style

def house_style() -> dict:
    """This production's OWN rendering style, captured from what already
    governs it (user 2026-08-16: "we should capture my style and make it
    the Production Painting style").

    `Production Painting` shipped as a phrase someone wrote. For a
    production that has been rendering for weeks that is backwards — the
    authority on how its panels are drawn is the saved bible's Rendering
    Language section, which has ridden every prompt, and the truest
    example of it is a panel it actually produced.

    words: the Required bullets, joined into one directive line. Feeding
      them back is deliberate rather than circular — a re-draft then
      restates the established look instead of drifting off it.
    plate: an approved take's image URL, newest first, or "" if none.
    """
    from . import generate, paths as _paths, store
    sections = parse_sections(load_text())
    body = sections.get("Rendering Language", "")
    # `### Required` when the bible has one; the whole section when it does
    # not. A bible written as prose is still a bible — an earlier pass read
    # bullets only and returned nothing at all for those.
    subs = parse_sections(body, level=3)
    required = subs.get("Required") or ""
    if not required.strip():
        required = chr(10).join(
            ln for ln in body.splitlines()
            if not ln.strip().startswith("###")) if body else ""
        # never let the Avoid list in — it is what a panel must NOT be
        for cut in ("### Avoid", "Avoid"):
            if cut in body:
                required = body.split(cut, 1)[0]
                break
    lines = []
    for ln in required.splitlines():
        t = re.sub(r"^\s*[-*]\s*", "", ln).strip()
        if not t or t.startswith("#") or t.lower().startswith("keywords:"):
            continue
        lines.append(t.rstrip("."))
    # Cap on a boundary, never mid-word — a directive that ends "Board
    # layo" is what the user saw. The cap exists so one long section
    # cannot swamp the prompt, not to trim a sentence in half.
    words, joined = "", "; ".join(lines)
    if len(joined) <= 480:
        words = joined
    else:
        for ln in lines:
            if len(words) + len(ln) + 2 > 480:
                break
            words = f"{words}; {ln}" if words else ln
        words = words or joined[:480].rsplit(" ", 1)[0]

    plate, plate_from = "", ""
    if _paths.BOARDS_DIR.exists():
        newest = None
        for d in sorted(_paths.BOARDS_DIR.iterdir()):
            if not d.is_dir():
                continue
            for c in generate.list_candidates(d.name):
                if (c.get("status") == "APPROVED"
                        and str(c.get("candidate_id", "")).startswith("CAND-")):
                    n = int(re.sub(r"\D", "", c["candidate_id"]) or 0)
                    if newest is None or n > newest[0]:
                        newest = (n, d.name, c["candidate_id"])
        if newest:
            _, sid, cid = newest
            plate = f"/api/specs/{sid}/candidates/{cid}/image?size=thumb"
            plate_from = cid
    return {"words": words, "lines": lines, "plate": plate,
            "plate_from": plate_from,
            "has_bible": bool(load_text().strip()),
            "board_refs": [r["id"] for r in store.list_references()
                           if store.role_head(r.get("role", "")) == "BOARD_RENDERING_STYLE"
                           and r.get("status") == "APPROVED"]}
