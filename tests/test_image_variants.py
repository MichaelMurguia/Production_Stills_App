"""Display-tier image serving (app.imaging + candidate/reference resolvers).

Renders are native 4K PNGs kept as the archival truth; the app serves a
right-sized WebP derivative everywhere except where full resolution is actually
consumed (lightbox/crop/repair). These tests pin the tier contract: correct
max-edge per tier, WebP output, caching + mtime rebuild, no upscaling,
graceful fallback, that `size=full` is the untouched source, that the `thumb=1`
alias still works, and that deletion removes every derivative. Display-only —
the size gate still reads the record's real width/height, never a served file.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app import generate, imaging, paths, store  # noqa: E402

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


class VariantHelperTests(unittest.TestCase):
    """app.imaging.variant_path — the shared derivative builder."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-var-"))
        self.src = self.tmp / "src.png"
        Image.new("RGB", (2048, 1152), (30, 40, 50)).save(self.src, "PNG")

    def test_downscales_to_max_edge_as_webp(self):
        out = imaging.variant_path(self.src, self.tmp / "o.webp", 1600, 82)
        with Image.open(out) as im:
            self.assertEqual(im.format, "WEBP")
            self.assertLessEqual(max(im.size), 1600)
        self.assertLess(out.stat().st_size, self.src.stat().st_size)

    def test_cache_is_reused_until_source_is_newer(self):
        c = self.tmp / "c.webp"
        first = imaging.variant_path(self.src, c, 512, 80)
        mt = first.stat().st_mtime_ns
        imaging.variant_path(self.src, c, 512, 80)
        self.assertEqual(mt, c.stat().st_mtime_ns)  # not rebuilt
        # touch source forward → rebuild
        import os
        os.utime(self.src, (self.src.stat().st_atime, self.src.stat().st_mtime + 10))
        imaging.variant_path(self.src, c, 512, 80)
        self.assertNotEqual(mt, c.stat().st_mtime_ns)

    def test_never_upscales_small_source(self):
        small = self.tmp / "small.png"
        Image.new("RGB", (200, 120)).save(small, "PNG")
        out = imaging.variant_path(small, self.tmp / "s.webp", 512, 80)
        with Image.open(out) as im:
            self.assertEqual(im.size, (200, 120))
            self.assertEqual(im.format, "WEBP")

    def test_falls_back_to_source_on_unreadable(self):
        bad = self.tmp / "bad.png"
        bad.write_bytes(b"not an image")
        out = imaging.variant_path(bad, self.tmp / "b.webp", 512, 80)
        self.assertEqual(out, bad)  # degrade to source, never raise


class CandidateVariantTests(unittest.TestCase):
    SPEC = "SPEC001"
    CAND = "SPEC001_V001"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-cand-"))
        _redirect_home(self.tmp)
        self.board = paths.BOARDS_DIR / self.SPEC
        self.board.mkdir(parents=True, exist_ok=True)
        self.png = self.board / f"{self.CAND}.png"
        Image.new("RGB", (3840, 2160), (40, 30, 20)).save(self.png, "PNG")

    def tearDown(self):
        _restore_home()

    def test_full_returns_untouched_png(self):
        p = generate.candidate_variant_path(self.SPEC, self.CAND, "full")
        self.assertEqual(p, self.png)

    def test_each_tier_builds_a_bounded_webp(self):
        for size, (edge, _) in imaging.VARIANTS.items():
            p = generate.candidate_variant_path(self.SPEC, self.CAND, size)
            self.assertEqual(p.name, f"{self.CAND}.{size}.webp")
            with Image.open(p) as im:
                self.assertEqual(im.format, "WEBP")
                self.assertLessEqual(max(im.size), edge)

    def test_unknown_size_degrades_to_full(self):
        self.assertEqual(generate.candidate_variant_path(self.SPEC, self.CAND, "huge"),
                         self.png)

    def test_warm_prebuilds_every_tier(self):
        generate.warm_candidate_variants(self.SPEC, self.CAND)
        for size in imaging.VARIANTS:
            self.assertTrue((self.board / f"{self.CAND}.{size}.webp").exists())

    def test_delete_removes_png_and_all_variants(self):
        (self.board / f"{self.CAND}.json").write_text(
            '{"candidate_id": "%s", "panel_id": "P01", "status": "REJECTED", '
            '"status_reason": "t"}' % self.CAND, encoding="utf-8")
        generate.warm_candidate_variants(self.SPEC, self.CAND)
        (self.board / f"{self.CAND}.thumb.jpg").write_bytes(b"legacy")  # pre-WebP
        generate.delete_candidate(self.SPEC, self.CAND)
        self.assertFalse(self.png.exists())
        self.assertFalse((self.board / f"{self.CAND}.thumb.jpg").exists())
        for size in imaging.VARIANTS:
            self.assertFalse((self.board / f"{self.CAND}.{size}.webp").exists())


class ReferenceVariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-ref-"))
        _redirect_home(self.tmp)
        buf = self._png_bytes(1600, 900)
        self.ref = store.add_reference("shot.png", buf, "STYLE", [], [], "note")

    def tearDown(self):
        _restore_home()

    @staticmethod
    def _png_bytes(w, h):
        import io
        b = io.BytesIO()
        Image.new("RGB", (w, h), (10, 20, 30)).save(b, "PNG")
        return b.getvalue()

    def test_full_returns_the_original(self):
        p = store.reference_image_path(self.ref["id"], size="full")
        self.assertEqual(p, paths.REF_ORIGINALS / self.ref["file"])

    def test_thumb_size_and_alias_resolve_to_webp(self):
        rid = self.ref["id"]
        by_size = store.reference_image_path(rid, size="thumb")
        by_alias = store.reference_image_path(rid, thumb=True)
        self.assertEqual(by_size, by_alias)
        self.assertEqual(by_size.suffix, ".webp")
        with Image.open(by_size) as im:
            self.assertEqual(im.format, "WEBP")
            self.assertLessEqual(max(im.size), imaging.VARIANTS["thumb"][0])

    def test_intake_warms_variants(self):
        rid = self.ref["id"]
        for size in imaging.VARIANTS:
            self.assertTrue((paths.REF_THUMBS / f"{rid}.{size}.webp").exists())

    def test_delete_reference_removes_variants(self):
        rid = self.ref["id"]
        store.delete_reference(rid)
        self.assertEqual(list(paths.REF_THUMBS.glob(f"{rid}.*")), [])


if __name__ == "__main__":
    unittest.main()
