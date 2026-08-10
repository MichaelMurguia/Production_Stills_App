from __future__ import annotations
import os
import sys
import threading
from pathlib import Path

# Guards every flip-work-restore sequence over the module-level project
# paths (the projects-summary sweep points the globals at each production
# in turn) and any read-modify-write that must not interleave with a flip
# — a counter allocation or switch landing mid-sweep once risked writing
# one production's record into another's directory. Reentrant: a switch
# inside a locked sweep nests cleanly.
SWITCH_LOCK = threading.RLock()

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
# SCREENBOARD_HOME relocates everything user-mutable (projects, settings) —
# cloud workspaces point it at their persistent volume. Unset (every
# standalone install), it is the repo root and nothing changes.
HOME = Path(os.environ.get("SCREENBOARD_HOME") or ROOT)

# Install-level, project-independent: API keys / engine registry, the
# active-project pointer, and the projects directory itself.
SETTINGS = HOME / "settings.json"
ACTIVE_PROJECT_FILE = HOME / "active_project.json"
PROJECTS_DIR = HOME / "projects"

STATIC = Path(__file__).resolve().parent / "static"

# The governance scripts (validate_spec, audit_spec, common) are the canon
# rule engine; the app imports them rather than reimplementing the rules.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def safe_id(name: str) -> str:
    """Traversal guard for URL-supplied ids that become path components:
    one alnum-led component, no separators, no dot-led names (so '..' can
    never pass). KeyError → the API's 404. Use on every spec/candidate id
    that reaches the filesystem."""
    import re as _re
    n = str(name or "")
    if not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", n):
        raise KeyError(name)
    return n


def _project_base(slug: str) -> Path:
    """'' is the legacy root project (data/ directly under HOME — every
    install that predates multi-project); named projects live under
    HOME/projects/<slug>/."""
    return HOME if not slug else PROJECTS_DIR / slug


def set_project(slug: str) -> None:
    """Point every mutable path at one project. All modules read these as
    paths.X at call time (verified: no `from .paths import X` anywhere), so
    reassignment here switches the whole app."""
    global ACTIVE_PROJECT, DATA, REFERENCES, REF_ORIGINALS, REF_THUMBS, \
        REF_QUARANTINE, REF_INDEX, SCREENPLAY_DIR, SPECS_DIR, SPEC_LOCKS, \
        APP_STATE, SUBJECTS, WIZARD_ANALYSIS, BOARDS_DIR, BIBLE, \
        PROJECT_STATE, APPROVAL_LOG, REJECTION_HISTORY, CAMERA_DEFAULTS
    base = _project_base(slug)
    ACTIVE_PROJECT = slug
    DATA = base / "data"
    REFERENCES = DATA / "references"
    REF_ORIGINALS = REFERENCES / "originals"
    REF_THUMBS = REFERENCES / "thumbs"
    REF_QUARANTINE = REFERENCES / "quarantine"
    REF_INDEX = REFERENCES / "references.json"
    SCREENPLAY_DIR = DATA / "screenplay"
    SPECS_DIR = DATA / "specs"
    SPEC_LOCKS = SPECS_DIR / "locks.json"
    APP_STATE = DATA / "app_state.json"
    CAMERA_DEFAULTS = DATA / "camera_defaults.json"
    SUBJECTS = DATA / "subjects.json"
    WIZARD_ANALYSIS = DATA / "wizard_analysis.json"
    BOARDS_DIR = DATA / "boards"
    BIBLE = base / "context" / "01_ART_DIRECTION_BIBLE.md"
    PROJECT_STATE = base / "project_state" / "project_state.json"
    APPROVAL_LOG = base / "project_state" / "approval_log.md"
    REJECTION_HISTORY = base / "project_state" / "rejection_history.md"


def list_projects() -> list[dict]:
    """Every directory under HOME/projects/, plus the legacy root project —
    which is listed only while it has content (a data/ dir), is active, or
    no named project exists yet. A migrated install therefore shows only
    its named projects; a fresh one still starts with 'Main project'."""
    # Dot-led dirs are staging areas (e.g. an in-flight restore), never
    # productions.
    named = ([d for d in sorted(PROJECTS_DIR.iterdir())
              if d.is_dir() and not d.name.startswith(".")]
             if PROJECTS_DIR.exists() else [])
    out = []
    if (HOME / "data").exists() or ACTIVE_PROJECT == "" or not named:
        out.append({"slug": "", "name": _project_name(HOME, "Untitled Production")})
    out += [{"slug": d.name, "name": _project_name(d, d.name)} for d in named]
    for p in out:
        p["active"] = p["slug"] == ACTIVE_PROJECT
    return out


def _project_name(base: Path, fallback: str) -> str:
    import json as _json
    meta = base / "project.json"
    if meta.exists():
        try:
            return str(_json.loads(meta.read_text(encoding="utf-8")).get("name") or fallback)
        except Exception:
            pass
    return fallback


def save_active_project(slug: str) -> None:
    import json as _json
    HOME.mkdir(parents=True, exist_ok=True)
    ACTIVE_PROJECT_FILE.write_text(
        _json.dumps({"slug": slug}) + "\n", encoding="utf-8")


def _load_active_project() -> str:
    import json as _json
    try:
        slug = str(_json.loads(
            ACTIVE_PROJECT_FILE.read_text(encoding="utf-8")).get("slug", ""))
    except Exception:
        return ""
    return slug if _project_base(slug).exists() else ""


# Point the module at the last active project on import; '' (the legacy
# root layout) when none is recorded.
set_project(_load_active_project())


def ensure_dirs() -> None:
    for d in (DATA, REFERENCES, REF_ORIGINALS, REF_THUMBS, REF_QUARANTINE,
              SCREENPLAY_DIR, SPECS_DIR, BOARDS_DIR,
              PROJECT_STATE.parent, BIBLE.parent):
        d.mkdir(parents=True, exist_ok=True)
