"""Stop 2: the panel renders what the panel says.

The three render failures from the first user test (FEEDBACK_PLAN, D1/D3).
None of them was a hallucination — in every case the app instructed the
model to do the thing the user then complained about.

  D1  "six descending figures" summoned LEDGER SIX, his recon aircraft,
      and the prompt asserted it was required content.
  D3  A panel about the pristine Descent Team was handed the weathered
      airbase faction's palette as the only image the model saw.

The fixtures here are his own production, because a synthetic one would
not have had a callsign with a number in it or thirty palette swatches
across three factions — which is to say it would not have found either
bug."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BACKUP = ROOT / "feedback/screenboard-backup-ANCESTOR-2026-08-23.zip"

# His twenty cards, transcribed from the backup so the test stands alone
# once the zip is gone. LEDGER SIX is the one that matters; the rest are
# here because a matcher is only as good as the collisions it survives.
SUBJECTS = [
    {"name": "AVREL NDIAYE-DEKKER", "kind": "CHARACTER", "subtitle": "COMMANDER.",
     "traits": ["Tall, straight-backed.", "Unweathered face."]},
    {"name": "LEDGER SIX", "kind": "VEHICLE", "subtitle": "RECON AIRCRAFT. SURVIVOR. EYE.",
     "traits": ["Compact aircraft with tail flash 118.",
                "Riveted airframe older than its pilot.",
                "Sun-cracked paint and scratched canopy."]},
    {"name": "DESCENT VEHICLE", "kind": "VEHICLE", "subtitle": "THE HULL.",
     "traits": ["Matte. Seamless."]},
    {"name": "FINE LATTICE", "kind": "PROP", "subtitle": "REACTIVE MESH.",
     "traits": ["Glints cold silver."]},
    {"name": "KETTLE", "kind": "CHARACTER", "subtitle": "YOUNGEST.",
     "traits": ["Birthday board. Inherited gloves."]},
    {"name": "COIN", "kind": "PROP", "subtitle": "KEEPSAKE.", "traits": ["Worn smooth."]},
    {"name": "CREW CHIEF", "kind": "CHARACTER", "subtitle": "GROUND.", "traits": ["Oil-black hands."]},
    {"name": "OLD MECHANICAL WATCH", "kind": "PROP", "subtitle": "HARLOW'S.",
     "traits": ["Worn face-in against the pulse."]},
]

P01_REQUIRED = [
    "matte hull the size of a fishing boat",
    "pan with crust and salt",
    "shivering air beneath the hull",
    "unlit open ramp",
    "six descending figures",
]


class TheWordSixNeverSummonsAnAircraft(unittest.TestCase):
    """D1.1. The whole failure in one sentence."""

    def match(self, obj: str) -> list[str]:
        from app.generate import subjects_for_object
        return [s["name"] for s in subjects_for_object(obj, SUBJECTS)]

    def test_the_reported_failure(self):
        self.assertNotIn("LEDGER SIX", self.match("six descending figures"))

    def test_no_object_of_his_salt_panel_names_the_aircraft(self):
        for obj in P01_REQUIRED:
            self.assertNotIn("LEDGER SIX", self.match(obj), obj)

    def test_digits_are_treated_like_the_words_they_stand_for(self):
        """'LEDGER 6' is the same callsign shape. A rule that fixed the
        spelled-out numeral and not the digit would fix one production."""
        subs = [dict(SUBJECTS[1], name="LEDGER 6")]
        from app.generate import subjects_for_object
        self.assertEqual(subjects_for_object("6 descending figures", subs), [])

    def test_the_aircraft_still_answers_to_its_own_name(self):
        """The fix must not make canon subjects unreachable — that is the
        bug it is standing next to, not an improvement on it."""
        self.assertIn("LEDGER SIX", self.match("LEDGER SIX on the flight line"))
        self.assertIn("LEDGER SIX", self.match("ledger six returns with nineteen holes"))

    def test_a_distinctive_word_alone_is_still_enough(self):
        """`Sal inside the cryochamber` — the 2026-08-16 failure this
        matcher was widened to fix. Narrowing it must not re-open that."""
        self.assertIn("FINE LATTICE", self.match("fine lattice over fatigues"))
        self.assertIn("AVREL NDIAYE-DEKKER", self.match("Avrel's boot"))
        self.assertIn("AVREL NDIAYE-DEKKER", self.match("Avrel's unweathered face"))

    def test_a_single_word_common_name_still_matches(self):
        """COIN and KETTLE are whole names. For them the common word is all
        the evidence there is, and refusing it would be a different bug —
        the absence of LEDGER is what makes 'six' a coincidence."""
        self.assertIn("COIN", self.match("a coin pressed into her palm"))
        self.assertIn("KETTLE", self.match("Kettle at the birthday board"))

    def test_a_common_word_cannot_carry_a_multi_word_name(self):
        from app.validation import is_common_word
        self.assertTrue(is_common_word("six"))
        self.assertTrue(is_common_word("dark"))
        self.assertTrue(is_common_word("118"))
        self.assertFalse(is_common_word("ledger"))
        self.assertFalse(is_common_word("lattice"))
        self.assertFalse(is_common_word("avrel"))

    def test_crew_chief_is_not_summoned_by_a_crew(self):
        """'crew' is common; CREW CHIEF has a second word that is not."""
        self.assertNotIn("CREW CHIEF", self.match("the crew works the flight line"))
        self.assertIn("CREW CHIEF", self.match("the crew chief signs the sheet"))


class ThePromptStopsAssertingWhatItCannotKnow(unittest.TestCase):
    """D1.2. The heading claimed the subject was required content, which is
    what made a coincidence into an instruction."""

    GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")

    def test_it_no_longer_claims_the_subject_is_required(self):
        self.assertNotIn("required content above includes these canon", self.GEN)

    def test_it_says_what_is_actually_true(self):
        self.assertIn("canon subjects the required content above", self.GEN)
        self.assertIn("appears to name", self.GEN)

    def test_it_still_forbids_generic_substitutes(self):
        """The block's real job survives: a named subject must be itself."""
        self.assertIn("never a generic substitute of", self.GEN)

    def test_and_now_forbids_adding_one(self):
        self.assertIn("Do not add a subject that the required content does not", self.GEN)


