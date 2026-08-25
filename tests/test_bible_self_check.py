"""R2 — does the Art Direction Bible agree with itself?

Selection is repair work (R1). A Bible that does not contradict itself
needs less of it.

At draft time the whole document is wanted — that is the point of it.
But nothing had ever read it back to ask whether its sections agree, and
the production this was built from carried, in three different places:

    Lighting Language    "use wide or moderate-wide lenses with deep focus"
    Rendering Language   "readable form over surface"
    Composition Rules    legibility everywhere

Three sections independently ruling out selective focus, none of them
aware of the others, under a Subjective/Poetic grammar whose whole
subject is selective focus. Two days of renders came back flat while
every part of the plumbing tested correct.

The hard part is not finding disagreements. It is telling a
CONTRADICTION from a DESIGNED CONTRAST — `Weathered Present` against
`Pristine Future` is the spine of that production, not an error. A
checker that cannot tell those apart is turned off within a day, and is
right to be.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import autofill  # noqa: E402
from app import wizard  # noqa: E402

HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")

BIBLE = """# Art Direction Bible

## Rendering Language

Readable form over surface. Every plane legible.

## Lighting Language

Use wide or moderate-wide lenses with deep focus.

## Weathered Present

Salt-eaten, patched, repaired in public.

## Pristine Future

