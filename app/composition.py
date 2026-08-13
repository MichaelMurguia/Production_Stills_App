"""Scene composition check — a cinematography supervisor before the spend.

Motivated 2026-08-13 (CANYON_GRM_GT40_GETAWAY): a hero GT40 rendered
small, mid-air, at an arbitrary angle — the prompt served the scene's
inventory but not its action, and nothing in the pipeline ever asked
whether the framing would. This module is that question: one narrative
JSON pass over (a) the screenplay's own scene text, re-derived via
insights.scene_anchor at check time (it is never persisted on a spec),
(b) the panel's brief and resolved camera, and (c) the exact compiled
render prompt.

The check is ADVISORY: pre-render, on-demand, text-only — zero image
spend, no new blocker kind, nothing persisted (staleness cannot lie; a
changed brief just means re-running the check). The verdict's alignment
is computed server-side from the findings, never read from the model.
Suggested camera values are validated against store.CAMERA_FIELDS, so an
applied suggestion can never fail the /camera endpoint's validation —
and a future axis flows through with zero edits here.
"""
from __future__ import annotations

from . import generate, insights, store
from .autofill import AutofillError, _draft, narrative_choices

AXES = ("SUBJECT_PROMINENCE", "ANGLE", "ACTION_COVERAGE", "COMPOSITION")
SEVERITIES = ("WARN", "NOTE")
MAX_FINDINGS = 8
MAX_TEXT = 400  # per note/suggestion — a finding is a verdict, not an essay


def _resolved_camera(panel: dict) -> dict:
    """The camera the render would actually use — the same
    panel-value-or-production-default resolution _camera_block performs,
    with the legacy vocabularies migrated."""
    defaults = store.camera_defaults()
    out = {}
    for field in store.CAMERA_FIELDS:
        for source in (panel.get(field), defaults.get(field)):
            v = str(source or "").strip().upper()
            if field == "camera_lens":
                v = generate._LEGACY_LENS.get(v, v)
            elif field == "scale":
                v = store.LEGACY_SCALE.get(v, v)
            if v and store._camera_valid(field, v):
                out[field] = v
                break
    return out


def _camera_vocabulary() -> str:
    """The legal values per axis, straight from store.CAMERA_FIELDS — the
    model may only suggest these, and a new axis rides automatically."""
    lines = []
    for field, allowed in store.CAMERA_FIELDS.items():
        if hasattr(allowed, "match"):
            lines.append(f"- {field}: a focal length like 24MM")
        else:
            lines.append(f"- {field}: {' | '.join(sorted(allowed))}")
    return "\n".join(lines)


def _instructions(spec: dict, panel: dict, prompt: str, anchored: bool) -> str:
    camera = _resolved_camera(panel)
    cam_line = "  ".join(f"{k}={v}" for k, v in camera.items()) or "unset"
    doc_is = ("the screenplay scene(s) this panel serves, quoted verbatim"
              if anchored else
              "the sheet's own scene prose — the screenplay scene could not "
              "be located, so judge against this and say so in a NOTE")
    return f"""You are a cinematography supervisor reviewing ONE render prompt before
money is spent on it. The attached document is {doc_is}.

PANEL BRIEF
- purpose: {str(panel.get('purpose', '')).strip()}
- composition role: {str(panel.get('composition_role') or 'support')}
- required content: {', '.join(str(x) for x in panel.get('required_objects', [])) or 'none listed'}
- resolved camera: {cam_line}

THE COMPILED RENDER PROMPT (verbatim, what the image model will receive):
{prompt}

Judge ONLY these four axes, against the scene's stated action:
- SUBJECT_PROMINENCE: will the primary subject read at the size and weight
  its composition role demands? A hero subject rendered small, distant, or
  edge-of-frame is a failure.
- ANGLE: do the camera's angle, orientation and tilt serve the action and
  the subject's intended presence?
- ACTION_COVERAGE: does the prompt actually depict the scene's action, or
  a static substitute for it?
- COMPOSITION: framing conflicts, competing subjects, required objects
  that cannot all be prominent at this shot scale.

Camera vocabulary — any suggested_camera value MUST come from exactly these:
{_camera_vocabulary()}

Rules: judge only what is written — never invent scene content. Quote the
scene line a finding rests on inside its note. If the prompt serves the
scene, return zero findings; do not manufacture criticism. Suggest a
camera change only when a finding warrants it, and include only the axes
that should CHANGE.

Return ONLY JSON:
{{"findings": [{{"axis": "SUBJECT_PROMINENCE|ANGLE|ACTION_COVERAGE|COMPOSITION",
   "severity": "WARN|NOTE", "note": "...", "suggestion": "..."}}],
 "suggested_camera": {{"scale": "...", "camera_angle": "..."}},
 "purpose_amendment": ""}}
"""


