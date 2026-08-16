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

import re

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
  "acts": [
    {"n": 1, "title": "SHORT UPPERCASE NAME FOR THIS ACT",
     "turn": "the scene or beat this act ends on, in the screenplay's own words"}
  ],
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
do not invent.
Name the three acts ("acts"). A feature screenplay has a three-act shape
whether or not it prints ACT headings, and most do not print them — read the
turns and name what each act is ABOUT, in two or three words, uppercase, in
the screenplay's own vocabulary (THE FALL, THE LONG ROAD, TERRA NOVA). The
name is a reading of the story, not a summary of its locations. Give the beat
each act turns on so the reading can be checked. Return exactly three unless
the screenplay itself prints a different number of act headings."""


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
    result, model = autofill._draft(provider, doc, mime, instructions)
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
    result, _model = autofill._draft(provider, doc, mime, instructions)
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

SECTION FENCE (user-hit 2026-08-06): Rendering Language describes the
medium and finish of a SINGLE panel's artwork only — how one image is
painted: medium, brushwork, surface, finish. Board architecture — title
blocks, grids, modules, image cells, hero layouts, captions, callouts,
palette bars, annotations, information hierarchy — belongs ONLY in
Production Board Presentation. The app assembles boards and draws their
typography itself; the model renders single full-bleed panels. A
Rendering Language bullet that describes a board SHEET rather than a
panel's paint is wrong and will corrupt every render prompt. If an
attached BOARD_RENDERING_STYLE reference shows a full board layout,
take only its paint from it for Rendering Language; its layout goes to
Production Board Presentation.

DIRECTOR'S ANSWERS — BINDING. These are decisions, not suggestions: build
the Overall Visual Identity, Rendering Language and Lighting sections
AROUND them, carry their concrete vocabulary into the bible verbatim, and
translate the never-list item for item into the Avoid list. Where an
answer conflicts with your own instinct, the answer wins.
- WORLD_TEXTURE in words (wear, patina, entropy): {answers.get('texture') or 'not specified — propose, mark PROPOSED'}
- COLOR_PALETTE in words (hue, value key, saturation): {answers.get('palette') or 'not specified — propose, mark PROPOSED'}
- CINEMATOGRAPHY_STYLE in words (light behaviour, lens, framing): {answers.get('light') or 'not specified — propose, mark PROPOSED'}
- BOARD_RENDERING_STYLE in words (medium and finish): {answers.get('medium') or 'not specified — propose, mark PROPOSED'}
- It must NEVER look like: {answers.get('never') or 'not specified'}
- Additional notes: {answers.get('notes') or 'none'}

Each of those four answers is the WORDS half of the anchor it names, and
carries exactly that anchor's scope — the same fence its attached photos
carry. An answer feeds only its anchor's sections. Where an anchor has
both words and photos, they describe one thing: read them together, and
if they genuinely conflict the director's words win.

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
(bulleted feel/influences from the anchors + screenplay; end with one line on what the world must feel designed for)

## Rendering Language
### Required
(bullets — a single panel's medium and finish ONLY, per the SECTION FENCE)
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

    if provider in ("anthropic", "openrouter"):
        from . import narrative
        try:
            text, model = narrative.complete(
                provider, doc, mime, instructions, tuple(ref_paths))
        except narrative.NarrativeError as e:
            raise autofill.AutofillError(str(e)) from e
    elif provider == "openai":
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


# --------------------------------------------------------------- swatches
# NON-CANON (user-directed 2026-08-05, awaiting the designer's UI/UX
# pass). A swatch is an ordinary COLOR_PALETTE reference whose pixels are
# pure color — never text, since engines study these images. Generation
# is Bible-cited: the narrative model may only propose colors it can
# ground in a line of the saved Bible, grouped by Design Language, and
# nothing is persisted until the user approves a proposal.

_SWATCH_SCHEMA_NOTE = """Return ONLY a JSON array (no prose, no code fence) with this shape:
[
  {"language": "<a ## Design Language section title, verbatim>",
   "swatches": [
     {"name": "OXIDE RUST",
      "hex": "#8A4B2E",
      "pair_hex": null,
      "hero": false,
      "cite": "GT40 yellow"}
   ]}
]
Rules:
- 4 to 8 swatches per design language, nothing outside the Bible's languages.
- Every swatch must be grounded in the Bible — a color the Bible cannot
  support is not proposed.
