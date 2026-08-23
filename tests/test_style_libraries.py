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

LIBRARIES = {"cinematography": 8, "texture": 5, "rendering": 10}


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


class TheDrafterSeesTheWholeDocument(unittest.TestCase):
    """User, 2026-08-22: the deep prompts existed and only a human read
    them.

    An anchor answer is free text, and the picker writes a style's
    DIRECTIVE into it — name, subtitle, principle and six mechanics,
    capped at 600 characters. The document entry behind it also carries
    the remaining mechanics and an explicit Avoid list, and the Bible
    drafter never saw either. So the library's depth improved what a human
    read and left the model working from a summary.

    Deliberately NOT solved by injecting a style's image-model prompt into
    renders. Every anchor already reaches a panel through the bible's own
    global sections — `Rendering Language` is one, which is why picking
    Production Painting produces brushwork today. A second injection
    around the bible would be a second source for a fact the bible already
    carries, on a product whose whole premise is canon-locked art
    direction.
    """

    def answers(self, **kw):
        from app import style_docs
        out = {}
        for field, lib in (("texture", "texture"), ("medium", "rendering"),
                           ("light", "cinematography")):
            if field in kw:
                out[field] = style_docs.styles(lib)[kw[field]]["value"]
        return out

    def test_a_picked_style_hands_over_its_whole_entry(self):
        from app import style_docs, wizard
        st = style_docs.styles("texture")[2]
        out = wizard.style_depth(self.answers(texture=2))
        self.assertIn(st["name"], out)
        self.assertIn(st["principle"][:40], out)
        for m in st["mechanics"]:
            self.assertIn(m, out, "every mechanic, not the directive's six")
        self.assertIn(st["avoid"][0], out)

    def test_it_carries_more_than_the_directive_did(self):
        from app import style_docs, wizard
        st = style_docs.styles("rendering")[4]
        out = wizard.style_depth(self.answers(medium=4))
        self.assertGreater(len(out), len(st["value"]) * 2)
        self.assertGreater(len(st["mechanics"]), 6,
                           "the directive only carries six")

    def test_it_names_the_sections_the_anchor_is_fenced_into(self):
        """A mechanic may only land in a section its anchor feeds — the
        section fence the drafter already enforces."""
        from app import wizard
        out = wizard.style_depth(self.answers(medium=0, texture=0, light=0))
        self.assertIn("Rendering Language and Production Board Presentation", out)
        self.assertIn("Overall Visual Identity and Core Material Language", out)
        self.assertIn("Lighting Language and Composition Rules", out)
        self.assertIn("and nothing else", out)

    def test_an_edited_answer_expands_to_nothing(self):
        """The director's own words are theirs. An answer that no longer
        matches a library entry verbatim must not drag that entry's full
        mechanics along behind it."""
        from app import style_docs, wizard
        v = style_docs.styles("texture")[1]["value"]
        self.assertEqual(wizard.style_depth({"texture": v[:-8]}), "")
        self.assertEqual(wizard.style_depth({"texture": "my own words"}), "")
        self.assertEqual(wizard.style_depth({}), "")

    def test_palette_has_no_library_to_expand(self):
        """Swatches are proposed FROM the bible, not chosen before it."""
        from app import wizard
        self.assertNotIn("palette", wizard._ANCHOR_LIBRARY)

    def test_the_depth_reaches_the_bible_instructions(self):
        from app import wizard
        src = (ROOT / "app" / "wizard.py").read_text(encoding="utf-8")
        self.assertIn("{style_depth(answers)}", src)

    def test_no_style_prompt_is_injected_into_a_render(self):
        """The evaluated call (2026-08-22): the bible is the one path.
        Cinematography's ride block predates this and stays, behind its own
        off-by-default switch."""
        gen = (ROOT / "app" / "generate.py").read_text(encoding="utf-8")
        self.assertNotIn("style_docs", gen)
        self.assertIn("_cine.prompt_block(panel)", gen)


