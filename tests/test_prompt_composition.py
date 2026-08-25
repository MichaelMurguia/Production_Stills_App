"""R1.5 — what a compiled prompt is actually made of.

Evidence for the selector, and a standing answer to "why is my style not
reaching the image". Before this, the only way to know was to export a
prompt and count by hand — which is how the figure that drove two days of
work (a style block at ~4% of 19,094 characters) was arrived at, from one
panel of one production.

The first automated measurement immediately corrected it and found
something larger: CHARACTER PRESENTATION at 31.5% of a panel whose
required content names no characters, describing a recon pilot and a
colonel who are not in the frame. Nearly six times the cinematography
block that had all the attention.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


class ItBreaksAPromptIntoItsBlocks(unittest.TestCase):
    def comp(self, text):
        from app.generate import prompt_composition
        return prompt_composition(text)

    def test_blocks_are_found_by_their_heads(self):
        NL = chr(10)
        p = NL.join(["THE SCENE", "a b c", "", "REQUIRED CONTENT", "- x", "- y"])
        heads = [b["head"] for b in self.comp(p)["blocks"]]
        self.assertEqual(heads, ["THE SCENE", "REQUIRED CONTENT"])

    def test_shares_sum_to_the_whole(self):
        NL = chr(10)
        p = NL.join(["THE SCENE", "a" * 100, "", "REQUIRED CONTENT", "b" * 300])
        r = self.comp(p)
        self.assertAlmostEqual(sum(b["share"] for b in r["blocks"]), 1.0, places=2)

    def test_text_before_the_first_head_is_owned_not_absorbed(self):
        """A breakdown that quietly attributes bytes to the wrong block is
        worse than one that admits a gap."""
        NL = chr(10)
        p = NL.join(["ANCESTOR PRODUCTION RENDER", "hash 123", "", "THE SCENE", "x"])
        heads = [b["head"] for b in self.comp(p)["blocks"]]
        self.assertEqual(heads[0], "(header)")

    def test_an_unrecognised_prompt_reports_no_blocks_rather_than_guessing(self):
        r = self.comp("just some free text with no headings at all")
        self.assertEqual(r["blocks"], [])
        self.assertGreater(r["total"], 0)

    def test_empty_is_safe(self):
        self.assertEqual(self.comp("")["total"], 0)
        self.assertEqual(self.comp(None)["blocks"], [])

    def test_the_blocks_it_knows_cover_the_compiler(self):
        """A head the compiler writes and this does not know becomes an
        invisible share — the exact blindness this exists to remove."""
        from app import generate
        for head in ("THE SCENE", "REQUIRED CONTENT", "VISUAL STYLE",
                     "CINEMATOGRAPHY GRAMMAR", "CHARACTER PRESENTATION",
                     "LIGHTING LANGUAGE", "FORBIDDEN CONTENT",
                     "APPROVED REFERENCE ROLES"):
            self.assertIn(head, generate._BLOCK_HEADS, head)


class ThePanelShowsIt(unittest.TestCase):
    def test_the_endpoint_carries_it(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        self.assertIn('"composition": generate.prompt_composition(', main)

    def test_the_preview_renders_it_biggest_first(self):
        i = JS.index('const comp = $("[data-f=composition]", report);')
        seg = JS[i:i + 1400]
        self.assertIn("sort((a, b) => b.chars - a.chars)", seg)
        self.assertIn("MADE OF", seg)

    def test_it_says_why_a_large_block_matters(self):
        """A number without a consequence is trivia."""
        i = JS.index('const comp = $("[data-f=composition]", report);')
        seg = " ".join(JS[i:i + 1600].split())
        self.assertIn("competes with the ones that do", seg)
        self.assertIn("is not neutral", seg)

    def test_the_bar_is_a_measurement_not_a_verdict(self):
        """No block is good or bad on its own, so nothing here is painted
        with --bad or the accent."""
        i = CSS.index(".prompt-comp")
        seg = CSS[i:i + 700]
        self.assertNotIn("--bad", seg)
        self.assertNotIn("--accent", seg)


if __name__ == "__main__":
    unittest.main()