- "cite" is a LABEL, not a quotation: the film's own short name for this
  color, worded as the Bible words it. "cold GRM white light".
  "GT40 yellow". "Onyx Unit black". TWO TO FIVE WORDS. Never a sentence,
  never a clause with commas, no trailing punctuation. Prefer the film's
  own proper nouns — units, factions, vehicles, materials — over generic
  color talk. If the Bible gives the color no name, use the shortest
  phrase that names where the color comes from.
- Exactly ONE swatch per design language has "hero": true — the color a
  production designer would splash through that faction's sets, vehicles
  and costumes so the area reads on sight. Every other swatch is false.
- "pair_hex" is for a VALUE-KEY PAIR only: the same hue at the opposite
  value key (light-key/dark-key). Use it sparingly, null otherwise.
- Never propose time-of-day sets — a panel's hour is per-panel lighting,
  not palette.
- Uppercase hex like #8A4B2E. Names are short and concrete."""

# A label, not a paragraph (user 2026-08-06). The model is asked for the
# film's own name for the colour; anything longer is cut down to a label
# rather than shown as a run-on quote the eye skips.
_CITE_WORDS = 6
_CITE_CHARS = 44


def short_cite(v) -> str:
    """First clause, clamped to a label. Returns '' when nothing survives."""
    t = re.sub(r"\s+", " ", str(v or "")).strip().strip('"“”\'')
    t = re.split(r"[.;:—]|,\s", t)[0].strip()
    words = t.split()
    if len(words) > _CITE_WORDS:
        t = " ".join(words[:_CITE_WORDS])
    if len(t) > _CITE_CHARS:
        t = t[:_CITE_CHARS].rstrip()
    return t.strip(" ,;:-—\"'“”").strip()

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _clean_hex(v) -> str:
    v = str(v or "").strip()
    if v and not v.startswith("#"):
        v = "#" + v
    return v.upper() if _HEX_RE.match(v) else ""


def parse_swatch_proposals(text: str) -> list[dict]:
    """Strict parse of the model's JSON: bad hexes are dropped, groups are
    clamped to 8 swatches, empty groups vanish. Raises AutofillError when
    nothing usable survives."""
    import json

    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    start, end = t.find("["), t.rfind("]")
    if start < 0 or end <= start:
        raise autofill.AutofillError(
            "The model did not return the swatch JSON shape. Try again.")
    try:
        raw = json.loads(t[start:end + 1])
    except ValueError as e:
        raise autofill.AutofillError(
            "The model returned unreadable swatch JSON. Try again.") from e
    return normalize_swatch_groups(raw)


def normalize_swatch_groups(raw) -> list[dict]:
    """The one shape swatches take, whatever produced them. The mock engine
    runs through here too — otherwise the debug path drifts from the real
    one and a capture taken against it proves nothing."""
    groups = []
    for g in raw if isinstance(raw, list) else []:
        if not isinstance(g, dict):
            continue
        swatches = []
        for s in (g.get("swatches") or [])[:8]:
            if not isinstance(s, dict):
                continue
            hexv = _clean_hex(s.get("hex"))
            if not hexv:
                continue
            pair = _clean_hex(s.get("pair_hex")) or None
            swatches.append({
                "name": str(s.get("name") or hexv).strip()[:48].upper(),
                "hex": hexv, "pair_hex": pair,
                "hero": bool(s.get("hero")),
                "cite": short_cite(s.get("cite")),
            })
        if swatches:
            # Exactly one hero per language — the colour that gets splashed
            # through that faction's sets. The model is asked for one; if it
            # flags several the first wins, and if it flags none the group
            # simply has no hero rather than one invented here.
            seen_hero = False
            for sw in swatches:
                if sw["hero"] and not seen_hero:
                    seen_hero = True
                else:
                    sw["hero"] = False
            groups.append({"language": str(g.get("language") or "PALETTE")
                          .strip()[:64], "swatches": swatches})
    if not groups:
        raise autofill.AutofillError(
            "The model proposed no swatches the Bible could ground. Try again.")
    return groups


HERO_MARK = "HERO"


