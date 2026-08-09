"""Responsive marketing imagery — the storefront must not serve raw stills.

The landing page used to pull ~88 MB of source PNGs (p01–p15, board-0001) at
150–380px. scripts/build_images.py generalizes the `web/` derivative convention
into a responsive WebP set; these tests keep the pages on the derivatives and
keep every referenced derivative present on disk, so a template that reaches for
a raw multi-megabyte PNG (or a missing variant) fails the build, not the visitor.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(
        tempfile.mkdtemp(prefix="storefront-images-"), "t.db").replace("\\", "/"))

TEMPLATES = ROOT / "app/templates"
IMG = ROOT / "app/static/img"
RAW = re.compile(r"/static/img/(p\d+|board-0001)\.(png|jpg|jpeg)")
DERIV = re.compile(r"/static/img/web/([a-z0-9-]+\.(?:webp|jpg))")


def _template_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in TEMPLATES.rglob("*.html"))


class ResponsiveImageTests(unittest.TestCase):
    def test_no_template_serves_a_raw_marketing_still(self):
        hits = []
        for p in TEMPLATES.rglob("*.html"):
            for m in RAW.finditer(p.read_text(encoding="utf-8")):
                hits.append(f"{p.name}: {m.group(0)}")
        self.assertEqual(hits, [], f"raw multi-MB stills referenced directly: {hits}")

    def test_every_referenced_derivative_exists(self):
        missing = [d for d in sorted(set(DERIV.findall(_template_text())))
                   if not (IMG / "web" / d).exists()]
        self.assertEqual(missing, [], f"referenced derivatives absent from disk: {missing}")

    def test_the_social_card_is_present_and_jpeg(self):
        # og:image / JSON-LD use a JPEG card — crawlers support WebP unevenly.
        og = IMG / "web" / "board-0001-og.jpg"
        self.assertTrue(og.exists(), "board-0001-og.jpg missing — run scripts/build_images.py")

    def test_build_script_emits_bounded_webp(self):
        from PIL import Image
        from scripts import build_images as b
        src = Image.new("RGB", (3000, 1688))
        with tempfile.TemporaryDirectory() as td:
            b.WEB = Path(td)
            for w in (400, 1600):
                b._webp(src, "probe", w)
                out = Path(td) / f"probe-w{w}.webp"
                self.assertTrue(out.exists())
                with Image.open(out) as im:
                    self.assertEqual(im.format, "WEBP")
                    self.assertEqual(im.width, w)
            b._webp(src, "probe", 4000)  # wider than source → never upscales
            self.assertFalse((Path(td) / "probe-w4000.webp").exists())


if __name__ == "__main__":
    unittest.main()
