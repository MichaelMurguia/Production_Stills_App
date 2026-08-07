"""One act, one name.

2026-08-07, user: the link that creates a breakdown from a location read
"Create Breakdown" on the Screenplay tab and "Make sheet" on Production
Design — the same act, two names, for the same object. Stage 03 is called
Breakdowns everywhere else, so that is the word.

Buttons are sentence case in this app ("Add images", "Read the
screenplay", "Upload a new draft"), so it is "Create breakdown".
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def button_labels() -> list[str]:
    """Every literal label on a location-finder verb."""
    return re.findall(r'class="(?:block-act loc-draft|loc-open)"[^>]*>([^<${]+)</button>', JS)


class OneActOneName(unittest.TestCase):
    def test_the_finders_have_labels_to_check(self):
        self.assertGreaterEqual(len(button_labels()), 3, button_labels())

    def test_the_breakdown_verb_is_the_same_in_both_finders(self):
        """Screenplay and Production Design both offer it — one wording."""
        labels = {l.strip() for l in button_labels()}
        self.assertTrue(labels <= {"Create breakdown", "Open breakdown"},
                        f"unexpected verb wording: {labels}")

    def test_the_old_sheet_wordings_are_gone(self):
        for dead in ("Make sheet", "Open sheet", "Create Sheet", "Create Breakdown"):
            self.assertNotIn(f">{dead}<", JS, f"{dead} should be 'Create/Open breakdown'")

    def test_buttons_stay_sentence_case(self):
        """Not Courier caps — a verb is a word, not machine data."""
        for label in button_labels():
            label = label.strip()
            self.assertEqual(label, label[0].upper() + label[1:].lower(), label)


if __name__ == "__main__":
    unittest.main()
