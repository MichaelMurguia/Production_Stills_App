from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from . import imaging, paths, revisions

REF_STATUSES = {"PROVISIONAL", "APPROVED", "REJECTED"}

# Camera & composition vocabulary (user 2026-08-09). The allowed values for the
# structured per-panel/per-bible camera fields; the model-facing phrasing lives
# in generate.CAMERA_*_PHRASING, and the JS label consts by TIMES_OF_DAY.
_LENS_RE = re.compile(r"^\d{1,3}MM$")  # a focal length like 24MM — presets + custom
CAMERA_FIELDS = {
    "camera_angle": {"EYE_LEVEL", "LOW", "HIGH", "BIRDS_EYE", "WORMS_EYE"},
    # Orientation is the azimuth axis (2026-08-13): which face of the subject
    # the camera sees. camera_angle is elevation only, which left "side view"
    # inexpressible as structure — a director's correction asking for one
    # could only ride as prose.
    "camera_orientation": {"FRONT", "THREE_QUARTER_FRONT", "SIDE",
                           "THREE_QUARTER_REAR", "REAR"},
    "camera_lens": _LENS_RE,
    "camera_tilt": {"LEVEL", "DUTCH"},
    "scale": {"AERIAL", "EXTREME_WIDE", "WIDE", "MEDIUM", "CLOSE",
              "EXTREME_CLOSE", "MACRO", "MICRO"},
}
# A new production starts from this camera grammar (user 2026-08-10); stored
# values override, and every panel inherits it unless it sets its own axis.
# camera_orientation has NO baseline: it is subject-relative, and a house
# default would fight every panel's references — unset means the model
# chooses, exactly like any empty axis.
CAMERA_BASELINE = {"camera_angle": "EYE_LEVEL", "camera_lens": "24MM",
                   "camera_tilt": "LEVEL", "scale": "WIDE"}
# Pre-camera-enum autofill shot vocabulary (2026-08-12 review): drafted specs
# persisted FULL_BODY / DETAIL verbatim. Mapped onto the canon enum wherever a
# scale is read — the same lazy style as generate._LEGACY_LENS; a sheet save
# persists the migrated form.
LEGACY_SCALE = {"FULL_BODY": "WIDE", "DETAIL": "EXTREME_CLOSE"}


def _camera_valid(field: str, value: str) -> bool:
    allowed = CAMERA_FIELDS[field]
    return bool(allowed.match(value)) if hasattr(allowed, "match") else value in allowed


def _clean_camera_fields(fields: dict) -> dict:
    """Validate/normalise a camera payload: upper-cased, only known fields, each
    value valid for its axis (an enum, or a focal length for the lens). Empty
    values are dropped (they mean clear/inherit), so the result carries only
    fields being SET. Raises ValueError on a bad value."""
    out = {}
    for field in CAMERA_FIELDS:
        if field not in fields:
            continue
        v = str(fields.get(field) or "").strip().upper()
        if not v:
            continue
        if not _camera_valid(field, v):
            raise ValueError(f"{field}: {v!r} is not a valid value")
        out[field] = v
    return out

# Roles suggested by context/02_CANON_AND_REFERENCE_RULES.md; free-form roles
# are also allowed — these seed the UI dropdown.
SUGGESTED_ROLES = [
    "WORLD_TEXTURE",
    "COLOR_PALETTE",
    "CINEMATOGRAPHY_STYLE",
    "BOARD_RENDERING_STYLE",
    "BOARD_LAYOUT_STYLE",
    "CHARACTER_LIKENESS",
    "VEHICLE_GEOMETRY",
    "ENVIRONMENT_LAYOUT",
    "SCENE_REFERENCE",
    "LIGHTING_REFERENCE",
    "MATERIAL_REFERENCE",
    "PROP_REFERENCE",
]

# The four-anchor ruling (user, 2026-08-03): THREE MOVIE PARAMETERS —
# WORLD_TEXTURE (condition/patina), COLOR_PALETTE (hue/value/saturation),
# CINEMATOGRAPHY_STYLE (light behaviour/lens/framing) — and ONE BOARD
# PARAMETER, BOARD_RENDERING_STYLE (the medium boards are drawn in; how
# the work is PRESENTED, nothing to do with the film). All four
# auto-attach to every panel generation, capped per role so style never
# starves the subject-anchoring budget. BOARD_LAYOUT_STYLE is assembly
# grammar: it gates board assembly and never enters a panel render.
MOVIE_STYLE_ROLES = ("WORLD_TEXTURE", "COLOR_PALETTE", "CINEMATOGRAPHY_STYLE")
AUTO_STYLE_ROLES = {*MOVIE_STYLE_ROLES, "BOARD_RENDERING_STYLE"}
STYLE_ATTACH_CAP = 2  # newest approved N per role ride each render


# The role vocabulary the picker offers, as families. Kept here so both
# the em-dash form and the fully underscore-sanitized one resolve to the
# same head.
ROLE_FAMILY_HEADS = (
    "BOARD_RENDERING_STYLE", "BOARD_LAYOUT_STYLE", "CINEMATOGRAPHY_STYLE",
    "CHARACTER_LIKENESS", "LOCATION_GEOMETRY", "VEHICLE_GEOMETRY",
    "ENVIRONMENT_LAYOUT", "LIGHTING_REFERENCE", "MATERIAL_REFERENCE",
    "SCENE_REFERENCE", "PROP_REFERENCE", "WORLD_TEXTURE", "COLOR_PALETTE",
)


