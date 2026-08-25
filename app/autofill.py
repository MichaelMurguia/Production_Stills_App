from __future__ import annotations

import json
import re

from . import generate, paths, store

# Preference order — first model the account can access wins.
TEXT_MODEL_PREFERENCES = [
    "gemini-3.5-flash",
    "gemini-3-pro",
    "gemini-3-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
]

EVIDENCE_CLASSES = {
    "SCRIPT_EXPLICIT", "SCRIPT_NECESSARY_INFERENCE", "VISUAL_CANON_LOCKED",
    "USER_DIRECTED", "STRONG_INFERENCE", "WEAK_INFERENCE",
    "PROPOSED_NOT_CANON", "UNSUPPORTED",
}


NL = chr(10)
NLNL = NL + NL
TAB = chr(9)


class AutofillError(Exception):
    pass


def pick_text_model(client) -> str:
    try:
        available = {m.name.split("/")[-1] for m in client.models.list()}
    except Exception:
        return TEXT_MODEL_PREFERENCES[0]
    for name in TEXT_MODEL_PREFERENCES:
        if name in available:
            return name
    return TEXT_MODEL_PREFERENCES[0]


# SAME / CONTINUOUS / LATER are screenplay CONTINUITY markers, not hours —
# a slugline that says SAME is deferring to the scene before it. Recording
# one as the board's time of day states a light the script never gave
# (user 2026-08-07); the field stays empty and the designer picks.
_CONTINUITY = {"SAME", "CONTINUOUS", "LATER", "MOMENTS LATER", "MOMENTS",
               "SAME TIME", "CONT", "CONT'D", "PRESENT"}


def _real_hour(v) -> str:
    t = str(v or "").strip()[:60].upper()
    return "" if t in _CONTINUITY else t


def _screenplay_bytes() -> tuple[bytes, str]:
    state = store.load_app_state()
    rec = state.get("screenplay")
    if not rec:
        raise AutofillError("No screenplay uploaded. Add it on the Dashboard first.")
    # The efficient format first (user ruling 2026-08-02): extracted text
    # costs a fraction of PDF-per-page billing and prompt-caches across
    # scans, drafts and redrafts. The original file is the stated
    # fallback for image-only PDFs that yield no text.
    text = store.screenplay_text_cached()
    if text.strip():
        return text.encode("utf-8"), "text/plain"
    # The raw upload NEVER reaches a model (user rule 2026-08-16). It is
    # kept so the user can open and read it, and that is its whole job.
    # Sending it instead was a silent fallback that billed a PDF per page
    # on every scan, draft and redraft — the exact cost the extracted
    # text exists to avoid, and invisible at the moment it happened.
    # Refusing names the fix instead.
    raise AutofillError(
        f"No text could be extracted from {rec['file']} — it looks like an "
        "image-only PDF. The original is never sent to a model (it would "
        "cost a page at a time on every run), so re-export the screenplay "
        "with selectable text, or upload a .txt or .fountain, and try again.")


