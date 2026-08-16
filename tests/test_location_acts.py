"""The location list reads in acts, chronologically (user 2026-08-16:
"LOCATION list should be divided into 3 acts if they can be derived from
the screenplay, title it. If not, just call it Act I, Act II, Act III
without the title", then "chronological order and show 5 per act with an
expand button").

A screenplay that MARKS its acts gets its own divisions and its own
titles — that is the author's structure. Most features do not mark them,
so the fallback is the standard three-act split by scene position,
unnamed: `ACT I` with no title is honest, while a title we invented is a
claim about the script we cannot support."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import insights  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
SRC = (ROOT / "app/insights.py").read_text(encoding="utf-8")


def scenes(text: str):
    lines = text.splitlines()
    return lines, [{"line": i} for i, l in enumerate(lines)
                   if l.strip().startswith(("INT.", "EXT."))]


MARKED = "\n".join([
    "ACT ONE - THE FALL", "",
    "INT. SHACK - DAY", "action", "",
    "EXT. RIDGE - DAY", "action", "",
    "ACT TWO - THE LONG ROAD", "",
    "INT. TRUCK - NIGHT", "action", "",
    "EXT. CANYON - DUSK", "action", "",
    "ACT THREE - TERRA NOVA", "",
    "EXT. LAUNCH SITE - DAWN", "action", "",
])

PLAIN = "\n".join(
    f"INT. PLACE {i} - DAY\naction\n" for i in range(20))


class TheAuthorsStructureWins(unittest.TestCase):
    def test_marked_acts_keep_their_own_titles(self):
        r = insights._acts(*scenes(MARKED))
        self.assertTrue(r["derived"])
        self.assertEqual([a["roman"] for a in r["acts"]], ["I", "II", "III"])
        self.assertEqual([a["title"] for a in r["acts"]],
                         ["THE FALL", "THE LONG ROAD", "TERRA NOVA"])

    def test_each_act_owns_a_scene_range(self):
        r = insights._acts(*scenes(MARKED))
        spans = [(a["start"], a["end"]) for a in r["acts"]]
        self.assertEqual(spans, [(0, 2), (2, 4), (4, 5)])
        for a, b in zip(spans, spans[1:]):
            self.assertEqual(a[1], b[0], "no gap, no overlap")

    def test_roman_numerals_and_digits_are_read_too(self):
        for head in ("ACT I", "ACT 1", "ACT ONE"):
            body = f"{head}\n\nINT. A - DAY\nx\n\nACT II\n\nINT. B - DAY\nx\n"
            self.assertTrue(insights._acts(*scenes(body))["derived"], head)


class WithoutMarkersItSaysSoRatherThanInventing(unittest.TestCase):
    def test_the_standard_split_unnamed(self):
        r = insights._acts(*scenes(PLAIN))
        self.assertFalse(r["derived"])
        self.assertEqual([a["roman"] for a in r["acts"]], ["I", "II", "III"])
        self.assertEqual([a["title"] for a in r["acts"]], ["", "", ""])

    def test_it_is_the_conventional_quarter_half_quarter(self):
        r = insights._acts(*scenes(PLAIN))
        self.assertEqual([(a["start"], a["end"]) for a in r["acts"]],
                         [(0, 5), (5, 15), (15, 20)])

    def test_a_marker_inside_prose_is_not_a_division(self):
        body = "INT. A - DAY\nHe said ACT ONE was fine.\nx\n"
        self.assertFalse(insights._acts(*scenes(body))["derived"])

    def test_a_word_starting_with_act_is_not_a_marker(self):
        body = "ACTION MOVIE\n\nINT. A - DAY\nx\n"
        self.assertFalse(insights._acts(*scenes(body))["derived"])

    def test_an_empty_screenplay_still_returns_three_acts(self):
        r = insights._acts([], [])
        self.assertEqual(len(r["acts"]), 3)
        self.assertFalse(r["derived"])


class TheListIsChronological(unittest.TestCase):
    def test_ordered_by_first_appearance_not_by_size(self):
        """Scene COUNT answered "which location is biggest" — a different
        question from the one a location list is asked, which is where the
        story goes."""
        self.assertIn('key=lambda x: x["first_line"]', SRC)
        self.assertNotIn('key=lambda x: -x["scenes"]', SRC)

    def test_a_location_belongs_to_the_act_it_enters_the_story_in(self):
        self.assertIn('"act": act_of(g["first_line"])', SRC)
        i = SRC.index("def act_of(")
        self.assertIn('a["start"] <= i < a["end"]', SRC[i:i + 300])

    def test_the_payload_carries_the_acts_and_their_provenance(self):
        self.assertIn('"acts": act_info["acts"]', SRC)
        self.assertIn('"acts_derived": act_info["derived"]', SRC)


class FivePerActWithAnExpand(unittest.TestCase):
    def body(self):
        i = JS.index("// Grouped by ACT")
        return JS[i:i + 4200]

    def test_it_groups_on_the_acts_the_server_derived(self):
        b = self.body()
        self.assertIn("wizCov?.acts", b)
        self.assertIn("g.act === a.n", b)

    def test_the_heading_carries_the_title_only_when_there_is_one(self):
        b = self.body()
        self.assertIn("a.title ?", b, "no title, no dash")

    def test_five_shown_then_an_expand(self):
        b = self.body()
        self.assertIn("capList(locs, g.key", b)
        self.assertIn("capRow(g.key", b)
        self.assertIn("FIVE SHOWN PER ACT", b)
        # the cap itself is the app's one capping rule, not a second one
        self.assertIn("const LOC_CAP = 5;", JS)

    def test_the_head_says_where_the_acts_came_from(self):
        b = self.body()
        self.assertIn("ACTS FROM THE SCREENPLAY", b)
        self.assertIn("STANDARD THREE-ACT SPLIT", b)

    def test_a_location_with_no_scene_is_said_outright(self):
        """It has no act because it has no scene. Filing it into one would
        be inventing a position in the story."""
        b = self.body()
        self.assertIn("NOT IN A SLUGLINE", b)

    def test_the_environment_is_still_reachable_per_row(self):
        """Grouping moved to acts; inheritance is still a per-row fact."""
        b = self.body()
        self.assertIn("loc-reassign", b)
        self.assertIn("saveAnalysis(a)", b)


if __name__ == "__main__":
    unittest.main()
