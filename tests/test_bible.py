"""Bible section model: every non-system ## section is a design language,
environments ride the level-3 container, and render_context injects in the
documented order (global → languages → environments → lessons).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import bible, paths  # noqa: E402

TEXT = """# Test — Bible

## Status
authoritative

## Overall Visual Identity
- weathered

## Rendering Language
### Required
- gouache

## Design Languages

## Resistance
Keywords: resistance, outpost
**Design language:** scrap-built
- riveted plate

## GRM Order
Keywords: grm
- polished chrome

## Environments

### FOREST
- green-black shade, wet light

### DESERT
- bleached ochre

## Core Material Language
### Resistance
- mild steel

## Lighting Language
contrast rules
Approved atmosphere studies include:
- Dawn haze
- Storm light

## Current Locked Scene-Specific Lessons

### GT40
- exact rear intakes

## Drift Prevention Rule
stop and check
"""


class BibleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-bible-"))
        self._saved = paths.BIBLE
        paths.BIBLE = self.tmp / "bible.md"
        paths.BIBLE.write_text(TEXT, encoding="utf-8")

    def tearDown(self):
        paths.BIBLE = self._saved

    def test_languages_exclude_system_and_environments(self):
        self.assertEqual(bible.design_language_names(),
                         ["Resistance", "GRM Order"])

    def test_catalog_lists_environments_and_lessons_and_atmospheres(self):
        cat = bible.sections_catalog()
        self.assertEqual(cat["environments"], ["FOREST", "DESERT"])
        self.assertEqual(cat["scene_lessons"], ["GT40"])
        self.assertEqual(cat["atmospheres"], ["Dawn haze", "Storm light"])

    def test_render_context_injection_order(self):
        ctx = bible.render_context("", ["Resistance"], ["GT40"],
                                   environments=["forest"])
        i_lang = ctx.index("RESISTANCE — DESIGN LANGUAGE")
        i_env = ctx.upper().index("FOREST — ENVIRONMENT")
        i_lesson = ctx.index("LOCKED LESSONS — GT40")
        self.assertTrue(i_lang < i_env < i_lesson,
                        "order must be languages → environment → lessons")
        self.assertIn("mild steel", ctx, "materials attach to their language")
        self.assertNotIn("Keywords:", ctx, "selection metadata never reaches a prompt")

    def test_environments_never_infer(self):
        ctx = bible.render_context("deep green forest shade", None, None)
        self.assertNotIn("ENVIRONMENT", ctx.upper().replace("ENVIRONMENTS", ""))

    def test_keyword_inference_falls_back_to_first_language(self):
        sel = bible.infer_selection("nothing matches this text")
        self.assertEqual(sel["design_languages"], ["Resistance"])
        sel2 = bible.infer_selection("a grm patrol")
        self.assertEqual(sel2["design_languages"], ["GRM Order"])


if __name__ == "__main__":
    unittest.main()
