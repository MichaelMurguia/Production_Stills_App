"""A required object names a subject the way the SCRIPT does (user-caught
2026-08-16: "the script specifically mentions Sal — why would the required
objects not pick up Sal Craft? I had to add manually").

The matcher asked whether the phrase contained the cast card's WHOLE name.
`Sal inside the cryochamber` contains "Sal" and not "Sal Craft", so it
failed — and so did every other multi-word character in the production:
Kyra McGuire, Tom McGuire, Charlie Stanner, John Stanner. Only a card
named with a single token, like GT40, ever matched.

On the user's own breakdown the score was 0 of 24. The failure was silent:
no REF marker on the tile, and nothing anywhere saying why."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

# The user's real cast, and their real breakdown's objects.
CAST = [
    {"name": "SAL CRAFT", "ref_ids": [1, 2]},
    {"name": "KYRA McGUIRE", "ref_ids": [1]},
    {"name": "TOM McGUIRE", "ref_ids": []},          # cast, but no photos
    {"name": "GT40", "ref_ids": [3]},
    {"name": "CHARLIE STANNER", "ref_ids": [1]},
    {"name": "JOHN STANNER", "ref_ids": [1]},
]


def words(n):
    return [w for w in re.split(r"[^a-z0-9]+", n.lower()) if len(w) >= 3]


def word_in(needle, hay):
    return bool(needle) and re.search(
        rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", hay) is not None


def subject_for(o, cast=CAST):
    """The port of app.js's subjectFor — kept in step by the source
    assertions at the bottom of this file."""
    have = [s for s in cast if s["ref_ids"]]
    exact = next((s for s in have
                  if word_in(s["name"].lower(), o) or s["name"].lower() in o), None)
    if exact:
        return exact["name"]
    named = [s for s in cast if any(word_in(w, o) for w in words(s["name"]))]
    if len(named) != 1:
        return None
    return named[0]["name"] if named[0]["ref_ids"] else None


class TheScriptsWordingFindsTheCard(unittest.TestCase):
    def test_a_first_name_in_a_phrase_finds_the_card(self):
        for o in ("sal inside the cryochamber",
                  "restraints across sal's chest, arms, and legs",
                  "sal's fogging breath",
                  "airlock hatch behind sal",
                  "frost-covered sal"):
            self.assertEqual(subject_for(o), "SAL CRAFT", o)

    def test_a_possessive_is_still_the_name(self):
        """The apostrophe is a word boundary, so "Sal's" contains "sal"."""
        self.assertEqual(subject_for("rime covering sal's eyes"), "SAL CRAFT")

    def test_a_single_token_card_still_works(self):
        self.assertEqual(subject_for("gt40 cockpit controls"), "GT40")

    def test_a_shared_surname_is_ambiguous(self):
        self.assertEqual(subject_for("stanner drive housing"), None,
                         "two Stanners — ambiguous, so it refuses")
        self.assertEqual(subject_for("charlie in the shotgun seat"),
                         "CHARLIE STANNER")

    def test_ambiguity_refuses_rather_than_guessing(self):
        """"McGuire" belongs to two characters. Picking one would attach
        the wrong face to a panel, which is worse than no marker — and it
        is ambiguous whether or not both have been photographed, so the
        whole cast is what decides it, not the photographed part of it."""
        self.assertIsNone(subject_for("mcguire steps forward"))
        self.assertEqual(subject_for("kyra, late 20s"), "KYRA McGUIRE",
                         "the given name is still unambiguous")

    def test_a_cast_card_with_no_photos_is_not_a_reference(self):
        """Tom is cast but has no images — there is nothing to offer, and
        claiming otherwise would be a marker that leads nowhere."""
        self.assertIsNone(subject_for("tom stepping from shadow"))

    def test_an_unrelated_object_matches_nothing(self):
        for o in ("whole cryochamber", "curved glass door",
                  "vapor leaking from the seals", "freezing gas"):
            self.assertIsNone(subject_for(o), o)

    def test_the_old_rule_would_have_found_none_of_them(self):
        """The regression this pins: 0 of 24 on the user's own breakdown."""
        def old(o):
            return next((s["name"] for s in CAST if s["ref_ids"]
                         and (s["name"].lower() in o or o in s["name"].lower())), None)
        sal = ["sal inside the cryochamber", "sal's eyes", "frost-covered sal",
               "sweat beads on sal's face"]
        self.assertEqual([old(o) for o in sal], [None] * 4)
        self.assertEqual([subject_for(o) for o in sal], ["SAL CRAFT"] * 4)


class TheSourceKeepsOneMatcher(unittest.TestCase):
    def test_word_in_is_defined_once(self):
        """It was copied — the locations table had one and the required-
        object matcher grew another. Two copies of a matching rule is how
        two surfaces start disagreeing about what counts as a match."""
        self.assertEqual(JS.count("const wordIn = (needle, hay)"), 1)
        self.assertIn("\nconst wordIn = (needle, hay)", JS,
                      "at module scope, so both callers see it")

    def test_the_matcher_prefers_the_whole_name(self):
        i = JS.index("const subjectFor = (o) =>")
        seg = JS[i:i + 1100]
        self.assertIn("const exact = withRefs.find", seg)
        self.assertLess(seg.index("exact"), seg.index("named"))

    def test_it_requires_photos_and_refuses_ambiguity(self):
        i = JS.index("const subjectFor = (o) =>")
        seg = JS[i:i + 1100]
        self.assertIn("(s.ref_ids || []).length", seg)
        self.assertIn("if (named.length !== 1) return null", seg)
        self.assertIn("named[0].ref_ids", seg,
                      "one candidate, but only if there is a photo to show")

    def test_short_words_are_not_matched_on(self):
        i = JS.index("const nameWords = n =>")
        self.assertIn("w.length >= 3", JS[i:i + 200])


if __name__ == "__main__":
    unittest.main()
