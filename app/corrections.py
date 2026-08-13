"""Correction intake — a rejection becomes structure, not just prose.

Found 2026-08-13 (CANYON_GRM_GT40_GETAWAY): a carried rejection asking
for a side view, a destroyed hover jet and enclosing canyon walls rode
the next prompt as one prose bullet and mostly lost. The verbatim
DIRECTOR'S CORRECTIONS block still carries (head and tail, see
generate.compile_panel_prompt) — this module additionally parses the
rejection into applicable deltas: camera axis changes, required/forbidden
content, a brief extension.

The model PROPOSES; the user APPLIES — never auto (the codebase's own
rule: the user, not the model, promotes weak evidence). A proposal lives
on the rejected candidate's record (`correction_intake`), one per
rejection, replaced on re-propose. Applying routes every delta through
the existing controlled-edit contract: store.amend_panel_camera and
store.amend_panel_content — approved-take freeze, lock re-stamp,
approval-log entry naming the source rejection. The verbatim block and
the applied structure coexist until the director retires the former
(the existing Retire button; never auto-retired — prose can carry nuance
the deltas don't).
"""
from __future__ import annotations

import json

from . import generate, store
from .autofill import AutofillError, _draft, narrative_choices

KINDS = ("camera", "require", "forbid", "purpose_append")
MAX_DELTAS = 8
MAX_TEXT = 200


def _instructions(reason: str, panel: dict) -> str:
    vocab = []
    for field, allowed in store.CAMERA_FIELDS.items():
        if hasattr(allowed, "match"):
            vocab.append(f"- {field}: a focal length like 24MM")
        else:
            vocab.append(f"- {field}: {' | '.join(sorted(allowed))}")
    return f"""A film director rejected a rendered take of one panel with this verbatim
reason:

{reason}

Translate the reason into STRUCTURED deltas for the panel's specification.
The panel currently has:
- purpose: {str(panel.get('purpose', '')).strip()}
- required content: {', '.join(str(x) for x in panel.get('required_objects', [])) or 'none'}
- forbidden content: {', '.join(str(x) for x in panel.get('forbidden_objects', [])) or 'none'}
- camera: {'  '.join(f"{f}={panel.get(f)}" for f in store.CAMERA_FIELDS if panel.get(f)) or 'inherited'}

Delta kinds:
- camera: set one camera axis. Values MUST come from exactly this vocabulary:
{chr(10).join(vocab)}
- require: content that MUST appear (one concrete noun phrase per delta).
- forbid: content that must NOT appear.
- purpose_append: one short clause extending the panel's brief.

Rules: extract only what the director actually said — do not invent,
generalise, or editorialise. Prefer a camera delta over prose whenever the
reason names an angle, view, distance or framing. A reason with no
structural content yields zero deltas; that is a valid answer.

Return ONLY JSON:
{{"deltas": [
  {{"kind": "camera", "field": "camera_orientation", "value": "SIDE"}},
  {{"kind": "require", "value": "the hover jet exploding in a fireball"}},
  {{"kind": "forbid", "value": "an open flat horizon"}},
  {{"kind": "purpose_append", "value": "canyon walls rise close on both sides"}}
]}}
"""


def _coerce_deltas(draft: dict, panel: dict) -> list[dict]:
    """Enum-validate camera deltas, dedupe content against the panel's
    current lists (so a re-proposal after partial application stays
    clean), cap length and volume. Invalid rows drop silently — the
    worst outcome of a misparse is a bad PROPOSAL, never a bad spec."""
    have_req = {str(x).casefold() for x in panel.get("required_objects", [])}
    have_forb = {str(x).casefold() for x in panel.get("forbidden_objects", [])}
    purpose = str(panel.get("purpose", "")).casefold()
    out: list[dict] = []
    seen: set[tuple] = set()
    for d in (draft.get("deltas") or []):
        if not isinstance(d, dict) or len(out) >= MAX_DELTAS:
            break
        kind = str(d.get("kind", "")).strip()
        value = str(d.get("value", "")).strip()[:MAX_TEXT]
        if kind not in KINDS or not value:
            continue
        if kind == "camera":
            field = str(d.get("field", "")).strip()
            if field not in store.CAMERA_FIELDS:
                continue
            v = value.upper()
            if field == "camera_lens":
                v = generate._LEGACY_LENS.get(v, v)
            elif field == "scale":
                v = store.LEGACY_SCALE.get(v, v)
            if not store._camera_valid(field, v):
                continue
            if str(panel.get(field, "")).upper() == v:
                continue  # already set — nothing to propose
            key = ("camera", field)
            row = {"kind": "camera", "field": field, "value": v}
        else:
            low = value.casefold()
            if (kind == "require" and low in have_req) or \
               (kind == "forbid" and low in have_forb) or \
               (kind == "purpose_append" and low in purpose):
                continue
            key = (kind, low)
            row = {"kind": kind, "value": value}
        if key in seen:
            continue
        seen.add(key)
        out.append({**row, "applied": False})
    return out