def role_head(role: str) -> str:
    """The role's family name, tolerant of legacy underscore-sanitized
    records: 'CHARACTER_LIKENESS_—_JOHN' splits on the dash, and
    'CHARACTER_LIKENESS_JOHN' — where the dash itself was replaced — is
    resolved by family prefix. Without the second pass a titled reference
    had no recognisable family, so it fell through to the generic
    jurisdiction line in a render prompt (2026-08-07)."""
    raw = str(role or "").split("—")[0].strip(" _-").upper()
    fams = sorted((h for h in ROLE_FAMILY_HEADS
                   if raw == h or raw.startswith(h + "_")),
                  key=len, reverse=True)
    return fams[0] if fams else raw


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append_approval_log(entry: str) -> None:
    line = f"\n- {utcnow()} — {entry}"
    with paths.APPROVAL_LOG.open("a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------- app state

def load_app_state() -> dict:
    return _read_json(paths.APP_STATE, {"ref_counter": 0, "screenplay": None})


def save_app_state(state: dict) -> None:
    _atomic_write_json(paths.APP_STATE, state)


def next_counter(key: str, prefix: str) -> str:
    """Allocate 'PREFIX-000N' atomically. The read-increment-persist is a
    race without the lock: two concurrent renders both read N and one
    candidate record silently clobbered the other. paths.SWITCH_LOCK (not
    a private lock) so an allocation can also never land while the
    summary sweep has the path globals pointed at another production."""
    with paths.SWITCH_LOCK:
        state = load_app_state()
        state[key] = int(state.get(key, 0)) + 1
        save_app_state(state)
        return f"{prefix}-{state[key]:04d}"


# The screenplay analysis (design languages, subjects, key locations) lives
# server-side so it survives browser storage and can be debriefed.
def load_wizard_analysis() -> dict | None:
    return _read_json(paths.WIZARD_ANALYSIS, None)


def save_wizard_analysis(analysis: dict) -> None:
    _atomic_write_json(paths.WIZARD_ANALYSIS, analysis)


# ---------------------------------------------------------------- screenplay

_EXTRACTED_NAME = "_extracted.txt"


def _extract_screenplay_text(p: Path) -> str:
    """The screenplay's plain text — the model-efficient format. A PDF
    billed to a model costs per PAGE (image + text); the same script as
    text costs a fraction and prompt-caches. Empty return = extraction
    failed (image-only scan) and callers fall back to the original file."""
    if p.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            return "\n".join((page.extract_text() or "")
                             for page in PdfReader(str(p)).pages)
        except Exception:
            return ""
    try:
        return p.read_bytes().decode("utf-8", "replace")
    except Exception:
        return ""


def screenplay_text_cached() -> str:
    """The stored extraction (user ruling 2026-08-02: convert at import).
    Productions that predate the rule extract once here and persist."""
    state = load_app_state()
    rec = state.get("screenplay")
    if not rec:
        return ""
    tp = paths.SCREENPLAY_DIR / _EXTRACTED_NAME
    if rec.get("text_file") and tp.exists():
        return tp.read_text(encoding="utf-8")
    p = paths.SCREENPLAY_DIR / rec["file"]
    if not p.exists():
        return ""
    text = _extract_screenplay_text(p)
    if text.strip():  # backfill the efficient format for legacy uploads
        tp.write_text(text, encoding="utf-8")
        rec["text_file"] = _EXTRACTED_NAME
        rec["text_chars"] = len(text)
        save_app_state(state)
    return text


def set_screenplay(original_name: str, content: bytes) -> dict:
    paths.ensure_dirs()
    safe = re.sub(r"[^A-Za-z0-9._ -]", "_", original_name)
    dest = paths.SCREENPLAY_DIR / safe
    dest.write_bytes(content)
    record = {
        "file": safe,
        "sha256": sha256_file(dest),
        "size": dest.stat().st_size,
        "uploaded_at": utcnow(),
    }
    # Convert to the efficient format ONCE at import — every model call
    # reads this, not the PDF.
    text = _extract_screenplay_text(dest)
    if text.strip():
        (paths.SCREENPLAY_DIR / _EXTRACTED_NAME).write_text(text, encoding="utf-8")
        record["text_file"] = _EXTRACTED_NAME
        record["text_chars"] = len(text)
    state = load_app_state()
    state["screenplay"] = record
    save_app_state(state)
    # Keep the governance project_state in sync so the existing scripts and
    # docs see the dependency as satisfied.
    ps = _read_json(paths.PROJECT_STATE, None)
    if ps is not None:
        ps.setdefault("screenplay", {})
        ps["screenplay"]["current_file"] = safe
        ps["screenplay"]["status"] = "CURRENT"
        _atomic_write_json(paths.PROJECT_STATE, ps)
    return record


# ---------------------------------------------------------------- references

def _load_refs() -> list[dict]:
    return _read_json(paths.REF_INDEX, [])


def _save_refs(refs: list[dict]) -> None:
    _atomic_write_json(paths.REF_INDEX, refs)


def list_references() -> list[dict]:
    return _load_refs()


# ---------------------------------------------------------------- subjects
# The cast & key-subjects collection: characters, vehicles, props — WHO and
# WHAT the film needs visual reference for. Each subject is a title card
# (name, subtitle epithets, terse traits from the screenplay) that
# encapsulates its reference images.

SUBJECT_KINDS = {"CHARACTER", "VEHICLE", "PROP"}
SUBJECT_ROLE_PREFIX = {"CHARACTER": "CHARACTER_LIKENESS",
                       "VEHICLE": "VEHICLE_GEOMETRY",
                       "PROP": "PROP_REFERENCE"}


def list_subjects() -> list[dict]:
    if not paths.SUBJECTS.exists():
        return []
    try:
        return json.loads(paths.SUBJECTS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Corrupt cast file: set aside, never brick /api/state.
        paths.SUBJECTS.replace(paths.SUBJECTS.with_suffix(".json.corrupt"))
        return []


def _save_subjects(subjects: list[dict]) -> None:
    _atomic_write_json(paths.SUBJECTS, subjects)


def get_subject(sid: str) -> dict | None:
    return next((s for s in list_subjects() if s["id"] == sid), None)


def add_subject(name: str, kind: str, subtitle: str = "",
                traits: list[str] | None = None, source: str = "") -> dict:
    name = name.strip()
    if not name:
        raise ValueError("subject name is required")
    kind = kind.strip().upper()
    if kind not in SUBJECT_KINDS:
        raise ValueError(f"kind must be one of {sorted(SUBJECT_KINDS)}")
    subjects = list_subjects()
    if any(s["name"].casefold() == name.casefold() for s in subjects):
        raise FileExistsError(f"subject already exists: {name}")
    state = load_app_state()
    state["subject_counter"] = int(state.get("subject_counter", 0)) + 1
    save_app_state(state)
    rec = {
        "id": f"SUBJ-{state['subject_counter']:04d}",
        "name": name,
        "kind": kind,
        "subtitle": subtitle.strip(),
        "traits": [str(t).strip() for t in (traits or []) if str(t).strip()],
        "ref_ids": [],
        "source": source,
        "created_at": utcnow(),
    }
    subjects.append(rec)
    _save_subjects(subjects)
    return rec


def update_subject(sid: str, fields: dict) -> dict:
    subjects = list_subjects()
    rec = next((s for s in subjects if s["id"] == sid), None)
    if rec is None:
        raise KeyError(sid)
    for k in ("subtitle", "name"):
        if k in fields:
            rec[k] = str(fields[k]).strip()
    if "traits" in fields:
        rec["traits"] = [str(t).strip() for t in fields["traits"] if str(t).strip()]
    _save_subjects(subjects)
    return rec


def link_subject_ref(sid: str, ref_id: str) -> dict:
    subjects = list_subjects()
    rec = next((s for s in subjects if s["id"] == sid), None)
    if rec is None:
        raise KeyError(sid)
    if ref_id not in rec["ref_ids"]:
        rec["ref_ids"].append(ref_id)
    _save_subjects(subjects)
    return rec


def delete_subject(sid: str) -> dict:
    """Remove the title card. Its reference images stay in the library —
    they are canon anchors in their own right."""
    subjects = list_subjects()
    rec = next((s for s in subjects if s["id"] == sid), None)
    if rec is None:
        raise KeyError(sid)
    _save_subjects([s for s in subjects if s["id"] != sid])
    return {"deleted": sid, "kept_references": rec["ref_ids"]}


def delete_reference(ref_id: str) -> dict:
    """Permanently delete a reference image and its record — an explicit,
    journaled act (deleting an approved anchor changes future generations).
    Past candidates are unaffected: they store their own copies of the
    reference metadata."""
    refs = _load_refs()
    rec = next((r for r in refs if r["id"] == ref_id), None)
    if rec is None:
        raise KeyError(ref_id)
    for folder in (paths.REF_ORIGINALS, paths.REF_THUMBS, paths.REF_QUARANTINE):
        for f in folder.glob(f"{ref_id}.*"):
            f.unlink(missing_ok=True)
    _atomic_write_json(paths.REF_INDEX, [r for r in refs if r["id"] != ref_id])
    subjects = list_subjects()
    changed = False
    for s in subjects:
        if ref_id in s.get("ref_ids", []):
            s["ref_ids"].remove(ref_id)
            changed = True
    if changed:
        _save_subjects(subjects)
    append_approval_log(
        f"REFERENCE {ref_id} ({rec.get('role', '?')}, was {rec.get('status', '?')}) "
        "permanently deleted.")
    return {"deleted": ref_id}


def auto_style_references() -> list[dict]:
    """Approved style anchors attached to every panel generation — capped
    per role (newest first) so four global anchors cannot starve the
    subject-reference budget that holds faces and vehicles on model."""
    by_role: dict[str, list[dict]] = {}
    for r in _load_refs():
        if r["status"] == "APPROVED" and role_head(r["role"]) in AUTO_STYLE_ROLES:
            by_role.setdefault(role_head(r["role"]), []).append(r)
    out = []
    for role, refs in by_role.items():
        out.extend(sorted(refs, key=lambda r: r.get("added_at", ""),
                          reverse=True)[:STYLE_ATTACH_CAP])
    return out


def get_reference(ref_id: str) -> dict | None:
    return next((r for r in _load_refs() if r["id"] == ref_id), None)


def _ref_variant_cache(ref_id: str, size: str) -> Path:
    return paths.REF_THUMBS / f"{ref_id}.{size}.webp"


def _warm_reference_variants(src: Path, ref_id: str) -> str:
    """Build every display tier (see app.imaging) for a reference at intake, so
    the library grid never waits on a first-request downscale. Returns the thumb
    filename for the record (back-compat with the `thumb` field)."""
    imaging.warm(src, lambda s: _ref_variant_cache(ref_id, s))
    return f"{ref_id}.thumb.webp"


# The engines accept exactly these (OpenAI and Gemini alike) — anything
# else the modern web hands us (AVIF above all, TIFF, BMP…) transcodes at
# intake so the library only ever holds render-ready files. Observed live
# 2026-08-02: an AVIF reference 400'd a whole generation at image[12].
RENDER_SAFE_FORMATS = {"JPEG", "PNG", "WEBP"}
_SAFE_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def _render_safe(content: bytes, original_name: str) -> tuple[bytes, str]:
    """(bytes, ext), transcoded if the actual format (sniffed, never the
    filename) is one no engine accepts. Alpha keeps PNG; else JPEG q95."""
    import io

    from PIL import Image
    im = Image.open(io.BytesIO(content))
    fmt = (im.format or "").upper()
    if fmt in RENDER_SAFE_FORMATS:
        ext = Path(original_name).suffix.lower() or _SAFE_EXT[fmt]
        return content, ext
    buf = io.BytesIO()
    if "A" in im.getbands():
        im.save(buf, "PNG")
        return buf.getvalue(), ".png"
    im.convert("RGB").save(buf, "JPEG", quality=95)
    return buf.getvalue(), ".jpg"


def add_reference(original_name: str, content: bytes, role: str,
                  controls: list[str], does_not_control: list[str],
                  notes: str = "", source: str = "") -> dict:
    paths.ensure_dirs()
    # Allocated-and-persisted atomically — a crash after the file write
    # can never reuse this id and overwrite the previous image.
    ref_id = next_counter("ref_counter", "REF")

    try:
        content, ext = _render_safe(content, original_name)
    except Exception:
        raise ValueError(f"{original_name} is not a readable image")
    file_name = f"{ref_id}{ext}"
    dest = paths.REF_ORIGINALS / file_name
    dest.write_bytes(content)
    try:
        thumb = _warm_reference_variants(dest, ref_id)
    except Exception:
        dest.unlink(missing_ok=True)
        raise ValueError(f"{original_name} is not a readable image")

    record = {
        "id": ref_id,
        "original_name": original_name,
        "file": file_name,
        "thumb": thumb,
        "role": role.strip().upper(),
        "controls": controls,
        "does_not_control": does_not_control,
        "status": "PROVISIONAL",
        "notes": notes,
        "source": source,
        "sha256": sha256_file(dest),
        "added_at": utcnow(),
        "updated_at": utcnow(),
    }
    refs = _load_refs()
    refs.append(record)
    _save_refs(refs)
    return record


def update_reference_notes(updates: dict[str, str]) -> list[dict]:
    """Rewrite several references' notes in ONE load/save. Hero is a
    single-valued fact across a design language, so setting it moves two
    records at once — doing that as separate update_reference calls would
    leave a window with two heroes, or none."""
    refs = _load_refs()
    touched = []
    by_id = {r["id"]: r for r in refs}
    missing = [k for k in updates if k not in by_id]
    if missing:
        raise KeyError(missing[0])
    for ref_id, notes in updates.items():
        by_id[ref_id]["notes"] = notes
        by_id[ref_id]["updated_at"] = utcnow()
        touched.append(by_id[ref_id])
    _save_refs(refs)
    return touched


def replace_reference_image(ref_id: str, content: bytes,
                            original_name: str) -> dict:
    """Swap a reference's pixels, keeping its id, role, status and history.
    Only the image, its thumb and its hash change — used by swatch recolour,
    where a new id would orphan the approvals already recorded against it."""
    refs = _load_refs()
    for r in refs:
        if r["id"] != ref_id:
            continue
        try:
            content, ext = _render_safe(content, original_name)
        except Exception:
            raise ValueError(f"{original_name} is not a readable image")
        old = paths.REF_ORIGINALS / r["file"]
        dest = paths.REF_ORIGINALS / f"{ref_id}{ext}"
        dest.write_bytes(content)
        if old.name != dest.name:
            old.unlink(missing_ok=True)
        r["file"] = dest.name
        r["thumb"] = _warm_reference_variants(dest, ref_id)
        r["sha256"] = sha256_file(dest)
        r["updated_at"] = utcnow()
        _save_refs(refs)
        return r
    raise KeyError(ref_id)


def update_reference(ref_id: str, fields: dict) -> dict:
    refs = _load_refs()
    for r in refs:
        if r["id"] == ref_id:
            if r["status"] == "APPROVED" and any(
                    k in fields for k in ("role", "controls", "does_not_control")):
                raise PermissionError(
                    f"{ref_id} is APPROVED; its role assignment is locked. "
                    "Reject it first if the role must change.")
            for k in ("role", "controls", "does_not_control", "notes"):
                if k in fields:
                    r[k] = fields[k]
            if "role" in fields:
                r["role"] = str(fields["role"]).strip().upper()
            r["updated_at"] = utcnow()
            _save_refs(refs)
            return r
    raise KeyError(ref_id)


def set_reference_status(ref_id: str, status: str, reason: str = "") -> dict:
    if status not in REF_STATUSES:
        raise ValueError(f"invalid status: {status}")
    refs = _load_refs()
    for r in refs:
        if r["id"] == ref_id:
            previous = r["status"]
            if previous == status:
                return r
            r["status"] = status
            r["updated_at"] = utcnow()
            if reason:
                r["status_reason"] = reason
            original = paths.REF_ORIGINALS / r["file"]
            quarantined = paths.REF_QUARANTINE / r["file"]
            # Rejected references are physically quarantined so no future
            # pipeline stage can attach them to a generation call.
            if status == "REJECTED" and original.exists():
                shutil.move(str(original), str(quarantined))
            elif previous == "REJECTED" and status != "REJECTED" and quarantined.exists():
                shutil.move(str(quarantined), str(original))
            _save_refs(refs)
            if status == "APPROVED":
                append_approval_log(
                    f"REFERENCE {ref_id} ({r['original_name']}) approved as "
                    f"{r['role']}. Controls: {', '.join(r['controls']) or 'unspecified'}.")
            return r
    raise KeyError(ref_id)


def reference_image_path(ref_id: str, size: str = "full", thumb: bool = False,
                         include_quarantine: bool = False) -> Path | None:
    """Resolve a reference's image at a display tier. `size='full'` is the raw
    original; a tier in `imaging.VARIANTS` is a cached WebP derived from it.
    `thumb=True` is a back-compat alias for `size='thumb'`.

    Quarantined (REJECTED) files resolve only when the record itself says
    REJECTED or the caller explicitly asks — the physical quarantine must hold
    even if index and disk ever disagree; generation paths must never attach a
    rejected file (they call with the default `size='full'`)."""
    if thumb:
        size = "thumb"
    r = get_reference(ref_id)
    if not r:
        return None
    src = paths.REF_ORIGINALS / r["file"]
    if not src.exists():
        q = paths.REF_QUARANTINE / r["file"]
        if (include_quarantine or r.get("status") == "REJECTED") and q.exists():
            src = q
        else:
            return None
    if size == "full" or size not in imaging.VARIANTS:
        return src
    edge, quality = imaging.VARIANTS[size]
    return imaging.variant_path(src, _ref_variant_cache(ref_id, size), edge, quality)


# --------------------------------------------------------------------- specs

def _spec_path(spec_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", spec_id):
        raise ValueError(f"invalid specification_id: {spec_id}")
    # safe_id refuses dot-led names ('..' matched the regex above, and
    # delete_spec builds an rmtree target from this id) — the guard
    # belongs here, not in whichever caller happens to run first.
    paths.safe_id(spec_id)
    return paths.SPECS_DIR / f"{spec_id}.json"


def _load_locks() -> dict:
    return _read_json(paths.SPEC_LOCKS, {})


def list_specs() -> list[dict]:
    locks = _load_locks()
    out = []
    for p in sorted(paths.SPECS_DIR.glob("*.json")):
        if p.name == paths.SPEC_LOCKS.name:
            continue
        try:
            spec = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        sid = spec.get("specification_id", p.stem)
        out.append({
            "specification_id": sid,
            "subject": spec.get("subject", ""),
            "mode": spec.get("mode", ""),
            "status": spec.get("status", "DRAFT"),
            "revision": spec.get("revision", 1),
            "panel_count": len(spec.get("panels", [])),
            "locked": sid in locks,
        })
    return out


def get_spec(spec_id: str) -> dict | None:
    p = _spec_path(spec_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def spec_lock_hash(spec_id: str) -> str:
    """The locked hash the sheet was approved under, '' when unlocked —
    the card states it at the moment of dispatch (PANEL_CARD_PLAN P6)."""
    return str((_load_locks().get(spec_id) or {}).get("hash", ""))


def spec_locked(spec_id: str) -> bool:
    return spec_id in _load_locks()


# Board grammars (director's ruling 2026-07-30): a template is panel COUNT
# and ALLOCATION structure only — never camera views, never content. The
# board may crop images to fit its layout; originals stay one click away.
BOARD_TEMPLATES = {
    "SCENE": [50, 25, 25],
    "LOCATION": [50, 25, 25],
    "ASSET": [60, 20, 20],
    "LIGHTING_STUDY": [25, 25, 25, 25],
    "MASTER": [55, 15, 15, 15],
}


def template_panels(board_type: str) -> tuple[list[dict], list[dict]]:
    """Structural panels for a fresh sheet: neutral titles, empty purposes
    (the lock gate keeps them honest), hero-weighted allocations."""
    allocs = BOARD_TEMPLATES.get(board_type, BOARD_TEMPLATES["LOCATION"])
    panels, layout = [], []
    for i, a in enumerate(allocs, 1):
        pid = f"P{i:02d}"
        panels.append({
            "id": pid,
            "title": "Hero" if i == 1 else f"Support {i - 1}",
            "purpose": "",
            "required_objects": [],
            "forbidden_objects": [],
            "evidence": ["USER_DIRECTED"],
            "scale": "WIDE" if i == 1 else "MEDIUM",
            "composition_role": "hero" if i == 1 else "support",
        })
        layout.append({"id": pid, "allocation_percent": a})
    return panels, layout


def project_name() -> str:
    """The active production's name — prompts and records carry it, never
    a hardcoded film's (user ruling 2026-08-02)."""
    return paths._project_name(paths._project_base(paths.ACTIVE_PROJECT),
                               "Untitled Production")


def new_spec(spec_id: str, subject: str, mode: str,
             board_type: str = "LOCATION") -> dict:
    if mode not in {"CANON_EXTRACTION", "DESIGN_EXPLORATION"}:
        raise ValueError(f"invalid mode: {mode}")
    if board_type not in BOARD_TEMPLATES:
        raise ValueError(f"invalid board type: {board_type}")
    p = _spec_path(spec_id)
    if p.exists():
        raise FileExistsError(f"specification already exists: {spec_id}")
    panels, layout_panels = template_panels(board_type)
    spec = {
        "specification_id": spec_id,
        "project": project_name(),
        "subject": subject,
        "mode": mode,
        "board_type": board_type,
        "status": "DRAFT",
        "revision": 1,
        "canon_sources": [
            {"id": "CURRENT_SCREENPLAY", "type": "screenplay", "status": "CURRENT"},
            {"id": "MASTER_BOARD_001", "type": "presentation_grammar", "status": "APPROVED"},
        ],
        "forbidden_elements": [],
        "canon_budget": {
            "weak_inference_max": 2 if mode == "CANON_EXTRACTION" else 10,
            "unsupported_max": 0,
        },
        "layout": {
            "canvas": "wide cinematic production board",
            "panels": layout_panels,
        },
        "render_intent": ("Painterly production-development board, warm neutral "
                          "ground, strong hierarchy, visible brushwork, concise labels."),
        "panels": panels,
        "evidence_ledger": [],
    }
    _atomic_write_json(p, spec)
    return spec


def create_spec_from_dict(spec: dict) -> dict:
    spec_id = spec.get("specification_id", "")
    p = _spec_path(spec_id)
    if p.exists():
        raise FileExistsError(f"specification already exists: {spec_id}")
    _atomic_write_json(p, spec)
    return spec


def save_spec(spec_id: str, spec: dict) -> dict:
    if spec_locked(spec_id):
        raise PermissionError(
            f"{spec_id} is APPROVED and locked; create a revision instead.")
    if spec.get("specification_id") != spec_id:
        raise ValueError("specification_id may not change on save")
    if spec.get("status") == "APPROVED":
        raise ValueError("status APPROVED can only be set via the approve action")
    p = _spec_path(spec_id)
    if not p.exists():
        raise KeyError(spec_id)
    violation = _carried_panel_violation(spec_id, spec)
    if violation:
        raise ValueError(violation)
    # The scope declaration itself is server-owned: a save may not
    # rewrite it (the panel floors trust what revise/upgrade journaled).
    stored_scope = (get_spec(spec_id) or {}).get("revision_scope")
    if stored_scope is not None:
        spec["revision_scope"] = stored_scope
    _atomic_write_json(p, spec)
    return spec


def approve_spec(spec_id: str, validate_fn) -> dict:
    from common import stable_hash  # scripts/common.py via paths sys.path hook
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    if spec_locked(spec_id):
        raise PermissionError(f"{spec_id} is already approved and locked")
    errors = validate_fn(spec)
    if errors:
        raise ValueError("specification failed validation: " + "; ".join(errors))
    spec["status"] = "APPROVED"
    _atomic_write_json(_spec_path(spec_id), spec)
    locks = _load_locks()
    locks[spec_id] = {"hash": stable_hash(spec), "approved_at": utcnow()}
    _atomic_write_json(paths.SPEC_LOCKS, locks)
    append_approval_log(
        f"SPECIFICATION {spec_id} approved and locked (hash {locks[spec_id]['hash'][:16]}…).")
    return spec


def _board_records(spec_id: str) -> list[dict]:
    d = paths.BOARDS_DIR / paths.safe_id(spec_id)
    out = []
    if d.exists():
        for j in d.glob("*.json"):
            try:
                out.append(json.loads(j.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass
    return out


def _approved_outputs(spec_id: str) -> list[str]:
    return [r.get("candidate_id") for r in _board_records(spec_id)
            if r.get("status") == "APPROVED"]


def unlock_spec(spec_id: str) -> dict:
    """Explicitly unlock an approved spec back to an editable DRAFT.

    Core promise enforced here: nothing upstream of an approval may change.
    A spec with APPROVED candidates or boards cannot be unlocked — that canon
    was approved against this exact spec hash. Reject that output first (an
    explicit, journaled act of destruction) or create a revision instead.

    The lock hash is journaled before removal, and candidates keep the
    spec_hash they were generated against, so provenance survives the unlock.
    Re-approving after edits mints a new hash."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    if not spec_locked(spec_id):
        raise ValueError(f"{spec_id} is not locked")
    approved = _approved_outputs(spec_id)
    if approved:
        raise PermissionError(
            f"{spec_id} has approved canon output ({', '.join(approved)}) generated "
            "against its locked hash and cannot be unlocked. Create a revision, or "
            "reject that output first if you truly intend to void it.")
    locks = _load_locks()
    old = locks.pop(spec_id)
    _atomic_write_json(paths.SPEC_LOCKS, locks)
    spec["status"] = "DRAFT"
    _atomic_write_json(_spec_path(spec_id), spec)
    append_approval_log(
        f"SPECIFICATION {spec_id} UNLOCKED for editing — approval of "
        f"{old.get('approved_at', '?')} (hash {old.get('hash', '?')[:16]}…) is "
        "void; existing candidates keep the hash they were generated against.")
    return spec


def _refuse_carried(spec: dict, panel_id: str) -> None:
    """A panel carried by a revision's scope is read-only in that revision
    file forever — the stored scope is what the unit's panel floors trust,
    so it must always match what actually happened to the panels. The way
    to change a carried panel is a newer revision that declares it
    revised (or 'Also revise' while this one is a draft)."""
    scope = spec.get("revision_scope")
    if scope and panel_id in (scope.get("carried") or []):
        raise PermissionError(
            f"{panel_id} is carried read-only in "
            f"{spec.get('specification_id')} — it is not part of this "
            "revision. Use 'Also revise' (while a draft) or a new revision "
            "to change it.")


def amend_panel_purpose(spec_id: str, panel_id: str, purpose: str) -> dict:
    """Amend one panel's purpose — the brief that rides into its prompt —
    without unlocking the sheet (user 2026-08-08: a purpose that says
    "the three people" keeps painting three people; the fix belongs on
    the workbench, between takes).

    The lock's core promise survives because provenance is per-candidate:
    every take records the spec_hash it was generated against, so old
    takes keep the old hash, the lock re-stamps to the amended spec, and
    the amend itself is journaled. The one hard gate is the same as
    unlock's, scoped to this panel: an APPROVED take was approved against
    the old brief and freezes it."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise KeyError(f"{spec_id} has no panel {panel_id}")
    _refuse_carried(spec, panel_id)
    approved = [r.get("candidate_id") for r in _board_records(spec_id)
                if r.get("status") == "APPROVED" and r.get("panel_id") == panel_id]
    if approved:
        raise PermissionError(
            f"{panel_id} has approved canon output ({', '.join(approved)}) painted "
            "from its current purpose. Reject that take first if you truly intend "
            "to change what this panel asks for.")
    if not str(purpose).strip() and not panel.get("required_objects"):
        # validation's own rule, held through the amend: a panel needs a
        # purpose or at least one required object, else nothing to render
        raise ValueError(
            f"{panel_id} has no required objects — its purpose is the only thing "
            "steering the render and cannot be emptied, only rewritten.")
    old_text = str(panel.get("purpose", ""))
    panel["purpose"] = str(purpose).strip()
    _atomic_write_json(_spec_path(spec_id), spec)
    if spec_locked(spec_id):
        from common import stable_hash  # scripts/common.py via paths sys.path hook
        locks = _load_locks()
        prev = locks.get(spec_id, {})
        locks[spec_id] = {**prev, "hash": stable_hash(spec), "amended_at": utcnow()}
        _atomic_write_json(paths.SPEC_LOCKS, locks)
        append_approval_log(
            f"SPECIFICATION {spec_id} panel {panel_id} purpose amended post-lock "
            f"(lock re-stamped {prev.get('hash', '?')[:16]}… → "
            f"{locks[spec_id]['hash'][:16]}…): \"{old_text[:120]}\" → "
            f"\"{panel['purpose'][:120]}\". Existing takes keep the hash they "
            "were generated against.")
    return {"spec_id": spec_id, "panel_id": panel_id, "purpose": panel["purpose"]}


def warm_all_references() -> int:
    """Build display variants for every reference (back-catalogue predates
    eager warming). References are smaller than 4K renders but the same
    on-demand-build cost applies to their first view. Best-effort; capped in
    imaging. Returns the count warmed."""
    warmed = 0
    for r in _load_refs():
        try:
            src = paths.REF_ORIGINALS / r.get("file", "")
            if src.exists():
                imaging.warm(src, lambda s, rid=r["id"]: _ref_variant_cache(rid, s))
                warmed += 1
        except Exception:
            pass
    return warmed


def camera_defaults() -> dict:
    """The production's default camera grammar — the default angle/tilt/lens/scale
    every panel inherits unless it sets its own. A production starts from
    CAMERA_BASELINE (Eye level · 24mm · Level · Wide, user 2026-08-10); stored
    values override. Its own file so it never races app_state's counter writes."""
    return {**CAMERA_BASELINE, **_read_json(paths.CAMERA_DEFAULTS, {})}


def save_camera_defaults(fields: dict) -> dict:
    """Replace the production camera default. Only known fields with valid enum
    values survive; empties clear. Returns the stored dict."""
    clean = _clean_camera_fields(fields)
    _atomic_write_json(paths.CAMERA_DEFAULTS, clean)
    return clean


def amend_panel_camera(spec_id: str, panel_id: str, fields: dict) -> dict:
    """Set a panel's camera (angle/orientation/tilt/lens/scale) from the
    workbench between takes, without unlocking. Same controlled-edit contract as
    amend_panel_purpose: an APPROVED take was composed at its camera and freezes
    it; otherwise the lock re-stamps and the change is journaled. A present field
    with an empty value clears it (back to the bible default)."""
    clean = _clean_camera_fields(fields)  # validates before any mutation
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise KeyError(f"{spec_id} has no panel {panel_id}")
    _refuse_carried(spec, panel_id)
    approved = [r.get("candidate_id") for r in _board_records(spec_id)
                if r.get("status") == "APPROVED" and r.get("panel_id") == panel_id]
    if approved:
        raise PermissionError(
            f"{panel_id} has approved canon output ({', '.join(approved)}) composed "
            "at its current camera. Reject that take first if you truly intend to "
            "change the shot.")
    for field in CAMERA_FIELDS:
        if field in fields:  # only touch fields the caller sent
            v = clean.get(field, "")
            if v:
                panel[field] = v
            else:
                panel.pop(field, None)
    _atomic_write_json(_spec_path(spec_id), spec)
    if spec_locked(spec_id):
        from common import stable_hash  # scripts/common.py via paths sys.path hook
        locks = _load_locks()
        prev = locks.get(spec_id, {})
        locks[spec_id] = {**prev, "hash": stable_hash(spec), "amended_at": utcnow()}
        _atomic_write_json(paths.SPEC_LOCKS, locks)
        append_approval_log(
            f"SPECIFICATION {spec_id} panel {panel_id} camera amended post-lock "
            f"(lock re-stamped {prev.get('hash', '?')[:16]}… → "
            f"{locks[spec_id]['hash'][:16]}…): {clean or 'cleared'}. Existing takes "
            "keep the hash they were generated against.")
    return {"spec_id": spec_id, "panel_id": panel_id,
            **{f: panel.get(f, "") for f in CAMERA_FIELDS}}


def amend_panel_content(spec_id: str, panel_id: str,
                        add_required: list[str] | None = None,
                        add_forbidden: list[str] | None = None,
                        purpose_append: str = "",
                        source: str = "") -> dict:
    """Add required/forbidden content or extend the brief between takes —
    the correction-intake apply path (2026-08-13), same controlled-edit
    contract as amend_panel_camera: an APPROVED take freezes the panel;
    otherwise the lock re-stamps and the change is journaled, naming the
    rejection it was structured from. Additive only: nothing here removes
    or rewrites what the breakdown research established."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise KeyError(f"{spec_id} has no panel {panel_id}")
    _refuse_carried(spec, panel_id)
    approved = [r.get("candidate_id") for r in _board_records(spec_id)
                if r.get("status") == "APPROVED" and r.get("panel_id") == panel_id]
    if approved:
        raise PermissionError(
            f"{panel_id} has approved canon output ({', '.join(approved)}) painted "
            "from its current content. Reject that take first if you truly intend "
            "to change what this panel asks for.")
    changed = []
    for key, items in (("required_objects", add_required or []),
                       ("forbidden_objects", add_forbidden or [])):
        have = {str(x).casefold() for x in panel.get(key, [])}
        for item in items:
            item = str(item).strip()
            if item and item.casefold() not in have:
                panel.setdefault(key, []).append(item)
                have.add(item.casefold())
                changed.append(f"{key.split('_')[0]} + \"{item[:60]}\"")
    extra = str(purpose_append or "").strip()
    if extra and extra.casefold() not in str(panel.get("purpose", "")).casefold():
        panel["purpose"] = (str(panel.get("purpose", "")).strip()
                            + (" — " if panel.get("purpose") else "") + extra)
        changed.append(f"purpose + \"{extra[:60]}\"")
    if not changed:
        return {"spec_id": spec_id, "panel_id": panel_id, "changed": []}
    _atomic_write_json(_spec_path(spec_id), spec)
    if spec_locked(spec_id):
        from common import stable_hash  # scripts/common.py via paths sys.path hook
        locks = _load_locks()
        prev = locks.get(spec_id, {})
        locks[spec_id] = {**prev, "hash": stable_hash(spec), "amended_at": utcnow()}
        _atomic_write_json(paths.SPEC_LOCKS, locks)
        append_approval_log(
            f"SPECIFICATION {spec_id} panel {panel_id} content amended post-lock "
            f"(lock re-stamped {prev.get('hash', '?')[:16]}… → "
            f"{locks[spec_id]['hash'][:16]}…): {'; '.join(changed)}"
            + (f" — structured from {source}'s rejection" if source else "")
            + ". Existing takes keep the hash they were generated against.")
    return {"spec_id": spec_id, "panel_id": panel_id, "changed": changed}


def add_panel(spec_id: str, title: str, purpose: str) -> dict:
    """Append a panel to a sheet from the panels workbench, without a full
    unlock (user 2026-08-09: adding a panel mid-generation otherwise meant
    unlocking the sheet, which is blocked once any take is approved).

    Append-only, so nothing upstream of an existing approval changes: the new
    panel starts as a work order, the lock re-stamps, and the add is journaled
    — the same controlled-edit contract as `amend_panel_purpose`. It lands at
    0% allocation; the assembly gate surfaces the imbalance to be balanced in
    the sheet editor, readable as state before it is hit."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    purpose = str(purpose).strip()
    if not purpose:
        # validation's rule, held at the door: a panel needs a purpose or a
        # required object, and the workbench add only offers the brief.
        raise ValueError(
            "a new panel needs a brief — it is the only thing steering its "
            "render until objects are added on the sheet.")
    panels = spec.setdefault("panels", [])
    existing = {str(p.get("id", "")).upper() for p in panels}
    n = 1
    while f"P{n:02d}" in existing:
        n += 1
    pid = f"P{n:02d}"
    panel = {
        "id": pid,
        "title": str(title).strip() or pid,
        "purpose": purpose,
        "required_objects": [],
        "forbidden_objects": [],
        "evidence": ["USER_DIRECTED"],
        "scale": "MEDIUM",
        "composition_role": "support",
    }
    panels.append(panel)
    spec.setdefault("layout", {}).setdefault("panels", []).append(
        {"id": pid, "allocation_percent": 0})
    # A panel born inside a scoped revision is by definition revised there
    # — record it so the unit's panel floors stay truthful.
    if spec.get("revision_scope"):
        rs = spec["revision_scope"]
        if pid not in (rs.get("revised") or []):
            rs["revised"] = list(rs.get("revised") or []) + [pid]
    _atomic_write_json(_spec_path(spec_id), spec)
    if spec_locked(spec_id):
        from common import stable_hash  # scripts/common.py via paths sys.path hook
        locks = _load_locks()
        prev = locks.get(spec_id, {})
        locks[spec_id] = {**prev, "hash": stable_hash(spec), "amended_at": utcnow()}
        _atomic_write_json(paths.SPEC_LOCKS, locks)
        append_approval_log(
            f"SPECIFICATION {spec_id} panel {pid} added post-lock (lock re-stamped "
            f"{prev.get('hash', '?')[:16]}… → {locks[spec_id]['hash'][:16]}…): "
            f"\"{panel['title'][:80]}\". Allocation 0% until balanced; existing "
            "takes keep the hash they were generated against.")
    return panel


def delete_spec(spec_id: str) -> dict:
    """Permanently delete a specification and its candidates. Canon guard: a
    spec with APPROVED candidates or boards cannot be deleted — that output is
    locked canon. The deletion is journaled in the approval log."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)

    board_dir = paths.BOARDS_DIR / spec_id
    records = _board_records(spec_id)
    approved = _approved_outputs(spec_id)
    if approved:
        raise PermissionError(
            f"{spec_id} has approved canon output ({', '.join(approved)}) and cannot "
            "be deleted. Reject those candidates/boards first if you truly intend to "
            "destroy them.")

    n_images = len(list(board_dir.glob("*.png"))) if board_dir.exists() else 0
    locked = spec_locked(spec_id)
    if locked:
        locks = _load_locks()
        locks.pop(spec_id, None)
        _atomic_write_json(paths.SPEC_LOCKS, locks)
    if board_dir.exists():
        shutil.rmtree(board_dir)
    _spec_path(spec_id).unlink()
    append_approval_log(
        f"SPECIFICATION {spec_id} permanently deleted"
        + (" (was APPROVED/locked)" if locked else "")
        + f"; {len(records)} candidate record(s) and {n_images} image(s) removed.")
    return {"deleted": spec_id, "was_locked": locked,
            "candidates_removed": len(records), "images_removed": n_images}


def revise_spec(spec_id: str, revise_panels: list[str] | None = None) -> dict:
    """Clone a locked spec into the next revision as an editable DRAFT.

    revise_panels (user model 2026-08-13) declares WHICH panels the
    revision changes: those become editable; the rest are CARRIED —
    read-only in the clone, and their approvals keep feeding the unit's
    board (see app/revisions.py panel floors). None = all revised
    (legacy callers). Empty list = a layout-only revision. The scope is
    a canon-shaping declaration, so it is journaled."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    base = revisions.base_of(spec_id)
    revision = int(spec.get("revision", 1)) + 1
    new_id = f"{base}_R{revision}"
    p = _spec_path(new_id)
    if p.exists():
        raise FileExistsError(f"revision already exists: {new_id}")
    panel_ids = [str(x.get("id")) for x in spec.get("panels", [])]
    if revise_panels is None:
        revised = list(panel_ids)
    else:
        unknown = sorted(set(revise_panels) - set(panel_ids))
        if unknown:
            raise ValueError(
                f"unknown panel(s) for revision scope: {', '.join(unknown)}")
        revised = [pid for pid in panel_ids if pid in set(revise_panels)]
    carried = [pid for pid in panel_ids if pid not in set(revised)]
    clone = json.loads(json.dumps(spec))
    clone["specification_id"] = new_id
    clone["revision"] = revision
    clone["status"] = "DRAFT"
    clone["revised_from"] = {"specification_id": spec_id,
                             "locked": spec_locked(spec_id)}
    clone["revision_scope"] = {"revised": revised, "carried": carried}
    _atomic_write_json(p, clone)
    append_approval_log(
        f"SPECIFICATION {new_id} drafted from {spec_id} — revising: "
        f"{', '.join(revised) or 'layout only'}; carried read-only: "
        f"{', '.join(carried) or 'none'}.")
    return clone


def upgrade_revision_panel(spec_id: str, panel_id: str) -> dict:
    """'Also revise this panel' — a carried panel joins the revision.
    DRAFT-only, one-way, journaled: the stored scope is what the panel
    floors trust, so it only ever moves toward 'revised'."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    scope = spec.get("revision_scope")
    if spec_locked(spec_id) or spec.get("status") == "APPROVED" or not scope:
        raise ValueError(
            f"{spec_id} is not a draft revision with a scope — nothing to upgrade")
    if panel_id in (scope.get("revised") or []):
        raise ValueError(f"{panel_id} is already being revised")
    if panel_id not in (scope.get("carried") or []):
        raise KeyError(f"{spec_id} has no carried panel {panel_id}")
    scope["carried"] = [p for p in scope["carried"] if p != panel_id]
    scope["revised"] = list(scope.get("revised") or []) + [panel_id]
    _atomic_write_json(_spec_path(spec_id), spec)
    append_approval_log(
        f"SPECIFICATION {spec_id}: {panel_id} upgraded into the revision "
        "(carried → revised) — its board slot will ask for a new take.")
    return scope


def _carried_panel_violation(spec_id: str, incoming: dict) -> str | None:
    """The carried-panel contract: while a draft revision declares a
    scope, its carried panels must remain byte-identical to the source
    revision's. Returns a stated violation, or None."""
    stored = get_spec(spec_id) or {}
    scope = stored.get("revision_scope")
    if not scope or stored.get("status") == "APPROVED" or spec_locked(spec_id):
        return None
    source_id = str((stored.get("revised_from") or {})
                    .get("specification_id", ""))
    source = get_spec(source_id) or {}
    src_by_id = {str(p.get("id")): p for p in source.get("panels", [])}
    inc_by_id = {str(p.get("id")): p for p in incoming.get("panels", [])}
    for pid in scope.get("carried", []):
        if pid not in src_by_id:
            continue
        if pid not in inc_by_id:
            return (f"{pid} is carried read-only in this revision and cannot "
                    "be removed — use 'Also revise' first")
        if (json.dumps(inc_by_id[pid], sort_keys=True)
                != json.dumps(src_by_id[pid], sort_keys=True)):
            return (f"{pid} is carried read-only in this revision — use "
                    "'Also revise' to edit it")
    return None
