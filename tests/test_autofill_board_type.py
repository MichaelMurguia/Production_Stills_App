"""The board's shape is the user's decision (user-hit 2026-08-07).

From the Locations register, Create breakdown seeded a scene-specific
draft. The user wanted a location study, rewrote the description, ran it —
and got the seeded scene back.

The brief was never dropped. It just had almost no influence over the one
thing being changed:

  * the auto intake had no board-type control at all, so the only way to
    ask for a location study was prose;
  * `scene_anchor()` matches on the LOCATION, so a rewritten brief naming
    the same place produced a byte-identical anchor — which then asserted,
    last and longest and marked NOT OPTIONAL, "This board is about THESE
    scenes";
  * the JSON schema asked every board, whatever its type, for a `scene`
    field "describing the scene".

These hold the fix: a stated type outranks the model's reading, the anchor
supplies evidence rather than dictating shape, and the schema stops asking
a place to describe a scene.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import autofill  # noqa: E402

ANCHOR = {"matched": True, "location": "GRM BRIDGE", "scenes": 4,
          "text": "INT. GRM BRIDGE - NIGHT\n\nOnyx panels."}


class StatedTypeWins(unittest.TestCase):
    def coerce(self, draft_type, stated):
        # an evidence row only survives if its panel_id matches a panel
        draft = {"subject": "s", "board_type": draft_type,
                 "panels": [{"id": "P01", "title": "t", "purpose": "p"}],
                 "evidence_ledger": [{"panel_id": "P01", "object": "o",
                                      "evidence_class": "SCRIPT_EXPLICIT",
                                      "status": "PASS", "source": "line"}]}
        return autofill._coerce(draft, "SPEC_X", "CANON_EXTRACTION", stated)["board_type"]

    def test_a_stated_type_overrides_the_models_choice(self):
        self.assertEqual(self.coerce("SCENE", "LOCATION"), "LOCATION")

    def test_an_unstated_type_still_falls_back_to_the_model(self):
        self.assertEqual(self.coerce("SCENE", ""), "SCENE")

    def test_the_old_default_survives_an_unusable_draft(self):
        self.assertEqual(self.coerce("", ""), "LOCATION")

    def test_every_offered_type_is_accepted(self):
        for t in ("SCENE", "LOCATION", "ASSET", "LIGHTING_STUDY", "MASTER"):
            self.assertEqual(self.coerce("SCENE", t), t)

    def test_an_invalid_type_is_refused_at_the_door(self):
        with self.assertRaises(autofill.AutofillError):
            autofill.autofill_spec("SPEC_X", "a brief", "CANON_EXTRACTION",
                                   "gemini", "NONSENSE")


class OneVocabularyReadTwice(unittest.TestCase):
    """The five board types are load-bearing in six places — the blank
    sheet's panel template, the drafting prompt, the render prompt's
    SETTING block, which fields the sheet editor shows, the assembled
    board's header, and the layout solver. Two selects offer them, and
    for a while the two rendered the same list differently."""

    JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")

    def test_the_intake_shows_the_label_not_the_machine_token(self):
        """`LIGHTING_STUDY` reached the screen. The user had already ruled
        on that exact shape (2026-08-22, on BOARD_LAYOUT_STYLE): "that
        underscore is not for end users, has no meaning". The list carried
        `label: "LIGHTING STUDY"` all along — this select rendered around
        it while the sheet editor rendered through it."""
        i = self.JS.index('for (const sel of ["#spec-auto-btype", "#spec-new-btype"])')
        seg = self.JS[i:i + 800]
        self.assertIn("esc(t.label)", seg)
        self.assertNotIn("esc(t.value)", seg)

    def test_both_selects_read_the_same_definitions(self):
        """The intake's tooltip named three of the five; the sheet
        editor's named all five. The intake is where a sheet is MADE, so
        it was the one place the two undocumented types mattered — and
        two hand-written copies of one vocabulary is how that happened."""
        self.assertEqual(self.JS.count("const boardTypeTitle = "), 1)
        self.assertEqual(self.JS.count("boardTypeTitle("), 2,
                         "both selects, and no third copy")
        i = self.JS.index("const BOARD_TYPES = [")
        seg = self.JS[i:i + 900]
        for t in ("SCENE", "LOCATION", "ASSET", "LIGHTING_STUDY", "MASTER"):
            self.assertIn(t, seg)
        self.assertEqual(seg.count("hint:"), 5, "every type defines itself")

    def test_the_static_title_is_gone_from_the_markup(self):
        """A title attribute in index.html cannot read the list, so it
        would drift again the moment a type is added."""
        i = self.HTML.index('id="spec-auto-btype"')
        self.assertNotIn("SCENE:", self.HTML[max(0, i - 400):i + 400])

    def test_the_client_list_and_the_server_set_agree(self):
        """The server refuses anything outside `BOARD_TYPES`, so an option
        the client offers and the server rejects is a door that fails at
        the moment it is pressed."""
        i = self.JS.index("const BOARD_TYPES = [")
        seg = self.JS[i:self.JS.index("];", i)]
        offered = {ln.split('value: "')[1].split('"')[0]
                   for ln in seg.splitlines() if 'value: "' in ln}
        self.assertEqual(offered, autofill.BOARD_TYPES)


class TheShotLandsInTheEnum(unittest.TestCase):
    """Regression (2026-08-12 review): the drafting prompt asked for
    FULL_BODY | DETAIL — pre-camera-enum vocabulary — and _coerce persisted
    it verbatim, so the shot axis silently vanished from every render
    prompt and the sheet editor misreported '— from bible —'."""

    def coerce_scale(self, scale):
        draft = {"subject": "s", "board_type": "LOCATION",
                 "panels": [{"id": "P01", "title": "t", "purpose": "p",
                             "scale": scale}],
                 "evidence_ledger": [{"panel_id": "P01", "object": "o",
                                      "evidence_class": "SCRIPT_EXPLICIT",
                                      "status": "PASS", "source": "line"}]}
        out = autofill._coerce(draft, "SPEC_X", "CANON_EXTRACTION", "")
        return out["panels"][0]["scale"]

    def test_the_prompt_offers_the_canon_enum(self):
        out = autofill._instructions("brief", "CANON_EXTRACTION", [], "")
        self.assertIn("AERIAL | EXTREME_WIDE | WIDE | MEDIUM | CLOSE | "
                      "EXTREME_CLOSE | MACRO | MICRO", out)
        self.assertNotIn("FULL_BODY", out)

    def test_canon_values_persist_as_stated(self):
        for v in ("AERIAL", "EXTREME_WIDE", "WIDE", "MEDIUM", "CLOSE",
                  "EXTREME_CLOSE", "MACRO", "MICRO"):
            self.assertEqual(self.coerce_scale(v), v)

    def test_legacy_words_migrate_at_the_door(self):
        self.assertEqual(self.coerce_scale("FULL_BODY"), "WIDE")
        self.assertEqual(self.coerce_scale("DETAIL"), "EXTREME_CLOSE")

    def test_nonsense_means_inherit_not_a_stored_orphan(self):
        self.assertEqual(self.coerce_scale("CINEMATIC"), "")
        self.assertEqual(self.coerce_scale(""), "")


class TheInstructionsCarryIt(unittest.TestCase):
    def test_a_stated_type_is_an_absolute_rule(self):
        out = autofill._instructions("brief", "CANON_EXTRACTION", [], "LOCATION")
        self.assertIn("Board type for this board: LOCATION", out)
        self.assertIn("This is the user's decision, not yours", out)

    def test_nothing_is_added_when_the_user_left_it_open(self):
        out = autofill._instructions("brief", "CANON_EXTRACTION", [], "")
        self.assertNotIn("Board type for this board", out)

    def test_a_location_board_is_not_asked_to_describe_a_scene(self):
        loc = autofill._instructions("brief", "CANON_EXTRACTION", [], "LOCATION")
        self.assertIn("describing THE PLACE", loc)
        self.assertIn("Do not narrate one scene's events", loc)

    def test_a_scene_board_keeps_the_original_wording(self):
        sc = autofill._instructions("brief", "CANON_EXTRACTION", [], "SCENE")
        self.assertIn("describing the scene as the screenplay establishes it", sc)


class TheAnchorSuppliesEvidenceNotShape(unittest.TestCase):
    def test_a_location_board_is_told_the_place_is_the_subject(self):
        out = autofill._anchor_block(ANCHOR, "LOCATION")
        self.assertIn("about THE PLACE across every scene", out)
        self.assertIn("not any single one of these scenes", out)

    def test_a_scene_board_is_told_one_scene_is_the_subject(self):
        out = autofill._anchor_block(ANCHOR, "SCENE")
        self.assertIn("exactly one of the scenes below is the subject", out)

    def test_the_old_unconditional_claim_is_gone(self):
        """It asserted the same thing for every board, derived only from
        the location name — which is why rewriting the brief changed
        nothing."""
        for bt in ("LOCATION", "SCENE", "ASSET", ""):
            self.assertNotIn("This board is about THESE scenes",
                             autofill._anchor_block(ANCHOR, bt), bt)

    def test_the_deterministic_quote_survives_in_every_case(self):
        """The quoting fixed a real bug and stays absolute."""
        for bt in ("LOCATION", "SCENE", "ASSET", ""):
            out = autofill._anchor_block(ANCHOR, bt)
            self.assertIn("DETERMINISTIC, NOT OPTIONAL", out)
            self.assertIn(ANCHOR["text"], out)
            self.assertIn("GRM BRIDGE", out)
            self.assertIn("Every panel, evidence row and citation must anchor", out)

    def test_it_still_states_the_scene_count(self):
        self.assertIn("(4 scenes)", autofill._anchor_block(ANCHOR, "LOCATION"))
        self.assertIn("(1 scene)", autofill._anchor_block(
            {**ANCHOR, "scenes": 1}, "LOCATION"))


class TheIntakeStatesIt(unittest.TestCase):
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")

    def test_both_doors_have_a_board_type_control(self):
        """RULE_PASS_2 C1 collapsed the two intake doors into one on
        2026-08-18 and `#spec-auto-*` retired; the user reversed that on
        2026-08-22 ("I want two separate columns") and it came back. Board
        type is a property of the sheet, not of how the sheet was made, so
        BOTH doors carry it."""
        self.assertIn('id="spec-auto-btype"', self.HTML)
        self.assertIn('id="spec-new-btype"', self.HTML)

    def test_it_offers_the_same_vocabulary_everywhere(self):
        self.assertIn("BOARD_TYPES.map", self.JS)

    def test_it_is_posted(self):
        self.assertIn('board_type: $("#spec-new-btype")?.value', self.JS)

    def test_it_survives_a_reload_like_the_other_fields(self):
        i = self.JS.index('persistForm("blankSpecDraft"')
        self.assertIn("spec-new-btype", self.JS[i:i + 260])

    def test_the_hint_defaults_it_and_then_stops(self):
        """A scene row means SCENE, a location row LOCATION — but once the
        user has chosen, the hint never overwrites them."""
        self.assertIn('autoBtype.value = scene ? "SCENE" : "LOCATION"', self.JS)
        self.assertIn("!autoBtype.dataset.touched", self.JS)


if __name__ == "__main__":
    unittest.main()
