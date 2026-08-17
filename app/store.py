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


def resolve_spec_current(spec_id: str) -> dict | None:
    """The unit's CURRENT truth: the newest locked revision of the id's
    base, else the spec itself. Board-facing reads use this instead of
    get_spec because the base id is also R1's id — reading it directly
    silently serves a stale revision (one board per unit, 2026-08-13)."""
    current = revisions.newest_locked_revision(revisions.base_of(spec_id))
    return get_spec(current or spec_id)


def evidence_rows_for_panel(spec: dict, panel_id: str) -> list[dict]:
    """Which evidence rows justify a panel's required objects.

    ONE list, read by the approval SNAPSHOT and by the GATE that protects
    it. A comment above the snapshot copy already claimed they shared it —
    "what an approval freezes and what a locked breakdown refuses must be
    the same set, or the app promises one thing and guards another" — and
    what was actually shared was the board-field list, not this predicate.
    The two agreed by coincidence of having been typed twice (adversarial
    review F13). A comment asserting a sharing that does not exist is worse
    than no comment: the next reader trusts it and changes one side.
    """
    objs = {str(o).lower()
            for o in next((p.get("required_objects") or []
                           for p in (spec.get("panels") or [])
                           if p.get("id") == panel_id), [])}
    return [r for r in (spec.get("evidence_ledger") or [])
            if str(r.get("panel_id", "")).upper() == str(panel_id).upper()
            or str(r.get("object", "")).lower() in objs]


def _refuse_frozen_edits(spec_id: str, current: dict, incoming: dict) -> None:
    """What a locked breakdown will not accept (user rulings 2026-08-16).

    One breakdown, edited in place. An approval freezes exactly what it
    was approved against and nothing else: that panel's own fields, the
    evidence rows justifying its objects, and — because they ride into
    every prompt — the board-level fields for the whole sheet."""
    approved = approved_takes_by_panel(spec_id)
    if not approved:
        return

    changed_board = [f for f in BOARD_LEVEL_FIELDS
                     if f in incoming and incoming.get(f) != current.get(f)]
    if changed_board:
        refuse_if_any_panel_approved(spec_id, changed_board)

    cur_panels = {p.get("id"): p for p in (current.get("panels") or [])}
    new_panels = {p.get("id"): p for p in (incoming.get("panels") or [])}
    for pid in approved:
        if pid not in new_panels and pid in cur_panels:
            raise PermissionError(
                f"{pid} has an approved take and cannot be removed from the "
                "breakdown. Withdraw that approval first.")
        if pid in new_panels and new_panels[pid] != cur_panels.get(pid):
            refuse_if_panel_approved(spec_id, pid, "specification")

    # Evidence rows are frozen for an approved panel's objects — they are
    # the justification for what actually got rendered (user ruling).
    rows_for = evidence_rows_for_panel

    for pid in approved:
        if rows_for(incoming, pid) != rows_for(current, pid):
            raise PermissionError(
                f"the evidence rows justifying {pid}'s objects are frozen — "
                f"{pid} has an approved take that those rows account for. "
                "Withdraw that approval to change them.")


def save_spec(spec_id: str, spec: dict) -> dict:
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
    current = get_spec(spec_id) or {}
    stored_scope = current.get("revision_scope")
    if stored_scope is not None:
        spec["revision_scope"] = stored_scope
    locked = spec_locked(spec_id)
    if locked:
        _refuse_frozen_edits(spec_id, current, spec)
    _atomic_write_json(p, spec)
    if locked:
        # The lock re-stamps to the amended document and the change is
        # journaled — every take keeps the hash it was rendered against,
        # so provenance stays per-candidate rather than per-sheet.
        from common import stable_hash
        locks = _load_locks()
        prev = locks.get(spec_id, {})
        locks[spec_id] = {**prev, "hash": stable_hash(spec), "amended_at": utcnow()}
        _atomic_write_json(paths.SPEC_LOCKS, locks)
        changed = [f for f in BOARD_LEVEL_FIELDS
                   if f in spec and spec.get(f) != current.get(f)]
        append_approval_log(
            f"SPECIFICATION {spec_id} amended post-lock (lock re-stamped "
            f"{prev.get('hash', '?')[:16]}… → {locks[spec_id]['hash'][:16]}…)"
            + (f": {', '.join(changed)}." if changed else ".")
            + " Existing takes keep the hash they were generated against.")
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
    """Approved takes/boards generated AGAINST this spec id — scanned
    across the unit's sibling revision dirs (2026-08-13): board artifacts
    now land in the base dir but carry the structure revision's id, so a
    board built on R2 must keep blocking R2's unlock wherever it lives."""
    out = []
    for rid in revisions.revisions_of(revisions.base_of(spec_id)) or [spec_id]:
        for r in _board_records(rid):
            if (r.get("status") == "APPROVED"
                    and str(r.get("specification_id") or rid) == spec_id):
                out.append(r.get("candidate_id"))
    return out


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


