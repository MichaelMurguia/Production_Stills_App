"""Project setup wizard — establish art direction for a new screenplay.

Flow: the research model reads the screenplay and proposes the project's
design worlds (factions / technology families / distinct looks); the user
answers a short interview (touchstones, medium, palette, never-list) and
uploads reference photos; the model then drafts an Art Direction Bible in
the exact section schema `bible.py` parses — so everything downstream
(selective injection, scope checkboxes, drift rule) works immediately.

The draft is always reviewed and saved by the user; the wizard never
overwrites the bible silently.
"""
from __future__ import annotations

from . import autofill, generate, store

ANALYZE_SCHEMA_NOTE = """Return ONLY a JSON object with exactly this shape:
{
  "logline": "one-sentence summary of the screenplay",
  "design_worlds": [
    {"name": "short name, e.g. a faction, culture, or technology family",
     "description": "1-2 sentences on what it is and what defines its look",
     "keywords": ["lowercase", "trigger", "words"]}
  ],
  "subjects": [
    {"name": "character or object name as the screenplay uses it",
     "kind": "CHARACTER | VEHICLE | PROP",
     "subtitle": "2-4 punchy role epithets separated by periods, e.g. BUILDER. PROTECTOR. FATHER.",
     "traits": ["terse production-note fragments, e.g.", "40s. Lean. Hard-edged.",
                "Former pilot.", "Carries a rifle.", "Lives simply."]}
  ],
  "environments": [
    {"name": "UPPERCASE biome/world name, e.g. FOREST, DESERT, ORBITAL / STATION",
     "notes": "one line — the palette, light, and atmosphere of this world",
     "keywords": ["lowercase", "trigger", "words"],
     "locations": ["entries copied VERBATIM from the LOCATION LIST"]}
  ],
  "key_locations": ["recurring locations that boards will likely depict"],
  "unresolved": ["visual questions the screenplay leaves open"]
}
Identify 2-5 design languages ("design_worlds" in the JSON) — distinct visual
cultures that each need their own design language (protagonist world,
antagonist institutions, exotic technology, etc.).
Identify 2-6 environments — the physical worlds panels live in (forest,
desert town, ship interior). Environments are not factions:
a faction's outpost in forest vs. desert shares its culture but not its
palette, light, or atmosphere. If a LOCATION LIST is provided below, assign
each of its entries to exactly ONE environment, copied verbatim — never
invent, merge, or rephrase a listed location.
List every subject the art department needs visual reference for: main
and supporting characters, hero vehicles, key props. Subtitles and traits are
clipped production-note prose drawn ONLY from what the screenplay states or
directly implies — no invented biography. Only what the screenplay supports;
do not invent."""


def analyze_screenplay(provider: str = "gemini") -> dict:
    if provider == "mock" and generate.mock_enabled():
        from . import mockflow
        result = mockflow.analyze()
        result["model"] = mockflow.MODEL_NAME
        return result
    doc, mime = autofill._screenplay_bytes()
    # Environment membership is ASSIGNMENT, not generation (Gap 6 ruling):
    # the model picks from the deterministic slugline parse, so the coverage
    # table and finder list group with zero fuzzy matching downstream.
    from . import insights
    slugs = [l["location"] for l in
             insights.locations().get("locations", [])]
    loc_note = ("\n\nLOCATION LIST — the screenplay's slugline locations. "
                "Assign each to exactly one environment, copied verbatim:\n"
                + "\n".join(f"- {s}" for s in slugs)) if slugs else ""
    instructions = (
        "You are the production designer's research assistant. Read the attached "
        "screenplay and identify the visual worlds a film art department would "
        "need to design.\n\n" + ANALYZE_SCHEMA_NOTE + loc_note)
    draft_fn = autofill._draft_openai if provider == "openai" else autofill._draft_gemini
    result, model = draft_fn(doc, mime, instructions)
    result["model"] = model
    return result


def merge_analysis(prior: dict, fresh: dict) -> dict:
    """Re-run semantics (Gap 5, approved rulings): everything the user has
    confirmed survives by name — design languages and environments keep
    their notes, keywords, and location assignments; the fresh read's finds
    that don't match a confirmed name arrive as PROPOSED; answered questions
    carry over untouched. A first run (no prior analysis) returns the fresh
    read as-is — its worlds stand as confirmed by default (confirmation is
    the default state, not a badge)."""
    if not prior:
        return fresh
    out = dict(fresh)
    for field in ("design_worlds", "environments"):
        if field not in fresh and field not in prior:
            continue
        kept = [w for w in (prior.get(field) or [])
                if w.get("name") and w.get("status") != "PROPOSED"]
        have = {str(w["name"]).casefold() for w in kept}
        for w in (fresh.get(field) or []):
            name = str(w.get("name", "")).casefold()
            if name and name not in have:
                kept.append({**w, "status": "PROPOSED"})
                have.add(name)
        out[field] = kept
    if prior.get("question_answers"):
        out["question_answers"] = prior["question_answers"]
    return out


