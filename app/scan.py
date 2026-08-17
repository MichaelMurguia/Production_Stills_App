"""Tell the app anything about a panel; it re-reads the screenplay and
proposes what the panel should say.

Motivated 2026-08-16, reframed by the user on 2026-08-17: "I want to be
able to say just about anything and have it considered. Paste the
screenplay. Describe a feel. Explain in my own words. It re-reads the
screenplay and updates the panel info. It is not an object scan."

So the text is DIRECTION, not a search query. It may be a question, a
correction, a mood, a paste from elsewhere, or a half-formed note.
Whatever it is, the model reads it alongside the panel's own screenplay
scene and comes back with a proposed BRIEF and proposed REQUIRED CONTENT.

The one line that must never blur is where a fact came from:

- `screenplay` — the scene says it, and the find carries the VERBATIM
  line. Checked here against the text actually sent; anything not
  literally present is dropped rather than demoted, because the designer
  never said it either. Files as SCRIPT_EXPLICIT evidence.
- `direction` — the DESIGNER said it. No quote, and any the model offers
  is stripped: a citation on the user's own words would file as
  SCRIPT_EXPLICIT and put words in the screenplay's mouth. Files as
  USER_DIRECTED, which is authority in its own right — direction is never
  withheld for lacking a citation.

Everything is a PROPOSAL. Nothing is written until the caller accepts an
item, because the breakdown is canon and a model does not edit canon
unasked. Text-only, no image spend, nothing persisted by this module.

The scene text comes from insights.scene_anchor at call time, never from
a stored copy and never from the raw uploaded PDF (the token rule of
2026-08-16: the extracted text is the agents' copy, the upload is the
user's).
"""
from __future__ import annotations

from . import generate, insights, store
from .autofill import AutofillError, _draft, narrative_choices

MAX_FINDS = 12
MAX_TEXT = 300
MAX_OBJECT = 120


def _instructions(spec: dict, panel: dict, ask: str, anchored: bool) -> str:
    known = [str(o) for o in (panel.get("required_objects") or [])]
    return f"""\
You are a production designer's researcher working on ONE panel of a film
production art board. The designer has told you something. Take it
seriously, read the screenplay scene behind the panel, and propose what
this panel should say.

THE PANEL AS IT STANDS
  Board: {spec.get('specification_id', '')} — {spec.get('subject', '')}
  Panel: {panel.get('id', '')} — {panel.get('title', '')}
  Brief: {panel.get('purpose', '') or '(none yet)'}
  Required content: {', '.join(known) or '(nothing yet)'}

WHAT THE DESIGNER SAID
{ask.strip() or '(nothing in particular — re-read the scene and propose what this panel is missing)'}

That may be a question, a correction, a mood, a paste from somewhere
else, or a half-formed note. It is not a search string. Read it for
INTENT and answer the intent.

WHAT ELSE YOU ARE READING
{"The screenplay scene this panel comes from, verbatim."
 if anchored else
 "The breakdown's own scene prose — the screenplay scene could not be "
 "located, so say so in `note` and be conservative."}

THE ONE RULE YOU MUST NOT BREAK
Every proposal declares where it came from.
  "from": "screenplay" — the scene says it. Put the VERBATIM line in
      `quote`. Do not paraphrase into it, do not stitch two lines
      together, do not tidy the capitalisation. A quote that is not
      literally in the text is discarded.
  "from": "direction" — the DESIGNER said it, or it follows from what
      they said. Leave `quote` empty. Never invent a citation for it, and
      never withhold it for lacking one: their direction is authority in
      its own right.
Never label the designer's words as the screenplay's, or the screenplay's
as theirs.

ALSO
- Prefer PHYSICAL, DRAWABLE facts: what is present, where it sits, what
  state it is in, what it is made of, how it moves. A production designer
  cannot draw a mood — when the designer gives you one, propose what it
  LOOKS like.
- `brief` is a rewrite of the panel's brief, and only if you can improve
  it on what you were told and what the scene says; otherwise leave it
  empty. One or two sentences: the production question this panel answers.
- `object` is a short noun phrase for a required-content list. Omit it
  when the find is context rather than a thing to render.
- Do not repeat existing required content unless you are adding a
  physical detail its wording misses — and then say what the detail is.
- At most {MAX_FINDS} finds.

Return JSON only:
{{
  "brief": "proposed rewrite of the panel brief, or empty",
  "brief_reason": "one sentence on why, or empty",
  "finds": [
    {{"from": "screenplay | direction",
      "object": "short noun phrase, or empty",
      "detail": "the physical fact, one sentence",
      "quote": "verbatim from the scene — screenplay finds only"}}
  ],
  "note": "one sentence on what is still unsettled, or empty"
}}"""