def _require_rejected(spec_id: str, cand_id: str) -> tuple[dict, dict, dict]:
    record = generate.get_candidate(spec_id, cand_id)
    if record is None:
        raise KeyError(cand_id)
    if record.get("status") != "REJECTED" or not str(
            record.get("status_reason", "")).strip():
        raise generate.GenerationError(
            f"{cand_id} is not a rejected take with a reason — correction "
            "intake structures rejections, nothing else.")
    spec = store.get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    panel = next((p for p in spec.get("panels", [])
                  if p.get("id") == record.get("panel_id")), None)
    if panel is None:
        raise KeyError(f"{spec_id} has no panel {record.get('panel_id')}")
    return record, spec, panel


def _save_record(spec_id: str, record: dict) -> None:
    d = generate._spec_board_dir(spec_id)
    (d / f"{record['candidate_id']}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")


def propose(spec_id: str, cand_id: str, provider: str = "") -> dict:
    """Parse the rejection into proposed deltas and store them on the
    candidate record. Idempotent per rejection: re-proposing replaces.
    Zero deltas is a stated outcome (prose-only correction), not an
    error."""
    record, _spec, panel = _require_rejected(spec_id, cand_id)

    settings = generate.load_settings()
    provider = str(provider or settings.get("narrative_provider")
                   or "openai").strip()
    if provider not in narrative_choices() and not (
            provider == "mock" and generate.mock_enabled()):
        raise AutofillError(
            f"provider must be one of {sorted(narrative_choices())}, "
            f"not: {provider}")

    reason = str(record["status_reason"]).strip()
    if provider == "mock":
        from . import mockflow
        draft, model = mockflow.correction_deltas(reason, panel), mockflow.MODEL_NAME
    else:
        draft, model = _draft(provider, reason.encode("utf-8"), "text/plain",
                              _instructions(reason, panel))

    record["correction_intake"] = {
        "provider": provider, "model": model, "created_at": store.utcnow(),
        "deltas": _coerce_deltas(draft, panel), "dismissed": False,
    }
    _save_record(spec_id, record)
    return {"candidate_id": cand_id, **record["correction_intake"]}


def apply(spec_id: str, cand_id: str, indices: list[int]) -> dict:
    """Apply the selected proposed deltas to the panel through the
    controlled-edit doors. PermissionError (approved take) propagates —
    that freeze is the point, not an obstacle."""
    record, _spec, panel = _require_rejected(spec_id, cand_id)
    intake = record.get("correction_intake") or {}
    deltas = intake.get("deltas") or []
    picked = [deltas[i] for i in indices
              if isinstance(i, int) and 0 <= i < len(deltas)]
    if not picked:
        raise generate.GenerationError("no valid deltas selected")

    camera = {d["field"]: d["value"] for d in picked if d["kind"] == "camera"}
    required = [d["value"] for d in picked if d["kind"] == "require"]
    forbidden = [d["value"] for d in picked if d["kind"] == "forbid"]
    extensions = [d["value"] for d in picked if d["kind"] == "purpose_append"]

    panel_id = str(record.get("panel_id", ""))
    if camera:
        store.amend_panel_camera(spec_id, panel_id, camera)
    if required or forbidden or extensions:
        store.amend_panel_content(spec_id, panel_id,
                                  add_required=required,
                                  add_forbidden=forbidden,
                                  purpose_append=" — ".join(extensions),
                                  source=cand_id)
    for d in picked:
        d["applied"] = True
    _save_record(spec_id, record)
    return {"candidate_id": cand_id, "applied": len(picked),
            "deltas": deltas}


def dismiss(spec_id: str, cand_id: str) -> dict:
    """An unwanted proposal stops occupying the rail; the rejection and
    its verbatim carry are untouched."""
    record, _spec, _panel = _require_rejected(spec_id, cand_id)
    intake = record.get("correction_intake")
    if not intake:
        raise KeyError("no correction intake on this candidate")
    intake["dismissed"] = True
    _save_record(spec_id, record)
    return {"candidate_id": cand_id, "dismissed": True}
