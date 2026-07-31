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


def drift_prevention() -> str:
    return parse_sections(load_text()).get("Drift Prevention Rule", "")