def faction_self_check(analysis: dict, provider: str = "gemini") -> list[dict]:
    """Gap 5's second pass: one cheap re-read hunting for named groups no
    design language covers. The covered list is the analysis worlds PLUS the
    Bible's current language sections — the Bible can hold confirmed
    languages the analysis never emitted. Returns uncovered groups as
    PROPOSED worlds; the model never adds a language itself."""
    from . import bible

    if provider == "mock":
        return []  # the mock scan proposes nothing beyond its own read
    covered = [str(w.get("name", "")) for w in analysis.get("design_worlds", [])
               if w.get("name")]
    for n in bible.design_language_names():
        if n not in covered:
            covered.append(n)
    doc, mime = autofill._screenplay_bytes()
    instructions = (
        "You are auditing a screenplay read for missed visual cultures. List "
        "every named faction, order, culture, corporation, or recurring group "
        "in the attached screenplay. For each, decide which of these design "
        "languages covers it:\n"
        + "\n".join(f"- {n}" for n in covered)
        + "\n\nReturn ONLY a JSON object with exactly this shape:\n"
          '{"missing": [\n'
          '  {"name": "a group with its own visual identity that NONE of the '
          'design languages above covers",\n'
          '   "description": "1-2 sentences on what it is and what defines its look",\n'
          '   "keywords": ["lowercase", "trigger", "words"]}\n'
          "]}\n"
          "missing must contain only groups with a distinct visual identity "
          "that no listed language covers. Do not re-litigate, rename, or "
          'include the listed languages. If everything is covered, return '
          '{"missing": []}.')
    draft_fn = autofill._draft_openai if provider == "openai" else autofill._draft_gemini
    result, _model = draft_fn(doc, mime, instructions)
    known = {c.casefold() for c in covered}
    out = []
    for m in result.get("missing", []):
        name = str(m.get("name", "")).strip() if isinstance(m, dict) else ""
        if not name or name.casefold() in known:
            continue
        out.append({"name": name,
                    "description": str(m.get("description", "")),
                    "keywords": [str(k) for k in (m.get("keywords") or [])],
                    "status": "PROPOSED", "source": "self-check"})
    return out


def _bible_instructions(answers: dict) -> str:
    worlds = answers.get("worlds") or []
    world_lines = "\n".join(
        f"- {w.get('name', '?')}: {w.get('notes') or w.get('description') or ''}"
        f" (keywords: {', '.join(w.get('keywords', []) or [])})"
        for w in worlds)
    envs = answers.get("environments") or []
    env_lines = "\n".join(
        f"- {e.get('name', '?')}: {e.get('notes') or ''}" for e in envs)
    refs_note = ""
    if answers.get("reference_roles"):
        refs_note = ("\nATTACHED REFERENCE PHOTOS — study them; each controls only "
                     "its stated scope. Fold what they show into the relevant "
                     "sections:\n"
                     + "\n".join(f"- image {i + 1}: {r}" for i, r in
                                 enumerate(answers["reference_roles"])))
    return f"""You are a film production designer writing the locked Art Direction Bible
for this screenplay (attached). The director has answered an interview; the bible must
reflect their answers and the screenplay's evidence — never your own inventions.

THE FOUR ANCHORS (ruled structure). The attached style anchors divide into
THREE MOVIE PARAMETERS and ONE BOARD PARAMETER, and the bible is structured
by that split:
- WORLD_TEXTURE (movie): the world's condition — wear, patina, entropy.
  Feeds Overall Visual Identity, Design Languages, Core Material Language.
- COLOR_PALETTE (movie): the film's color language — permitted hues, value
  key, saturation limits. Feeds Environments and Lighting Language.
- CINEMATOGRAPHY_STYLE (movie): light behaviour, lens and framing feel.
  Feeds Lighting Language and Composition Rules.
- BOARD_RENDERING_STYLE (board): how the BOARDS are drawn. It says nothing
  about the film's world and feeds ONLY the Rendering Language and
  Production Board Presentation sections.
HARD RULE: the movie sections describe the FILM, never the medium — no
"painterly", "gouache", "photorealistic" or any rendering-technique
language outside Rendering Language and Production Board Presentation.
The film would be the same film boarded in a different medium.

DIRECTOR'S ANSWERS — BINDING. These are decisions, not suggestions: build
the Overall Visual Identity, Rendering Language and Lighting sections
AROUND them, carry their concrete vocabulary into the bible verbatim, and
translate the never-list item for item into the Avoid list. Where an
answer conflicts with your own instinct, the answer wins.
- Visual touchstones (films/artists/eras it should feel like): {answers.get('touchstones') or 'not specified — propose from the screenplay, mark PROPOSED'}
- Medium and finish: {answers.get('medium') or 'not specified — propose, mark PROPOSED'}
- Palette and light bias: {answers.get('palette') or 'not specified — propose, mark PROPOSED'}
- It must NEVER look like: {answers.get('never') or 'not specified'}
- Additional notes: {answers.get('notes') or 'none'}

DESIGN LANGUAGES (one ## section each, in this order — first is the default world):
{world_lines or '- derive 2-4 from the screenplay'}

ENVIRONMENTS (one ### entry each under '## Environments' — the physical worlds
panels live in; palette, light, and atmosphere only, never culture):
{env_lines or '- none identified — omit the Environments section entirely'}
{refs_note}

OUTPUT FORMAT — return ONLY markdown in EXACTLY this section structure
(these headings are parsed by software; keep them verbatim where shown):

# <Project> — Locked Art Direction Bible

## Status
(one line: authoritative visual context; agents must not reinterpret without user instruction)

## Overall Visual Identity
(bulleted feel/influences from the touchstones + screenplay; end with one line on what the world must feel designed for)

## Rendering Language
### Required
(bullets)
### Avoid
(bullets — seed from the director's never-list)

## Design Languages

## <World 1 name>
Keywords: <comma-separated lowercase trigger words>
**Design language:** <one line>
(bullets)

## <World 2 name>
(same shape, for each world)

## Environments

### <Environment 1 name>
(bullets — the palette, light, and atmosphere of this world)

### <Environment 2 name>
(same shape, for each environment; omit the whole section if none were listed)

## Core Material Language
### <World 1 name>
(material bullets)
### <World 2 name>
(…)

## Lighting Language
(contrast rules; then "Approved atmosphere studies include:" with 6-8 named studies)

## Composition Rules
(board readability rules)

## Character Presentation
(grounding rules; do-not-invent list)

## Production Board Presentation
(preferred board characteristics)

## Current Locked Scene-Specific Lessons

(empty for now — lessons accrue from approved/rejected work)

## Drift Prevention Rule
(the five-question guardian checklist: which locked rules apply, which references
apply, what is prohibited, what is scene-specific, what must remain unchanged;
if unknown, generation stops until checked)

Anything you proposed without director input must be marked (PROPOSED) so the
director can confirm or replace it during review."""