def _anchor_block(anchor: dict, board_type: str = "") -> str:
    """The deterministic scene quote, framed by the board's SHAPE.

    The quoting itself fixed a real bug (a machine slug lost to model fuzzy
    matching) and is kept absolute. What is NOT absolute is what the board
    is *about*: the old frame said "This board is about THESE scenes" for
    every board, derived only from the location name — so rewriting the
    brief produced a byte-identical anchor, and a location study asked for
    in prose came back as the seeded scene (user-hit 2026-08-07). The
    anchor supplies the evidence base; the board type states the shape.
    """
    n = anchor["scenes"]
    plural = "s" if n != 1 else ""
    head = (f"\n\nSCENE ANCHOR — DETERMINISTIC, NOT OPTIONAL. The subject names "
            f"the screenplay location \"{anchor['location']}\" ({n} scene{plural}). "
            "All of its scenes are quoted below verbatim from the attached "
            "screenplay.\n")
    if board_type == "LOCATION":
        shape = ("This is a LOCATION board: it is about THE PLACE across every "
                 "scene set there — not any single one of these scenes. Draw the "
                 "set, its structure, dressing and atmosphere from all of them "
                 "together, and do not let the first or longest scene stand in "
                 "for the location.\n")
    elif board_type == "SCENE":
        shape = ("This is a SCENE board: exactly one of the scenes below is the "
                 "subject — the one the brief names. The others are quoted as "
                 "context for the same set and are never the subject.\n")
    elif board_type in BOARD_TYPES:
        shape = (f"This is a {board_type} board. The scenes below are evidence "
                 "for it, not its subject.\n")
    else:
        shape = ("These scenes are the subject's evidence base; the brief above "
                 "states what shape the board takes.\n")
    tail = ("Every panel, evidence row and citation must anchor to the scenes "
            "below; any other location in the screenplay is context only and "
            "never the subject.\n\n")
    return head + shape + tail + anchor["text"]


def _scene_field(board_type: str) -> str:
    """The `scene` field's own wording. It said "describing the scene" for
    every board, so a LOCATION board was asked to describe a scene and
    obligingly described one (user-hit 2026-08-07)."""
    tail = ("Only screenplay-supported details — where the screenplay is "
            "silent, stay silent.")
    if board_type == "LOCATION":
        return ("one flowing paragraph (4-8 sentences) describing THE PLACE as "
                "the screenplay establishes it across every scene set there: "
                "its structure and layout, how it is dressed, what it contains "
                "and how that is arranged, and the light and atmosphere it "
                "carries. Do not narrate one scene's events. " + tail)
    return ("one flowing paragraph (4-8 sentences) describing the scene as the "
            "screenplay establishes it: the location and its structure, time of "
            "day and light, atmosphere, and the key contents and their "
            "arrangement. " + tail)


def _board_rule(board_type: str) -> str:
    """Stated board type as an absolute rule. Empty when the user left the
    shape to the model, so nothing changes for that path."""
    if board_type not in BOARD_TYPES:
        return ""
    return (f"\n- Board type for this board: {board_type}. This is the user's "
            "decision, not yours — return exactly this board_type and shape "
            "the panels for it.")


def _framing_rule() -> str:
    """A3 — the framing menu and the method for choosing from it.

    The research pass already reads the screenplay and writes each panel's
    purpose and required objects. It is the only pass that has read the
    scene, so it is the one that should name the shot — and naming it here
    makes the choice inspectable before the spend rather than inferable
    from the picture afterwards, which is the failure the whole framing
    feature exists to end.

    A lookup keyed on intent cannot do this, and that is worth stating
    because it was the first design and it is wrong: a surfer at 400mm and
    a race car at 24mm are both "action" and land on opposite rows
    (`Compressed crowd / city / pursuit` against `Threatening /
    confrontational proximity`). Choosing needs judgement about the shot,
    not a table lookup on a label.

    Where a grammar is already chosen, only its sanctioned rows are
    offered — a menu that includes a contradiction is a menu that will
    eventually be used to pick one. With no grammar, all twenty.
    """
    from . import camera_recipes as recipes
    rows = recipes.sanctioned(None)
    if not rows:
        return ""
    menu = "\n".join(
        f"    {r['key']} — {r['name']}: {r['focal']}, {r['aperture']}, "
        f"{r['relationship'].lower()}, {r['focus'].lower()} focus. {r['look']}"
        for r in rows)
    return f"""
- Name the FRAMING for each panel, as `camera_recipe`, from this list and no other.
  These are camera settings, not adjectives: a style can be satisfied by doing
  nothing, a focal length and an aperture cannot.
{menu}

  Choose by reasoning about the shot, in this order — never by matching the
  panel's genre to a row's name:
    1. What is this panel FOR — the question its purpose answers.
    2. Where does the weight sit: one face, a relationship, an object, a place,
       an event?
    3. What must stay READABLE, and what may be given up. This is the choice a
       list of adjectives never forces anyone to make, and it is the one that
       decides the row. A required object can be PRESENT without being SHARP —
       a character at 1.5m on a wide lens keeps the hull, the ramp and the
       figures behind her in frame, softer. Do not reject a row because the
       panel has many required objects.
    4. Then modifiers, as `camera_recipe_mods` — an object of axis:setting —
       and ONLY where this shot departs from the row's baseline, so the panel
       carries the difference rather than restating the row it already named.
  Give one line in `camera_recipe_why` saying why that row and not its nearest
  neighbour. A director has to be able to argue with it."""


