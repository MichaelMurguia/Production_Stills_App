from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
REFERENCES = DATA / "references"
REF_ORIGINALS = REFERENCES / "originals"
REF_THUMBS = REFERENCES / "thumbs"
REF_QUARANTINE = REFERENCES / "quarantine"
REF_INDEX = REFERENCES / "references.json"
SCREENPLAY_DIR = DATA / "screenplay"
SPECS_DIR = DATA / "specs"
SPEC_LOCKS = SPECS_DIR / "locks.json"
APP_STATE = DATA / "app_state.json"
SUBJECTS = DATA / "subjects.json"
WIZARD_ANALYSIS = DATA / "wizard_analysis.json"
BOARDS_DIR = DATA / "boards"

BIBLE = ROOT / "context" / "01_ART_DIRECTION_BIBLE.md"

PROJECT_STATE = ROOT / "project_state" / "project_state.json"
APPROVAL_LOG = ROOT / "project_state" / "approval_log.md"
REJECTION_HISTORY = ROOT / "project_state" / "rejection_history.md"

STATIC = Path(__file__).resolve().parent / "static"

# The governance scripts (validate_spec, audit_spec, common) are the canon
# rule engine; the app imports them rather than reimplementing the rules.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def ensure_dirs() -> None:
    for d in (DATA, REFERENCES, REF_ORIGINALS, REF_THUMBS, REF_QUARANTINE,
              SCREENPLAY_DIR, SPECS_DIR, BOARDS_DIR):
        d.mkdir(parents=True, exist_ok=True)
