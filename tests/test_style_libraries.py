"""Three anchors, three documents, one parser.

The 2026-08-16 ruling that made cinematography document-backed said why:
"the document is the source of truth and the one the user maintains, so
editing it updates the app and there is never a second list to keep in
step."

Until 2026-08-22 that was true of exactly one anchor. World texture and
rendering style were arrays in `app.js` — five and nine options, each with
a one-line description and a prompt fragment of about sixty characters.
The deepest world texture said, in full:

    weathered surfaces, patina, sun-bleach and oxidation, repairs visible

against 1,210 characters for a cinematography grammar. Adding a texture
meant editing the client. They were precisely the second list that ruling
was written against (user, 2026-08-22: "are there in depth prompts for
each?" — there were not).
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

ROOT = pathlib.Path(__file__).resolve().parents[1]
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")

LIBRARIES = {"cinematography": 8, "texture": 5, "rendering": 9}


class EveryLibraryIsDocumentBacked(unittest.TestCase):

    def test_all_three_documents_exist_and_parse(self):
        from app import style_docs
        for lib, count in LIBRARIES.items():
            self.assertTrue(style_docs.doc_path(lib).exists(),
                            f"{lib} has no document")
            self.assertEqual(len(style_docs.styles(lib)), count, lib)

    def test_every_style_carries_the_whole_format(self):
        """The format the documents promise in their own Purpose section:
        key question, description, operating principle, visual mechanics,
        image-model prompt."""
        from app import style_docs
        for lib in LIBRARIES:
            for st in style_docs.styles(lib):
                where = f"{lib}/{st['name']}"
                self.assertTrue(st["subtitle"], where)
                self.assertTrue(st["question"], where)
                self.assertTrue(st["description"], where)
                self.assertTrue(st["principle"], where)
                self.assertGreaterEqual(len(st["mechanics"]), 6, where)
                self.assertGreater(len(st["prompt"]), 200, where)

    def test_the_prompts_are_in_depth_not_fragments(self):
        """The thing that was actually missing. A sixty-character phrase
        is a label, not a prompt."""
        from app import style_docs
        for lib in LIBRARIES:
            for st in style_docs.styles(lib):
                self.assertGreater(
                    len(st["prompt"]), 400,
                    f"{lib}/{st['name']} prompt is {len(st['prompt'])} chars")

    def test_every_style_states_what_it_is_not(self):
        from app import style_docs
        for lib in LIBRARIES:
            for st in style_docs.styles(lib):
                self.assertTrue(st["avoid"],
                                f"{lib}/{st['name']} has no Avoid list")

    def test_keys_are_unique_and_namespaced_per_library(self):
        from app import style_docs
        seen = set()
        for lib in LIBRARIES:
            prefix = style_docs.LIBRARIES[lib][1]
            for st in style_docs.styles(lib):
                self.assertTrue(st["key"].startswith(prefix), st["key"])
                self.assertNotIn(st["key"], seen, "duplicate key")
                seen.add(st["key"])

    def test_the_directive_carries_mechanics_not_the_whole_prompt(self):
        """`value` is what rides a render. Per the cinematography
        document's Usage Note, generation leans on the mechanics and the
        operating principle rather than reciting the full prompt."""
        from app import style_docs
        for lib in LIBRARIES:
            for st in style_docs.styles(lib):
                where = f"{lib}/{st['name']}"
                self.assertNotEqual(st["value"], st["prompt"], where)
                self.assertIn(st["principle"].rstrip(".")[:30], st["value"], where)
                self.assertLessEqual(len(st["value"]), 600, where)

    def test_a_missing_document_is_an_empty_library_not_a_crash(self):
        """A library whose document is gone must degrade to nothing, so
        the caller can say so — never to an invented fallback."""
        from app import style_docs
        real = style_docs.doc_path
        try:
            style_docs.doc_path = lambda lib: ROOT / "docs" / "__absent__.md"
            self.assertEqual(style_docs.styles("texture"), [])
        finally:
            style_docs.doc_path = real


class TheClientHoldsNoSecondList(unittest.TestCase):

    def test_the_arrays_are_empty(self):
        self.assertIn("const RENDER_STYLES = [];", JS)
        self.assertIn("const TEXTURE_STYLES = [];", JS)
        self.assertIn("const CINEMA_STYLES = [];", JS)

    def test_no_retired_style_prose_survives_in_the_client(self):
        """The old one-line descriptions and directives. If any is still
        here it is the stale copy, because the document is now edited."""
        for gone in ("pristine surfaces, no wear, factory-new finishes",
                     "weathered surfaces, patina, sun-bleach and oxidation",
                     "painterly production art, visible brushwork, matte finish",
                     "orthographic technical drawing, keylines and dimension ticks"):
            self.assertNotIn(gone, JS, f"{gone!r} outlived the move to documents")

    def test_one_loader_serves_all_three(self):
        self.assertEqual(JS.count("async function loadStyleLibrary"), 1)
        for lib in LIBRARIES:
            self.assertIn(f'loadStyleLibrary("{lib}"', JS)

    def test_the_plates_are_kept_because_they_are_artwork(self):
        """A plate is a drawn diagram keyed by style name. It cannot live
        in markdown, so it stays here and is looked up — and every style
        the documents define that had one must still find it."""
        from app import style_docs
        i = JS.index("const STYLE_PLATES = ")
        plates = JS[i:JS.index(";", i)]
        for lib in ("texture", "rendering"):
            for st in style_docs.styles(lib):
                self.assertIn('"' + st["name"] + '"', plates, st["name"])


if __name__ == "__main__":
    unittest.main()
