"""Takes strip / panel rail thumbnails: a native-4K take is 20–40 MB, so the
panels page must not load the full PNG for every take in every strip (user
2026-08-09). candidate_thumb_path serves a small cached JPEG, display-only —
it never feeds a render or a size gate — while the staged shot and lightbox
keep serving the full image."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app import generate, paths  # noqa: E402

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


class CandidateThumbTests(unittest.TestCase):
    SPEC = "SPEC001"
    CAND = "SPEC001_V001"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-thumb-"))
        _redirect_home(self.tmp)
        self.board = paths.BOARDS_DIR / self.SPEC
        self.board.mkdir(parents=True, exist_ok=True)
        self.png = self.board / f"{self.CAND}.png"
        Image.new("RGB", (2048, 1152), (40, 30, 20)).save(self.png, "PNG")

    def tearDown(self):
        _restore_home()

    def test_thumb_is_built_downscaled_and_smaller_than_full(self):
        thumb = generate.candidate_thumb_path(self.SPEC, self.CAND)
        self.assertIsNotNone(thumb)
        self.assertEqual(thumb.name, f"{self.CAND}.thumb.jpg")
        self.assertTrue(thumb.exists())
        with Image.open(thumb) as im:
            self.assertLessEqual(max(im.size), generate.CANDIDATE_THUMB_SIZE)
        self.assertLess(thumb.stat().st_size, self.png.stat().st_size)

    def test_thumb_is_cached_not_rebuilt(self):
        first = generate.candidate_thumb_path(self.SPEC, self.CAND)
        mtime = first.stat().st_mtime_ns
        again = generate.candidate_thumb_path(self.SPEC, self.CAND)
        self.assertEqual(first, again)
        self.assertEqual(mtime, again.stat().st_mtime_ns)  # not regenerated

    def test_unknown_candidate_returns_none(self):
        self.assertIsNone(generate.candidate_thumb_path(self.SPEC, "NOPE_V999"))

    def test_full_image_path_is_untouched(self):
        # The staged shot and the lightbox must still get the real render.
        full = generate.candidate_image_path(self.SPEC, self.CAND)
        self.assertEqual(full, self.png)

    def test_delete_removes_the_cached_thumb(self):
        (self.board / f"{self.CAND}.json").write_text(
            '{"candidate_id": "%s", "panel_id": "P01", "status": "REJECTED", '
            '"status_reason": "test"}' % self.CAND, encoding="utf-8")
        thumb = generate.candidate_thumb_path(self.SPEC, self.CAND)
        self.assertTrue(thumb.exists())
        generate.delete_candidate(self.SPEC, self.CAND)
        self.assertFalse(thumb.exists())
        self.assertFalse(self.png.exists())


if __name__ == "__main__":
    unittest.main()
