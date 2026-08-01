"""Re-run merge semantics (Gap 5 rulings): confirmed work survives by name,
fresh finds arrive PROPOSED, answered questions are never touched."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.wizard import merge_analysis  # noqa: E402


class MergeAnalysisTests(unittest.TestCase):
    def test_first_run_passes_through(self):
        fresh = {"design_worlds": [{"name": "A"}], "logline": "x"}
        self.assertIs(merge_analysis({}, fresh), fresh)

    def test_confirmed_worlds_survive_by_name_case_insensitive(self):
        prior = {"design_worlds": [
            {"name": "GRM Order", "keywords": ["grm"], "description": "mine"}]}
        fresh = {"design_worlds": [
            {"name": "GRM ORDER", "description": "model rewrite"},
            {"name": "Skinners"}]}
        out = merge_analysis(prior, fresh)
        names = [w["name"] for w in out["design_worlds"]]
        self.assertEqual(names, ["GRM Order", "Skinners"])
        self.assertEqual(out["design_worlds"][0]["description"], "mine",
                         "the user's edits must not be clobbered by the fresh read")
        self.assertEqual(out["design_worlds"][1].get("status"), "PROPOSED")

    def test_old_proposals_are_rederived_not_preserved(self):
        prior = {"design_worlds": [{"name": "Ghost", "status": "PROPOSED"}]}
        fresh = {"design_worlds": []}
        out = merge_analysis(prior, fresh)
        self.assertEqual(out["design_worlds"], [])

    def test_environments_merge_with_location_assignments(self):
        prior = {"environments": [
            {"name": "FOREST", "locations": ["SHACK", "MEADOW"]}]}
        fresh = {"environments": [
            {"name": "FOREST", "locations": ["SHACK"]},
            {"name": "DESERT", "locations": ["CANYON"]}]}
        out = merge_analysis(prior, fresh)
        forest = out["environments"][0]
        self.assertEqual(forest["locations"], ["SHACK", "MEADOW"],
                         "confirmed assignments survive verbatim")
        self.assertEqual(out["environments"][1].get("status"), "PROPOSED")

    def test_answers_carry_over(self):
        prior = {"question_answers": {"Q?": {"answer": "A"}},
                 "design_worlds": []}
        fresh = {"design_worlds": [], "unresolved": ["Q?", "New?"]}
        out = merge_analysis(prior, fresh)
        self.assertEqual(out["question_answers"], {"Q?": {"answer": "A"}})


if __name__ == "__main__":
    unittest.main()
