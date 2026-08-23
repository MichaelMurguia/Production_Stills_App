"""Scene anchor regression (user-hit 2026-08-06): a breakdown run for
"INT_BRIEFING_ROOM_DAY_V01" drafted the crash site. The subject is now
de-slugged and matched deterministically against the slugline parse, and
the matched scenes' text is quoted into the instructions verbatim."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import autofill, insights  # noqa: E402

SCRIPT = """INT. BRIEFING ROOM - DAY

Twelve steel chairs face a chalkboard. KELLY drops a folder on the desk.

EXT. CRASH SITE - DAY

Smoking wreckage across bleached earth. A P-38 tail fin, half buried.

INT. BRIEFING ROOM - NIGHT

The chalkboard is full now. Kelly circles one number twice.
"""


class SceneAnchorTests(unittest.TestCase):
    def setUp(self):
        self._saved = insights.screenplay_text
        insights.screenplay_text = lambda: SCRIPT
        self.addCleanup(lambda: setattr(insights, "screenplay_text", self._saved))

    def test_machine_slug_matches_its_slugline(self):
        a = insights.scene_anchor("INT_BRIEFING_ROOM_DAY_V01")
        self.assertTrue(a["matched"])
        self.assertEqual(a["location"], "BRIEFING ROOM")
        self.assertEqual(a["scenes"], 2, "both briefing-room scenes ride")
        self.assertIn("Twelve steel chairs", a["text"])
        self.assertIn("The chalkboard is full now", a["text"])
        self.assertNotIn("Smoking wreckage", a["text"],
                         "the other location's scenes never leak in")

    def test_free_text_subject_matches_too(self):
        a = insights.scene_anchor("the briefing room, the morning it all starts")
        self.assertTrue(a["matched"])
        self.assertEqual(a["location"], "BRIEFING ROOM")

    def test_unrelated_subject_stays_unanchored(self):
        a = insights.scene_anchor("Kelly's design philosophy as an asset board")
        self.assertFalse(a["matched"],
                         "free-form boards keep the un-anchored path")

    def test_no_screenplay_no_anchor(self):
        insights.screenplay_text = lambda: ""
        self.assertFalse(insights.scene_anchor("BRIEFING ROOM")["matched"])

    def test_long_scenes_truncate_stated(self):
        insights.screenplay_text = lambda: (
            "INT. BRIEFING ROOM - DAY\n\n" + ("A very long line of action.\n" * 600))
        a = insights.scene_anchor("briefing room", max_chars=500)
        self.assertTrue(a["matched"])
        self.assertLess(len(a["text"]), 600)
        self.assertIn("truncated", a["text"])


class ThePickedSceneIsAPointerNotAGuess(unittest.TestCase):
    """User, 2026-08-22: "when I select it, a reference is saved to that
    page and section including the scene name."

    `scene_anchor` above answers "which scene did these words mean?" and it
    has to guess: BRIEFING ROOM is two scenes, and a board for the night
    one gets the day one riding along. When the scene was PICKED from the
    search there is nothing to guess — the pick carries the line."""

    def setUp(self):
        self._saved = insights.screenplay_text
        insights.screenplay_text = lambda: SCRIPT
        self.addCleanup(lambda: setattr(insights, "screenplay_text", self._saved))

    def test_the_pointer_quotes_one_scene_where_the_match_quotes_two(self):
        both = insights.scene_anchor("BRIEFING ROOM")
        self.assertEqual(both["scenes"], 2)

        one = insights.scene_anchor_at(8, "INT. BRIEFING ROOM - NIGHT")
        self.assertTrue(one["matched"])
        self.assertTrue(one["exact"])
        self.assertEqual(one["scenes"], 1)
        self.assertIn("The chalkboard is full now", one["text"])
        self.assertNotIn("Twelve steel chairs", one["text"],
                         "the day scene is a different board")

    def test_it_stops_at_the_next_slugline(self):
        a = insights.scene_anchor_at(0, "INT. BRIEFING ROOM - DAY")
        self.assertIn("Twelve steel chairs", a["text"])
        self.assertNotIn("Smoking wreckage", a["text"])

    def test_a_replaced_draft_refuses_rather_than_reads_the_wrong_scene(self):
        """The pointer is saved on the page and the screenplay can be
        re-uploaded under it. Reading line 8 of a different draft and
        calling it BRIEFING ROOM - NIGHT is precisely the failure the
        pointer exists to prevent, so the heading is verified."""
        a = insights.scene_anchor_at(8, "EXT. CRASH SITE - DAY")
        self.assertFalse(a["matched"])
        self.assertIn("draft changed", a["reason"])

    def test_a_line_past_the_end_refuses(self):
        a = insights.scene_anchor_at(9000, "INT. BRIEFING ROOM - DAY")
        self.assertFalse(a["matched"])
        self.assertIn("outside the draft", a["reason"])

    def test_a_missing_line_refuses_without_raising(self):
        for bad in ("", None, "not a number"):
            self.assertFalse(insights.scene_anchor_at(bad)["matched"])

    def test_no_screenplay_no_anchor(self):
        insights.screenplay_text = lambda: ""
        self.assertFalse(insights.scene_anchor_at(0, "")["matched"])

    def test_the_heading_is_optional_but_the_line_is_not(self):
        """A location pick saves no pointer, so it never reaches here — but
        a pointer without its heading still reads the line it names."""
        a = insights.scene_anchor_at(4)
        self.assertTrue(a["matched"])
        self.assertEqual(a["location"], "EXT. CRASH SITE - DAY")


class TheScanPrefersThePointer(unittest.TestCase):
    """The wiring, not the anchor: autofill takes the pointer when it has
    one and falls back to matching when it does not."""

    def setUp(self):
        self._saved = insights.screenplay_text
        insights.screenplay_text = lambda: SCRIPT
        self.addCleanup(lambda: setattr(insights, "screenplay_text", self._saved))

    def test_a_stale_pointer_stops_the_run_instead_of_drafting_blind(self):
        with self.assertRaises(autofill.AutofillError) as e:
            autofill.autofill_spec("s1", "briefing room",
                                   "CANON_EXTRACTION",
                                   scene_line=8,
                                   scene_heading="EXT. CRASH SITE - DAY")
        self.assertIn("could not be found", str(e.exception))
        self.assertIn("Search for it again", str(e.exception))

    def test_the_endpoint_forwards_both_halves_of_the_pointer(self):
        src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('body.get("scene_line", "")', src)
        self.assertIn('body.get("scene_heading", "")', src)


if __name__ == "__main__":
    unittest.main()
