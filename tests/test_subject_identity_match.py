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
    # THE card that makes the case a case. The fixture carried the
    # un-possessed, un-hyphenated "CRYOCHAMBER" instead, so `sal` was never
    # a shared word and the suite stayed green over a bug the user had
    # caught in the field (adversarial review, round 2). A fixture for a
    # cross-language fix carries the reporting user's real data, never a
    # paraphrase of it.
    {"id": "S6", "name": "SAL'S CRYO-CHAMBER", "kind": "PROP",
     "subtitle": "Curved glass, frost-rimed.", "traits": []},
    # A group whose name is mostly stopwords — without the stoplist every
    # object containing "the" matched it.
    {"id": "S7", "name": "The Beacon", "kind": "PROP", "subtitle": "",
     "traits": ["brass, cracked lens"]},
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
            self.assertIn("SAL CRAFT", names_of(o), o)

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
        for o, who in zip(objs, ["SAL CRAFT", "TOM McGUIRE", "KYRA McGUIRE"]):
            self.assertIn(who, names_of(o), o)

    def test_the_whole_name_still_wins(self):
        """The full name is the strongest signal. Sal's prop rides along
        because the phrase names him and it is his — see
        test_a_person_and_their_prop_are_not_an_ambiguity."""
        self.assertIn("SAL CRAFT", names_of("SAL CRAFT"))
        self.assertEqual(name_of("gt40 cockpit"), "GT40")

    def test_a_shared_surname_refuses_rather_than_guessing(self):
        """Two McGuires. Picking one would put the wrong person's canon
        traits into the prompt, which is worse than sending none."""
        self.assertIsNone(name_of("McGuire steps forward"))

    def test_a_card_with_no_identity_text_contributes_nothing(self):
        """CRYOCHAMBER is a real subject with no traits and no subtitle —
        there is nothing to say about it, so it must not produce an empty
        identity line. SAL'S CRYO-CHAMBER, which DOES carry identity text,
        legitimately matches the same phrase."""
        self.assertNotIn("CRYOCHAMBER", names_of("the whole cryochamber"))

    def test_a_phrase_naming_two_subjects_carries_both(self):
        """A required object is a phrase, not a token: "Sal inside the
        cryochamber" is about both, and the workbench's pick-exactly-one
        rule would drop Sal for being ambiguous. Sending neither identity is
        the worst of the three answers."""
        got = names_of("Sal inside the cryochamber")
        self.assertIn("SAL CRAFT", got)
        self.assertIn("SAL'S CRYO-CHAMBER", got)

    def test_an_unrelated_object_matches_nothing(self):
        for o in ("curved glass door", "freezing gas", "airlock hatch"):
            self.assertIsNone(name_of(o), o)

    def test_short_words_are_not_matched_on(self):
        """A two-letter fragment of a name would match half the script."""
        self.assertIsNone(name_of("a to b"))


class TheFieldReportedCases(unittest.TestCase):
    """Every one of these was caught by the user or the reviewer, against
    this exact cast."""

    def test_a_possessive_still_finds_the_person(self):
        """"Sal's eyes" returned NOTHING while `sal` was treated as shared
        between the man and his cryo-chamber. A missing identity renders a
        stranger's face, which is the failure this block exists to prevent."""
        self.assertIn("SAL CRAFT", names_of("Sal's eyes"))

    def test_a_person_and_their_prop_are_not_an_ambiguity(self):
        """They are two things in the scene, so naming both is right. Two
        CHARACTERS sharing a surname genuinely is a question."""
        got = sorted(names_of("Sal's eyes"))
        self.assertEqual(got, ["SAL CRAFT", "SAL'S CRYO-CHAMBER"])

    def test_two_characters_sharing_a_surname_still_refuse(self):
        self.assertEqual(names_of("McGuire steps forward"), [])

    def test_a_hyphenated_group_matches_the_closed_compound(self):
        self.assertIn("SAL'S CRYO-CHAMBER", names_of("closing cryochamber"))

    def test_a_stopword_in_a_name_matches_nothing(self):
        for o in ("the drill rig", "a mug of coffee on the table"):
            self.assertNotIn("The Beacon", names_of(o), o)

    def test_a_real_word_of_that_name_still_matches(self):
        self.assertIn("The Beacon", names_of("the beacon on the ridge"))


class TheIdentityBlockUsesIt(unittest.TestCase):
    def test_the_primitives_are_shared_with_the_client(self):
        """One stoplist and one normalisation, in app/validation.py, which
        both sides import — the client had them and the server did not."""
        gen = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        self.assertIn("from .validation import name_words as _name_words", gen)
        self.assertIn("from .validation import norm_name as _norm_name", gen)
        val = (ROOT / "app/validation.py").read_text(encoding="utf-8")
        self.assertIn("NAME_STOPWORDS = frozenset", val)
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        self.assertIn("function adoptNameStopwords(settings)", js)
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        self.assertIn('"name_stopwords": sorted(validation.NAME_STOPWORDS)', main)

    def test_compile_goes_through_the_shared_matcher(self):
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        i = src.index('lines += ["", "SUBJECT IDENTITIES')
        seg = src[max(0, i - 900):i]
        self.assertIn("subjects_for_object(str(obj), subjects)", seg)
        self.assertNotIn("(n in o or o in n)", seg,
                         "the narrow rule this replaced")


if __name__ == "__main__":
    unittest.main()
