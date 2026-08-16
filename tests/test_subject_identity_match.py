"""The SUBJECT IDENTITIES block missed the same way the workbench did.

Fixed in the workbench on 2026-08-16 (see test_required_object_refs), a
THIRD copy of the same narrow rule survived in generate.py — and this copy
is the more damaging one. The workbench's version decides whether a `REF`
marker is offered; this one decides whether a character's canon identity
reaches the image model at all.

`Sal inside the cryochamber` does not contain `sal craft`, so Sal's
identity never rode the prompt. A render with no identity text AND no
attached plate invents the person from nothing, which is how a dark-haired
man in his forties comes back white-haired and bearded (user 2026-08-16:
"Sal has a specific likeness referenced with images ... that is not Sal").

One rule that is NOT shared with the workbench, deliberately: photos are
not required here. Identity text is worth sending on its own."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.generate import subjects_for_object  # noqa: E402

CAST = [
    {"id": "S1", "name": "SAL CRAFT", "kind": "CHARACTER",
     "subtitle": "AUTHORITARIAN. SURVIVOR. WARDEN.",
     "traits": ["Mid-40s before the Fall; later appears in his 50s."]},
    {"id": "S2", "name": "KYRA McGUIRE", "kind": "CHARACTER",
     "subtitle": "", "traits": ["Late 20s."]},
    {"id": "S3", "name": "TOM McGUIRE", "kind": "CHARACTER",
     "subtitle": "", "traits": ["Calm, edged with steel."]},
    {"id": "S4", "name": "GT40", "kind": "VEHICLE", "subtitle": "", "traits": ["Blue."]},
    {"id": "S5", "name": "CRYOCHAMBER", "kind": "PROP", "subtitle": "", "traits": []},
]


def names_of(o):
    return [s["name"] for s in subjects_for_object(o, CAST)]


def name_of(o):
    """The single character a phrase is about, for the cases where exactly
    one is expected. Props with no identity text never appear."""
    n = [x for x in names_of(o)]
    return n[0] if len(n) == 1 else (None if not n else n)


class TheScriptsWordingReachesTheIdentity(unittest.TestCase):
    def test_a_first_name_in_a_phrase_finds_the_character(self):
        for o in ("Sal inside the cryochamber",
                  "restraints across Sal's chest, arms, and legs",
                  "frost-covered Sal",
                  "sweat beads on Sal's face"):
            self.assertEqual(name_of(o), "SAL CRAFT", o)

    def test_the_old_rule_would_have_found_none_of_them(self):
        """The regression this pins: the identity block was empty for every
        multi-word character in the production."""
        def old(o):
            oc = o.casefold()
            return next((s["name"] for s in CAST
                         if (s["name"].casefold() in oc or oc in s["name"].casefold())
                         and (s.get("traits") or s.get("subtitle"))), None)
        objs = ["Sal inside the cryochamber", "Tom stepping from shadow",
                "Kyra in the exoskeleton"]
        self.assertEqual([old(o) for o in objs], [None, None, None])
        self.assertEqual([name_of(o) for o in objs],
                         ["SAL CRAFT", "TOM McGUIRE", "KYRA McGUIRE"])

    def test_the_whole_name_still_wins(self):
        self.assertEqual(name_of("SAL CRAFT"), "SAL CRAFT")
        self.assertEqual(name_of("gt40 cockpit"), "GT40")

    def test_a_shared_surname_refuses_rather_than_guessing(self):
        """Two McGuires. Picking one would put the wrong person's canon
        traits into the prompt, which is worse than sending none."""
        self.assertIsNone(name_of("McGuire steps forward"))

    def test_a_card_with_no_identity_text_contributes_nothing(self):
        """CRYOCHAMBER is a real subject with no traits and no subtitle —
        there is nothing to say about it, so it must not produce an empty
        identity line."""
        self.assertEqual(names_of("the whole cryochamber"), [])

    def test_a_phrase_naming_two_subjects_carries_both(self):
        """A required object is a phrase, not a token: "Sal inside the
        cryochamber" is about both, and the workbench's pick-exactly-one
        rule would drop Sal for being ambiguous. Sending neither identity is
        the worst of the three answers."""
        CAST2 = CAST + [{"id": "S6", "name": "CRYOCHAMBER", "kind": "PROP",
                         "subtitle": "Curved glass. Frost-rimed.", "traits": []}]
        got = [s["name"] for s in subjects_for_object(
            "Sal inside the cryochamber", CAST2)]
        self.assertEqual(sorted(got), ["CRYOCHAMBER", "SAL CRAFT"])

    def test_an_unrelated_object_matches_nothing(self):
        for o in ("curved glass door", "freezing gas", "airlock hatch"):
            self.assertIsNone(name_of(o), o)

    def test_short_words_are_not_matched_on(self):
        """A two-letter fragment of a name would match half the script."""
        self.assertIsNone(name_of("a to b"))


class TheIdentityBlockUsesIt(unittest.TestCase):
    def test_compile_goes_through_the_shared_matcher(self):
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        i = src.index('lines += ["", "SUBJECT IDENTITIES')
        seg = src[max(0, i - 900):i]
        self.assertIn("subjects_for_object(str(obj), subjects)", seg)
        self.assertNotIn("(n in o or o in n)", seg,
                         "the narrow rule this replaced")


if __name__ == "__main__":
    unittest.main()