class TheProductionSaysWhenItIsSet(unittest.TestCase):
    """D1.4. His screenplay is 241 years ahead and no panel ever said so —
    the era lived in the bible's prose and in a logline no prompt reads."""

    GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")
    WIZ = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def setUp(self):
        from app import paths
        self.tmp = tempfile.TemporaryDirectory()
        self._old = paths.WIZARD_ANALYSIS
        paths.WIZARD_ANALYSIS = Path(self.tmp.name) / "wizard_analysis.json"

    def tearDown(self):
        from app import paths
        paths.WIZARD_ANALYSIS = self._old
        self.tmp.cleanup()

    def write(self, obj):
        from app import paths
        paths.WIZARD_ANALYSIS.write_text(json.dumps(obj), encoding="utf-8")

    def test_the_scan_is_asked_for_it(self):
        self.assertIn('"period"', self.WIZ)

    def test_a_stated_period_is_returned(self):
        from app import generate
        self.write({"period": "241 years in the future"})
        self.assertEqual(generate.production_period(), "241 years in the future")

    def test_an_unstated_period_constrains_nothing(self):
        """Inventing an era would be exactly the fabrication this exists to
        prevent."""
        from app import generate
        for v in ({}, {"period": ""}, {"period": "UNSTATED"}, {"period": "unknown"}):
            self.write(v)
            self.assertEqual(generate.production_period(), "")

    def test_the_prompt_forbids_other_eras_when_one_is_stated(self):
        self.assertIn("This production is set in", self.GEN)
        self.assertIn("Technology from", self.GEN)
        self.assertIn("another era is forbidden", self.GEN)

    def test_it_can_be_stated_by_hand(self):
        """A production that predates the field must not have to pay for
        another screenplay read to say when it is set."""
        self.assertIn('data-f="edit-period"', self.JS)
        self.assertIn("When is this production set?", self.JS)


