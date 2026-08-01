"""Engine-facing unit rules: size legality (×16, ≤3840, no upscaling), the
ChatGPT-pipeline preset clamp, and deterministic keyword derivation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import insights  # noqa: E402
from app.generate import _chat_tool_size, legal_openai_size, openai_size  # noqa: E402


class SizeRuleTests(unittest.TestCase):
    def test_openai_size_edges_are_legal(self):
        for size in ("1K", "2K", "4K"):
            for ar in ("16:9", "21:9", "9:16", "1:1", "2.55:1"):
                w, h = map(int, openai_size(size, ar).split("x"))
                self.assertEqual(w % 16, 0)
                self.assertEqual(h % 16, 0)
                self.assertLessEqual(max(w, h), 3840)

    def test_legal_openai_size_never_upscales(self):
        self.assertEqual(legal_openai_size(1024, 1024), "1024x1024")
        w, h = map(int, legal_openai_size(8000, 4000).split("x"))
        self.assertLessEqual(max(w, h), 3840)
        self.assertLessEqual(w * h, 8_294_400 * 1.02)  # rounding headroom

    def test_chat_tool_size_is_preset_only(self):
        self.assertEqual(_chat_tool_size("16:9"), "1536x1024")
        self.assertEqual(_chat_tool_size("9:16"), "1024x1536")
        self.assertEqual(_chat_tool_size("1:1"), "1024x1024")
        self.assertEqual(_chat_tool_size("junk"), "auto")


class DeriveKeywordTests(unittest.TestCase):
    TEXT = ("EXT. RESISTANCE OUTPOST - DAY\n"
            "The Resistance warp ship idles in the hangar. Resistance "
            "fighters load weapons beside the warp ship engines.\n" * 3
            + "INT. BAKERY - DAY\nBread. Nothing else.\n")

    def setUp(self):
        self._saved = insights.screenplay_text
        insights.screenplay_text = lambda: self.TEXT

    def tearDown(self):
        insights.screenplay_text = self._saved

    def test_name_tokens_lead_and_cooccurrence_follows(self):
        r = insights.derive_keywords("Resistance")
        self.assertTrue(r["available"])
        self.assertGreater(r["hits"], 0)
        self.assertEqual(r["keywords"][0], "resistance")
        self.assertIn("warp", r["keywords"])
        self.assertNotIn("bread", r["keywords"], "far-away words must not attach")
        self.assertLessEqual(len(r["keywords"]), 20)

    def test_unmentioned_name_reports_zero_hits(self):
        r = insights.derive_keywords("Skinners")
        self.assertEqual(r["hits"], 0)
        self.assertEqual(r["keywords"], ["skinners"])


if __name__ == "__main__":
    unittest.main()
