"""Naming the acts is its own small call (user 2026-08-16: "No Act
Titles", reported on an analysis that predates the field).

A full re-scan would have filled it — and overwritten eight design
languages, five environments and forty-four subjects of curated work to
set one key. Naming the acts is one small read of the screenplay, so it
gets its own call and merges one field."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import autofill, paths, store, wizard  # noqa: E402

CURATED = {
    "logline": "A gifted young builder.",
    "design_worlds": [{"name": "RESISTANCE"}, {"name": "GRM ORDER"}],
    "environments": [{"name": "POST-FALL EARTH", "locations": ["SHACK"]}],
    "subjects": [{"name": "JAKE"}, {"name": "CHARLIE"}],
    "key_locations": ["SHACK", "RIDGE"],
    "unresolved": ["what colour is the GT40"],
}


class NamingActsTouchesNothingElse(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-acts-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR,
                       paths.ACTIVE_PROJECT_FILE, paths.SETTINGS,
                       paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        store.save_wizard_analysis(dict(CURATED))
        self._draft = autofill._draft
        self._bytes = autofill._screenplay_bytes
        autofill._screenplay_bytes = lambda: (b"INT. SHACK - DAY", "text/plain")

    def tearDown(self):
        autofill._draft = self._draft
        autofill._screenplay_bytes = self._bytes
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def answer(self, payload):
        autofill._draft = lambda *a, **k: (payload, "test-model")

    def test_the_curated_analysis_survives(self):
        """The whole reason this is not a re-scan."""
        self.answer({"acts": [
            {"n": 1, "title": "THE FALL", "turn": "the crash"},
            {"n": 2, "title": "THE LONG ROAD", "turn": "the betrayal"},
            {"n": 3, "title": "TERRA NOVA", "turn": "the launch"}]})
        wizard.name_acts("gemini")
        after = store.load_wizard_analysis()
        for k, v in CURATED.items():
            self.assertEqual(after[k], v, f"{k} was rewritten")

    def test_the_names_land(self):
        self.answer({"acts": [
            {"n": 1, "title": "the fall", "turn": "the crash"},
            {"n": 2, "title": "The Long Road", "turn": "x"},
            {"n": 3, "title": "TERRA NOVA", "turn": "y"}]})
        r = wizard.name_acts("gemini")
        self.assertEqual([a["title"] for a in r["acts"]],
                         ["THE FALL", "THE LONG ROAD", "TERRA NOVA"],
                         "uppercased, because the heading is Courier caps")
        self.assertEqual(store.load_wizard_analysis()["acts"], r["acts"])

    def test_the_turn_is_kept_so_the_reading_can_be_checked(self):
        self.answer({"acts": [{"n": 1, "title": "THE FALL",
                               "turn": "Jake watches the rocket break up"}]})
        r = wizard.name_acts("gemini")
        self.assertIn("rocket", r["acts"][0]["turn"])

    def test_which_model_named_them_is_recorded(self):
        self.answer({"acts": [{"n": 1, "title": "THE FALL"}]})
        wizard.name_acts("gemini")
        self.assertEqual(store.load_wizard_analysis()["acts_named_by"],
                         "test-model")

    def test_an_empty_answer_refuses_rather_than_writing_nothing(self):
        self.answer({"acts": []})
        with self.assertRaises(autofill.AutofillError):
            wizard.name_acts("gemini")
        self.assertNotIn("acts", store.load_wizard_analysis())

    def test_titleless_entries_are_dropped_not_stored_blank(self):
        self.answer({"acts": [{"n": 1, "title": "  "},
                              {"n": 2, "title": "THE ROAD"}]})
        r = wizard.name_acts("gemini")
        self.assertEqual([a["title"] for a in r["acts"]], ["THE ROAD"])

    def test_it_asks_for_the_reading_not_the_locations(self):
        src = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
        i = src.index("ACTS_SCHEMA_NOTE")
        seg = src[i:i + 1200]
        self.assertIn("not a summary of its locations", seg)
        self.assertIn("whether or", seg)
        self.assertIn("not it prints ACT headings", seg)
        self.assertIn('"turn"', seg)


class TheAffordanceOnlyAppearsWhenItIsNeeded(unittest.TestCase):
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")

    def test_the_route_exists_and_refuses_cleanly(self):
        self.assertIn('@app.post("/api/wizard/acts")', self.MAIN)
        i = self.MAIN.index('@app.post("/api/wizard/acts")')
        self.assertIn("HTTPException(422", self.MAIN[i:i + 700])

    def test_the_button_is_absent_once_the_acts_have_names(self):
        i = self.JS.index("data-f=\"name-acts\"")
        seg = self.JS[i - 400:i]
        self.assertIn("acts.some(a => a.title)", seg)
        self.assertIn("wizCov?.acts_derived", seg,
                      "a screenplay that prints its own headings needs nothing")

    def test_it_says_what_it_will_not_touch(self):
        i = self.JS.index("data-f=\"name-acts\"")
        seg = self.JS[i:i + 400]
        self.assertIn("are not touched", seg)

    def test_it_reports_while_it_runs(self):
        i = self.JS.index("nameBtn.onclick")
        seg = self.JS[i:i + 900]
        self.assertIn("nameBtn.disabled = true", seg)
        self.assertIn("Reading the screenplay…", seg)
        self.assertIn("nameBtn.disabled = false", seg, "and comes back on failure")

    def test_one_control_two_presentations(self):
        """D3/R7: the control becomes `Rename the acts` once names exist."""
        self.assertIn('acts.some(a => a.title) ? "Rename the acts" : "Name the acts"',
                      self.JS)


class ANameSurvivesAndCanBeDisagreedWith(unittest.TestCase):
    """Finishing the acts (user 2026-08-16). A reading is a claim, so it
    has to survive a re-run and it has to be arguable."""

    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def test_a_re_scan_does_not_drop_the_names(self):
        """merge_analysis starts from the FRESH read, so a run about
        design languages would have taken the act names with it."""
        merged = wizard.merge_analysis(
            {"design_worlds": [{"name": "W"}],
             "acts": [{"n": 1, "title": "THE FALL", "turn": "the crash"}],
             "acts_named_by": "test-model"},
            {"design_worlds": [{"name": "W"}]})
        self.assertEqual(merged["acts"][0]["title"], "THE FALL")
        self.assertEqual(merged["acts_named_by"], "test-model")

    def test_a_fresh_reading_still_wins(self):
        merged = wizard.merge_analysis(
            {"acts": [{"n": 1, "title": "OLD"}]},
            {"acts": [{"n": 1, "title": "NEW"}]})
        self.assertEqual(merged["acts"][0]["title"], "NEW")

    def test_the_heading_can_be_renamed(self):
        self.assertIn("loc-act-name", self.JS)
        i = self.JS.index('$$(".loc-act-name", secHost)')
        seg = self.JS[i:i + 900]
        self.assertIn("askText(`Act ${n}`", seg)
        self.assertIn("saveAnalysis(a)", seg)
        self.assertIn("e.stopPropagation()", seg, "renaming is not expanding")
        self.assertIn(".filter(x => x.title)", seg,
                      "clearing a name returns it to an unnamed act")

    def test_the_beat_is_printed_not_hidden_in_a_tooltip(self):
        """D2 (2026-08-18): the turn is the evidence that makes an inferred
        act name checkable, and it was a bare `title` on the group — the
        evidence, hidden. A tooltip nobody knows exists is not
        documentation."""
        self.assertIn("loc-turn mono\">TURNS ON —", self.JS)
        self.assertNotIn("Turns on: ", self.JS)


if __name__ == "__main__":
    unittest.main()