class APanelGetsItsOwnFactionsPalette(unittest.TestCase):
    """D3.1 and the cap. The single most consequential of the three: the
    only IMAGE the model saw was the wrong faction's colour world."""

    def setUp(self):
        from app import paths
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self._old = paths.REF_INDEX
        paths.REF_INDEX = d / "references.json"
        # Three factions, uneven counts, newest belonging to the WRONG one
        # — the exact shape of his library.
        refs = []
        for i, (lang, n) in enumerate([("THE DESCENT TEAM", 8),
                                       ("THE CATCHMENT", 10),
                                       ("FENN HARROW COMPACT", 12)]):
            for k in range(n):
                refs.append({
                    "id": f"REF-{i}{k:02d}", "role": "COLOR_PALETTE",
                    "status": "APPROVED",
                    "notes": f"{lang} · SWATCH {k} · #3439{k:02d} · cite",
                    "added_at": f"2026-08-23T{10 + i:02d}:{k:02d}:00+00:00",
                })
        paths.REF_INDEX.write_text(json.dumps(refs), encoding="utf-8")

    def tearDown(self):
        from app import paths
        paths.REF_INDEX = self._old
        self.tmp.cleanup()

    def langs_of(self, refs):
        from app import store
        return sorted({store.reference_language(r) for r in refs
                       if store.role_head(r["role"]) == "COLOR_PALETTE"})

    def test_a_panel_gets_only_its_own_language(self):
        from app import store
        got = store.auto_style_references(["THE DESCENT TEAM"])
        self.assertEqual(self.langs_of(got), ["THE DESCENT TEAM"])

    def test_it_gets_the_whole_ramp_not_two_of_it(self):
        """collapse() composites swatches into ONE image, so the per-role
        cap saves no slot — it just sends two colours and calls them the
        film's colour language."""
        from app import store
        got = [r for r in store.auto_style_references(["THE DESCENT TEAM"])
               if store.role_head(r["role"]) == "COLOR_PALETTE"]
        self.assertEqual(len(got), 8)

    def test_the_reported_failure(self):
        """Before: the two newest approved swatches rode, and both were
        FENN HARROW COMPACT — so the Descent Team's panel was coloured by
        the weathered airbase faction."""
        from app import store
        got = store.auto_style_references(["THE DESCENT TEAM"])
        self.assertNotIn("FENN HARROW COMPACT", self.langs_of(got))

    def test_the_language_is_read_from_where_it_actually_lives(self):
        """A swatch's language is in its NOTES, not its role — filtering on
        the role alone silently matched nothing and would have looked like
        a working fix."""
        from app import store
        self.assertEqual(
            store.reference_language(
                {"role": "COLOR_PALETTE",
                 "notes": "THE CATCHMENT · DARK IRON · #343936 · cite"}),
            "THE CATCHMENT")
        self.assertEqual(
            store.reference_language({"role": "WORLD_TEXTURE — SALT PANS"}),
            "SALT PANS")

    def test_an_unscoped_anchor_still_rides_everything(self):
        """A palette belonging to no design language is the production's
        own, and scoping must not silently retire it."""
        from app import store
        refs = json.loads(paths_ref().read_text(encoding="utf-8"))
        refs.append({"id": "REF-999", "role": "COLOR_PALETTE", "status": "APPROVED",
                     "notes": "HOUSE GREY · #808080 · cite",
                     "added_at": "2026-08-23T23:00:00+00:00"})
        paths_ref().write_text(json.dumps(refs), encoding="utf-8")
        got = store.auto_style_references(["THE DESCENT TEAM"])
        self.assertIn("REF-999", [r["id"] for r in got])

    def test_no_language_named_means_no_filtering(self):
        """The library's own preview wants every anchor; only a caller that
        states languages is asking to be filtered."""
        from app import store
        self.assertEqual(len(self.langs_of(store.auto_style_references(None))), 3)


def paths_ref():
    from app import paths
    return paths.REF_INDEX


class TheSpendIsPreviewable(unittest.TestCase):
    """D1.3 and D3.2 — what will ride, and what will not, before paying."""

    GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")

    def test_the_manifest_names_the_matching_word(self):
        """'LEDGER SIX will be described because P01 says six' is the
        sentence that would have saved the render."""
        self.assertIn('"because": str(obj), "matched": why', self.GEN)

    def test_a_missing_palette_is_stated_not_silent(self):
        self.assertIn("render carries none", self.GEN)

    def test_it_says_which_languages_do_have_one(self):
        """So the answer to 'why has my panel no colour' is on screen."""
        self.assertIn("Palettes exist for:", self.GEN)


class TheResearchPassCarriesStatedConditions(unittest.TestCase):
    """D3.3. His P03 said 'Avrel's unweathered face' and P01 said only
    'six descending figures' — while the screenplay said the descent team
    comes down pristine."""

    AUTO = (ROOT / "app/autofill.py").read_text(encoding="utf-8")

    def test_the_object_carries_its_condition(self):
        self.assertIn("CARRYING ANY CONDITION THE SCREENPLAY STATES", self.AUTO)

    def test_it_may_not_invent_one(self):
        self.assertIn("Never invent a condition the screenplay does not", self.AUTO)


class HisActualProductionIsClean(unittest.TestCase):
    """The end-to-end check, run against the backup when it is present.
    Skips on a machine without it; every mechanism above is pinned by the
    fixtures regardless."""

    def setUp(self):
        if not BACKUP.exists():
            self.skipTest("tester backup not present")
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        with zipfile.ZipFile(BACKUP) as z:
            for m in ("data/subjects.json", "data/specs/SHIP_DESCENDS_V1.json",
                      "data/references/references.json"):
                z.extract(m, self.d)
        self.addCleanup(self.tmp.cleanup)

    def test_no_panel_of_his_breakdown_summons_the_aircraft(self):
        from app.generate import subjects_for_object
        subs = json.loads((self.d / "data/subjects.json").read_text(encoding="utf-8"))
        spec = json.loads((self.d / "data/specs/SHIP_DESCENDS_V1.json")
                          .read_text(encoding="utf-8"))
        for panel in spec["panels"]:
            for obj in panel["required_objects"]:
                names = [s["name"] for s in subjects_for_object(obj, subs)]
                self.assertNotIn("LEDGER SIX", names, f"{panel['id']}: {obj}")

    def test_his_salt_panel_would_get_the_descent_teams_palette(self):
        from app import paths, store
        old = paths.REF_INDEX
        paths.REF_INDEX = self.d / "data/references/references.json"
        try:
            got = store.auto_style_references(["THE DESCENT TEAM"])
            langs = {store.reference_language(r) for r in got
                     if store.role_head(r["role"]) == "COLOR_PALETTE"}
            self.assertEqual(langs, {"THE DESCENT TEAM"})
        finally:
            paths.REF_INDEX = old


if __name__ == "__main__":
    unittest.main()
