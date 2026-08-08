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


def make_backup(slug: str, record: bool = True) -> tuple[bytes, str]:
    """Zip the project → (bytes, filename). Records last_backup_at in the
    project's project.json (best effort — the zip is the point).

    record=False is for the safety zip an import takes on the user's behalf:
    it is a real archive, but it is not the user's own backup and must not
    make the shelf's care line read BACKED UP TODAY."""
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
    if record:
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


def _open_archive(payload: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as e:
        raise BackupError("that file is not a production backup zip") from e


def _validated_members(payload_z: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Every member checked for zip-slip and declared size before a single
    byte is written. Shared by restore (new project) and import (overwrite)
    so the two paths can never drift apart on safety."""
    total = 0
    members = []
    for info in payload_z.infolist():
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
    return members


def _archive_meta(z: zipfile.ZipFile) -> dict:
    try:
        return json.loads(z.read("project.json").decode("utf-8"))
    except Exception:
        return {}


def _extract_members(z: zipfile.ZipFile, members: list[zipfile.ZipInfo],
                     staging: Path) -> None:
    """Size caps are enforced on the DECOMPRESSED stream, not the
    attacker-controlled header sizes."""
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


def inspect_backup(payload: bytes) -> dict:
    """Read a backup zip and write NOTHING — what the archive holds, so an
    overwrite can be described accurately before it is confirmed rather
    than reported after it has happened."""
    z = _open_archive(payload)
    members = _validated_members(z)
    meta = _archive_meta(z)
    return {
        "name": str(meta.get("name") or "Unnamed production"),
        "created_at": str(meta.get("created_at") or ""),
        "backed_up_at": str(meta.get("last_backup_at") or ""),
        "files": len(members),
        "bytes": sum(m.file_size for m in members),
        "counts": {top: sum(1 for m in members
                            if m.filename.startswith(f"{top}/"))
                   for top in BACKUP_DIRS},
    }


def import_into(slug: str, payload: bytes) -> dict:
    """Set an EXISTING production to the version a backup holds.

    The production keeps its identity — name, slug, place on the shelf; only
    what a backup carries (data/, project_state/, context/) is replaced. It
    is destructive, so two things happen before anything is removed: the
    current state is packed to a safety zip beside the production, and the
    archive is extracted to a staging dir. The swap is renames only, and a
    failure mid-swap puts back what it moved — a half-written import never
    becomes the production.
    """
    base = _project_base(slug)
    z = _open_archive(payload)
    members = _validated_members(z)
    source_name = str(_archive_meta(z).get("name") or "Unnamed production")

    # Two imports inside one second must not collide — the second safety zip
    # is the one you want when the first import was the mistake.
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    safety = base / f"pre-import-{stamp}.zip"
    n = 2
    while safety.exists():
        safety = base / f"pre-import-{stamp}-{n}.zip"
        n += 1
    payload = make_backup(slug, record=False)[0]
    # Filling the volume to protect against an import is self-defeating —
    # and the import that follows needs room too.
    from . import storage
    if not storage.free_bytes() or storage.free_bytes() < len(payload) * 2:
        raise BackupError(
            f"Not enough disk space to take a safety copy before importing: "
            f"{storage.human(storage.free_bytes())} free, and the copy alone "
            f"is {storage.human(len(payload))}. Free space first — the import "
            "was not started and nothing was changed.")
    safety.write_bytes(payload)
    _prune_safety_zips(base)

    staging = base / ".import-staging"
    trash = base / ".import-replaced"
    for d in (staging, trash):
        if d.exists():
            shutil.rmtree(d)
    staging.mkdir(parents=True)
    try:
        _extract_members(z, members, staging)
        trash.mkdir(parents=True)
        moved: list[str] = []
        try:
            for top in BACKUP_DIRS:
                if (base / top).exists():
                    (base / top).rename(trash / top)
                    moved.append(top)
                if (staging / top).exists():
                    (staging / top).rename(base / top)
        except BaseException:
            for top in moved:
                shutil.rmtree(base / top, ignore_errors=True)
                (trash / top).rename(base / top)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(trash, ignore_errors=True)

    meta = _read_project_meta(base)
    meta["name"] = paths._project_name(base, slug or "Untitled Production")
    meta["imported_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    meta["imported_from"] = source_name
    # The incoming content has never been backed up BY THIS PRODUCTION, and
    # the old stamp described work that is no longer here. Clearing it makes
    # the shelf's care line tell the truth and asks for a fresh backup.
    meta.pop("last_backup_at", None)
    (base / "project.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    return {"slug": slug, "name": meta["name"], "imported_from": source_name,
            "files": len(members), "safety_zip": safety.name}


def _prune_safety_zips(base: Path, keep: int = 1) -> None:
    """Safety zips are insurance, not an archive — keep the newest ONE.

    Three full copies of a production on the same volume the production
    lives on is a lot of disk for insurance (user 2026-08-07, after a
    studio filled its volume). One copy, downloadable, is the useful
    amount; older ones go as soon as a newer one exists."""
    # By mtime, NOT by name: two imports in one second produce
    # "…-120000.zip" and "…-120000-2.zip", and "-" sorts before "." — so a
    # name sort kept the OLDER copy and deleted the one just written.
    zips = sorted(base.glob("pre-import-*.zip"), key=lambda z: z.stat().st_mtime)
    for stale in zips[:-keep] if len(zips) > keep else []:
        stale.unlink(missing_ok=True)


def restore_backup(payload: bytes) -> dict:
    """Create a NEW project from a backup zip; returns {slug, name}.
    Existing projects are never touched — a name collision gets a numeric
    suffix. Every member is validated before extraction."""
    z = _open_archive(payload)
    members = _validated_members(z)
    name = str(_archive_meta(z).get("name") or "Restored project")

    slug_base = re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-._") or "restored"
    slug = slug_base
    n = 2
    while (paths.PROJECTS_DIR / slug).exists():
        slug = f"{slug_base}-{n}"
        n += 1

    # Extract into a hidden staging dir renamed into place on success — a
    # half-written tree must never appear on the shelf as a real production.
    dest = paths.PROJECTS_DIR / slug
    staging = paths.PROJECTS_DIR / f".restore-{slug}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        _extract_members(z, members, staging)
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