Unmarked, unweathered, factory-exact.
"""


class ItAsksTheRightQuestion(unittest.TestCase):
    def instr(self):
        return wizard._consistency_instructions(BIBLE)

    def test_it_defines_a_contradiction_by_the_frame_not_by_disagreement(self):
        """Two rules that cannot both hold for the same subject in the
        same frame. Nothing else counts."""
        self.assertIn("CANNOT BOTH HOLD for the same subject in the\nsame frame",
                      self.instr())

    def test_designed_contrast_is_ruled_out_by_name(self):
        t = self.instr()
        self.assertIn("DESIGNED CONTRAST is not a contradiction", t)
        self.assertIn("Weathered Present", t)
        self.assertIn("Pristine Future", t)

    def test_it_says_an_empty_answer_is_a_good_answer(self):
        """A checker that must find something will find something."""
        self.assertIn("An empty\nanswer is a good answer", self.instr())

    def test_it_is_told_not_to_edit(self):
        t = self.instr()
        self.assertIn("do not resolve anything", t)
        self.assertIn("reporting, not editing", t)

    def test_the_document_itself_is_in_the_question(self):
        self.assertIn("Readable form over surface", self.instr())


class NothingUnverifiableSurvives(unittest.TestCase):
    """A report the document does not support is worse than no report:
    it sends a director hunting for a sentence nobody wrote."""

    def check(self, conflicts):
        was = autofill._draft
        autofill._draft = lambda *a, **k: ({"conflicts": conflicts}, "fake")
        try:
            return wizard.bible_self_check(BIBLE, "gemini")["conflicts"]
        finally:
            autofill._draft = was

    GOOD = {"sections": ["Rendering Language", "Lighting Language"],
            "quotes": ["Readable form over surface",
                       "Use wide or moderate-wide lenses with deep focus"],
            "why": "one frame cannot give up a plane and keep every plane legible",
            "confidence": 0.9}

    def test_a_real_one_survives(self):
        out = self.check([self.GOOD])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["sections"],
                         ["Rendering Language", "Lighting Language"])

    def test_a_section_the_document_does_not_have_is_dropped(self):
        """R2.3 — the report lands in the Bible's own sections so the fix
        is one edit away from the reading. A heading that does not exist
        cannot be navigated to."""
        bad = {**self.GOOD, "sections": ["Rendering Language", "Colour Doctrine"]}
        self.assertEqual(self.check([bad]), [])

    def test_a_quote_the_document_does_not_contain_is_dropped(self):
        bad = {**self.GOOD,
               "quotes": ["Readable form over surface",
                          "Shoot everything at f/1.4 and let the world dissolve"]}
        self.assertEqual(self.check([bad]), [])

    def test_a_one_sided_report_is_not_a_conflict(self):
        """One quote is a model complaining about a sentence it dislikes,
        which is not what was asked for."""
        self.assertEqual(self.check([{**self.GOOD, "quotes": ["Readable form over surface"]}]), [])
        self.assertEqual(self.check([{**self.GOOD, "sections": ["Rendering Language"]}]), [])

    def test_junk_does_not_crash_it(self):
        self.assertEqual(self.check(["a string", None, {}]), [])


class ItNeverEdits(unittest.TestCase):
    def test_the_answer_carries_no_replacement_text(self):
        """The director decides what a contradiction means. The app's job
        is to have READ the thing."""
        was = autofill._draft
        autofill._draft = lambda *a, **k: ({"conflicts": [
            {**NothingUnverifiableSurvives.GOOD, "fix": "delete the lighting line"}]}, "f")
        try:
            out = wizard.bible_self_check(BIBLE, "gemini")["conflicts"][0]
        finally:
            autofill._draft = was
        self.assertNotIn("fix", out)

    def test_an_empty_bible_costs_nothing(self):
        self.assertEqual(wizard.bible_self_check("   ", "gemini"),
                         {"conflicts": [], "checked_chars": 0})

    def test_the_length_read_is_reported(self):
        """"No conflicts" from a read of 400 characters and from a read
        of 40,000 are different facts."""
        r = wizard.bible_self_check(BIBLE, "mock")
        self.assertEqual(r["checked_chars"], len(BIBLE.strip()))


class ItDoesNotDragTheScreenplayAlong(unittest.TestCase):
    def test_a_pass_can_run_with_no_document(self):
        """Every research pass until now read the screenplay, so a
        document was assumed. This one reads the Bible, which is already
        in the instructions — attaching 130 KB of screenplay would be
        paid for on every run and answer nothing."""
        src = (ROOT / "app/autofill.py").read_text(encoding="utf-8")
        self.assertIn("def _draft(provider: str, doc: bytes | None, mime: str | None,", src)
        self.assertIn("parts = ([] if doc is None", src)
        self.assertIn("if doc is None:\n        content = [{", src)

    def test_the_self_check_passes_none(self):
        src = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
        self.assertIn("autofill._draft(\n        provider, None, None,", src)


class TheReportIsReadableAndAdvisory(unittest.TestCase):
    def test_the_act_sits_under_the_document_it_reads(self):
        self.assertLess(HTML.index('id="style-bible"'), HTML.index('id="bible-check"'))

    def test_it_only_appears_once_there_is_a_saved_document(self):
        """An unsaved edit is not a document yet."""
        i = JS.index('$("#bible-check")?.classList.toggle')
        self.assertIn('"hidden", st !== "saved"', JS[i:i + 120])

    def test_a_stale_report_never_outlives_the_text_it_read(self):
        """An all-clear describing text no longer on screen is worse than
        no report."""
        i = JS.index('$("#style-bible").addEventListener("input"')
        self.assertIn("renderBibleConflicts(null)", JS[i:i + 200])

    def test_a_failed_read_is_never_shown_as_a_clean_read(self):
        """"No conflicts" and "the read failed" look identical on screen,
        and one of them means the document has not been checked."""
        i = JS.index('$("#bible-check")?.addEventListener')
        seg = " ".join(JS[i:i + 900].split())
        self.assertIn("renderBibleConflicts(null); toast(", seg)

    def test_a_clean_read_says_what_it_read_and_what_it_ignored(self):
        i = JS.index("const renderBibleConflicts")
        seg = " ".join(JS[i:i + 900].split())
        self.assertIn("characters", seg)
        self.assertIn("Deliberate contrast between different subjects is not counted", seg)

    def test_the_report_says_nothing_was_changed(self):
        i = JS.index("const renderBibleConflicts")
        self.assertIn("ADVISORY, NOTHING WAS CHANGED", JS[i:i + 1400])

    def test_it_is_not_painted_as_a_failure(self):
        """A contradiction the director meant is still the director's
        call, so nothing here is amber or --bad."""
        for sel in (".bc-head {", ".bc-row {", ".bc-q {", ".bc-why {", ".bc-none {"):
            block = CSS.split(sel)[1].split("}")[0]
            self.assertNotIn("--accent", block, sel)
            self.assertNotIn("--bad", block, sel)

    def test_the_section_names_are_courier_and_the_rules_are_prose(self):
        """Rule 2 — the headings are the document's own machine-ish
        identifiers; the quoted rules are its prose."""
        i = JS.index("const renderBibleConflicts")
        seg = JS[i:i + 1400]
        self.assertIn('class="bc-secs mono"', seg)
        self.assertIn('class="bc-q"', seg)


if __name__ == "__main__":
    unittest.main()
