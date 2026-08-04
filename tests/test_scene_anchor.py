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

from app import insights  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