def _instructions(subject_prompt: str, mode: str, prohibited: list[str],
                  board_type: str = "") -> str:
    return f"""You are the research agent for a film production art department on the project "{store.project_name()}".
The attached document is the current screenplay. Your task: draft a Production Generation
Specification for an art direction board about: {subject_prompt}

GOVERNING RULES — these are absolute:
- Your job is to EXTRACT what the screenplay establishes, not to invent. Unknown is an
  acceptable result. Empty space is preferable to invented content.
- Every claim must cite its screenplay evidence: quote the exact line or describe the exact
  scene in the "source" field of each evidence row.
- Classify every proposed visible object with one evidence_class:
  SCRIPT_EXPLICIT (directly stated), SCRIPT_NECESSARY_INFERENCE (physically unavoidable to
  depict explicit action), STRONG_INFERENCE (well supported, does not alter plot),
  WEAK_INFERENCE (plausible but nonessential — use sparingly, mark status HOLD),
  PROPOSED_NOT_CANON (only in DESIGN_EXPLORATION mode).
- Never use UNSUPPORTED objects. If the screenplay is silent on something important, list it
  in unresolved_questions instead of guessing.
- Do not force generic board categories. Panels must be driven by available evidence: if the
  screenplay supports 2 panels, return 2 panels, not 5.
- Board grammar (structure, never content): the first panel is the HERO — the board's
  central question, largest allocation (~50; ~60 for ASSET boards); remaining panels are
  supporting strips splitting the rest. Evidence rules the COUNT; this grammar rules the
  SHAPE.
- Mode for this board: {mode}.{_board_rule(board_type)}{_framing_rule()}
- Known prohibited inventions for this project (never include): {", ".join(prohibited) or "none recorded"}.

Return ONLY a JSON object with exactly this shape:
{{
  "subject": "short board subject line",
  "board_type": "SCENE if this is one specific screenplay scene | LOCATION if it is a place across scenes/times | ASSET if it is a prop, vehicle, or character",
  "setting": {{
    "int_ext": "INT | EXT | INT/EXT | empty if not applicable",
    "location": "the location name as the screenplay names it, empty for ASSET boards",
    "time_of_day": "for SCENE boards only: the slugline time (DAY, NIGHT, DUSK, DAWN, ...) taken from the actual scene heading — empty if the screenplay does not say or this is not a SCENE board"
  }},
  "scene": "{_scene_field(board_type)}",
  "render_intent": "one-sentence painterly production-board treatment note",
  "panels": [
    {{
      "id": "P01",
      "title": "short title",
      "purpose": "the single production question this panel answers",
      "required_objects": ["object, CARRYING ANY CONDITION THE SCREENPLAY STATES FOR IT IN THIS MOMENT - e.g. 'six descending figures, unweathered and pristine' rather than 'six descending figures'. A condition the screenplay states about these people or things HERE belongs in the object, because the object line is what the render is held to. Never invent a condition the screenplay does not state.", "..."],
      "forbidden_objects": ["likely-but-wrong additions to exclude", "..."],
      "scale": "AERIAL | EXTREME_WIDE | WIDE | MEDIUM | CLOSE | EXTREME_CLOSE | MACRO | MICRO",
      "camera_recipe": "one id from the framing list above",
      "camera_recipe_why": "one line: why this row and not its nearest neighbour",
      "camera_recipe_mods": {{"axis": "setting"}},
      "allocation_percent": 60
    }}
  ],
  "forbidden_elements": ["board-wide exclusions"],
  "evidence_ledger": [
    {{
      "panel_id": "P01",
      "object": "one required object",
      "evidence_class": "SCRIPT_EXPLICIT",
      "source": "exact quote or scene citation from the screenplay",
      "confidence": 0.95,
      "status": "PASS",
      "rationale": "why this evidence supports this object"
    }}
  ],
  "unresolved_questions": ["design questions the screenplay does not answer"]
}}

Every required object in every panel MUST have a matching evidence_ledger row with the same
panel_id and object text. Allocation percentages must total 100."""


