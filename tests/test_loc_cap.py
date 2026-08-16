"""A long list shows its head and states its tail (SCAN_CONSOLIDATION §3).

105 locations printed in full put the two sections below them out of
reach. Five rows per group, then one row saying how many more — and a
search must ignore the cap entirely, because a list that hides matches
behind an Expand is a list that lies.

The capping rule lives in app.js, so these assert the RULE against a
faithful port plus the source that implements it — the same shape
tests/test_palette_order.py uses for the ramp ordering.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

CAP = 5


def cap_list(items, key, expanded, cap=CAP, searching=False):
    """Port of capList()."""
    if searching or len(items) <= cap or key in expanded:
        return {"shown": list(items), "hidden": 0, "capped": False}
    return {"shown": list(items[:cap]), "hidden": len(items) - cap, "capped": True}


class TheRule(unittest.TestCase):
    def test_a_group_of_five_renders_no_expand_row(self):
        out = cap_list([f"L{i}" for i in range(5)], "G", set())
        self.assertEqual(out["hidden"], 0)
        self.assertFalse(out["capped"])
        self.assertEqual(len(out["shown"]), 5)

    def test_a_group_of_six_hides_exactly_one(self):
        out = cap_list([f"L{i}" for i in range(6)], "G", set())
        self.assertEqual(out["hidden"], 1)
        self.assertEqual(len(out["shown"]), 5)

    def test_a_big_group_states_its_whole_tail(self):
        out = cap_list([f"L{i}" for i in range(40)], "G", set())
        self.assertEqual(out["hidden"], 35)

    def test_a_search_lifts_the_cap_entirely(self):
        """Every match, in every group, however many."""
        out = cap_list([f"L{i}" for i in range(40)], "G", set(), searching=True)
        self.assertEqual(len(out["shown"]), 40)
        self.assertEqual(out["hidden"], 0)

    def test_expanding_one_group_does_not_expand_its_neighbour(self):
        expanded = {"POST-FALL EARTH / WILDERNESS"}
        big = [f"L{i}" for i in range(40)]
        mine = cap_list(big, "POST-FALL EARTH / WILDERNESS", expanded)
        theirs = cap_list(big, "RESISTANCE ENCLAVES", expanded)
        self.assertEqual(len(mine["shown"]), 40)
        self.assertEqual(len(theirs["shown"]), CAP)

    def test_collapsing_restores_the_cap(self):
        big = [f"L{i}" for i in range(40)]
        self.assertEqual(len(cap_list(big, "G", {"G"})["shown"]), 40)
        self.assertEqual(len(cap_list(big, "G", set())["shown"]), CAP)


class SourceImplementsTheRule(unittest.TestCase):
    def cap_fn(self) -> str:
        i = JS.index("const capList =")
        return JS[i:JS.index("const wireCapRows", i)]

    def test_the_cap_is_five(self):
        self.assertIn("const LOC_CAP = 5;", JS)

    def test_search_short_circuits_the_cap(self):
        body = self.cap_fn()
        self.assertIn("searching", body)
        self.assertLess(body.index("searching"), body.index("items.slice"),
                        "the search escape must come before any slicing")

    def test_expansion_state_survives_a_re_render(self):
        """Held beside expandedWorlds, outside the render, or expanding a
        group would collapse again on the next redraw."""
        self.assertIn("const expandedGroups = new Set();", JS)
        i = JS.index("const expandedGroups")
        j = JS.index("const renderWizLocs")
        self.assertLess(i, j, "the Set must outlive the list that uses it")

    def test_the_expand_row_says_how_many_more(self):
        self.assertIn("Expand — ${hidden} more", JS)
        self.assertIn('"Collapse"', JS)

    def test_the_group_header_states_the_cap_while_collapsed(self):
        self.assertIn("SHOWING ${cut.shown.length}", JS)
        # the grouping moved from environment to ACT (user 2026-08-16);
        # the cap and the way it states itself are unchanged
        self.assertIn("FIVE SHOWN PER ACT", JS)

    def test_one_helper_serves_both_lists(self):
        """The locations table and the modal's inheriting list must not
        drift apart — §3 says one helper."""
        self.assertEqual(JS.count("const capList ="), 1)
        self.assertGreaterEqual(JS.count("capList("), 2,
                                "both the locations table and the modal call it")
        self.assertIn("capRow(KEY, cut.hidden)", JS)      # the modal's list


class EnvironmentRoundTrip(unittest.TestCase):
    """§2's save must not lose what the modal does not show."""

    def modal_fn(self) -> str:
        i = JS.index("async function openEnvModal")
        return JS[i:JS.index("\n  const renderWizLocs", i)]

    def test_it_spreads_the_existing_record(self):
        """keywords and locations are not fields in the room, so the save
        must carry them through rather than rebuild the object."""
        body = self.modal_fn()
        self.assertIn("{ ...list[idx]", body)

    def test_a_proposed_environment_is_confirmed_by_saving(self):
        body = self.modal_fn()
        self.assertIn('if (next.status === "PROPOSED") delete next.status;', body)

    def test_empty_light_and_material_are_dropped_not_written_blank(self):
        body = self.modal_fn()
        self.assertIn("delete next.light", body)
        self.assertIn("delete next.material", body)

    def test_writes_still_go_through_patch_envs(self):
        """All writes go patchEnvs -> saveAnalysis -> renderWorlds."""
        body = self.modal_fn()
        self.assertIn("patchEnvs(list =>", body)
        self.assertNotIn("saveAnalysis(", body,
                         "the modal must not write the analysis itself")

    def test_the_verdict_acts_stay_on_the_card(self):
        """A verdict happens where the proposal is — CONFIRM / DROP are
        not in the room."""
        body = self.modal_fn()
        for verb in ("CONFIRM", "DROP", 'data-f="confirm"', 'data-f="drop"'):
            self.assertNotIn(verb, body)
        self.assertIn('data-f="confirm"', JS, "they still exist on the card")

    def test_the_room_states_the_blast_radius(self):
        body = self.modal_fn()
        self.assertIn("EDITING THE RULES REPAINTS ALL", body)

    def test_no_language_renders_a_stated_blank_not_an_empty_ramp(self):
        body = self.modal_fn()
        self.assertIn("— NO DESIGN LANGUAGE ASSIGNED", body)

    def test_the_language_link_is_an_inference_and_says_so(self):
        """There is no stored env -> language field; the modal must not
        claim an assignment the data does not hold."""
        self.assertIn("const languageFor =", JS)
        self.assertIn("this is an", JS)
        self.assertIn("DESIGN LANGUAGE — WHERE ITS PALETTE COMES FROM", JS)


if __name__ == "__main__":
    unittest.main()
