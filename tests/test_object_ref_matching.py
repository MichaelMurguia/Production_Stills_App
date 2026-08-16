"""One rule for "does this phrase name that thing", shared by every
surface that asks (user-caught 2026-08-16: a panel with the required
object "Sal's eyes" showed `+ REF` — "it should find that ref because I
have Sal Ref").

Four copies of this question existed and disagreed. The one fixed here
drives the green REF marker AND the first-take tick default, so a Sal
panel offered no Sal plate and nothing on screen said why. It asked
whether either string CONTAINED the other, and "Sal's eyes" does not
contain "SAL CRAFT".

Two normalisations earn their place against the user's real data:
possessives ("Sal's" vs the card SAL CRAFT) and hyphens ("closing
cryochamber" vs the group SAL'S CRYO-CHAMBER).

Measured on the user's own P02: 1 of 5 objects had a reference before,
5 of 5 after."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

STOP = {"the", "and", "for", "with", "from", "into", "its", "his", "her",
        "their", "that", "this", "over", "under", "onto", "off"}


def norm(s):
    s = str(s).lower()
    s = re.sub(r"['’]s\b", "", s)
    s = re.sub(r"['’]", "", s)
    return s.replace("-", "")


def words(n):
    return [w for w in re.split(r"[^a-z0-9]+", norm(n))
            if len(w) >= 3 and w not in STOP]


def word_in(needle, hay):
    return bool(needle) and re.search(
        rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", hay) is not None


def names_phrase(obj, name):
    """Port of app.js namesPhrase — kept in step by the source assertions."""
    o, n = norm(obj), norm(name)
    if not o or not n:
        return False
    # Word-bounded BOTH ways: a bare substring test let the group "SOD"
    # match "sodium vapour lamp".
    if word_in(n, o) or word_in(o, n):
        return True
    return any(word_in(w, o) for w in words(n))


# The user's real approved reference groups on this production.
GROUPS = ["SAL CRAFT", "KYRA MCGUIRE", "MARK PAYNE", "SOD", "ONYX UNIT",
          "PROSPECTOR", "GT40", "P02 SHACK IN THE MEADOW", "RESISTANCE BASE",
          "GRM LIGHT TRUCK", "GRM HEAVY TRUCK", "GRM HOVER JET", "EXOSKELETON",
          "REPAIR SHOP", "VILLAGE", "CLEASE", "SAL'S CRYO-CHAMBER"]


def hits(obj):
    return sorted(g for g in GROUPS if names_phrase(obj, g))


class TheUsersOwnPanel(unittest.TestCase):
    """P02 of FINAL_CONFRONTATION_SAL_TOM, verbatim."""

    P02 = ["Sal's eyes", "Sal's fogging breath", "sweat beads on Sal's face",
           "faint frost line at Sal's hair", "SAL CRAFT"]

    def test_every_object_now_finds_sal(self):
        for o in self.P02:
            self.assertIn("SAL CRAFT", hits(o), o)

    def test_the_old_rule_found_only_one_of_the_five(self):
        def old(obj, name):
            o, n = str(obj).lower(), str(name).lower()
            return o in n or n in o
        before = [o for o in self.P02 if any(old(o, g) for g in GROUPS)]
        self.assertEqual(before, ["SAL CRAFT"],
                         "1 of 5 — the regression this pins")
        self.assertEqual(len([o for o in self.P02 if hits(o)]), 5)


class TheNormalisations(unittest.TestCase):
    def test_a_possessive_finds_the_card(self):
        self.assertIn("SAL CRAFT", hits("Sal's eyes"))

    def test_a_hyphen_in_the_group_matches_a_closed_compound(self):
        """"closing cryochamber" vs the group SAL'S CRYO-CHAMBER."""
        self.assertIn("SAL'S CRYO-CHAMBER", hits("closing cryochamber"))

    def test_a_stopword_in_a_group_name_matches_nothing(self):
        """A real group is called "P02 SHACK IN THE MEADOW". Without the
        stoplist, every object containing the word "the" matched it."""
        self.assertNotIn("P02 SHACK IN THE MEADOW", hits("frost along the glass"))
        self.assertIn("P02 SHACK IN THE MEADOW", hits("the shack at dusk"),
                      "a real word in the name still matches")

    def test_a_short_fragment_is_not_a_word(self):
        """The group SOD must not be found inside "sodium"."""
        self.assertNotIn("SOD", hits("sodium vapour lamp"))

    def test_an_unreferenced_object_still_finds_nothing(self):
        for o in ("curved glass door", "freezing gas flooding the chamber",
                  "Tom at the control"):
            self.assertEqual(hits(o), [], o)


class TheRuleIsDeliberatelyLooserThanTheIdentityRule(unittest.TestCase):
    def test_a_shared_word_matches_both_rather_than_neither(self):
        """generate.py's SUBJECT IDENTITIES refuses on a shared word: one
        McGuire's traits on the other writes a WRONG FACT into the prompt.
        Here the answer only decides which plates are offered and ticked,
        and the failures are not symmetric — an extra plate is visible in
        step 04 and one click away, a missing one is invisible and renders
        a stranger's face. "sal" is shared by the man and his cryochamber,
        which is why refusing lost him entirely."""
        self.assertEqual(hits("Sal's eyes locked on Tom"),
                         ["SAL CRAFT", "SAL'S CRYO-CHAMBER"])


class TheSourceKeepsOneCopy(unittest.TestCase):
    def test_the_helpers_are_module_scope(self):
        for decl in ("const wordIn = (needle, hay)", "const nameWords = n =>",
                     "const namesPhrase = (obj, name)", "const normName = s =>"):
            self.assertEqual(JS.count(decl), 1, decl)
            self.assertIn("\n" + decl, JS, f"{decl} must be at module scope")

    def test_the_workbench_matcher_delegates(self):
        self.assertIn("const matches = (obj, name) => namesPhrase(obj, name);", JS)
        self.assertNotIn("return o.includes(n) || n.includes(o);", JS,
                         "the narrow rule this replaced")

    def test_the_marker_and_the_tick_default_share_it(self):
        """If these ever diverge again, a green REF appears beside a group
        that was not ticked, or the reverse."""
        self.assertIn("const objHasRef = obj => groupList.some(g => matches(obj, g.name));", JS)
        self.assertIn("reqObjs.some(o => matches(o, g.name))", JS)


if __name__ == "__main__":
    unittest.main()
