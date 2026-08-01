"""Multi-project home: switching repoints every mutable path, the legacy
root layout is always project '', and the active pointer persists.

Run at repo root:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

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


def _restore_home() -> None:
    paths.HOME = _SAVED["HOME"]
    paths.PROJECTS_DIR = _SAVED["PROJECTS_DIR"]
    paths.ACTIVE_PROJECT_FILE = _SAVED["ACTIVE"]
    paths.SETTINGS = _SAVED["SETTINGS"]
    paths.set_project(_SAVED["slug"])


class ProjectPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-projects-"))
        _redirect_home(self.tmp)

    def tearDown(self):
        _restore_home()

    def test_root_project_is_home_layout(self):
        self.assertEqual(paths.DATA, self.tmp / "data")
        self.assertEqual(paths.BIBLE.parent, self.tmp / "context")
        self.assertEqual(paths.APPROVAL_LOG.parent, self.tmp / "project_state")

    def test_switch_repoints_every_mutable_path(self):
        (self.tmp / "projects" / "film-two").mkdir(parents=True)
        paths.set_project("film-two")
        base = self.tmp / "projects" / "film-two"
        for p in (paths.DATA, paths.SPECS_DIR, paths.BOARDS_DIR, paths.BIBLE,
                  paths.APPROVAL_LOG, paths.WIZARD_ANALYSIS, paths.SUBJECTS):
            self.assertTrue(str(p).startswith(str(base)),
                            f"{p} did not move into the project")
        # install-level paths must NOT move with the project
        self.assertEqual(paths.SETTINGS, self.tmp / "settings.json")

    def test_list_projects_marks_active_and_hides_empty_root(self):
        (self.tmp / "projects" / "b-film").mkdir(parents=True)
        listed = paths.list_projects()
        self.assertEqual(listed[0]["slug"], "",
                         "root stays listed while it is the active project")
        paths.set_project("b-film")
        listed = paths.list_projects()
        self.assertNotIn("", [p["slug"] for p in listed],
                         "an empty, inactive root disappears from a migrated install")
        active = [p["slug"] for p in listed if p["active"]]
        self.assertEqual(active, ["b-film"])
        # root with content stays listed even when inactive
        (self.tmp / "data").mkdir()
        self.assertIn("", [p["slug"] for p in paths.list_projects()])

    def test_active_pointer_persists_and_survives_missing_dir(self):
        (self.tmp / "projects" / "keeper").mkdir(parents=True)
        paths.save_active_project("keeper")
        self.assertEqual(paths._load_active_project(), "keeper")
        paths.save_active_project("gone-project")  # dir never created
        self.assertEqual(paths._load_active_project(), "",
                         "a dangling pointer must fall back to the root project")

    def test_ensure_dirs_materializes_a_fresh_home(self):
        paths.ensure_dirs()
        for d in (paths.DATA, paths.SCREENPLAY_DIR, paths.SPECS_DIR,
                  paths.BOARDS_DIR, paths.PROJECT_STATE.parent, paths.BIBLE.parent):
            self.assertTrue(d.is_dir())


if __name__ == "__main__":
    unittest.main()
