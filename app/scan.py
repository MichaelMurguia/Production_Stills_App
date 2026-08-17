"""Re-scan the screenplay for ONE panel, for something the user names.

Motivated 2026-08-16. A breakdown is drafted once, from a brief, and the
draft is a summary: it captured "airlock hatch behind Sal" but not that
the hatch irises, and nothing in the app could go back and ask. The user
asked for "a Scan Screenplay button that will rescan for information. A
modal will pop up asking for information to scan for which the AI will
use to get better info."

So this is a NARROW, ASKED question rather than a re-draft. The user says
what they want to know; the model reads the panel's own scene text and
answers with things it can point at in the script. What comes back is a
PROPOSAL — the caller chooses which required objects to accept — because
the breakdown is canon and a model does not get to edit canon unasked.

Text-only, no image spend, nothing persisted by this module. Like the
composition check, staleness cannot lie: a changed brief just means
scanning again.

Two rules it inherits from the rest of the app:

- The scene text comes from insights.scene_anchor at scan time, never
  from a stored copy, and never from the raw uploaded PDF (the token rule
  of 2026-08-16: the extracted text is the agents' copy, the upload is
  the user's).
- Quotes must be verbatim. A "find" the screenplay does not actually say
  is worse than no find, because it enters a breakdown looking like
  evidence.
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
You are a production designer's researcher, reading a film screenplay to
answer ONE question about ONE panel of a production art board.

THE PANEL
  Board: {spec.get('specification_id', '')} — {spec.get('subject', '')}
  Panel: {panel.get('id', '')} — {panel.get('title', '')}
  What it must answer: {panel.get('purpose', '')}
  Already listed as required content: {', '.join(known) or '(nothing yet)'}

WHAT THE USER WANTS TO KNOW
{ask.strip() or '(nothing specific — report the physical detail this panel needs)'}

WHAT YOU ARE READING
{"The screenplay scene this panel comes from, verbatim."
 if anchored else
 "The breakdown's own scene prose — the screenplay scene could not be "
 "located, so say so in `note` and be conservative."}

RULES
- Answer ONLY from the text supplied. If it does not say, the honest
  answer is nothing — an empty `finds` list is a valid, useful result.
- Every find MUST carry a VERBATIM quote from the text. Do not paraphrase
  into the quote field, do not stitch two lines together, do not tidy the
  screenplay's capitalisation. A find whose quote is not literally present
  is worse than no find: it enters a breakdown looking like evidence.
- Prefer PHYSICAL, DRAWABLE facts: what is present, where it sits, what
  state it is in, what it is made of, how it moves. A production designer
  cannot draw a mood.
- `object` is a short noun phrase suitable for a required-content list,
  the way the screenplay words it. Omit it when the find is context
  rather than a thing to render.
- Do not repeat something already listed as required content unless the
  screenplay adds a physical detail the existing wording misses — and if
  it does, say what the detail is.
- At most {MAX_FINDS} finds.

Return JSON only:
{{
  "finds": [
    {{"object": "short noun phrase, or empty",
      "detail": "the physical fact, one sentence",
      "quote": "verbatim from the text"}}
  ],
  "note": "one sentence on what the text does NOT settle, or empty"
}}"""


def _coerce(draft: dict, source_text: str) -> dict:
    """Trust nothing. Drop any find whose quote is not literally in the
    text we sent — that check is the whole reason a quote is required."""
    hay = " ".join(str(source_text).split()).casefold()
    out, dropped = [], 0
    for f in (draft.get("finds") or [])[:MAX_FINDS]:
        if not isinstance(f, dict):
            continue
        quote = str(f.get("quote", "")).strip()
        detail = str(f.get("detail", "")).strip()[:MAX_TEXT]
        if not detail:
            continue
        needle = " ".join(quote.split()).casefold()
        if not needle or needle not in hay:
            dropped += 1
            continue
        out.append({"object": str(f.get("object", "")).strip()[:MAX_OBJECT],
                    "detail": detail, "quote": quote[:MAX_TEXT]})
    return {"finds": out,
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