# The fields that belong to the BOARD rather than to one panel. They ride
# into every panel's prompt, so they are exactly what an approval freezes
# — and this one list is both what a snapshot captures and what the gate
# protects, so the promise and the guard can never drift apart.
BOARD_LEVEL_FIELDS = (
    "subject", "board_type", "setting", "scene", "mode", "render_intent",
    "forbidden_elements", "canon_budget", "design_languages", "scene_lessons",
    "environments", "layout",
)


def approved_takes_by_panel(spec_id: str) -> dict[str, list[str]]:
    """panel_id → the approved candidate ids that freeze it."""
    out: dict[str, list[str]] = {}
    for r in _board_records(spec_id):
        if r.get("status") == "APPROVED":
            out.setdefault(str(r.get("panel_id", "")), []).append(
                str(r.get("candidate_id", "")))
    return out


def refuse_if_panel_approved(spec_id: str, panel_id: str, what: str) -> None:
    """The one gate of the one-breakdown model (user ruling 2026-08-16): a
    locked breakdown is edited in place, and the only thing that stops an
    edit is an approved take ON THAT PANEL.

    Withdrawing is the way through, NOT rejecting — a rejection is a
    judgement that rides into every future prompt for the panel, and
    wanting to change what the panel asks for is not that."""
    approved = approved_takes_by_panel(spec_id).get(panel_id, [])
    if approved:
        raise PermissionError(
            f"{panel_id} has approved canon output ({', '.join(approved)}) "
            f"painted from its current {what}. Withdraw that approval first "
            "if you intend to change what this panel asks for — withdrawing "
            "keeps the image and carries nothing into future prompts.")


def refuse_if_any_panel_approved(spec_id: str, fields: list[str]) -> None:
    """Board-level fields lock the moment ANY panel is approved (user
    ruling 2026-08-16). They ride into every prompt, so letting them drift
    under an approved image would leave that image accounted for by a
    document it was never rendered from."""
    approved = approved_takes_by_panel(spec_id)
    if not approved:
        return
    who = ", ".join(f"{pid} ({', '.join(ids)})" for pid, ids in sorted(approved.items()))
    raise PermissionError(
        f"{', '.join(fields)} {'is' if len(fields) == 1 else 'are'} board-level "
        f"and every panel renders from it. {who} already approved against the "
        "current text, so it is frozen. Withdraw that approval to change it.")


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