# The board's shape is the user's decision when they state one (user-hit
# 2026-08-07: a scene-seeded draft was rewritten as a location study in
# prose and came back as the original scene). Prose is the weakest signal
# in the request; a stated type outranks the model's reading of it.
BOARD_TYPES = {"SCENE", "LOCATION", "ASSET", "LIGHTING_STUDY", "MASTER"}


def _cited_quote(source: str) -> str:
    """The citation inside a model-written `source` string. Models write
    either a bare sentence or a quoted one, so take the quoted span when
    there is one and the whole string otherwise — the same tolerance
    insights._QUOTE_RE gives legacy rows, without requiring the quotes."""
    from .insights import _QUOTE_RE
    m = _QUOTE_RE.findall(str(source or ""))
    return (m[0] if m else str(source or "")).strip()[:300]


def _coerce(draft: dict, spec_id: str, mode: str, board_type: str = "") -> dict:
    """Coerce model output into a valid spec structure; never trust it blindly."""
    panels_in = draft.get("panels") or []
    if not panels_in:
        raise AutofillError("The model returned no panels — likely found no usable "
                            "screenplay evidence for that subject.")
    panels, layout_panels = [], []
    for i, p in enumerate(panels_in, 1):
        pid = str(p.get("id") or f"P{i:02d}").strip().upper()
        # The shot lands in the camera enum or not at all (2026-08-12
        # review: pre-enum drafts persisted FULL_BODY/DETAIL verbatim and
        # the axis silently vanished from prompts). An empty scale means
        # inherit the production default — the resolve chain's own grammar.
        scale = str(p.get("scale", "") or "").strip().upper()
        scale = store.LEGACY_SCALE.get(scale, scale)
        if not store._camera_valid("scale", scale):
            scale = ""
        # A3 — the framing, if the model named one the document defines.
        # An unknown id is DROPPED rather than persisted: the panel then
        # inherits its grammar's default row, which is a real framing,
        # where a persisted unknown would resolve to nothing and put the
        # panel back to having no optics at all — the original failure.
        from . import camera_recipes as _rec
        rec_key = str(p.get("camera_recipe", "") or "").strip()
        if _rec.by_key(rec_key) is None:
            rec_key = ""
        rec_mods = {}
        raw_mods = p.get("camera_recipe_mods")
        if rec_key and isinstance(raw_mods, dict):
            axes = {a["key"]: {x["setting"] for x in a["settings"]} for a in _rec.axes()}
            rec_mods = {k: v for k, v in
                        ((str(k).strip(), str(v or "").strip()) for k, v in raw_mods.items())
                        if k in axes and v in axes[k]}
        panels.append({
            "id": pid,
            "title": str(p.get("title", ""))[:120],
            "purpose": str(p.get("purpose", ""))[:400],
            "required_objects": [str(x) for x in (p.get("required_objects") or [])][:12],
            "forbidden_objects": [str(x) for x in (p.get("forbidden_objects") or [])][:20],
            "evidence": ["SCRIPT_EXPLICIT"],
            "scale": scale,
            "camera_recipe": rec_key,
            # The justification is stored beside the choice, not thrown
            # away. A framing the director cannot argue with is a framing
            # they will overrule blind.
            "camera_recipe_why": str(p.get("camera_recipe_why", "") or "")[:240],
            "camera_recipe_mods": rec_mods,
            "composition_role": "hero" if i == 1 else "support",
        })
        try:
            alloc = float(p.get("allocation_percent", 0))
        except (TypeError, ValueError):
            alloc = 0.0
        layout_panels.append({"id": pid, "allocation_percent": alloc})

    total = sum(lp["allocation_percent"] for lp in layout_panels)
    if not (99.0 <= total <= 101.0):
        # Fallback is hero-weighted, not even: the first panel is the board's
        # central question (board grammar, 2026-07-30).
        if len(layout_panels) == 1:
            layout_panels[0]["allocation_percent"] = 100.0
        else:
            hero = 60.0 if str(draft.get("board_type", "")).strip().upper() == "ASSET" else 50.0
            rest = round((100.0 - hero) / (len(layout_panels) - 1), 2)
            layout_panels[0]["allocation_percent"] = hero
            for lp in layout_panels[1:]:
                lp["allocation_percent"] = rest
            layout_panels[0]["allocation_percent"] += round(
                100.0 - hero - rest * (len(layout_panels) - 1), 2)

    panel_ids = {p["id"] for p in panels}
    ledger = []
    # The screenplay, normalised once, for the citation check below. A
    # breakdown can carry dozens of rows and the document is ~130 KB.
    from . import insights as _ins
    hay = _ins.screenplay_haystack()
    demoted = 0

    for i, row in enumerate(draft.get("evidence_ledger") or [], 1):
        ec = str(row.get("evidence_class", "")).strip().upper()
        status = str(row.get("status", "HOLD")).strip().upper()
        if ec not in EVIDENCE_CLASSES:
            ec, status = "WEAK_INFERENCE", "HOLD"
        if ec in {"WEAK_INFERENCE", "PROPOSED_NOT_CANON"} and status == "PASS":
            status = "HOLD"  # the user, not the model, promotes weak evidence
        if status not in {"PASS", "HOLD", "REMOVE"}:
            status = "HOLD"
        pid = str(row.get("panel_id", "")).strip().upper()
        if pid not in panel_ids:
            continue
        try:
            confidence = min(max(float(row.get("confidence", 0.5)), 0.0), 1.0)
        except (TypeError, ValueError):
            confidence = 0.5

        # SCRIPT_EXPLICIT is the only class that makes a FALSIFIABLE claim:
        # it asserts a verbatim line exists in a document the server is
        # holding. Until 2026-08-17 nothing opened it (adversarial review
        # F21) — so the app guarded the class it could not check and waved
        # through the one it could, and the incentive ran backwards:
        # classifying strongly was the route to a row needing no human.
        #
        # DEMOTE, never drop. The row is the only record that this object
        # was proposed at all, and silently shrinking the ledger the user is
        # about to review would hide the model's reach rather than show it.
        # WEAK_INFERENCE rather than STRONG (user ruling 2026-08-17): a row
        # whose cited line is not in the screenplay is not a strong
        # inference FROM the screenplay, it is not an inference from it at
        # all — and WEAK spends the CANON_EXTRACTION budget of 2, so a draft
        # whose citations mostly cannot be found hits the cap and stops
        # instead of relabelling itself and sailing through.
        source = str(row.get("source", ""))[:500]
        rationale = str(row.get("rationale", ""))[:500]
        quote = _cited_quote(source)
        if ec == "SCRIPT_EXPLICIT" and not _ins.quote_is_in_screenplay(quote, hay):
            demoted += 1
            was = f"Model cited this as SCRIPT_EXPLICIT: {source}" if source else                 "Model cited this as SCRIPT_EXPLICIT with no quote."
            rationale = (was + (" — " + rationale if rationale else ""))[:500]
            ec, status, quote = "WEAK_INFERENCE", "HOLD", ""
            source = "Citation not found in the screenplay"

        ledger.append({
            "object_id": f"OBJ-{i:03d}",
            "panel_id": pid,
            "object": str(row.get("object", ""))[:200],
            "evidence_class": ec,
            "source": source,
            "quote": quote,
            "confidence": confidence,
            "status": status,
            "rationale": rationale,
        })
    if not ledger:
        raise AutofillError("The model returned no usable evidence rows.")
    claimed = sum(1 for r in (draft.get("evidence_ledger") or [])
                  if str(r.get("evidence_class", "")).strip().upper() == "SCRIPT_EXPLICIT")

    return {
        # Surfaced, not swallowed: the numbers that tell the user whether
        # this draft is worth reviewing, and whether the narrative model is
        # worth its price. Stored on the spec so the breakdown can state it
        # long after the draft call returned.
        "citations": {"claimed": claimed, "demoted": demoted},
        "specification_id": spec_id,
        "project": store.project_name(),
        "subject": str(draft.get("subject", ""))[:200] or spec_id,
        # Stated wins; the model's reading is the fallback only when the
        # user left it to the model.
        "board_type": (board_type if board_type in BOARD_TYPES
                       else (str(draft.get("board_type", "")).strip().upper()
                             if str(draft.get("board_type", "")).strip().upper()
                             in {"SCENE", "LOCATION", "ASSET"} else "LOCATION")),
        "setting": {
            "int_ext": str((draft.get("setting") or {}).get("int_ext", ""))[:10].upper(),
            "location": str((draft.get("setting") or {}).get("location", ""))[:120],
            "time_of_day": _real_hour(
                (draft.get("setting") or {}).get("time_of_day", "")),
        },
        "scene": str(draft.get("scene", ""))[:2000],
        "mode": mode,
        "status": "DRAFT",
        "revision": 1,
        "autofilled": True,
        "canon_sources": [
            {"id": "CURRENT_SCREENPLAY", "type": "screenplay", "status": "CURRENT"},
            {"id": "MASTER_BOARD_001", "type": "presentation_grammar", "status": "APPROVED"},
        ],
        "forbidden_elements": [str(x) for x in (draft.get("forbidden_elements") or [])][:30],
        "canon_budget": {"weak_inference_max": 2 if mode == "CANON_EXTRACTION" else 10,
                         "unsupported_max": 0},
        "layout": {"canvas": "wide cinematic production board", "panels": layout_panels},
        "render_intent": str(draft.get("render_intent", ""))[:400]
            or "Painterly production-development board, warm neutral ground, visible brushwork.",
        "panels": panels,
        "evidence_ledger": ledger,
        "unresolved_questions": [str(x) for x in (draft.get("unresolved_questions") or [])][:20],
    }


