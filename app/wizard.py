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
  "key_locations": ["recurring locations that boards will likely depict"],
  "unresolved": ["visual questions the screenplay leaves open"]
}
Identify 2-5 design languages ("design_worlds" in the JSON) — distinct visual
cultures that each need their own design language (protagonist world,
antagonist institutions, exotic technology, etc.).
List every subject the art department needs visual reference for: main
and supporting characters, hero vehicles, key props. Subtitles and traits are
clipped production-note prose drawn ONLY from what the screenplay states or
directly implies — no invented biography. Only what the screenplay supports;
do not invent."""


def analyze_screenplay(provider: str = "gemini") -> dict:
    doc, mime = autofill._screenplay_bytes()
    instructions = (
        "You are the production designer's research assistant. Read the attached "
        "screenplay and identify the visual worlds a film art department would "
        "need to design.\n\n" + ANALYZE_SCHEMA_NOTE)
    draft_fn = autofill._draft_openai if provider == "openai" else autofill._draft_gemini
    result, model = draft_fn(doc, mime, instructions)
    result["model"] = model
    return result


def _bible_instructions(answers: dict) -> str:
    worlds = answers.get("worlds") or []
    world_lines = "\n".join(
        f"- {w.get('name', '?')}: {w.get('notes') or w.get('description') or ''}"
        f" (keywords: {', '.join(w.get('keywords', []) or [])})"
        for w in worlds)
    refs_note = ""
    if answers.get("reference_roles"):
        refs_note = ("\nATTACHED REFERENCE PHOTOS — study them; each controls only "
                     "its stated scope. Fold what they show (materials, light, "
                     "construction logic, palette) into the relevant sections:\n"
                     + "\n".join(f"- image {i + 1}: {r}" for i, r in
                                 enumerate(answers["reference_roles"])))
    return f"""You are a film production designer writing the locked Art Direction Bible
for this screenplay (attached). The director has answered an interview; the bible must
reflect their answers and the screenplay's evidence — never your own inventions.

DIRECTOR'S ANSWERS
- Visual touchstones (films/artists/eras it should feel like): {answers.get('touchstones') or 'not specified — propose from the screenplay, mark PROPOSED'}
- Medium and finish: {answers.get('medium') or 'not specified — propose, mark PROPOSED'}
- Palette and light bias: {answers.get('palette') or 'not specified — propose, mark PROPOSED'}
- It must NEVER look like: {answers.get('never') or 'not specified'}
- Additional notes: {answers.get('notes') or 'none'}

DESIGN LANGUAGES (one ## section each, in this order — first is the default world):
{world_lines or '- derive 2-4 from the screenplay'}
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
    doc, mime = autofill._screenplay_bytes()
    ref_ids = answers.get("ref_ids") or []
    ref_paths, roles = [], []
    for rid in ref_ids:
        r = store.get_reference(rid)
        p = store.reference_image_path(rid)
        if r and p:
            ref_paths.append(p)
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
            contents.append(Image.open(p))
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