class TheCardAlwaysShowsAPicture(unittest.TestCase):
    """User, 2026-08-22: "we lost the images on World Texture."

    Making texture and rendering document-backed set `rich` on their
    styles, which routed them down the photographed-frames path — and that
    path had no fallback. Five textures and ten rendering styles silently
    traded a diagram they HAD for a placeholder line saying they had none.

    B3 still holds: a rich card must not pad to three empty cells. Showing
    the drawn plate that already existed is not padding, and the
    placeholder is reserved for a style with neither.
    """

    def test_a_rich_style_falls_back_to_its_drawn_plate(self):
        i = JS.index("function styleCard(")
        seg = JS[i:i + 1600]
        self.assertIn("const drawn = st.plate || st.shot", seg)
        self.assertIn(": drawn || `<span class=\"rs-nof mono\">", seg)

    def test_the_placeholder_survives_for_a_style_with_neither(self):
        i = JS.index("function styleCard(")
        self.assertIn("REFERENCE FRAMES — NOT YET IN THE LIBRARY", JS[i:i + 1600])

    def test_a_drawn_plate_takes_the_frame_shape_in_a_rich_card(self):
        """The rich card is two-up and much wider than the three-up plain
        card, so the diagram's native 68/56 became a column of empty ground
        with a mark at the bottom."""
        css = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".rs-cards-rich .rs-frame { aspect-ratio: 16 / 9; }", css)


class ThePlatesAreTheUsersOwnRenders(unittest.TestCase):
    """The user rendered every grammar and every texture, three scenes
    each, and the manifest is what the picker reads.

    Cinematography: action / character / discovery.
    World texture:  action / sci-fi / shark — the same three subjects
    under each condition, so the five read as one comparison.
    """

    PHOTOGRAPHED = {"cinematography": "cine-", "texture": "tex-"}

    def manifest(self):
        import json
        return json.loads((ROOT / "app" / "static" / "style-plates"
                           / "index.json").read_text(encoding="utf-8"))

    def test_every_style_in_a_photographed_library_has_three_frames(self):
        from app import style_docs
        m = self.manifest()
        for lib in self.PHOTOGRAPHED:
            for st in style_docs.styles(lib):
                self.assertIn(st["key"], m, f"{st['name']} has no plates")
                self.assertEqual(len(m[st["key"]]), 3, st["name"])

    def test_every_named_file_exists(self):
        base = ROOT / "app" / "static" / "style-plates"
        for key, files in self.manifest().items():
            for f in files:
                self.assertTrue((base / f).exists(), f"{key}: {f} is missing")

    def test_the_manifest_names_no_orphans(self):
        """A file nothing references is clutter; an entry with no file is a
        broken image."""
        base = ROOT / "app" / "static" / "style-plates"
        named = {f for files in self.manifest().values() for f in files}
        on_disk = {p.name for p in base.glob("*.webp")}
        self.assertEqual(on_disk - named, set(), "unreferenced plate files")

    def test_no_style_shows_the_same_frame_twice(self):
        """User, 2026-08-22: "the cinematography images have the wrong
        image for discovery." Classical Adventure was showing action,
        character and character-again — its third slot held the old
        character render rather than the discovery one, because that style
        was the one gap in the new set and its two remaining frames came
        from an older folder whose scene order nobody had checked.

        A duplicate frame is invisible in a manifest and obvious on screen,
        so it is checked where it is visible: in the pixels."""
        import itertools
        from PIL import Image, ImageChops
        base = ROOT / "app" / "static" / "style-plates"

        def sig(p):
            return Image.open(p).convert("RGB").resize((48, 48), Image.LANCZOS)

        for key, files in self.manifest().items():
            sigs = [sig(base / f) for f in files]
            for (i, a), (j, b) in itertools.combinations(enumerate(sigs), 2):
                d = ImageChops.difference(a, b)
                score = sum(sum(px) for px in d.getdata()) / (48 * 48 * 3)
                self.assertGreater(
                    score, 10,
                    f"{key}: {files[i]} and {files[j]} are the same picture")

    # Rendering is the PARTLY photographed library (2026-08-22): the user
    # rendered five of the ten, one scene each — the same spaceport street
    # in five media — so five cards show a frame and five still show their
    # drawn diagram. Both halves have to keep working.
    RENDERED = {"rend-production-painting", "rend-photo-real",
                "rend-ink-wash", "rend-hand-drawn-cartoon",
                "rend-3d-rendered-cartoon"}

    def test_the_rendered_five_are_exactly_what_is_in_the_manifest(self):
        m = self.manifest()
        self.assertEqual({k for k in m if k.startswith("rend-")}, self.RENDERED)

    def test_every_rendering_style_keeps_a_diagram_to_fall_back_to(self):
        """Half the library is still unrendered, and a card with neither a
        frame nor a diagram is a hole."""
        from app import style_docs
        i = JS.index("const STYLE_PLATES = ")
        plates = JS[i:JS.index(";", i)]
        for st in style_docs.styles("rendering"):
            self.assertIn('"' + st["name"] + '"', plates)

    def test_a_partly_photographed_library_still_apologises(self):
        """The note is per-picker and reads "some card here is a diagram",
        which is true while five of ten are. It keys off the cards, not off
        the library having any frames at all — that earlier version had
        cinematography apologising for diagrams it no longer showed."""
        i = JS.index("PLATES ARE DIAGRAMS")
        seg = JS[max(0, i - 400):i]
        self.assertIn("styles.some(x => x.plate && !plateShots(x.key).length)",
                      seg)

    def test_the_diagram_apology_only_shows_over_a_diagram(self):
        """It used to key off "has a plate", which stays true after a
        library gains photographed frames — so cinematography and then
        world texture kept apologising for diagrams they no longer
        showed."""
        self.assertIn("styles.some(x => x.plate && !plateShots(x.key).length)", JS)