def parse_swatch_notes(notes: str) -> dict:
    """Read a swatch's notes back into fields.

    Two shapes exist and neither is positional enough to trust blindly:
    proposals write LANGUAGE · NAME · HEX · CITE, manual swatches write
    NAME · HEX · CITE. The hex is the one segment with a fixed SHAPE, so
    it is found first and everything else is placed relative to it.
    """
    parts = [p.strip() for p in str(notes or "").split(" · ")]
    hero = bool(parts) and parts[-1] == HERO_MARK
    if hero:
        parts = parts[:-1]
    hx = next((i for i, p in enumerate(parts)
               if _HEX_RE.match(p.split(" / ")[0].strip())), None)
    if hx is None:
        return {"language": "", "name": parts[0] if parts else "",
                "hex": "", "pair_hex": None, "cite": "", "hero": hero}
    hexes = [x.strip() for x in parts[hx].split(" / ")]
    return {
        "language": parts[0] if hx >= 2 else "",
        "name": parts[hx - 1] if hx >= 1 else "",
        "hex": hexes[0],
        "pair_hex": hexes[1] if len(hexes) > 1 else None,
        "cite": " · ".join(parts[hx + 1:]),
        "hero": hero,
    }


def _with_hero(notes: str, hero: bool) -> str:
    parts = [p.strip() for p in str(notes or "").split(" · ") if p.strip()]
    if parts and parts[-1] == HERO_MARK:
        parts = parts[:-1]
    if hero:
        parts.append(HERO_MARK)
    return " · ".join(parts)


def set_hero(ref_id: str) -> dict:
    """Name this swatch the hero of its design language (PALETTE_GROUPS_PLAN
    §4). Single-valued: every other palette swatch sharing the language
    loses the mark in the same pass. A swatch with no language segment is
    its own group, so it only ever affects itself."""
    ref = store.get_reference(ref_id)
    if ref is None:
        raise KeyError(ref_id)
    if store.role_head(ref.get("role", "")) != "COLOR_PALETTE":
        raise autofill.AutofillError(
            f"{ref_id} is not a palette swatch — only a swatch can be a hero.")

    language = parse_swatch_notes(ref.get("notes", ""))["language"]
    updates = {ref_id: _with_hero(ref.get("notes", ""), True)}
    if language:
        for other in store.list_references():
            if (other["id"] != ref_id
                    and store.role_head(other.get("role", "")) == "COLOR_PALETTE"
                    and parse_swatch_notes(other.get("notes", ""))["language"] == language
                    and parse_swatch_notes(other.get("notes", ""))["hero"]):
                updates[other["id"]] = _with_hero(other.get("notes", ""), False)
    store.update_reference_notes(updates)
    return {"language": language, "hero": ref_id,
            "cleared": [k for k in updates if k != ref_id]}


def recolor_swatch(ref_id: str, hexv: str, pair: str | None = None) -> dict:
    """Repaint an existing swatch (user 2026-08-06). The reference keeps its
    id, its language, its name and its place in the review strip — only the
    pixels and the hex in its notes change, because a swatch IS its color
    and a new id would orphan every approval already recorded against it."""
    hexv = _clean_hex(hexv)
    if not hexv:
        raise autofill.AutofillError("A swatch needs a full hex — like #8A4B2E.")
    pair = _clean_hex(pair) or None

    ref = store.get_reference(ref_id)
    if ref is None:
        raise KeyError(ref_id)
    if store.role_head(ref.get("role", "")) != "COLOR_PALETTE":
        raise autofill.AutofillError(
            f"{ref_id} is not a palette swatch — only a swatch has a color to edit.")

    store.replace_reference_image(
        ref_id, render_swatch_png(hexv, pair),
        f"{(ref.get('original_name') or ref_id).rsplit('.', 1)[0]}.png")

    # Proposals note LANGUAGE · NAME · HEX · CITE, manual swatches note
    # NAME · HEX · CITE — the hex is not at a fixed index, so it is found
    # by shape. Nothing else in the notes is touched.
    parts = str(ref.get("notes") or "").split(" · ")
    swatch_hex = hexv + (f" / {pair}" if pair else "")
    for i, seg in enumerate(parts):
        if _HEX_RE.match(seg.split(" / ")[0].strip()):
            parts[i] = swatch_hex
            store.update_reference(ref_id, {"notes": " · ".join(parts)})
            break
    return {**store.get_reference(ref_id), "hex": hexv, "pair_hex": pair}


