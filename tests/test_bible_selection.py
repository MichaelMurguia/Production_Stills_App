"""R1 — selection, not truncation.

One panel's prompt ran 19,094 characters and rendered worse than a
1,782-character hand-written one. The obvious conclusion is that length
is the constraint. It is not, and acting on it would have thrown away
canon the panel needed — the opposite of what this product is for. The
short prompt worked because everything left in it AGREED with the panel.

R1.5's instrumentation then found the largest disagreement, and it was
not a design language: CHARACTER PRESENTATION, riding every panel whole,
on a panel whose required content is a hull, a pan, shivering air, a
ramp and six descending figures — and which names no characters at all.

Measured against the real production it was built from, the section goes
from 1,877 characters to 828 on that panel, and the six bullets it drops
are exactly the ones describing a pilot, a colonel and two others who are
not in the frame. The six it keeps are the rules that govern any frame:
present characters as inhabitants of systems, the Descent Team's
collective competence, do not beautify injury into fashion styling.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import bible  # noqa: E402
from app import generate  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

CAST = [
    {"name": "AVREL NDIAYE-DEKKER", "kind": "CHARACTER"},
    {"name": "COLONEL VANN OKAFOR", "kind": "CHARACTER"},
    {"name": "HARLOW DECKER", "kind": "CHARACTER"},
    {"name": "LEDGER SIX", "kind": "VEHICLE"},
]

BIBLE = """# Art Direction Bible

## Overall Visual Identity

Sun-bleached industrial.

## Rendering Language

Photoreal.

## Character Presentation