NL = chr(10)


class AWrappedBulletKeepsItsTail(unittest.TestCase):
    def setUp(self):
        from app import style_docs
        self.style_docs = style_docs

    """A mechanic long enough to wrap lost everything after the first line
    until 2026-08-22, and these bullets are copied verbatim into the Art
    Direction Bible and from there into every render prompt. "Materials
    read at production-board viewing distance: value, edge quality and
    colour before texture" arrived as "...value, edge quality"."""

    def test_a_continuation_line_joins_its_bullet(self):
        got = self.style_docs._bullets(
            "- one" + NL + "- two that runs on" + NL
            + "  and finishes here" + NL + "- three")
        self.assertEqual(got, ["one", "two that runs on and finishes here",
                               "three"])

    def test_the_section_rule_is_still_not_a_bullet(self):
        rule = "- a" + NL + NL + "---" + NL + NL + "- b"
        self.assertEqual(self.style_docs._bullets(rule), ["a", "b"])

    def test_the_real_document_carries_the_whole_mechanic(self):
        m = [x for x in self.style_docs.styles("rendering")[0]["mechanics"]
             if x.startswith("Materials read")]
        self.assertEqual(len(m), 1)
        self.assertIn("no microscopic surface variation", m[0])

    def test_a_wrapped_avoid_line_keeps_its_tail(self):
        """Seven of the nine rendering styles wrap their Avoid line, and
        every one lost the tail until 2026-08-22. These become the card's
        NOT fence AND the Bible's `### Avoid` bullets, so the loss rode
        every render prompt silently."""
        got = self.style_docs._avoid(
            "text" + NL + NL + "Avoid: one, two," + NL + "three, four" + NL)
        self.assertEqual(got, ["one", "two", "three", "four"])

    def test_it_stops_at_the_blank_line(self):
        got = self.style_docs._avoid(
            "Avoid: one, two" + NL + NL + "Some other paragraph, with commas")
        self.assertEqual(got, ["one", "two"])

    def test_the_real_documents_lost_nothing(self):
        """The concrete recoveries — 3D Rendered Cartoon refused "heavy
        texture" where the document says "heavy texture maps", and Photo
        Real never refused cartoon proportion at all."""
        by = {e["name"]: e["avoid"]
              for e in self.style_docs.styles("rendering")}
        self.assertIn("heavy texture maps", by["3D Rendered Cartoon"])
        self.assertIn("chromatic aberration", by["3D Rendered Cartoon"])
        self.assertIn("cartoon proportion", by["Photo Real"])
        self.assertIn("background detail", by["Industrial Design"])
        self.assertNotIn("heavy texture", by["3D Rendered Cartoon"])

if __name__ == "__main__":
    unittest.main()
