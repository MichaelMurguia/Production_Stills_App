"""C3 — a style's own hedges, reported to the author who wrote them.

A hedge softens an instruction so that doing LESS still satisfies it. An
image model settles on the safest reading that satisfies everything, so
where a hedge and the instruction it modifies pull in opposite directions,
the hedge tends to win.

Measured 2026-08-25: Chromatic/Operatic carried four restraint cues against
one drama cue and rendered restrained across a dozen takes. Deep-Space
carries none and is the only style that ever landed reliably. Changing one
word did what four code changes could not.

The lint reports; it never edits and never refuses. Naturalistic wants
restraint and should keep it.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TheLintFindsWhatItShould(unittest.TestCase):
    def hedges(self, name: str):
        from app import style_docs
        st = next(s for s in style_docs.styles("cinematography")
                  if s["name"].startswith(name))
        return st["hedges"]

    def test_every_style_carries_the_field(self):
        from app import style_docs
        for lib in ("cinematography", "texture", "rendering"):
            for st in style_docs.styles(lib):
                self.assertIn("hedges", st, f"{lib}/{st['name']}")

    def test_the_style_that_always_worked_is_clean(self):
        """Deep-Space is the control. If a change to this lint ever flags
        it, the lint has drifted — that style has landed every time."""
        self.assertEqual(self.hedges("Deep-Space"), [])

    def test_an_opt_out_is_caught(self):
        """The strongest kind: 'when appropriate' lets the model decline
        and still comply."""
        h = self.hedges("Immersive")
        self.assertTrue(any("when appropriate" in x["words"] for x in h))

    def test_a_softener_is_caught(self):
        h = self.hedges("Naturalistic")
        self.assertTrue(any("restrained" in x["words"] for x in h))

    def test_it_reports_the_line_not_just_a_count(self):
        """The author needs to see WHICH instruction was softened. A hedge
        on a defining mechanic is a different fact from one elsewhere."""
        h = self.hedges("Naturalistic")
        self.assertTrue(h)
        self.assertIn("line", h[0])
        self.assertIn("words", h[0])


class TheLintDoesNotCryWolf(unittest.TestCase):
    """A lint that fires on correct writing gets switched off, and then it
    protects nothing. Three near-misses are excluded deliberately."""

    def hedges_of(self, prompt: str):
        from app import style_docs
        return style_docs.hedges(prompt)

    def test_a_technique_name_is_not_a_hedge(self):
        """'selective focus' names a technique. Only the ADVERB softens."""
        self.assertEqual(self.hedges_of("Use selective focus and negative space."), [])
        self.assertTrue(self.hedges_of("Use saturation selectively."))

    def test_a_lens_specification_is_not_a_hedge(self):
        """'moderately wide' is a real spec. Flagging it would have marked
        the one style that has always worked."""
        self.assertEqual(
            self.hedges_of("Favor a wide or moderately wide cinematic perspective."), [])

    def test_the_avoid_block_is_inverted_and_skipped(self):
        """'avoid uncontrolled background elements' asks for MORE control."""
        p = ("Use precise placement.\n\nAvoid:\nuncontrolled background elements\n"
             "restrained staging\n")
        found = [x["line"] for x in self.hedges_of(p)]
        self.assertNotIn("uncontrolled background elements", found)
        self.assertNotIn("restrained staging", found)

    def test_prioritize_reopens_scanning(self):
        """The blocks alternate; an Avoid must not swallow the rest."""
        p = ("Avoid:\nflat light\n\nPrioritize:\nrestrained exposure\n")
        self.assertTrue(any("restrained" in x["words"] for x in self.hedges_of(p)))


class TheRewritesLanded(unittest.TestCase):
    """C7.1 and C7.2, applied to the document."""

    DOC = (ROOT / "docs/CINEMATOGRAPHY_STYLES.md").read_text(encoding="utf-8")

    def test_chromatic_no_longer_asks_for_restraint(self):
        self.assertNotIn("Use saturation selectively", self.DOC)
        self.assertIn("Push saturation hard where colour carries meaning", self.DOC)
        self.assertNotIn("controlled saturation", self.DOC)
        self.assertIn("decisive saturation", self.DOC)

    def test_chromatic_keeps_the_discipline_that_works(self):
        """A controlled SECONDARY colour is palette discipline, and the
        value-structure line is what 'extremely' steamrollered."""
        self.assertIn("a controlled secondary or opposing color", self.DOC)
        self.assertIn("Maintain strong value structure", self.DOC)

    def test_subjective_no_longer_offers_a_way_out(self):
        self.assertNotIn("when emotionally motivated", self.DOC)
        self.assertIn("where the moment carries feeling", self.DOC)

    def test_the_reader_shows_them(self):
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        self.assertIn("HEDGED LINES", js)
        self.assertIn("satisfy the line by doing LESS", js)


if __name__ == "__main__":
    unittest.main()
