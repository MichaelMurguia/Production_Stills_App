"""A3 — the pass that read the scene names the shot.

The research pass already writes each panel's purpose and required
objects. It is the only pass that has read the screenplay, so it is the
one that should choose the framing — and choosing it there makes the
decision inspectable before the spend rather than inferable from the
picture afterwards, which is the whole failure this feature exists to
end.

A lookup keyed on intent cannot do it, and that is worth a test because
it was the first design: a surfer at 400mm and a race car at 24mm are
both "action" and land on opposite rows.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import autofill  # noqa: E402
from app import camera_recipes as rec  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def instr():
    return autofill._instructions("a salt pan", "CANON_EXTRACTION", [])


class TheMenuIsInThePrompt(unittest.TestCase):
    def test_every_row_is_offered_with_its_optics(self):
        t = instr()
        for r in rec.recipes():
            self.assertIn(r["key"], t)
            self.assertIn(r["focal"], t)

    def test_the_panel_shape_asks_for_it(self):
        t = instr()
        self.assertIn('"camera_recipe"', t)
        self.assertIn('"camera_recipe_why"', t)
        self.assertIn('"camera_recipe_mods"', t)

    def test_it_says_not_to_match_a_genre_to_a_row_name(self):
        """The design that does not work, ruled out in the prompt itself."""
        self.assertIn("never by matching the", instr())

    def test_it_removes_the_reason_a_framing_gets_rejected(self):
        """A required object can be PRESENT without being SHARP — a
        character at 1.5m on a wide lens keeps the hull, the ramp and the
        figures behind her in frame, softer. Without saying so, a model
        counts five required objects and picks a deep-focus wide every
        time."""
        t = instr()
        self.assertIn("PRESENT without being SHARP", t)
        self.assertIn("Do not reject a row because the", t)

    def test_modifiers_are_asked_for_as_departures_only(self):
        self.assertIn("ONLY where this shot departs", instr())

    def test_a_menu_never_offers_a_contradiction(self):
        """Where a grammar is chosen the list is its sanctioned rows —
        a menu that includes a contradiction is one that will eventually
        be used to pick one."""
        src = (ROOT / "app/autofill.py").read_text(encoding="utf-8")
        self.assertIn("recipes.sanctioned(None)", src)

    def test_no_library_means_no_rule_rather_than_an_empty_menu(self):
        import app.paths as paths
        was = paths.ROOT
        try:
            paths.ROOT = ROOT / "does-not-exist"
            self.assertNotIn("Name the FRAMING", instr())
        finally:
            paths.ROOT = was


class TheDraftIsCoercedNotTrusted(unittest.TestCase):
    def draft(self, panel):
        d = {"panels": [{"id": "P01", "title": "t", "purpose": "p",
                         "required_objects": ["x"], "allocation_percent": 100,
                         **panel}],
             "evidence_ledger": [{"panel_id": "P01", "object": "x",
                                  "evidence_class": "SCRIPT_EXPLICIT",
                                  "status": "PASS", "source": "line"}]}
        return autofill._coerce(d, "SB-X", "CANON_EXTRACTION")["panels"][0]

    def test_a_named_row_survives(self):
        p = self.draft({"camera_recipe": "intimate-close-up",
                        "camera_recipe_why": "the face carries the beat"})
        self.assertEqual(p["camera_recipe"], "intimate-close-up")
        self.assertEqual(p["camera_recipe_why"], "the face carries the beat")

    def test_an_unknown_row_is_dropped_so_the_grammar_default_takes_over(self):
        """Dropped rather than persisted: an unknown id resolves to
        nothing, which puts the panel back to having no optics at all —
        the original failure. Empty inherits a real framing."""
        p = self.draft({"camera_recipe": "cinematic-vibes"})
        self.assertEqual(p["camera_recipe"], "")
        self.assertEqual(
            rec.resolve({**p, "cinematography": "cine-subjective-poetic"})["key"],
            "subjective-poetic-character")

    def test_modifiers_are_validated_per_axis(self):
        p = self.draft({"camera_recipe": "intimate-close-up",
                        "camera_recipe_mods": {"camera-height": "0.3–0.8m",
                                               "camera-height-2": "x",
                                               "camera-angle": "Sideways"}})
        self.assertEqual(p["camera_recipe_mods"], {"camera-height": "0.3–0.8m"})

    def test_modifiers_without_a_row_are_dropped(self):
        """A delta with nothing to depart from is not a delta."""
        p = self.draft({"camera_recipe_mods": {"camera-height": "0.3–0.8m"}})
        self.assertEqual(p["camera_recipe_mods"], {})

    def test_a_draft_that_names_nothing_still_coerces(self):
        p = self.draft({})
        self.assertEqual(p["camera_recipe"], "")
        self.assertEqual(p["camera_recipe_mods"], {})


class ADisagreementIsStatedNotResolved(unittest.TestCase):
    def test_a_sanctioned_row_says_nothing(self):
        self.assertEqual(rec.conflict({"cinematography": "cine-subjective-poetic"}), "")
        self.assertEqual(rec.conflict({}), "")
        self.assertEqual(rec.conflict({"camera_recipe": "NONE"}), "")

    def test_a_row_that_fights_its_grammar_is_named_along_with_the_alternatives(self):
        note = rec.conflict({"cinematography": "cine-subjective-poetic",
                             "camera_recipe": "epic-environmental-wide"})
        self.assertIn("Epic environmental wide", note)
        self.assertIn("Subjective / Poetic", note)
        self.assertIn("Subjective / poetic character", note)

    def test_it_is_a_statement_and_not_a_refusal(self):
        """A director wanting an epic wide under a subjective grammar is
        making a choice. The app knowing the two disagree and saying
        nothing is how a 24mm sat under a selective-focus grammar for two
        days — but refusing it would be worse."""
        note = rec.conflict({"cinematography": "cine-subjective-poetic",
                             "camera_recipe": "epic-environmental-wide"})
        self.assertIn("a choice, not an error", note)

    def test_with_no_grammar_nothing_can_conflict(self):
        self.assertEqual(rec.conflict({"camera_recipe": "epic-environmental-wide"}), "")


class TheDirectorCanReadTheReasoning(unittest.TestCase):
    def test_the_note_carries_both_facts(self):
        i = JS.index("function framingNote")
        seg = " ".join(JS[i:i + 1200].split())
        self.assertIn("camera_recipe_why", seg)
        self.assertIn("pull against each other", seg)

    def test_it_redraws_when_either_select_changes(self):
        i = JS.index("function wireCameraRow")
        seg = " ".join(JS[i:i + 1600].split())
        self.assertIn('fram.addEventListener("change", note)', seg)

    def test_the_note_is_never_amber(self):
        """Amber marks the current stage, the one primary action, and
        focus. A disagreement the director is allowed to make is none of
        those."""
        css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
        block = css.split(".cam-field > .cam-note {")[1].split("}")[0]
        self.assertIn("var(--ink-faint)", block)
        self.assertNotIn("--accent", block)
        self.assertNotIn("--bad", block)


if __name__ == "__main__":
    unittest.main()