def render_swatch_png(hexv: str, pair: str | None = None) -> bytes:
    """Pure color, no text ever — engines study these pixels. A value-key
    pair renders as two vertical halves."""
    import io as _io

    from PIL import Image

    img = Image.new("RGB", (640, 400), hexv)
    if pair:
        img.paste(Image.new("RGB", (320, 400), pair), (320, 0))
    buf = _io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def persist_swatch_proposals(groups: list[dict]) -> list[dict]:
    """D8 ruling: proposals persist as PROVISIONAL references so a
    rejection leaves a record. Each swatch gains the ref id it landed
    under; notes carry language · name · hex · cite; provenance is
    source: swatch-proposal until the user's verdict."""
    for g in groups:
        for sw in g["swatches"]:
            notes = " · ".join(x for x in [
                # NOT uppercased: the viewer shows the language as the
                # Bible words it, and uppercasing here loses "GRM" vs
                # "Beltminer Technology" for good.
                g["language"], sw["name"],
                sw["hex"] + (f" / {sw['pair_hex']}" if sw.get("pair_hex") else ""),
                sw.get("cite", ""),
                # Trailing marker so a reload can rebuild the hero without a
                # second store — read and popped by the strip's restore.
                HERO_MARK if sw.get("hero") else ""] if x)
            ref = store.add_reference(
                f"{sw['name'].lower().replace(' ', '-')}.png",
                render_swatch_png(sw["hex"], sw.get("pair_hex")),
                "COLOR_PALETTE", [], [], notes, source="swatch-proposal")
            sw["ref_id"] = ref["id"]
    return groups


def swatches_in_play(languages: list[str] | None = None) -> tuple[dict, dict]:
    """What the palette already holds, and what it has already refused.

    A rescan that re-proposes an approved colour is noise; one that
    re-proposes a rejected colour is worse — it asks the designer to make
    the same decision twice. Both lists go into the prompt.
    """
    live: dict[str, list[dict]] = {}
    dead: dict[str, list[dict]] = {}
    for r in store.list_references():
        if store.role_head(r.get("role", "")) != "COLOR_PALETTE":
            continue
        p = parse_swatch_notes(r.get("notes", ""))
        if not p["hex"]:
            continue
        if languages and p["language"] not in languages:
            continue
        (dead if r.get("status") == "REJECTED" else live).setdefault(
            p["language"], []).append(p)
    return live, dead


def rescan_note(languages: list[str] | None = None, note: str = "",
                deep: bool = False) -> str:
    """The part of the instruction that makes a pass a RESCAN rather than a
    repeat of the first one (user 2026-08-07)."""
    live, dead = swatches_in_play(languages)
    out = []
    if languages:
        out.append("Propose swatches ONLY for these design languages, and "
                   "nothing else: " + ", ".join(languages) + ".")
    have = [f"{p['hex']} ({p['name']})" for ps in live.values() for p in ps]
    if have:
        out.append("The palette ALREADY HOLDS these — do not propose them "
                   "again, and do not propose near-duplicates. Propose what "
                   "is MISSING: " + ", ".join(have) + ".")
    refused = [f"{p['hex']} ({p['name']})" for ps in dead.values() for p in ps]
    if refused:
        out.append("These were already REJECTED by the designer. Do not "
                   "propose them again: " + ", ".join(refused) + ".")
    if deep:
        out.append("This is a DEEP pass — the obvious colours are already "
                   "found. Read for the ones the Bible mentions in passing: "
                   "materials and their finish, uniforms and insignia, "
                   "signage and hazard markings, practical light sources, "
                   "corrosion and staining, and any colour named as a "
                   "faction's own. Propose 4 to 8 per design language.")
    if note.strip():
        out.append('The production designer says: "' + note.strip()[:400]
                   + '" — treat that as the brief for this pass. Propose '
                     "colours that answer it, still grounded in the Bible.")
    return ("\n\n" + "\n".join(out)) if out else ""