- Present characters as inhabitants of systems rather than portrait subjects.
- Avrel is tall, straight-backed, unweathered, visibly burdened.
- Harlow is lean, regulation-adjacent, physically exact under pressure.
- Vann is a large man going gaunt inside a pressed uniform.
- The Descent Team's competence is collective, exact, and frightening.
- Do not beautify injury, deprivation, or sacrifice into fashion styling.
"""


def sel(haystack, text=BIBLE, cast=CAST):
    return bible.character_selection(haystack, text, cast)


class ARosterIsNotGlobal(unittest.TestCase):
    """Three of the four global sections are genuinely global: what the
    world looks like, what medium it is painted in, how it is lit. The
    fourth is a roster, and a roster is per-subject material that
    happened to be filed at the top level."""

    def test_every_bullet_is_read_with_the_cast_it_is_about(self):
        rows = bible.character_lines(BIBLE, CAST)
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[1]["who"], ["AVREL NDIAYE-DEKKER"])

    def test_a_panel_keeps_only_the_people_it_names(self):
        s = sel("Avrel at the ramp, six descending figures")
        self.assertEqual(len(s["withheld"]), 2)
        self.assertTrue(any("Avrel is tall" in x for x in s["lines"]))
        self.assertFalse(any("Harlow is lean" in x for x in s["lines"]))

    def test_the_panel_that_started_this_drops_all_four(self):
        """hull, pan, shivering air, ramp, six figures. No names."""
        s = sel("hull, salt pan, shivering air, boarding ramp, six descending figures")
        self.assertEqual(len(s["withheld"]), 3)
        self.assertEqual(len(s["lines"]), 3)

    def test_a_rank_is_not_an_identity(self):
        """`COLONEL VANN OKAFOR` is Vann. A line about a different
        colonel is not about him."""
        self.assertNotIn("colonel", bible._name_tokens("COLONEL VANN OKAFOR"))
        self.assertIn("vann", bible._name_tokens("COLONEL VANN OKAFOR"))

    def test_only_characters_are_cast(self):
        toks = bible.cast_tokens(CAST)
        self.assertNotIn("LEDGER SIX", toks)


class ALineAboutNobodyGovernsEveryPanel(unittest.TestCase):
    """`Do not beautify injury into fashion styling` governs a frame with
    no people in it. Only a bullet that is ABOUT specific people can be
    about the wrong ones."""

    def test_general_rules_always_ride(self):
        s = sel("an empty corridor")
        self.assertTrue(any("Do not beautify injury" in x for x in s["lines"]))
        self.assertTrue(any("inhabitants of systems" in x for x in s["lines"]))

    def test_a_group_the_cast_does_not_list_is_not_withheld(self):
        """`The Descent Team` is not a subject, so nothing decides it is
        the wrong team. A heuristic reading capitalisation would have
        withheld the line governing six of them."""
        s = sel("an empty corridor")
        self.assertTrue(any("Descent Team" in x for x in s["lines"]))


class LosingCanonSilentlyIsTheWorstOutcome(unittest.TestCase):
    """R1.3 — where the selector cannot tell, it carries and says so.
    Every uncertain case lands on the carry side by construction."""

    def test_a_section_written_as_flat_prose_is_carried_whole(self):
        b = BIBLE.replace("- Present characters", "Present characters")
        b = "\n".join(l for l in b.splitlines() if not l.startswith("- "))
        s = bible.character_selection("Avrel", b, CAST)
        self.assertTrue(s["unsure"])
        self.assertEqual(s["withheld"], [])

    def test_a_bible_with_no_such_section_is_not_an_error(self):
        s = bible.character_selection("Avrel", "# B\n\n## Rendering Language\n\nx\n", CAST)
        self.assertTrue(s["unsure"])

    def test_no_cast_means_nothing_is_withheld(self):
        """A production that has not entered its cast has told the app
        nothing about who is who, and guessing would be worse."""
        s = bible.character_selection("Avrel", BIBLE, [])
        self.assertEqual(s["withheld"], [])
        self.assertEqual(len(s["lines"]), 6)

    def test_a_section_written_as_subsections_still_works(self):
        b = ("# B\n\n## Character Presentation\n\n"
             "### Avrel Ndiaye-Dekker\n\nTall, unweathered.\n\n"
             "### Harlow Decker\n\nLean, exact.\n")
        s = bible.character_selection("Avrel at the ramp", b, CAST)
        self.assertEqual(list(s["carry"]), ["Avrel Ndiaye-Dekker"])
        self.assertEqual(len(s["withheld"]), 1)


class ItReachesTheCompiledPrompt(unittest.TestCase):
    def setUp(self):
        self._was = bible.load_text
        bible.load_text = lambda: BIBLE
        from app import store
        self._subs = store.list_subjects
        store.list_subjects = lambda: CAST

    def tearDown(self):
        bible.load_text = self._was
        from app import store
        store.list_subjects = self._subs

    def test_a_named_panel_loses_the_strangers(self):
        out = bible.render_context("Avrel at the ramp")
        self.assertIn("Avrel is tall", out)
        self.assertNotIn("Harlow is lean", out)
        self.assertIn("Do not beautify injury", out)

    def test_the_other_global_sections_are_untouched(self):
        out = bible.render_context("Avrel at the ramp")
        self.assertIn("Sun-bleached industrial", out)
        self.assertIn("Photoreal", out)

    def test_it_measurably_shrinks_the_block_it_was_built_for(self):
        whole = len(bible.render_context("Avrel and Harlow and Vann"))
        one = len(bible.render_context("hull, pan, ramp, six figures"))
        self.assertLess(one, whole)


class ThePanelSaysWhatItWithheld(unittest.TestCase):
    """R1.2 — a selector that silently drops a section takes canon out of
    a render and leaves nobody able to see it, which is the precise
    failure this week was made of."""

    def setUp(self):
        self._was = bible.load_text
        bible.load_text = lambda: BIBLE
        from app import store
        self._subs = store.list_subjects
        store.list_subjects = lambda: CAST

    def tearDown(self):
        bible.load_text = self._was
        from app import store
        store.list_subjects = self._subs

    SPEC = {"subject": "the ramp", "render_intent": ""}

    def test_the_report_names_both_halves(self):
        r = generate.bible_selection(self.SPEC, {"required_objects": ["Avrel, at the ramp"]})
        self.assertEqual(len(r["withheld"]), 2)
        self.assertFalse(r["unsure"])

    def test_the_carried_count_works_for_either_section_shape(self):
        """`carry` is the subsection path, `lines` the bullet path, and
        real bibles use the second — one count, or the report reads "0
        carried" beside four carried lines."""
        r = generate.bible_selection(self.SPEC, {"required_objects": ["Avrel"]})
        self.assertEqual(r["carried"], 4)

    def test_every_withholding_carries_its_reason_and_its_subject(self):
        r = generate.bible_selection(self.SPEC, {"required_objects": ["Avrel"]})
        for w in r["withheld"]:
            self.assertTrue(w["why"])
            self.assertTrue(w["title"])

    def test_the_report_reads_the_same_text_the_compiler_selects_with(self):
        """Two copies of the haystack would drift, and the drift would be
        invisible: the report would describe a selection the render did
        not make."""
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("def _bible_haystack"), 1)
        self.assertIn("haystack = _bible_haystack(spec, panel)", src)
        self.assertIn("bible.character_selection(_bible_haystack(spec, panel))", src)

    def test_the_endpoint_carries_it(self):
        self.assertIn('"bible_selection": generate.bible_selection(spec, panel),',
                      (ROOT / "app/main.py").read_text(encoding="utf-8"))

    def test_the_panel_states_it_beside_the_measurement(self):
        i = JS.index("function bibleSelectionHtml")
        seg = " ".join(JS[i:i + 1600].split())
        self.assertIn("Withheld from this panel", seg)

    def test_an_unsure_selection_is_not_a_blank_panel(self):
        """"No saving here" is a result. An empty panel is not."""
        i = JS.index("function bibleSelectionHtml")
        seg = " ".join(JS[i:i + 1600].split())
        self.assertIn("if (sel.unsure)", seg)
        self.assertIn("a chair someone has just left", seg)

    def test_it_is_not_a_warning(self):
        """Withholding a paragraph about someone who is not in the frame
        is the system working."""
        css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
        block = css.split(".pc-with {")[1].split("}")[0]
        self.assertNotIn("--bad", block)
        self.assertNotIn("--accent", block)


if __name__ == "__main__":
    unittest.main()