def _coerce(draft: dict, source_text: str) -> dict:
    """Trust nothing about PROVENANCE. A find claiming the screenplay must
    prove it with a line literally in the text we sent; a find from the
    designer's own direction needs no proof and gets none invented."""
    hay = " ".join(str(source_text).split()).casefold()
    out, dropped = [], 0
    for f in (draft.get("finds") or [])[:MAX_FINDS]:
        if not isinstance(f, dict):
            continue
        detail = str(f.get("detail", "")).strip()[:MAX_TEXT]
        if not detail:
            continue
        src = ("screenplay"
               if str(f.get("from", "")).strip().lower() == "screenplay"
               else "direction")
        quote = str(f.get("quote", "")).strip()
        if src == "screenplay":
            needle = " ".join(quote.split()).casefold()
            if not needle or needle not in hay:
                # It claimed the script and could not show it. Do NOT
                # quietly demote it to direction — the designer never said
                # it either, so it is nobody's fact.
                dropped += 1
                continue
        else:
            # The designer's own words never carry a citation, even if the
            # model offered one. A quote here would file as SCRIPT_EXPLICIT
            # downstream and put words in the screenplay's mouth.
            quote = ""
        out.append({"from": src,
                    "object": str(f.get("object", "")).strip()[:MAX_OBJECT],
                    "detail": detail, "quote": quote[:MAX_TEXT]})
    return {"finds": out,
            "brief": str(draft.get("brief", "")).strip()[:600],
            "brief_reason": str(draft.get("brief_reason", "")).strip()[:MAX_TEXT],
            "note": str(draft.get("note", "")).strip()[:MAX_TEXT],
            "unverified_dropped": dropped}


def scan_panel(spec_id: str, panel_id: str, ask: str = "",
               provider: str = "") -> dict:
    """One narrative pass over this panel's scene text, answering `ask`."""
    spec = store.get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise KeyError(f"{spec_id} has no panel {panel_id}")

    # Same anchor ladder as the composition check: the board's subject
    # first, then its slugline location.
    anchor = insights.scene_anchor(str(spec.get("subject", "")))
    if not anchor.get("matched"):
        loc = str((spec.get("setting") or {}).get("location", ""))
        if loc:
            anchor = insights.scene_anchor(loc)

    matched = bool(anchor.get("matched"))
    source = (anchor["text"] if matched
              else str(spec.get("scene", "")).strip())
    if not source:
        raise AutofillError(
            "There is no screenplay scene for this board and no scene prose "
            "on the sheet, so there is nothing to scan. Add a screenplay, or "
            "write the scene on the breakdown first.")

    settings = generate.load_settings()
    provider = str(provider or settings.get("narrative_provider")
                   or "openai").strip()
    if provider not in narrative_choices() and not (
            provider == "mock" and generate.mock_enabled()):
        raise AutofillError(
            f"provider must be one of {sorted(narrative_choices())}, "
            f"not: {provider}")

    if provider == "mock":
        from . import mockflow
        draft, model = mockflow.scan_panel(spec, panel, ask, source), mockflow.MODEL_NAME
    else:
        draft, model = _draft(provider, source.encode("utf-8"), "text/plain",
                              _instructions(spec, panel, ask, matched))

    out = _coerce(draft, source)
    out.update({
        "provider": provider, "model": model,
        "panel_id": panel_id, "ask": ask.strip(),
        "anchor": {"matched": matched,
                   "location": str(anchor.get("location", "")),
                   "scenes": int(anchor.get("scenes", 0) or 0)},
    })
    return out
