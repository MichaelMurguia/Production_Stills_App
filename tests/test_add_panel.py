"""Add a panel from the panels workbench (user 2026-08-09).

Adding a panel mid-generation used to mean unlocking the sheet — blocked once
any take is approved. `store.add_panel` appends a panel to the locked sheet
instead: append-only, so nothing upstream of an existing approval changes; the
new panel lands as a work order at 0% allocation, the lock re-stamps, and the
add is journaled — the same controlled-edit contract as `amend_panel_purpose`.
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
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")

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
    "specification_id": "ADD_V001",
    "status": "DRAFT",
    "panels": [
        {"id": "P01", "title": "HERO", "purpose": "the shop, wide",
         "required_objects": ["jukebox"]},
        {"id": "P02", "title": "", "purpose": "a neighbour"},
    ],
    "layout": {"panels": [{"id": "P01", "allocation_percent": 60},
                          {"id": "P02", "allocation_percent": 40}]},
    "evidence_ledger": [{"panel_id": "P01", "object": "jukebox", "status": "PASS"}],
}


class AddPanelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-addpanel-"))
        _redirect_home(self.tmp)
        store.create_spec_from_dict(json.loads(json.dumps(SPEC)))

    def tearDown(self):
        _restore_home()

    def test_append_gets_next_id_layout_entry_and_work_order_shape(self):
        p = store.add_panel("ADD_V001", "  The Workshop  ", "  a cluttered bench  ")
        self.assertEqual(p["id"], "P03")
        self.assertEqual(p["title"], "The Workshop")
        self.assertEqual(p["purpose"], "a cluttered bench")
        self.assertEqual(p["composition_role"], "support")
        spec = store.get_spec("ADD_V001")
        self.assertEqual([x["id"] for x in spec["panels"]], ["P01", "P02", "P03"])
        layout = {x["id"]: x["allocation_percent"] for x in spec["layout"]["panels"]}
        self.assertEqual(layout["P03"], 0, "a new panel lands at 0% until balanced")
        self.assertEqual(layout["P01"], 60, "existing allocations are untouched")

    def test_empty_brief_is_refused(self):
        with self.assertRaises(ValueError):
            store.add_panel("ADD_V001", "titled but blank", "   ")

    def test_post_lock_add_restamps_the_hash_and_journals(self):
        store.approve_spec("ADD_V001", lambda s: [])
        before = store.spec_lock_hash("ADD_V001")
        store.add_panel("ADD_V001", "New", "a fresh work order")
        after = store.spec_lock_hash("ADD_V001")
        self.assertNotEqual(before, after, "the lock must re-stamp to the amended spec")
        self.assertTrue(store.spec_locked("ADD_V001"), "adding a panel never unlocks")
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("P03 added post-lock", log)
        self.assertIn("keep the hash they were generated against", log)

    def test_append_is_allowed_even_when_a_panel_has_approved_canon(self):
        # The key difference from amend: adding a panel touches nothing that was
        # approved, so an APPROVED take elsewhere does NOT block it.
        store.approve_spec("ADD_V001", lambda s: [])
        d = paths.BOARDS_DIR / "ADD_V001"
        d.mkdir(parents=True, exist_ok=True)
        (d / "CAND-0001.json").write_text(json.dumps(
            {"candidate_id": "CAND-0001", "panel_id": "P01", "status": "APPROVED"}),
            encoding="utf-8")
        p = store.add_panel("ADD_V001", "still fine", "append-only, so allowed")
        self.assertEqual(p["id"], "P03")

    def test_unknown_spec_is_a_key_error(self):
        with self.assertRaises(KeyError):
            store.add_panel("NOPE_V999", "x", "y")


class TheWorkbenchOffersTheAdd(unittest.TestCase):
    def test_the_button_lives_in_the_panels_header_as_ghost_reuse(self):
        i = HTML.index('id="board-add-panel"')
        block = HTML[i - 60:i + 300]
        self.assertIn("ghost", block, "reuses the sheet editor's + Add panel vocabulary")
        self.assertIn("+ Add panel", block)

    def test_render_shows_and_wires_the_button(self):
        i = JS.index('$("#board-add-panel")')
        block = JS[i:i + 200]
        self.assertIn("addPanelDialog(specId)", block)
        self.assertIn("hidden = false", block)

    def test_dialog_posts_to_panels_and_repaints(self):
        i = JS.index("async function addPanelDialog")
        block = JS[i:i + 1200]
        self.assertIn("/panels`", block)
        self.assertIn('method: "POST"', block)
        self.assertIn("renderBoardPanels(specId)", block)


if __name__ == "__main__":
    unittest.main()
