"""Two panels rendered simultaneously must be two separate prompts.

User report 2026-08-13: a second panel rendered at the same time appeared
to paint the first panel's scene. This suite pins the isolation contract:
concurrent generate_panel calls compile independent prompts from their
own panel's brief, allocate distinct candidate ids, and write distinct
records bound to the right panel.
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, paths, store  # noqa: E402

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
    "specification_id": "CONC_V001",
    "status": "DRAFT",
    "mode": "CANON_EXTRACTION",
    "subject": "CANYON",
    "setting": {"int_ext": "EXT", "location": "CANYON"},
    "panels": [
        {"id": "P01", "title": "LEAP", "purpose": "the GT40 leaps the broken rim",
         "required_objects": ["gt40"], "composition_role": "hero"},
        {"id": "P02", "title": "COCKPIT", "purpose": "inside the cockpit, hands on the wheel",
         "required_objects": ["cockpit"], "composition_role": "support"},
    ],
    "layout": {"panels": [{"id": "P01", "allocation_percent": 50},
                          {"id": "P02", "allocation_percent": 50}]},
    "evidence_ledger": [
        {"panel_id": "P01", "object": "gt40", "status": "PASS"},
        {"panel_id": "P02", "object": "cockpit", "status": "PASS"}],
}


class ConcurrentGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-conc-"))
        _redirect_home(self.tmp)
        import os
        os.environ["SCREENBOARD_DEBUG_TOOLS"] = "1"
        generate.save_settings({"debug_mock": True})
        generate.save_style_bible(
            "# T\n\n## Rendering Language\n### Required\n- gouache\n")
        store.create_spec_from_dict(json.loads(json.dumps(SPEC)))
        store.approve_spec("CONC_V001", lambda s: [])

    def tearDown(self):
        import os
        os.environ.pop("SCREENBOARD_DEBUG_TOOLS", None)
        _restore_home()

    def test_simultaneous_panels_get_their_own_prompts(self):
        """Ten concurrent renders across two panels — every record binds
        to its own panel and carries a prompt compiled from that panel's
        brief, with no shared or crossed state."""
        results: list[dict] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def run(panel_id):
            try:
                r = generate.generate_panel("CONC_V001", panel_id, [],
                                            "1K", "16:9", "mock")
                with lock:
                    results.append(r)
            except Exception as e:  # pragma: no cover - failure detail
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=run,
                                    args=("P01" if i % 2 == 0 else "P02",))
                   for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 10)
        ids = [r["candidate_id"] for r in results]
        self.assertEqual(len(set(ids)), 10, "candidate ids must never collide")
        for r in results:
            if r["panel_id"] == "P01":
                self.assertIn("the GT40 leaps the broken rim", r["prompt"])
                self.assertNotIn("inside the cockpit", r["prompt"])
                self.assertIn("PANEL: P01", r["prompt"])
            else:
                self.assertIn("inside the cockpit, hands on the wheel",
                              r["prompt"])
                self.assertNotIn("GT40 leaps", r["prompt"])
                self.assertIn("PANEL: P02", r["prompt"])
        # The records on disk agree with what was returned — nothing
        # clobbered a neighbour's file.
        for r in results:
            on_disk = generate.get_candidate("CONC_V001", r["candidate_id"])
            self.assertEqual(on_disk["panel_id"], r["panel_id"])
            self.assertEqual(on_disk["prompt"], r["prompt"])
            self.assertIsNotNone(
                generate.candidate_image_path("CONC_V001", r["candidate_id"]))


if __name__ == "__main__":
    unittest.main()