def narrative_choices() -> set[str]:
    """Every provider the narrative role can run on right now — the two
    built-ins plus whichever F6 backends have a live credential."""
    from . import narrative
    out = {"gemini", "openai"}
    if narrative.usable("anthropic"):
        out.add("anthropic")
    if narrative.usable("openrouter"):
        out.add("openrouter")
    return out


def _draft(provider: str, doc: bytes | None, mime: str | None,
           instructions: str) -> tuple[dict, str]:
    """One narrative dispatch for every JSON research pass.

    `doc` may be None. Every pass until 2026-08-25 read the screenplay, so
    a document was assumed; the Bible self-check reads the Bible, which is
    already inside `instructions`. Attaching a 130 KB screenplay to a
    question that is not about it would be paid for on every run and
    answer nothing."""
    if provider == "openai":
        return _draft_openai(doc, mime, instructions)
    if provider == "gemini":
        return _draft_gemini(doc, mime, instructions)
    from . import narrative
    try:
        text, model = narrative.complete(provider, doc, mime, instructions)
    except narrative.NarrativeError as e:
        raise AutofillError(str(e)) from e
    return _parse_json(text), model


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        raise AutofillError("The model returned an empty response.")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            # No closing brace at all is the commonest shape of a cut-off
            # reply, and "did not return valid JSON" told the user nothing
            # about which failure they had paid for (F11).
            if raw.count("{") > raw.count("}"):
                raise AutofillError(
                    "The model's reply was cut off before its JSON closed, so "
                    "the draft is unusable. This is an output-length limit, "
                    "not a content problem — a re-run re-sends the whole "
                    "screenplay and will stop at the same place. Raise the "
                    "narrative model's output ceiling, or draft a smaller "
                    "section.")
            raise AutofillError("The model did not return valid JSON.")
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            # The most expensive failure in the app had the least usable
            # error (adversarial review F11): this second parse was outside
            # any try, so a reply cut off mid-JSON surfaced as
            # "auto-fill failed: Expecting ',' delimiter: line 1 column 91"
            # after the user had just paid for a full-screenplay pass, with
            # nothing to act on and no hint that a retry hits the same
            # ceiling.
            raise AutofillError(
                "The model's reply was cut off before its JSON closed, so the "
                "draft is unusable. This is an output-length limit, not a "
                "content problem — a re-run re-sends the whole screenplay and "
                "will stop at the same place. Raise the narrative model's "
                f"output ceiling, or draft a smaller section. ({e})") from e
    if not isinstance(obj, dict):
        # Callers index into this immediately — a top-level list or string
        # must be a stated 422, not a TypeError-turned-502.
        raise AutofillError("The model returned JSON that is not an object.")
    return obj