def _coerce_verdict(draft: dict) -> dict:
    """Never trust the model's shape: clamp axes and severities, cap
    volume, validate every suggested camera value, and COMPUTE alignment
    from the surviving findings."""
    findings = []
    for f in (draft.get("findings") or [])[:MAX_FINDINGS]:
        if not isinstance(f, dict):
            continue
        note = str(f.get("note", "")).strip()[:MAX_TEXT]
        if not note:
            continue
        axis = str(f.get("axis", "")).strip().upper()
        severity = str(f.get("severity", "")).strip().upper()
        findings.append({
            "axis": axis if axis in AXES else "COMPOSITION",
            "severity": severity if severity in SEVERITIES else "WARN",
            "note": note,
            "suggestion": str(f.get("suggestion", "")).strip()[:MAX_TEXT],
        })
    warned = any(f["severity"] == "WARN" for f in findings)

    camera = None
    raw_cam = draft.get("suggested_camera")
    if warned and isinstance(raw_cam, dict):
        clean = {}
        for field in store.CAMERA_FIELDS:
            v = str(raw_cam.get(field) or "").strip().upper()
            if field == "camera_lens":
                v = generate._LEGACY_LENS.get(v, v)
            elif field == "scale":
                v = store.LEGACY_SCALE.get(v, v)
            if v and store._camera_valid(field, v):
                clean[field] = v
        camera = clean or None

    return {
        "alignment": "WARN" if warned else "OK",
        "findings": findings,
        "suggested_camera": camera,
        "purpose_amendment": str(draft.get("purpose_amendment", ""))
        .strip()[:MAX_TEXT] if warned else "",
    }


def check_panel(spec_id: str, panel_id: str, ref_ids: list[str],
                provider: str = "") -> dict:
    """The check, end to end: resolve exactly what a generation would,
    compile the real prompt, anchor the screenplay scene, judge."""
    spec, panel, refs = generate._resolve_generation_inputs(
        spec_id, panel_id, ref_ids)
    prompt = generate.compile_panel_prompt(spec, panel, refs)

    anchor = insights.scene_anchor(str(spec.get("subject", "")))
    if not anchor.get("matched"):
        loc = str((spec.get("setting") or {}).get("location", ""))
        if loc:
            anchor = insights.scene_anchor(loc)

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
        draft, model = (mockflow.composition_check(spec, panel, prompt,
                                                   anchor),
                        mockflow.MODEL_NAME)
    else:
        if anchor.get("matched"):
            doc = anchor["text"].encode("utf-8")
        else:
            doc = ("SCENE PROSE (from the breakdown sheet — the screenplay "
                   "scene was not located):\n"
                   + str(spec.get("scene", "")).strip()).encode("utf-8")
        draft, model = _draft(provider, doc, "text/plain",
                              _instructions(spec, panel, prompt,
                                            bool(anchor.get("matched"))))

    from common import stable_hash  # scripts/ on sys.path via app.paths
    verdict = _coerce_verdict(draft)
    verdict.update({
        "provider": provider, "model": model,
        "spec_hash": stable_hash(spec)[:8],
        "anchor": {"matched": bool(anchor.get("matched")),
                   "location": str(anchor.get("location", "")),
                   "scenes": int(anchor.get("scenes", 0) or 0)},
    })
    return verdict
