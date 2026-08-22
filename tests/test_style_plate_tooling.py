"""The two scripts that stand between a folder of renders and the picker.

Both exist because the same work was done by hand twice — once for the
eight cinematography grammars, once for the five world textures — with a
bespoke filename-mapping table each time. The third library asked for the
same thing, so it became tooling.

`render_style_prompts.py` generates the calibration prompts FROM
`docs/RENDERING_STYLES.md`, so a prompt can never describe a style the app
does not have.

`import_style_plates.py` maps a folder of renders onto style keys. It
refuses rather than guesses: a mismapped plate is a picture of the wrong
thing under the right label, which is worse than no picture at all.
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ThePromptsAreGeneratedNotMaintained(unittest.TestCase):

    def built(self):
        from scripts import render_style_prompts
        return render_style_prompts.build()

    def committed(self):
        return (ROOT / "docs" / "RENDERING_STYLE_PROMPTS.md").read_text(
            encoding="utf-8")

    def test_the_committed_file_is_what_the_generator_produces(self):
        """It says "edit the document and re-run, never edit this file."
        This is what makes that true rather than a request."""
        self.assertEqual(self.built(), self.committed(),
                         "docs/RENDERING_STYLE_PROMPTS.md has drifted from "
                         "docs/RENDERING_STYLES.md — re-run "
                         "`python -m scripts.render_style_prompts`")

    def test_every_style_gets_all_three_scenes(self):
        from app import style_docs
        text = self.committed()
        styles = style_docs.styles("rendering")
        self.assertEqual(text.count("```text"), len(styles) * 3)
        for st in styles:
            for code in ("A", "B", "C"):
                self.assertIn(f"## {st['n']:02d}-{code} —", text, st["name"])

    def test_each_prompt_carries_its_own_style_and_fence(self):
        from app import style_docs
        text = self.committed()
        for st in style_docs.styles("rendering"):
            self.assertIn(st["prompt"], text, f"{st['name']} prompt missing")
            self.assertIn(st["principle"], text)
            for a in st["avoid"]:
                self.assertIn(a, text)

    def test_only_the_medium_is_allowed_to_vary(self):
        """The inverse of the user's cinematography set, whose baseline
        locks the rendering language. Here the subject, camera, light and
        palette are locked instead — otherwise three frames differ in five
        ways at once and prove nothing about the medium."""
        text = self.committed()
        self.assertIn("The rendering style is the ONLY variable", text)
        self.assertIn("camera position, framing, and subject-to-camera distance",
                      text)
        self.assertIn("If two images in this set differ in", text)

    def test_the_style_wins_where_a_scene_contradicts_it(self):
        """Scene C is dusk atmosphere; Technical Blueprint forbids
        lighting. The set has to say which loses."""
        self.assertIn("THE STYLE WINS", self.committed())


class TheImporterRefusesToGuess(unittest.TestCase):

    def imp(self):
        from scripts import import_style_plates
        return import_style_plates

    def test_a_style_is_matched_by_name_or_a_unique_prefix(self):
        from app import style_docs
        m = self.imp()
        styles = style_docs.styles("rendering")
        self.assertEqual(m.match_style("Production_Painting", styles, {})["key"],
                         "rend-production-painting")
        self.assertEqual(m.match_style("photo real", styles, {})["key"],
                         "rend-photo-real")
        # a unique prefix is enough
        self.assertEqual(m.match_style("Gouache", styles, {})["key"],
                         "rend-gouache-watercolor")

    def test_an_unmatched_name_matches_nothing(self):
        from app import style_docs
        m = self.imp()
        styles = style_docs.styles("rendering")
        self.assertIsNone(m.match_style("Watercolour", styles, {}))
        self.assertIsNone(m.match_style("", styles, {}))

    def test_an_alias_is_explicit_never_fuzzy(self):
        from app import style_docs
        m = self.imp()
        styles = style_docs.styles("texture")
        self.assertIsNone(m.match_style("Industrial_Use", styles, {}))
        self.assertEqual(
            m.match_style("Industrial_Use", styles,
                          {"Industrial_Use": "Industrial Grime"})["key"],
            "tex-industrial-grime")

    def test_the_longest_style_token_wins(self):
        """`Sci_Fi_Lived_In` is scene Sci_Fi, style Lived_In — not scene
        Sci_Fi_Lived, style In."""
        from app import style_docs
        m = self.imp()
        styles = style_docs.styles("texture")
        parts = "Sci_Fi_Lived_In".split("_")
        hit = next(("_".join(parts[:c]), m.match_style("_".join(parts[c:]), styles, {}))
                   for c in range(1, len(parts))
                   if m.match_style("_".join(parts[c:]), styles, {}))
        self.assertEqual(hit[0], "Sci_Fi")
        self.assertEqual(hit[1]["key"], "tex-lived-in")

    def test_it_only_clears_its_own_library(self):
        """Importing one library must not delete another's frames — both
        live in the same folder."""
        src = (ROOT / "scripts" / "import_style_plates.py").read_text(
            encoding="utf-8")
        self.assertIn('PLATES.glob(f"{prefix}*.webp")', src)

    def test_the_documented_naming_is_what_it_reads(self):
        prompts = (ROOT / "docs" / "RENDERING_STYLE_PROMPTS.md").read_text(
            encoding="utf-8")
        self.assertIn("Object_Production_Painting.png", prompts)
        self.assertIn("<Scene>_<Style>.png", prompts)


if __name__ == "__main__":
    unittest.main()
