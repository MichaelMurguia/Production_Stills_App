"""The period a director states must survive a re-scan.

Found 2026-08-26 while diagnosing why a 200-years-hence screenplay was
rendering WW2 aircraft. Two things were wrong and only one of them was
this; the other was that the production had never stated a period at all
— the scan wrote "241 years in the future" into the LOGLINE, which no
prompt reads, and left the `period` field null.

This is the half that would have thrown the answer away afterwards.
`merge_analysis` already protects everything a user can author by hand —
act names, confirmed design languages, confirmed environments, answered
questions — because a fresh read about design languages must not silently
drop them. The period is authored by hand too (Step 2 → PERIOD → State
it) and was not on that list.

UNSTATED is the sharp case. The scan is instructed to say UNSTATED when
the screenplay does not fix a period, so storing it over a director's
answer would let the model overrule them by failing to find something.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, wizard  # noqa: E402

STATED = "241 years in the future"


class AStatedPeriodOutlivesAReScan(unittest.TestCase):
    def merged(self, fresh_period, prior_period=STATED):
        prior = {"period": prior_period} if prior_period is not None else {}
        fresh = {"logline": "x"}
        if fresh_period is not None:
            fresh["period"] = fresh_period
        return wizard.merge_analysis(prior, fresh).get("period")

    def test_a_read_that_omits_it_keeps_it(self):
        self.assertEqual(self.merged(None), STATED)

    def test_a_read_that_says_unstated_keeps_it(self):
        """The scan is TOLD to say UNSTATED when the screenplay does not
        fix a period. Letting that overwrite a director's answer would be
        the model overruling them by failing to find something."""
        self.assertEqual(self.merged("UNSTATED"), STATED)
        self.assertEqual(self.merged("unstated"), STATED)

    def test_the_other_empty_words_too(self):
        for v in ("", "  ", "UNKNOWN", "N/A", "NONE"):
            self.assertEqual(self.merged(v), STATED, v)

    def test_a_read_that_names_a_real_period_wins(self):
        """Same rule as every other field here: a fresh read that actually
        says something is the newer answer."""
        self.assertEqual(self.merged("the 1940s"), "the 1940s")

    def test_a_first_run_is_untouched(self):
        self.assertEqual(wizard.merge_analysis({}, {"period": "the 1940s"})["period"],
                         "the 1940s")

    def test_it_does_not_invent_one(self):
        self.assertIsNone(self.merged(None, prior_period=None))


class OneDefinitionOfUnstated(unittest.TestCase):
    """A value the prompt treats as absent and the merge treats as an
    answer is a period that vanishes from renders while the screen still
    shows it."""

    def test_both_readers_share_it(self):
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        self.assertIn("from .wizard import _no_period", src)

    def test_the_same_words_are_absent_to_both(self):
        from app import store
        was = store.load_wizard_analysis
        try:
            for v in ("", "UNSTATED", "unknown", "N/A", "None", "  "):
                store.load_wizard_analysis = lambda v=v: {"period": v}
                self.assertEqual(generate.production_period(), "", repr(v))
                self.assertTrue(wizard._no_period(v), repr(v))
        finally:
            store.load_wizard_analysis = was

    def test_a_real_period_is_present_to_both(self):
        from app import store
        was = store.load_wizard_analysis
        try:
            store.load_wizard_analysis = lambda: {"period": STATED}
            self.assertEqual(generate.production_period(), STATED)
            self.assertFalse(wizard._no_period(STATED))
        finally:
            store.load_wizard_analysis = was


class ItReachesTheRender(unittest.TestCase):
    """Compiled against a stub Bible. The subject here is the PERIOD
    block, and a test that ALSO needed a real production on disk passed
    alone and failed in the suite the moment another test redirected
    paths to a temp home — which is exactly what happened."""

    SPEC = {"specification_id": "S1", "mode": "CANON_EXTRACTION",
            "subject": "x", "panels": []}
    PANEL = {"id": "P01", "title": "t", "purpose": "p",
             "required_objects": ["an aircraft in the sky"]}

    def compile(self, period):
        from app import bible, store
        was_a, was_b = store.load_wizard_analysis, bible.load_text
        try:
            store.load_wizard_analysis = lambda: {"period": period}
            bible.load_text = lambda: "# B\n\n## Rendering Language\n\nPhotoreal.\n"
            return generate.compile_panel_prompt(self.SPEC, self.PANEL, [])
        finally:
            store.load_wizard_analysis, bible.load_text = was_a, was_b

    def test_a_stated_period_becomes_a_prompt_block(self):
        out = self.compile(STATED)
        self.assertIn("PERIOD", out)
        self.assertIn(STATED, out)
        self.assertIn("anachronism is a canon violation", out)

    def test_an_unstated_period_injects_nothing(self):
        """Inventing an era would be exactly the fabrication the
        constraint exists to prevent."""
        self.assertNotIn("\nPERIOD\n", self.compile("UNSTATED"))


if __name__ == "__main__":
    unittest.main()
