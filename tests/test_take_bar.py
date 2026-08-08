"""The take action bar against corrected mock 14a (comparison pass,
2026-08-08).

T1/T2 were built from written spec; the corrected mock arrived after and
this holds the three places the build had drifted from it:

  * identity rides the TOP right (it sat bottom-right) and states which
    take of how many — `CAND-0008 · TAKE 2 OF 2`;
  * the bar is buttons on the page, not a box of fenced zones — each
    verb's own ghost border is the only chrome, no internal rule;
  * a take's ordinal is its CREATION position. panelCands is newest-first,
    so index+1 numbered the latest take 1 OF N — backwards.

One reported deviation, kept deliberately: the mock omits Reject, but
removing a verb is functionality, and styling work does not change
functionality (CLAUDE.md). Reject stays at the far end in its danger
colour, inside the same ghost grammar.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


class TheIdentityTag(unittest.TestCase):
    def test_it_states_which_take_of_how_many(self):
        self.assertIn("· TAKE ${", JS)
        self.assertIn("} OF ${panelCands.length}", JS)

    def test_the_ordinal_is_the_creation_position(self):
        """panelCands is newest-first (.reverse()); the ordinal counts from
        the other end or the latest take reads TAKE 1 OF N."""
        self.assertIn("panelCands.length - panelCands.indexOf(staged)", JS)
        i = JS.index("const panelCands")
        self.assertIn(".reverse()", JS[i:i + 120],
                      "if this ordering changes, the ordinal math must too")

    def test_a_promoted_take_still_carries_its_ref(self):
        i = JS.index("shot-tag-id")
        self.assertIn("` · REF ${esc(stagedRef)}`", JS[i:i + 400])


class TheBar(unittest.TestCase):
    def test_the_zones_are_bare_append_targets(self):
        i = JS.index('<div class="act-bar">')
        block = JS[i:i + 600]
        self.assertNotIn("act-rule", block)
        self.assertNotIn("<span data-f=", block,
                         "zones are the targets themselves, not wrappers")

    def test_reject_survives_the_mock(self):
        """The deliberate deviation: the verb exists in the source even
        though the mock does not draw it."""
        i = JS.index('actDanger.append(mk("Reject"')
        self.assertGreater(i, 0)


if __name__ == "__main__":
    unittest.main()
