"""A1 — the camera recipes, read as a fourth style library.

The style libraries speak in adjectives, and an image model satisfies an
adjective by doing nothing: `selective focus`, `negative space` and
`unusual subject placement` are all true of an everything-sharp frame if
the model decides they are. That is how a Subjective/Poetic grammar
produced two days of flat, evenly-lit renders while every part of the
plumbing tested correct.

`85–135mm, f/1.4–2, very shallow` has no such reading. This is the
document that says it, and these are the tests that keep it readable by
the app.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import style_docs  # noqa: E402

DOC = ROOT / "docs/CAMERA_RECIPES.md"


class TheDocumentIsTheLibrary(unittest.TestCase):
    def test_twenty_framings_and_thirteen_axes(self):
        """A1.3 — the count was reported as 21. It is 20, and the
        document now says so rather than leaving the question open."""
        self.assertEqual(len(style_docs.camera_recipes()), 20)
        self.assertEqual(len(style_docs.modifier_axes()), 13)

    def test_it_carries_every_framing_the_source_document_authored(self):
        src = (ROOT / "docs/Cinematography/CINEMATIC_LENS_AND_FRAMING_RECIPES.md"
               ).read_text(encoding="utf-8")
        body = src[src.index("# 2. Desired Framing"):src.index("# 3. Modifiers")]
        authored = {ln.split("**")[1] for ln in body.splitlines() if ln.startswith("| **")}
        self.assertEqual({r["name"] for r in style_docs.camera_recipes()}, authored)

    def test_a_row_carries_its_settings_not_just_its_name(self):
        r = style_docs.camera_recipe("extreme-emotional-isolation")
        self.assertEqual(r["focal"], "85–135mm")
        self.assertEqual(r["aperture"], "f/1.4–2")
        self.assertEqual(r["focus"], "Very shallow")

    def test_the_table_header_is_not_a_recipe(self):
        keys = [r["key"] for r in style_docs.camera_recipes()]
        self.assertNotIn("ID", keys)
        self.assertNotIn("Axis ID", [a["key"] for a in style_docs.modifier_axes()])

    def test_an_unknown_key_is_none_rather_than_a_guess(self):
        self.assertIsNone(style_docs.camera_recipe("nope"))
        self.assertIsNone(style_docs.camera_recipe(""))
        self.assertIsNone(style_docs.camera_recipe(None))


class TheIdIsTheContract(unittest.TestCase):
    """Panels store the ID. A derived ID would re-key every panel using a
    framing the first time someone fixed a typo in its name — and did:
    deriving from `Deep-space mise-en-scène` gave `deep-space-mise-en-sc-ne`."""

    def test_every_row_has_one_and_they_are_unique(self):
        keys = [r["key"] for r in style_docs.camera_recipes()]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(k and k == k.lower() and " " not in k for k in keys))

    def test_the_accented_row_keys_cleanly(self):
        self.assertIsNotNone(style_docs.camera_recipe("deep-space-mise-en-scene"))

    def test_the_document_states_that_ids_must_not_change(self):
        self.assertIn("orphans every panel", DOC.read_text(encoding="utf-8"))


class ItIsDenserThanTheGrammarItSupplements(unittest.TestCase):
    def test_a_recipe_value_is_a_fraction_of_a_grammar_block(self):
        """The reason this helps the prompt budget rather than fighting
        it: more instruction, fewer characters."""
        poetic = style_docs.camera_recipe("subjective-poetic-character")
        cine = [s for s in style_docs.styles("cinematography")
                if "poetic" in s["name"].lower() or "subjective" in s["name"].lower()]
        self.assertTrue(cine, "the Subjective/Poetic grammar should still exist")
        self.assertLess(len(poetic["value"]), len(cine[0]["value"]))

    def test_the_value_leads_with_settings_not_adjectives(self):
        v = style_docs.camera_recipe("intimate-close-up")["value"]
        self.assertIn("75–100mm", v)
        self.assertIn("f/2–2.8", v)
        self.assertLess(v.index("75–100mm"), v.index("Face dominates"))


class ModifiersAreGroupedByAxis(unittest.TestCase):
    def test_an_axis_owns_its_settings(self):
        """Flat, thirty-four rows would invite shipping `Locked` and
        `Handheld / reactive` in the same prompt."""
        h = next(a for a in style_docs.modifier_axes() if a["key"] == "camera-height")
        self.assertEqual([s["setting"] for s in h["settings"]],
                         ["0.3–0.8m", "1.2–1.7m", "2–4m", "Very high"])

    def test_every_axis_has_at_least_two_settings(self):
        """An axis with one setting is not a choice."""
        for a in style_docs.modifier_axes():
            self.assertGreaterEqual(len(a["settings"]), 2, a["key"])


class ItIsReadLive(unittest.TestCase):
    def test_an_edit_reaches_the_app_without_a_restart(self):
        """The property that let one word fix a style in an afternoon."""
        original = DOC.read_text(encoding="utf-8")
        try:
            DOC.write_text(original.replace("| **Intimate close-up** | 75–100mm",
                                            "| **Intimate close-up** | 300mm"),
                           encoding="utf-8")
            self.assertEqual(style_docs.camera_recipe("intimate-close-up")["focal"], "300mm")
        finally:
            DOC.write_text(original, encoding="utf-8")
        self.assertEqual(style_docs.camera_recipe("intimate-close-up")["focal"], "75–100mm")

    def test_a_missing_document_is_an_empty_library_not_a_crash(self):
        import app.paths as paths
        was = paths.ROOT
        try:
            paths.ROOT = ROOT / "does-not-exist"
            self.assertEqual(style_docs.camera_recipes(), [])
            self.assertEqual(style_docs.modifier_axes(), [])
        finally:
            paths.ROOT = was


if __name__ == "__main__":
    unittest.main()
