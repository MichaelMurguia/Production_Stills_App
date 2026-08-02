"""Project backup and restore — safeguarding the creative work.

A backup is one zip of one project's whole home (data/, project_state/,
context/, project.json). Install-level settings (API keys) are NEVER
included — a backup is shareable creative work, not credentials. Restore
always creates a NEW project (never overwrites), with every archive member
validated against zip-slip before a byte is written.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import shutil
import zipfile
from pathlib import Path

from . import paths

# Refuse absurd archives before extraction: per-member and total caps.
MAX_MEMBER_BYTES = 500 * 1024 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024 * 1024

BACKUP_DIRS = ("data", "project_state", "context")


class BackupError(Exception):
    pass


def _project_base(slug: str) -> Path:
    base = paths._project_base(slug)
    if not base.exists() or (slug and not (paths.PROJECTS_DIR / slug).is_dir()):
        raise KeyError(slug or "(root)")
    return base


def make_backup(slug: str) -> tuple[bytes, str]:
    """Zip the project → (bytes, filename). Records last_backup_at in the
    project's project.json (best effort — the zip is the point)."""
    base = _project_base(slug)
    name = paths._project_name(base, slug or "main-project")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        meta = _read_project_meta(base)
        meta["name"] = name
        z.writestr("project.json", json.dumps(meta, indent=2) + "\n")
        for top in BACKUP_DIRS:
            d = base / top
            if not d.exists():
                continue
            for p in sorted(d.rglob("*")):
                if p.is_file():
                    rel = p.relative_to(base).as_posix()
                    if rel == "data/settings.json":
                        continue  # legacy key location — never in a backup
                    z.write(p, rel)
    _record_backup(base)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "project"
    return buf.getvalue(), f"screenboard-backup-{safe}-{stamp}.zip"


def _read_project_meta(base: Path) -> dict:
    meta = base / "project.json"
    if meta.exists():
        try:
            return json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _record_backup(base: Path) -> None:
    try:
        meta = _read_project_meta(base)
        meta["last_backup_at"] = dt.datetime.now(dt.timezone.utc).isoformat(
            timespec="seconds")
        (base / "project.json").write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def last_backup_at(slug: str) -> str:
    try:
        return str(_read_project_meta(paths._project_base(slug))
                   .get("last_backup_at") or "")
    except Exception:
        return ""


def _safe_member(name: str) -> str:
    """Zip-slip guard: reject absolute paths, drive letters, backslashes,
    and any traversal component; only expected top-level dirs extract."""
    if "\\" in name or name.startswith("/") or ":" in name:
        raise BackupError(f"unsafe archive member: {name}")
    parts = name.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise BackupError(f"unsafe archive member: {name}")
    if parts[0] != "project.json" and parts[0] not in BACKUP_DIRS:
        raise BackupError(f"unexpected archive member: {name}")
    return name


def restore_backup(payload: bytes) -> dict:
    """Create a NEW project from a backup zip; returns {slug, name}.
    Existing projects are never touched — a name collision gets a numeric
    suffix. Every member is validated before extraction."""
    try:
        z = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as e:
        raise BackupError("that file is not a production backup zip") from e

    total = 0
    members = []
    for info in z.infolist():
        if info.is_dir():
            continue
        _safe_member(info.filename)
        if info.file_size > MAX_MEMBER_BYTES:
            raise BackupError(f"archive member too large: {info.filename}")
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise BackupError("archive too large to restore")
        members.append(info)
    if not members:
        raise BackupError("the archive is empty")

    name = "Restored project"
    try:
        meta = json.loads(z.read("project.json").decode("utf-8"))
        name = str(meta.get("name") or name)
    except Exception:
        pass

    slug_base = re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-._") or "restored"
    slug = slug_base
    n = 2
    while (paths.PROJECTS_DIR / slug).exists():
        slug = f"{slug_base}-{n}"
        n += 1

    # Extract into a hidden staging dir renamed into place on success — a
    # half-written tree must never appear on the shelf as a real
    # production. Size caps are enforced on the DECOMPRESSED stream, not
    # the attacker-controlled header sizes.
    dest = paths.PROJECTS_DIR / slug
    staging = paths.PROJECTS_DIR / f".restore-{slug}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        total_out = 0
        for info in members:
            target = staging / info.filename
            # Belt and braces on top of _safe_member.
            if not target.resolve().is_relative_to(staging.resolve()):
                raise BackupError(f"unsafe archive member: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with z.open(info) as src, target.open("wb") as out:
                while chunk := src.read(1 << 20):
                    written += len(chunk)
                    total_out += len(chunk)
                    if written > MAX_MEMBER_BYTES or total_out > MAX_TOTAL_BYTES:
                        raise BackupError(
                            f"archive member exceeds its declared size: {info.filename}")
                    out.write(chunk)
        meta = _read_project_meta(staging)
        meta["name"] = name
        meta["restored_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        (staging / "project.json").write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        staging.rename(dest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {"slug": slug, "name": name}


def days_since_backup(slug: str) -> int | None:
    """None = never backed up; otherwise whole days since the last one."""
    stamp = last_backup_at(slug)
    if not stamp:
        return None
    try:
        then = dt.datetime.fromisoformat(stamp)
    except ValueError:
        return None
    return max(0, (dt.datetime.now(dt.timezone.utc) - then).days)
