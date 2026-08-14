"""The panel brief is editable BETWEEN takes (user 2026-08-08).

"Establish … the arrangement of the three people within it" kept painting
three people, and the only fix lived behind a full unlock. The amend is
journaled, the lock re-stamps, and provenance survives because every take
already records the spec_hash it was generated against. An APPROVED take
freezes the brief it was approved against — the same promise unlock keeps,
scoped to the one panel.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import paths, store  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")

_SAVED = {}


def _redirect_home(tmp: Path) -> None:
    _SAVED.update(HOME=paths.HOME, PROJECTS_DIR=paths.PROJECTS_DIR,
                  ACTIVE=paths.ACTIVE_PROJECT_FILE, SETTINGS=paths.SETTINGS,
                  slug=paths.ACTIVE_PROJECT)
    paths.HOME = tmp
    paths.PROJECTS_DIR = tmp / "projects"
    paths.ACTIVE_PROJECT_FILE = tmp / "active_project.json"
    paths.SETTINGS = tmp / "settings.json"
    paths.set_project("")
    paths.ensure_dirs()


def _restore_home() -> None:
    paths.HOME = _SAVED["HOME"]
    paths.PROJECTS_DIR = _SAVED["PROJECTS_DIR"]
    paths.ACTIVE_PROJECT_FILE = _SAVED["ACTIVE"]
    paths.SETTINGS = _SAVED["SETTINGS"]
    paths.set_project(_SAVED["slug"])


SPEC = {
    "specification_id": "AMEND_V001",
    "status": "DRAFT",
    "panels": [
        {"id": "P01", "title": "CLUTTERED SHOP INTERIOR",
         "purpose": "the arrangement of the three people within it"},
        {"id": "P02", "title": "", "purpose": "untouched neighbour"},
    ],
}


class AmendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-amend-"))
        _redirect_home(self.tmp)
        store.create_spec_from_dict(json.loads(json.dumps(SPEC)))

    def tearDown(self):
        _restore_home()

    def test_amend_updates_the_panel_and_only_the_panel(self):
        out = store.amend_panel_purpose("AMEND_V001", "P01", "  empty shop, no people  ")
        self.assertEqual(out["purpose"], "empty shop, no people")
        spec = store.get_spec("AMEND_V001")
        self.assertEqual(spec["panels"][0]["purpose"], "empty shop, no people")
        self.assertEqual(spec["panels"][1]["purpose"], "untouched neighbour")

    def test_post_lock_amend_restamps_the_hash_and_journals(self):
        store.approve_spec("AMEND_V001", lambda s: [])
        before = store.spec_lock_hash("AMEND_V001")
        store.amend_panel_purpose("AMEND_V001", "P01", "empty shop, no people")
        after = store.spec_lock_hash("AMEND_V001")
        self.assertNotEqual(before, after, "the lock must re-stamp to the amended spec")
        self.assertTrue(store.spec_locked("AMEND_V001"), "the amend never unlocks")
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("P01 purpose amended post-lock", log)
        self.assertIn("keep the hash they were generated against", log)

    def test_an_approved_take_freezes_the_brief(self):
        d = paths.BOARDS_DIR / "AMEND_V001"
        d.mkdir(parents=True, exist_ok=True)
        (d / "CAND-0001.json").write_text(json.dumps(
            {"candidate_id": "CAND-0001", "panel_id": "P01", "status": "APPROVED"}),
            encoding="utf-8")
        with self.assertRaises(PermissionError):
            store.amend_panel_purpose("AMEND_V001", "P01", "different brief")
        # the neighbour panel's brief is NOT frozen by P01's approval
        store.amend_panel_purpose("AMEND_V001", "P02", "still amendable")

    def test_unknown_panel_is_a_key_error(self):
        with self.assertRaises(KeyError):
            store.amend_panel_purpose("AMEND_V001", "P99", "x")

    def test_the_only_steering_text_cannot_be_emptied(self):
        """Validation's rule held through the amend: a panel needs a purpose
        or a required object. P01 has neither fallback, so empty is refused;
        with a required object the purpose may go empty."""
        with self.assertRaises(ValueError):
            store.amend_panel_purpose("AMEND_V001", "P01", "   ")
        spec = store.get_spec("AMEND_V001")
        spec["panels"][0]["required_objects"] = ["jukebox"]
        store.save_spec("AMEND_V001", spec)
        out = store.amend_panel_purpose("AMEND_V001", "P01", "")
        self.assertEqual(out["purpose"], "")


class TheWorkbenchOffersTheEdit(unittest.TestCase):
    def test_the_verb_sits_with_the_brief(self):
        i = JS.index('data-f="brief-edit"')
        block = JS[i - 800:i + 900]
        self.assertIn('data-f="brief-text"', block)
        self.assertIn("Edit brief", block)

    def test_the_frozen_gate_reads_as_state_before_it_is_hit(self):
        self.assertIn('const frozen = panelCands.some(c => c.status === "APPROVED")', JS,
                      "the gate is one computed fact for the whole card")
        i = JS.index('data-f="brief-edit"')
        block = JS[i - 200:i + 900]
        self.assertIn("${frozen ? \"disabled\" : \"\"}", block)
        self.assertIn("Reject it first", block)

    def test_save_posts_the_journaled_amend_and_repaints(self):
        i = JS.index("[data-f=brief-save]")
        block = JS[i:i + 700]
        self.assertIn("/purpose`", block)
        self.assertIn("renderBoardPanels(specId)", block)

    def test_the_editor_save_is_never_amber(self):
        i = JS.index('data-f="brief-save"')
        self.assertIn('class="ghost"', JS[i - 60:i + 20],
                      "amber stays on the card's verdict")
        self.assertIn("UNCANONIZED — 2026-08-08 — editable panel brief", CSS)


if __name__ == "__main__":
    unittest.main()
