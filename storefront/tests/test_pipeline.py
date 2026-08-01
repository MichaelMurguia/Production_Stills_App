"""The /pipeline page: static, always 200, and its provenance claims stay
tied to the real Beltminers record (STORE_DESIGN_SYSTEM §6 — true numbers).

Run from storefront/:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-test-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


class PipelinePageTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_serves_and_carries_the_record(self):
        r = self.client.get("/pipeline")
        self.assertEqual(r.status_code, 200)
        # The five stages and the case file
        for marker in ("Screenplay", "Production design", "Breakdown",
                       "Panels", "Board", "CASE FILE"):
            self.assertIn(marker, r.text)
        # Provenance stays true to the production record
        for fact in ("CAND-0042", "BOARD-0001", "REF-0042",
                     "7 PANELS APPROVED", "1 BOARD ASSEMBLED"):
            self.assertIn(fact, r.text)
        # The footnotes are the argument of the page — never drop them
        for note in ("THE GATE", "WHAT PROPOSED MEANS", "WHY JURISDICTIONS",
                     "WHAT HOLD MEANS", "NATIVE RESOLUTION", "THE LOOP CLOSES"):
            self.assertIn(note, r.text)

    def test_downscaled_web_images_exist_and_are_referenced(self):
        static = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "app", "static", "img", "web")
        page = self.client.get("/pipeline").text
        for name in ("board-0001-w1400.jpg", "cand-0042-w1400.jpg",
                     "cand-0030-t320.jpg", "cand-0042-t320.jpg"):
            self.assertIn(f"/static/img/web/{name}", page)
            self.assertTrue(os.path.exists(os.path.join(static, name)),
                            f"missing web copy: {name}")

    def test_header_links_the_pipeline_page(self):
        home = self.client.get("/").text
        self.assertIn('href="/pipeline"', home)
