"""One board across revisions — client wiring pins (2026-08-13).

Text pins over app.js in the tests/test_camera.py style: the revise
modal posts the scope, carried rows are read-only with their stated chip
and Also revise act, and stage 05 speaks the unit's provenance grammar.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


class ReviseModalPins(unittest.TestCase):
    def test_the_modal_asks_the_users_own_question(self):
        self.assertIn("What panels would you like to include in revision", JS)

    def test_the_scope_rides_the_post(self):
        self.assertIn("revise_panels: ids", JS)

    def test_nothing_prechecked_and_confirm_gated_at_zero(self):
        self.assertIn("NOTHING REVISED YET — CHECK AT LEAST ONE PANEL", JS)
        self.assertIn('disabled = n === 0', JS)
        self.assertIn(">Select all<", JS)

    def test_the_counter_states_both_halves(self):
        self.assertIn("PANELS REVISED · ", JS)


class CarriedRowPins(unittest.TestCase):
    def test_the_row_flag_exists(self):
        self.assertIn("const ro = locked || carriedSet.has(pid)", JS)

    def test_the_chip_and_the_upgrade_act(self):
        self.assertIn("CARRIED — NOT IN THIS REVISION", JS)
        self.assertIn('data-f="also-revise"', JS)
        self.assertIn("/revision-scope", JS)

    def test_collect_passes_carried_rows_through_verbatim(self):
        i = JS.index("carried rows pass through VERBATIM".lower()
                     .replace("carried rows pass through verbatim",
                              "Carried rows pass through VERBATIM"))
        self.assertIn("out.panels.push(orig)", JS[i:i + 400])

    def test_the_header_states_the_scope(self):
        self.assertIn("REVISES ${spec.revision_scope.revised.length} OF", JS)

    def test_carried_rows_open_collapsed_and_rows_fold_in_general(self):
        """User 2026-08-13: carried panels are listed, not in the way —
        one head line, details folded; any row can fold by its toggle.
        Folding must HIDE, never remove — collect() reads the DOM."""
        self.assertIn('data-f="pc-toggle"', JS)
        self.assertIn("if (carriedSet.has(pid)) setCollapsed(true)", JS)
        css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
        self.assertIn(".panel-card.pc-collapsed > :not(.head) { display: none; }",
                      css)


class StageFivePins(unittest.TestCase):
    def test_the_picker_lists_bases_with_revision_counts(self):
        self.assertIn("` · ${u.family} REVISIONS`", JS)
        self.assertIn('uiGet("asmSpec", "")', JS)
        self.assertIn('baseOf(uiGet("asmSpec", ""))', JS)

    def test_the_stale_slot_states_the_choice(self):
        self.assertIn("STALE_APPROVAL", JS)
        self.assertIn("RE-RENDER ON THE WORKBENCH OR KEEP", JS)
        self.assertIn("data-keep=", JS)
        self.assertIn("/board-keeps/", JS)

    def test_provenance_chips(self):
        self.assertIn("` · FROM R${s.from_revision}`", JS)
        self.assertIn('" · KEPT"', JS)
        self.assertIn("BUILT ON R", JS)

    def test_the_arrange_room_reads_the_unit_pool(self):
        self.assertIn("candidates?scope=base", JS)
        self.assertIn("data-gate-keep", JS)

    def test_stage_four_labels_revisions(self):
        self.assertIn("· R${revOf(s)}", JS)


if __name__ == "__main__":
    unittest.main()
