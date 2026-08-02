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

from . import paths

REF_STATUSES = {"PROVISIONAL", "APPROVED", "REJECTED"}
THUMB_SIZE = 480

# Roles suggested by context/02_CANON_AND_REFERENCE_RULES.md; free-form roles
# are also allowed — these seed the UI dropdown.
SUGGESTED_ROLES = [
    "BOARD_RENDERING_STYLE",
    "CINEMATOGRAPHY_STYLE",
    "BOARD_LAYOUT_STYLE",
    "CHARACTER_LIKENESS",
    "VEHICLE_GEOMETRY",
    "ENVIRONMENT_LAYOUT",
    "SCENE_REFERENCE",
    "LIGHTING_REFERENCE",
    "MATERIAL_REFERENCE",
    "PROP_REFERENCE",
]

# Style roles auto-attached to every panel generation (style anchors HOW it
# is painted/photographed; subject references anchor WHAT things are).
# BOARD_LAYOUT_STYLE is style-kind but board-assembly grammar, so it stays a
# manual attachment.
AUTO_STYLE_ROLES = {"BOARD_RENDERING_STYLE", "CINEMATOGRAPHY_STYLE"}


def role_head(role: str) -> str:
    """The role's family name, tolerant of legacy underscore-sanitized records
    (e.g. 'CHARACTER_LIKENESS_—_JOHN' → 'CHARACTER_LIKENESS')."""
    return str(role or "").split("—")[0].strip(" _-").upper()


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
    """Approved style anchors attached to every panel generation."""
    return [r for r in _load_refs()
            if r["status"] == "APPROVED" and role_head(r["role"]) in AUTO_STYLE_ROLES]


def get_reference(ref_id: str) -> dict | None:
    return next((r for r in _load_refs() if r["id"] == ref_id), None)


def _make_thumb(src: Path, ref_id: str) -> str:
    thumb_name = f"{ref_id}.jpg"
    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((THUMB_SIZE, THUMB_SIZE))
        im.save(paths.REF_THUMBS / thumb_name, "JPEG", quality=88)
    return thumb_name


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
                  notes: str = "") -> dict:
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
        thumb = _make_thumb(dest, ref_id)
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
        "sha256": sha256_file(dest),
        "added_at": utcnow(),
        "updated_at": utcnow(),
    }
    refs = _load_refs()
    refs.append(record)
    _save_refs(refs)
    return record


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


def reference_image_path(ref_id: str, thumb: bool = False,
                         include_quarantine: bool = False) -> Path | None:
    """Resolve a reference's image. Quarantined (REJECTED) files resolve
    only when the record itself says REJECTED or the caller explicitly
    asks — the physical quarantine must hold even if index and disk ever
    disagree; generation paths must never attach a rejected file."""
    r = get_reference(ref_id)
    if not r:
        return None
    if thumb:
        p = paths.REF_THUMBS / r["thumb"]
        return p if p.exists() else None
    p = paths.REF_ORIGINALS / r["file"]
    if p.exists():
        return p
    if include_quarantine or r.get("status") == "REJECTED":
        q = paths.REF_QUARANTINE / r["file"]
        if q.exists():
            return q
    return None


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


def revise_spec(spec_id: str) -> dict:
    """Clone a locked spec into the next revision as an editable DRAFT."""
    spec = get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    base = re.sub(r"_R\d+$", "", spec_id)
    revision = int(spec.get("revision", 1)) + 1
    new_id = f"{base}_R{revision}"
    p = _spec_path(new_id)
    if p.exists():
        raise FileExistsError(f"revision already exists: {new_id}")
    clone = json.loads(json.dumps(spec))
    clone["specification_id"] = new_id
    clone["revision"] = revision
    clone["status"] = "DRAFT"
    clone["revised_from"] = {"specification_id": spec_id,
                             "locked": spec_locked(spec_id)}
    _atomic_write_json(p, clone)
    return clone
