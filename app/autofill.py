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


def _screenplay_bytes() -> tuple[bytes, str]:
    state = store.load_app_state()
    rec = state.get("screenplay")
    if not rec:
        raise AutofillError("No screenplay uploaded. Add it on the Dashboard first.")
    p = paths.SCREENPLAY_DIR / rec["file"]
    if not p.exists():
        raise AutofillError(f"Screenplay file missing on disk: {rec['file']}")
    suffix = p.suffix.lower()
    mime = "application/pdf" if suffix == ".pdf" else "text/plain"
    return p.read_bytes(), mime


def _instructions(subject_prompt: str, mode: str, prohibited: list[str]) -> str:
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
- Mode for this board: {mode}.
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
  "scene": "one flowing paragraph (4-8 sentences) describing the scene as the screenplay establishes it: the location and its structure, time of day and light, atmosphere, and the key contents and their arrangement. Only screenplay-supported details — where the screenplay is silent, stay silent.",
  "render_intent": "one-sentence painterly production-board treatment note",
  "panels": [
    {{
      "id": "P01",
      "title": "short title",
      "purpose": "the single production question this panel answers",
      "required_objects": ["object", "..."],
      "forbidden_objects": ["likely-but-wrong additions to exclude", "..."],
      "scale": "EXTREME_WIDE | WIDE | FULL_BODY | MEDIUM | DETAIL",
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


def _coerce(draft: dict, spec_id: str, mode: str) -> dict:
    """Coerce model output into a valid spec structure; never trust it blindly."""
    panels_in = draft.get("panels") or []
    if not panels_in:
        raise AutofillError("The model returned no panels — likely found no usable "
                            "screenplay evidence for that subject.")
    panels, layout_panels = [], []
    for i, p in enumerate(panels_in, 1):
        pid = str(p.get("id") or f"P{i:02d}").strip().upper()
        panels.append({
            "id": pid,
            "title": str(p.get("title", ""))[:120],
            "purpose": str(p.get("purpose", ""))[:400],
            "required_objects": [str(x) for x in (p.get("required_objects") or [])][:12],
            "forbidden_objects": [str(x) for x in (p.get("forbidden_objects") or [])][:20],
            "evidence": ["SCRIPT_EXPLICIT"],
            "scale": str(p.get("scale", "WIDE")),
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
        ledger.append({
            "object_id": f"OBJ-{i:03d}",
            "panel_id": pid,
            "object": str(row.get("object", ""))[:200],
            "evidence_class": ec,
            "source": str(row.get("source", ""))[:500],
            "confidence": confidence,
            "status": status,
            "rationale": str(row.get("rationale", ""))[:500],
        })
    if not ledger:
        raise AutofillError("The model returned no usable evidence rows.")

    return {
        "specification_id": spec_id,
        "project": store.project_name(),
        "subject": str(draft.get("subject", ""))[:200] or spec_id,
        "board_type": (str(draft.get("board_type", "")).strip().upper()
                       if str(draft.get("board_type", "")).strip().upper()
                       in {"SCENE", "LOCATION", "ASSET"} else "LOCATION"),
        "setting": {
            "int_ext": str((draft.get("setting") or {}).get("int_ext", ""))[:10].upper(),
            "location": str((draft.get("setting") or {}).get("location", ""))[:120],
            "time_of_day": str((draft.get("setting") or {}).get("time_of_day", ""))[:60].upper(),
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


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        raise AutofillError("The model returned an empty response.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise AutofillError("The model did not return valid JSON.")
        return json.loads(m.group(0))


def _draft_gemini(doc: bytes, mime: str, instructions: str) -> tuple[dict, str]:
    from google.genai import types

    client = generate._client()
    model = pick_text_model(client)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=doc, mime_type=mime),
            instructions,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return _parse_json(response.text), model


def _draft_openai(doc: bytes, mime: str, instructions: str) -> tuple[dict, str]:
    import base64

    client = generate._openai_client()
    model = generate._chat_model()
    if mime == "application/pdf":
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
                  provider: str = "gemini") -> dict:
    if mode not in {"CANON_EXTRACTION", "DESIGN_EXPLORATION"}:
        raise AutofillError(f"invalid mode: {mode}")
    if provider not in {"gemini", "openai"}:
        raise AutofillError(f"provider must be gemini or openai, not: {provider}")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", spec_id):
        raise AutofillError("spec ID may only contain letters, numbers, dot, dash, underscore")
    if store.get_spec(spec_id) is not None:
        raise AutofillError(f"specification already exists: {spec_id}")
    if not subject_prompt.strip():
        raise AutofillError("describe what the board is about — a location and which of its scenes")

    doc, mime = _screenplay_bytes()
    prohibited = []
    if paths.PROJECT_STATE.exists():
        prohibited = json.loads(paths.PROJECT_STATE.read_text(encoding="utf-8")) \
            .get("prohibited_inventions", [])

    instructions = _instructions(subject_prompt.strip(), mode, prohibited)
    draft_fn = _draft_openai if provider == "openai" else _draft_gemini
    draft, model = draft_fn(doc, mime, instructions)

    spec = _coerce(draft, spec_id, mode)
    spec["autofill"] = {"prompt": subject_prompt.strip(), "model": model,
                        "provider": provider, "created_at": store.utcnow()}
    store.create_spec_from_dict(spec)
    return spec