def generate_swatches(provider: str = "gemini",
                      languages: list[str] | None = None,
                      note: str = "", deep: bool = False) -> dict:
    """Bible-cited palette proposals. Nothing is persisted here — the
    client holds the proposals and each approval creates a reference.

    languages / note / deep make it a RESCAN: the same act aimed at one
    design language, told what the designer thinks is missing, and told
    what the palette already holds so it stops re-proposing it."""
    from . import bible

    bible_text = bible.load_text().strip()
    if not bible_text:
        raise autofill.AutofillError(
            "No saved Art Direction Bible yet — swatches are grounded in it. "
            "Draft and save the Bible first (step 5).")

    if provider == "mock" and generate.mock_enabled():
        from . import mockflow
        groups = normalize_swatch_groups(mockflow.mock_swatches(bible_text))
        if languages:
            groups = [g for g in groups if g["language"] in languages]
        if not groups:
            raise autofill.AutofillError(
                "The mock engine has nothing for "
                + (", ".join(languages) if languages else "this Bible") + ".")
        return {"groups": persist_swatch_proposals(groups),
                "model": mockflow.MODEL_NAME}

    instructions = (
        "You are the film's production designer. The saved Art Direction "
        "Bible follows. Propose the film's color swatches — grouped by its "
        "## Design Language sections, every color grounded in a quoted "
        "Bible line."
        + rescan_note(languages, note, deep)
        + "\n\n" + _SWATCH_SCHEMA_NOTE)
    doc = bible_text.encode("utf-8")
    mime = "text/plain"

    if provider in ("anthropic", "openrouter"):
        from . import narrative
        try:
            text, model = narrative.complete(provider, doc, mime,
                                             instructions, ())
        except narrative.NarrativeError as e:
            raise autofill.AutofillError(str(e)) from e
    elif provider == "openai":
        client = generate._openai_client()
        model = generate._chat_model()
        response = client.responses.create(
            model=model,
            input=[{"role": "user", "content": [
                {"type": "input_text",
                 "text": "ART DIRECTION BIBLE FOLLOWS\n" + bible_text},
                {"type": "input_text", "text": instructions}]}])
        text = (getattr(response, "output_text", "") or "").strip()
    else:
        client = generate._client()
        model = autofill.pick_text_model(client)
        response = client.models.generate_content(
            model=model, contents=[bible_text, instructions])
        text = (response.text or "").strip()

    return {"groups": persist_swatch_proposals(parse_swatch_proposals(text)),
            "model": model}


ACTS_SCHEMA_NOTE = """Return ONLY a JSON object with exactly this shape:
{
  "acts": [
    {"n": 1, "title": "SHORT UPPERCASE NAME, TWO OR THREE WORDS",
     "turn": "the scene or beat this act ends on, in the screenplay's own words"}
  ]
}
Name the three acts. A feature screenplay has a three-act shape whether or
not it prints ACT headings, and most do not print them — read the turns and
name what each act is ABOUT, in the screenplay's own vocabulary. The name is
a reading of the story, not a summary of its locations, and not a genre
label. Give the beat each act turns on so the reading can be checked.
Return exactly three unless the screenplay itself prints a different number
of act headings."""


def name_acts(provider: str = "gemini") -> dict:
    """Name the acts and NOTHING else.

    A full re-scan would rewrite design languages, environments and
    subjects the user has curated — on the draft this was written for,
    eight worlds, five environments and forty-four subjects. Naming the
    acts is one small read, so it gets its own call and merges one key
    into the stored analysis (user 2026-08-16: "No Act Titles", on an
    analysis that predates the field).
    """
    from . import autofill as _af
    if provider == "mock" and generate.mock_enabled():
        # the zero-cost path reads nothing — that is the point of it
        acts = [{"n": i, "title": t, "turn": "mock"} for i, t in
                enumerate(["THE SETUP", "THE LONG MIDDLE", "THE RECKONING"], 1)]
        model = "mock"
    else:
        doc, mime = _af._screenplay_bytes()
        raw, model = _af._draft(provider, doc, mime, ACTS_SCHEMA_NOTE)
        acts = raw.get("acts") if isinstance(raw, dict) else None
        if not isinstance(acts, list) or not acts:
            raise autofill.AutofillError(
                "the model returned no acts — try again, or a different model")

    clean = []
    for i, a in enumerate(acts, 1):
        if not isinstance(a, dict):
            continue
        title = str(a.get("title", "")).strip().upper()
        if not title:
            continue
        clean.append({"n": int(a.get("n") or i), "title": title,
                      "turn": str(a.get("turn", "")).strip()})
    if not clean:
        raise autofill.AutofillError("the model returned no usable act names")

    analysis = store.load_wizard_analysis() or {}
    analysis["acts"] = clean
    analysis["acts_named_by"] = model
    store.save_wizard_analysis(analysis)
    return {"acts": clean, "model": model}