def _draft_gemini(doc: bytes, mime: str, instructions: str) -> tuple[dict, str]:
    from google.genai import types

    client = generate._client()
    model = pick_text_model(client)
    parts = ([] if doc is None
             else [types.Part.from_bytes(data=doc, mime_type=mime)])
    response = client.models.generate_content(
        model=model,
        contents=[*parts, instructions],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return _parse_json(response.text), model


def _draft_openai(doc: bytes, mime: str, instructions: str) -> tuple[dict, str]:
    import base64

    client = generate._openai_client()
    model = generate._chat_model()
    if doc is None:
        content = [{"type": "input_text", "text": instructions}]
    elif mime == "application/pdf":
        content = [
            {"type": "input_file", "filename": "screenplay.pdf",
             "file_data": "data:application/pdf;base64," + base64.b64encode(doc).decode()},
            {"type": "input_text", "text": instructions},
        ]
    else:
        content = [{"type": "input_text",
                    "text": "SCREENPLAY FOLLOWS\n==================\n"
                            + doc.decode("utf-8", "replace")
                            + "\n\n" + instructions}]
    response = client.responses.create(
        model=model, input=[{"role": "user", "content": content}])
    return _parse_json(getattr(response, "output_text", "")), model


def autofill_spec(spec_id: str, subject_prompt: str, mode: str,
                  provider: str = "gemini", board_type: str = "",
                  source_text: str = "", panels_hint: str = "",
                  scene_line: int | str = "", scene_heading: str = "") -> dict:
    """Draft a breakdown from the screenplay, or from a pasted section.

    Two sources, and the caller chooses (user 2026-08-16). Empty
    `source_text` reads the whole screenplay and finds the material from
    `subject_prompt` — the original behaviour. A non-empty `source_text`
    IS the material: the pasted section replaces the document and the
    screenplay is not consulted, so a production can break down a scene
    that is not in the uploaded draft yet.

    `panels_hint` names the panels the board must contain, in order — the
    old textarea's meaning, kept for any caller that still sends a list.

    A count-and-a-sentence pair lived here for one afternoon on 2026-08-22
    and was withdrawn the same day when the user's mock kept the list.
    Nothing calls them now, so they are gone rather than left dead.
    Empty means the model decides what the content needs, which is what
    `Auto-generate` sends.
    """

    if mode not in {"CANON_EXTRACTION", "DESIGN_EXPLORATION"}:
        raise AutofillError(f"invalid mode: {mode}")
    board_type = str(board_type or "").strip().upper()
    if board_type and board_type not in BOARD_TYPES:
        raise AutofillError(f"invalid board type: {board_type}")
    from . import generate as _gen
    if provider not in narrative_choices() and not (
            provider == "mock" and _gen.mock_enabled()):
        raise AutofillError(
            f"provider must be one of {sorted(narrative_choices())}, not: {provider}")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", spec_id):
        raise AutofillError("spec ID may only contain letters, numbers, dot, dash, underscore")
    if store.get_spec(spec_id) is not None:
        raise AutofillError(f"specification already exists: {spec_id}")
    if not subject_prompt.strip() and not source_text.strip():
        raise AutofillError(
            "say what the board should show, or paste the screenplay section "
            "it comes from")

    if source_text.strip():
        # The pasted section IS the source. Reading the whole screenplay
        # beside it would let the model wander off the thing the user
        # deliberately narrowed to.
        doc, mime = source_text.strip().encode("utf-8"), "text/plain"
    else:
        doc, mime = _screenplay_bytes()
    prohibited = []
    if paths.PROJECT_STATE.exists():
        prohibited = json.loads(paths.PROJECT_STATE.read_text(encoding="utf-8")) \
            .get("prohibited_inventions", [])

    if provider == "mock":
        from . import mockflow
        draft, model = (mockflow.autofill_draft(subject_prompt.strip(), mode),
                        mockflow.MODEL_NAME)
        if board_type:
            draft["board_type"] = board_type
    else:
        instructions = _instructions(subject_prompt.strip(), mode, prohibited,
                                     board_type)
        if source_text.strip():
            instructions += (
                NLNL + "THE ATTACHED TEXT IS THE SOURCE. It is a section the "
                "user pasted, not the whole screenplay. Break down what is IN "
                "it; do not reach for material outside it, and do not assume "
                "scenes before or after it exist.")
        if panels_hint.strip():
            wanted = [ln.strip(" -*" + TAB) for ln in panels_hint.splitlines()
                      if ln.strip(" -*" + TAB)]
            if wanted:
                instructions += (
                    NLNL + "THE PANELS ARE GIVEN. Build exactly these, in this "
                    "order, one panel each — do not add, drop or reorder "
                    "them:" + NL
                    + NL.join("- " + w for w in wanted))
        # Deterministic scene anchor (user-hit 2026-08-06): when the
        # subject names a slugline location, the actual scene text is
        # quoted into the instructions — the model reads the scene, it
        # never has to find it.
        from . import insights
        # A PICKED scene is a pointer; a written brief has to be matched.
        # Prefer the pointer — it cannot land on the wrong scene.
        anchor = {}
        if str(scene_line).strip() != "":
            anchor = insights.scene_anchor_at(scene_line, scene_heading)
            if not anchor.get("matched"):
                raise AutofillError(
                    "That scene could not be found in the current draft: "
                    + str(anchor.get("reason", "unknown"))
                    + ". Search for it again.")
        if not anchor.get("matched"):
            anchor = insights.scene_anchor(subject_prompt)
        if anchor.get("matched"):
            instructions += _anchor_block(anchor, board_type)
        draft, model = _draft(provider, doc, mime, instructions)

    spec = _coerce(draft, spec_id, mode, board_type)
    spec["autofill"] = {"prompt": subject_prompt.strip(), "model": model,
                        "provider": provider, "created_at": store.utcnow(),
                        "source": ("pasted section" if source_text.strip()
                                   else "screenplay"),
                        "panels_given": bool(panels_hint.strip()),
                        "scene_line": (int(scene_line)
                                       if str(scene_line).strip() != "" else None)}
    store.create_spec_from_dict(spec)
    return spec