def amend_panel_objects(spec_id: str, panel_id: str, add: list[dict] | None = None,
                        remove: list[str] | None = None) -> dict:
    """Add or drop required objects between takes, from the workbench.

    The brief and the camera have been amendable here since 2026-08-08;
    the objects were not, so a screenplay scan run from the Panels page
    had nowhere to put what it found (user 2026-08-17). Same lock
    discipline as the others: journaled, lock re-stamped, refused only
    where an APPROVED take already froze this panel.

    Each added object carries its own evidence. A scan-sourced object
    arrives with the VERBATIM screenplay line that produced it, so it is
    filed SCRIPT_EXPLICIT against that quote rather than USER_DIRECTED —
    which is the truth, and is what validation wants to see. Without a
    PASS row the object would block approval, so writing the row is not
    a nicety, it is the other half of adding the object."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise KeyError(f"{spec_id} has no panel {panel_id}")
    _refuse_carried(spec, panel_id)
    refuse_if_panel_approved(spec_id, panel_id, "required objects")

    objs = [str(o) for o in (panel.get("required_objects") or [])]
    have = {o.casefold() for o in objs}
    ledger = list(spec.get("evidence_ledger") or [])
    added: list[str] = []
    unverified: list[str] = []
    for item in (add or []):
        obj = str(item.get("object", "")).strip()
        if not obj or obj.casefold() in have:
            continue
        quote = str(item.get("quote", "")).strip()
        # A citation is only a citation if the screenplay contains it
        # (adversarial review F6). This filed SCRIPT_EXPLICIT/PASS on the
        # mere PRESENCE of a quote string, so a hand-crafted request — or a
        # scan that fell back to the sheet's model-written scene prose —
        # could put a fabricated line into the ledger as the screenplay's
        # word, and satisfy the lock gate with it.
        #
        # An unverifiable quote does not demote to WEAK_INFERENCE here, as
        # it does in autofill: the USER asked for this object, so the honest
        # class is USER_DIRECTED. Their direction is authority; the citation
        # is the only part that was false.
        # Imported here, not at module scope: insights imports store.
        from . import insights
        if quote and not insights.quote_is_in_screenplay(quote):
            unverified.append(obj)
            quote = ""
        objs.append(obj)
        have.add(obj.casefold())
        added.append(obj)
        ledger.append({
            "panel_id": panel_id, "object": obj,
            "evidence_class": "SCRIPT_EXPLICIT" if quote else "USER_DIRECTED",
            "source": quote or "User direction",
            "quote": quote,
            "status": "PASS",
        })

    drop = {str(o).casefold() for o in (remove or [])}
    dropped = [o for o in objs if o.casefold() in drop]
    if dropped:
        objs = [o for o in objs if o.casefold() not in drop]
        ledger = [r for r in ledger
                  if not (str(r.get("panel_id", "")).upper() == panel_id.upper()
                          and str(r.get("object", "")).casefold() in drop)]

    if not added and not dropped:
        return {"panel_id": panel_id, "added": [], "removed": [],
                "unverified_citations": unverified, "required_objects": objs}

    panel["required_objects"] = objs
    spec["evidence_ledger"] = ledger
    _atomic_write_json(_spec_path(spec_id), spec)
    if spec_locked(spec_id):
        from common import stable_hash
        locks = _load_locks()
        prev = locks.get(spec_id, {})
        locks[spec_id] = {**prev, "hash": stable_hash(spec), "amended_at": utcnow()}
        _atomic_write_json(paths.SPEC_LOCKS, locks)
    append_approval_log(
        f"SPECIFICATION {spec_id} panel {panel_id} required objects amended"
        + (f" — added {', '.join(added)}" if added else "")
        + (f" — removed {', '.join(dropped)}" if dropped else "")
        + ". Existing takes keep the hash they were generated against.")
    return {"panel_id": panel_id, "added": added, "removed": dropped,
            # Stated, so the UI can say the citation did not hold rather
            # than quietly filing a weaker class.
            "unverified_citations": unverified,
            "required_objects": objs}


def amend_object_refs(spec_id: str, panel_id: str, obj: str,
                      exclude: list[str] | None = None,
                      include: list[str] | None = None) -> dict:
    """Say that a required object is NOT covered by a reference group, or
    take that back (user 2026-08-16: "I have reference for 'airlock hatch
    behind Sal' and it's green but the reference is wrong so I want to
    delete it").

    The app decides which plates cover an object by matching the object's
    wording against the group's name, and that match cannot read grammar:
    "airlock hatch behind Sal" names Sal because Sal is IN the phrase, even
    though the object is an airlock and Sal is only where it sits. Guessing
    harder is the wrong answer — a possessive, a preposition and a subject
    all look alike to a matcher. The right answer is that the production
    can overrule it, per object, and the overrule is remembered.

    Kept on the PANEL rather than in UI state: "this object is not about
    that plate" is a fact about the breakdown, it travels with the project,
    and it should survive a different browser."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise KeyError(f"{spec_id} has no panel {panel_id}")
    _refuse_carried(spec, panel_id)
    refuse_if_panel_approved(spec_id, panel_id, "object references")

    key = str(obj).strip()
    if not key:
        raise ValueError("which required object?")
    table = dict(panel.get("ref_exclusions") or {})
    now = {str(x) for x in (table.get(key) or [])}
    now |= {str(x) for x in (exclude or [])}
    now -= {str(x) for x in (include or [])}
    if now:
        table[key] = sorted(now)
    else:
        table.pop(key, None)
    if table:
        panel["ref_exclusions"] = table
    else:
        panel.pop("ref_exclusions", None)

    _atomic_write_json(_spec_path(spec_id), spec)
    if spec_locked(spec_id):
        from common import stable_hash
        locks = _load_locks()
        prev = locks.get(spec_id, {})
        locks[spec_id] = {**prev, "hash": stable_hash(spec), "amended_at": utcnow()}
        _atomic_write_json(paths.SPEC_LOCKS, locks)
    append_approval_log(
        f"SPECIFICATION {spec_id} panel {panel_id} object \"{key[:80]}\": "
        + (f"reference groups {', '.join(sorted(now))} ruled NOT its reference."
           if now else "reference match restored.")
        + " Affects which plates the panel offers and pre-ticks, never a take "
          "already rendered.")
    return {"panel_id": panel_id, "object": key, "excluded": sorted(now)}


def amend_panel_prompt(spec_id: str, panel_id: str, text: str) -> dict:
    """Save a hand-written prompt onto one panel, or clear it (empty text).

    The workbench could edit the compiled prompt for a single take but not
    keep it (user 2026-08-16: "I need to be able to Save the prompt once I
    edit it — explicit button"). A test run is one take; a correction the
    compile cannot express is a standing fact about the panel.

    This is the sharpest override in the app and it is deliberately loud:
    while a panel carries one, steps 01–04 STOP FEEDING ITS RENDER. Editing
    the camera or the required objects then changes nothing visible, which
    is exactly the silent trap the gate rules exist to prevent — so the
    saved text is stamped with the compile it replaced, and every surface
    that shows a step says the panel is off the compile.

    Same lock discipline as amend_panel_purpose: journaled, lock re-stamped,
    refused only where an APPROVED take already froze this panel."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise KeyError(f"{spec_id} has no panel {panel_id}")
    _refuse_carried(spec, panel_id)
    refuse_if_panel_approved(spec_id, panel_id, "prompt")

    body = str(text or "").strip()
    had = bool(str(panel.get("prompt_override", "")).strip())
    if body:
        # A prompt short enough to be an accident is not a prompt. The
        # compile runs to ~11k characters; a stray paste of one line would
        # silently strip the panel of its canon rules.
        if len(body) < 200:
            raise ValueError(
                "a saved prompt replaces the whole compiled prompt — canon "
                "rules, camera, references and all. This one is "
                f"{len(body)} characters, which is too short to be that. "
                "Edit the compiled text rather than replacing it.")
        panel["prompt_override"] = body
        panel["prompt_override_at"] = utcnow()
    else:
        panel.pop("prompt_override", None)
        panel.pop("prompt_override_at", None)

    _atomic_write_json(_spec_path(spec_id), spec)
    if spec_locked(spec_id):
        from common import stable_hash  # scripts/common.py via paths sys.path hook
        locks = _load_locks()
        prev = locks.get(spec_id, {})
        locks[spec_id] = {**prev, "hash": stable_hash(spec), "amended_at": utcnow()}
        _atomic_write_json(paths.SPEC_LOCKS, locks)
    append_approval_log(
        f"SPECIFICATION {spec_id} panel {panel_id} "
        + (f"prompt SAVED by hand ({len(body)} characters) — steps 01–04 no "
           "longer compile this panel's render."
           if body else
           "saved prompt CLEARED — the panel compiles from steps 01–04 again.")
        + " Existing takes keep the prompt and hash they were generated against.")
    return {"panel_id": panel_id, "saved": bool(body),
            "was_saved": had, "chars": len(body)}


def panel_prompt_override(spec_id: str, panel_id: str) -> str:
    """The panel's saved prompt, or '' — one reader so the preview, the
    render and the state line can never disagree about what will be sent."""
    spec = get_spec(spec_id)
    if spec is None:
        return ""
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    return str((panel or {}).get("prompt_override", "")).strip()


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
    refuse_if_panel_approved(spec_id, panel_id, "purpose")
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
    refuse_if_panel_approved(spec_id, panel_id, "camera")
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
    refuse_if_panel_approved(spec_id, panel_id, "content")
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

    # Units dismantle newest-first (2026-08-13): the base dir is shared —
    # it is R1's take dir AND holds the unit's board artifacts, keeps and
    # floor history — so a revision with later siblings must not fall.
    newer = [rid for rid in revisions.revisions_of(revisions.base_of(spec_id))
             if revisions.revision_of(rid) > revisions.revision_of(spec_id)]
    if newer:
        raise PermissionError(
            f"{spec_id} has later revisions ({', '.join(newer)}) — the "
            "unit's board history and carried panels feed from it. Delete "
            "the newest revision first.")

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
