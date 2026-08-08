"""The screenplay's places reach the Reference library (user 2026-08-08).

"Repair Shop" was findable on Production Design — the locations register
is a deterministic slugline parse — but the Reference library's search
covered only refs and subject cards, so the same name returned NOTHING.
No way to see the place lacked imagery, no act to give it any.

The link lands as the SCENES shelf's twin of the uncast pattern, and
casting stays subjects-only: subjects ride when their subject appears on
a panel, places ride when a board covers their scene.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import store  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


class TheShelfKnowsTheScreenplay(unittest.TestCase):
    def test_the_library_fetches_the_deterministic_register(self):
        i = JS.index("async function renderReferences")
        self.assertIn('api("/api/screenplay/locations")', JS[i:i + 900])

    def test_anchored_uses_the_panel_matchers_semantics(self):
        """Two-way containment on the titled-role suffix — the same rule
        the panel pre-check uses, so the two can never disagree."""
        i = JS.index("let unanchored = [];")
        block = JS[i:i + 900]
        self.assertIn("x.includes(y) || y.includes(x)", block)
        self.assertIn('String(r.role).split("—")[1]', block)

    def test_a_rejected_anchor_does_not_count_as_coverage(self):
        i = JS.index("let unanchored = [];")
        self.assertIn('r.status !== "REJECTED"', JS[i:i + 900])

    def test_the_count_line_states_the_gap(self):
        self.assertIn("} UNANCHORED`", JS)
        self.assertIn("${unanchored.length} LOCATION${", JS)

    def test_search_covers_locations_and_their_environment(self):
        self.assertIn("const matchesLoc = l =>", JS)
        i = JS.index("const matchesLoc")
        self.assertIn("envOfLoc(l.location)", JS[i:i + 300])


class TheCard(unittest.TestCase):
    def test_it_states_the_consequence_not_just_the_absence(self):
        i = JS.index("function buildUnanchoredLocCard")
        block = JS[i:i + 1600]
        self.assertIn("text and style alone", block)
        self.assertIn("UNANCHORED", block)

    def test_its_one_act_prefills_head_and_title(self):
        i = JS.index("function buildUnanchoredLocCard")
        block = JS[i:i + 1800]
        self.assertIn('addReferenceDialog({ head: "LOCATION_GEOMETRY", title: l.location })',
                      block)

    def test_the_dialog_accepts_the_prefill(self):
        i = JS.index("async function addReferenceDialog(prefill = {})")
        block = JS[i:i + 500]
        self.assertIn("prefillHead: prefill.head", block)
        self.assertIn("prefillTitle: prefill.title", block)


class CastingStaysSubjectsOnly(unittest.TestCase):
    def test_location_is_deliberately_not_a_subject_kind(self):
        """The jurisdiction split: making locations castable would attach
        place imagery per-panel-appearance instead of per-scene-coverage.
        If this ever changes, it is a design decision, not a drift."""
        self.assertEqual(store.SUBJECT_KINDS, {"CHARACTER", "VEHICLE", "PROP"})

    def test_the_card_offers_no_cast_act(self):
        i = JS.index("function buildUnanchoredLocCard")
        block = JS[i:JS.index("function buildUncastCard", i)]
        self.assertNotIn('data-f="cast"', block)
        self.assertNotIn("Cast this", block)


if __name__ == "__main__":
    unittest.main()
