"""Uploading a screenplay costs nothing, so it does not wait for a key.

User, 2026-09-01: "product is locked. I added key and cant access the
screenplay tab."

Their key WAS saved. The dev loop sets SCREENBOARD_NO_KEYS so a mis-click
in a fast local loop cannot spend money, and the app honours it by
blanking its own stored credentials. Two consequences met:

1. `any_credential` went false, and a ruling of 2026-08-18 locked EVERY
   stage on that — including the screenplay, which needs no engine at all.
   Uploading a draft spends nothing; the READ spends, and the read has its
   own gate. The tab was refusing the one thing it could have done for
   free. **The user amended that ruling on 2026-09-01: stage 01 no longer
   waits.**

2. The app reported the exact shape of an un-configured install, so every
   surface sent them to Settings to add the key that was sitting there
   saved. A gate must name the condition it is ACTUALLY enforcing, so
   `capability` now reports `keys_suppressed` and the popover says so.

The second half is why this was worth fixing rather than documenting: the
app told someone to do something they had already done.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
NL = chr(10)


class StageOneDoesNotWaitForAnEngine(unittest.TestCase):
    def seg(self):
        i = JS.index("With no model connected the pipeline waits")
        return JS[i:JS.index("for (const stage of STAGE_ORDER)", i)]

    def test_everything_downstream_still_locks(self):
        s = self.seg()
        self.assertIn("if (state.capability && !state.capability.any_credential) {", s)
        self.assertIn("forEach(s2 => lockedStages.add(s2))", s)

    def test_but_the_screenplay_does_not(self):
        self.assertIn('STAGE_ORDER.filter(s2 => s2 !== "screenplay")', self.seg())

    def test_the_amendment_is_recorded_where_the_ruling_was(self):
        """A later pass reading only the old comment would put it back."""
        s = self.seg()
        self.assertIn("2026-08-18", s)
        self.assertIn("amended by the user 2026-09-01", s)

    def test_the_sentence_no_longer_claims_every_stage_needs_a_model(self):
        i = JS.index("const NO_MODEL_SENTENCE =")
        seg = JS[i:i + 200]
        self.assertIn("Everything past the screenplay", seg)
        self.assertNotIn("Every stage runs on an AI model", seg)


class TheGateNamesTheConditionItEnforces(unittest.TestCase):
    def test_capability_reports_the_dev_guard(self):
        was = os.environ.get("SCREENBOARD_NO_KEYS")
        try:
            os.environ["SCREENBOARD_NO_KEYS"] = "1"
            self.assertTrue(generate.capability()["keys_suppressed"])
            del os.environ["SCREENBOARD_NO_KEYS"]
            self.assertFalse(generate.capability()["keys_suppressed"])
        finally:
            if was is None:
                os.environ.pop("SCREENBOARD_NO_KEYS", None)
            else:
                os.environ["SCREENBOARD_NO_KEYS"] = was

    def test_the_popover_says_the_key_is_saved_rather_than_missing(self):
        i = JS.index("const KEYS_SUPPRESSED_SENTENCE =")
        seg = JS[i:i + 400]
        self.assertIn("Your key is saved", seg)
        self.assertIn("cannot spend", seg)

    def test_it_names_the_command_that_lifts_it(self):
        """A gate states its remedy. And the remedy has to be typeable —
        `\\d` is not a JS escape, so the backslash was silently dropped
        and the sentence read `.dev.bat`, which is not a command."""
        i = JS.index("const KEYS_SUPPRESSED_SENTENCE =")
        seg = JS[i:i + 400]
        self.assertIn(chr(92) + chr(92) + "dev.bat --keys", seg)

    def test_the_two_sentences_are_chosen_by_the_real_condition(self):
        i = JS.index("const noModelSentence = () =>")
        seg = JS[i:i + 300]
        self.assertIn("_bandState?.capability?.keys_suppressed", seg)
        self.assertIn("KEYS_SUPPRESSED_SENTENCE : NO_MODEL_SENTENCE", seg)

    def test_the_popover_asks_for_the_sentence_rather_than_the_constant(self):
        """Otherwise the branch above is dead code."""
        self.assertIn("? noModelSentence()", JS)
        self.assertEqual(JS.count("NO_MODEL_SENTENCE"), 2,
                         "one definition, one use inside the chooser")


if __name__ == "__main__":
    unittest.main()