def draft_bible(answers: dict, provider: str = "gemini") -> dict:
    if provider == "mock" and generate.mock_enabled():
        from . import mockflow
        return {"markdown": mockflow.bible_markdown(answers),
                "model": mockflow.MODEL_NAME}
    doc, mime = autofill._screenplay_bytes()
    ref_ids = answers.get("ref_ids") or []
    ref_paths, roles = [], []
    for rid in ref_ids:
        r = store.get_reference(rid)
        p = store.reference_image_path(rid)
        if r and p:
            # Render-ready always (user ruling 2026-08-02): an engine that
            # cannot read a reference would either fail the draft or draft
            # the bible WITHOUT considering it — both unacceptable. Same
            # transcode backstop as panel generation.
            ref_paths.append(generate._render_ready(p))
            roles.append(f"{r.get('role', 'reference')} — {r.get('notes', '')}".strip(" —"))
    answers = dict(answers)
    answers["reference_roles"] = roles
    instructions = _bible_instructions(answers)

    if provider == "openai":
        import base64
        import mimetypes
        client = generate._openai_client()
        model = generate._chat_model()
        content = [{"type": "input_file", "filename": "screenplay.pdf",
                    "file_data": "data:application/pdf;base64,"
                                 + base64.b64encode(doc).decode()}
                   if mime == "application/pdf" else
                   {"type": "input_text",
                    "text": "SCREENPLAY FOLLOWS\n==================\n"
                            + doc.decode("utf-8", "replace")}]
        for p in ref_paths:
            m = mimetypes.guess_type(p.name)[0] or "image/png"
            content.append({"type": "input_image",
                            "image_url": f"data:{m};base64,"
                                         + base64.b64encode(p.read_bytes()).decode()})
        content.append({"type": "input_text", "text": instructions})
        response = client.responses.create(
            model=model, input=[{"role": "user", "content": content}])
        text = (getattr(response, "output_text", "") or "").strip()
    else:
        from google.genai import types
        from PIL import Image
        client = generate._client()
        model = autofill.pick_text_model(client)
        contents: list = [types.Part.from_bytes(data=doc, mime_type=mime)]
        for p in ref_paths:
            im = Image.open(p)
            im.load()  # release the handle before the long model call
            contents.append(im)
        contents.append(instructions)
        response = client.models.generate_content(model=model, contents=contents)
        text = (response.text or "").strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("markdown"):
            text = text[len("markdown"):]
        text = text.strip()
    if not text or "## Rendering Language" not in text:
        raise autofill.AutofillError(
            "The model did not return a bible in the expected structure. Try again.")
    return {"markdown": text, "model": model}
