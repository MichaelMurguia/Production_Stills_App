"""A2 — the framing a panel renders at, chosen before the spend.

The failure this answers: twenty renders under a Subjective/Poetic
grammar came back flat and evenly lit while every part of the plumbing
tested correct. The grammar was reaching the prompt. It said `selective
focus`, `negative space`, `unusual subject placement` — and an
everything-sharp frame contains all three if the model decides it does.
Meanwhile the only optics in the prompt were a production-wide default
nobody had chosen: eye level, 24mm, level, wide.

So the panel now names a framing row, and where it does, the unchosen
default gets out of the way.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import camera_recipes as rec  # noqa: E402
from app import generate  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
POETIC = "cine-subjective-poetic"


class TheGrammarNamesItsDefault(unittest.TestCase):
    def test_every_grammar_sanctions_framings(self):
        from app import style_docs
        for st in style_docs.styles("cinematography"):
            self.assertTrue(st["recipes"], st["key"])

    def test_the_grammar_that_failed_now_defaults_to_its_own_row(self):
        r = rec.resolve({"cinematography": POETIC})
        self.assertEqual(r["key"], "subjective-poetic-character")
        self.assertEqual(r["aperture"], "f/1.4–2.8")

    def test_a_sanctioned_list_is_a_family_not_a_single_answer(self):
        """A grammar constrains the family without determining the row —
        an action beat under Subjective/Poetic is that grammar's own row
        or Immersive opened up, never an epic environmental wide."""
        keys = [r["key"] for r in rec.sanctioned({"cinematography": POETIC})]
        self.assertIn("immersive-inside-the-action", keys)
        self.assertNotIn("epic-environmental-wide", keys)
        self.assertGreater(len(keys), 1)

    def test_no_grammar_narrows_nothing(self):
        """Offering five rows out of twenty to a production that never
        chose a grammar would be inventing a rule."""
        self.assertEqual(len(rec.sanctioned({})), len(rec.recipes()))

    def test_a_bad_id_in_the_document_is_dropped_not_offered(self):
        from app import style_docs
        self.assertEqual(style_docs._recipe_ids("- `not-a-real-row` — why"), [])


class ThePanelDecides(unittest.TestCase):
    def test_four_states(self):
        self.assertEqual(rec.panel_choice({}), "")
        self.assertEqual(rec.panel_choice({"camera_recipe": "NONE"}), "NONE")
        self.assertEqual(rec.panel_choice({"camera_recipe": "intimate-close-up"}),
                         "intimate-close-up")
        # unrecognised inherits rather than deleting the framing silently
        self.assertEqual(rec.panel_choice({"camera_recipe": "gone"}), "")

    def test_none_refuses_a_framing_even_under_a_grammar(self):
        self.assertIsNone(rec.resolve({"cinematography": POETIC, "camera_recipe": "NONE"}))

    def test_the_panel_overrides_the_grammars_default(self):
        r = rec.resolve({"cinematography": POETIC, "camera_recipe": "elegant-portrait"})
        self.assertEqual(r["key"], "elegant-portrait")

    def test_the_stamp_says_which_decided_it(self):
        self.assertEqual(rec.stamp({"cinematography": POETIC})["from"], "grammar")
        self.assertEqual(rec.stamp({"cinematography": POETIC,
                                    "camera_recipe": "elegant-portrait"})["from"], "panel")
        self.assertEqual(rec.stamp({"camera_recipe": "NONE"}),
                         {"rides": False, "refused": True})
        self.assertEqual(rec.stamp({}), {"rides": False, "refused": False})


class ModifiersAreDeltas(unittest.TestCase):
    def test_a_set_axis_rides(self):
        m = rec.mods({"camera_recipe_mods": {"camera-height": "0.3–0.8m"}})
        self.assertEqual([x["axis"] for x in m], ["camera-height"])

    def test_a_setting_the_document_no_longer_defines_is_dropped(self):
        """A stale delta would ride a prompt describing a camera move
        nobody can look up."""
        self.assertEqual(rec.mods({"camera_recipe_mods": {"camera-height": "9m"}}), [])
        self.assertEqual(rec.mods({"camera_recipe_mods": {"no-axis": "x"}}), [])
        self.assertEqual(rec.mods({"camera_recipe_mods": "not-a-dict"}), [])


class ItReachesTheRender(unittest.TestCase):
    def test_the_framing_leads_the_camera_block(self):
        block = generate._camera_block({"cinematography": POETIC})
        self.assertTrue(block[1].startswith("- FRAMING —"))
        self.assertIn("f/1.4–2.8", block[1])

    def test_the_unchosen_production_default_yields_to_it(self):
        """The contradiction that defeated the axis: `24mm, deep, wide`
        arriving under a line asking for 50–100mm at f/1.4–2.8, from a
        card nobody had ever opened."""
        block = " ".join(generate._camera_block({"cinematography": POETIC}))
        self.assertNotIn("24mm", block)
        self.assertNotIn("WIDE SHOT", block)

    def test_but_an_axis_this_panel_set_survives_and_is_said_to_win(self):
        """A4.3 — the director disagreeing with the recipe on one shot is
        the point of keeping the manual axes."""
        block = generate._camera_block({"cinematography": POETIC, "camera_angle": "LOW"})
        self.assertIn("LOW ANGLE", " ".join(block))
        self.assertIn("the directive wins", block[0])

    def test_with_no_framing_nothing_changes_at_all(self):
        """What makes this reversible: a production that has chosen no
        grammar renders byte-identically to before."""
        block = generate._camera_block({})
        self.assertNotIn("FRAMING", " ".join(block))
        self.assertNotIn("the directive wins", block[0])
        self.assertIn("24mm", " ".join(block))

    def test_a_modifier_rides_as_its_own_directive(self):
        block = generate._camera_block(
            {"cinematography": POETIC, "camera_recipe_mods": {"camera-stability": "Locked"}})
        self.assertIn("CAMERA STABILITY — Locked", " ".join(block))

    def test_the_take_records_the_framing_beside_the_grammar(self):
        g = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        i = g.index('"cinematography": _cine.stamp(panel),')
        self.assertIn('"camera_recipe": _rec_stamp(panel),', g[i:i + 700])


class TheAmendRouteValidates(unittest.TestCase):
    def test_an_unknown_row_is_refused_not_dropped(self):
        """A silent drop reads on screen as inherit, and renders
        something the user did not ask for."""
        from app import store
        with self.assertRaises(ValueError):
            store._clean_panel_recipe({"camera_recipe": "nope"})
        with self.assertRaises(ValueError):
            store._clean_panel_recipe({"camera_recipe_mods": {"no-axis": "x"}})
        with self.assertRaises(ValueError):
            store._clean_panel_recipe({"camera_recipe_mods": {"camera-height": "9m"}})

    def test_empty_clears_and_none_survives(self):
        from app import store
        self.assertEqual(store._clean_panel_recipe({"camera_recipe": ""}),
                         {"camera_recipe": ""})
        self.assertEqual(store._clean_panel_recipe({"camera_recipe": "none"}),
                         {"camera_recipe": "NONE"})

    def test_an_untouched_field_is_not_touched(self):
        from app import store
        self.assertEqual(store._clean_panel_recipe({}), {})

    def test_it_rides_the_same_contract_as_the_grammar(self):
        """Journaled, lock re-stamped, refused once a take is approved —
        all of it comes from being in this tuple."""
        from app import store
        self.assertIn("camera_recipe", store.PANEL_GRAMMAR_FIELDS)
        self.assertIn("camera_recipe_mods", store.PANEL_GRAMMAR_FIELDS)


class ItIsReadableBeforeTheSpend(unittest.TestCase):
    def test_the_picker_names_the_optics_in_every_option(self):
        i = JS.index("function framingSelect")
        seg = " ".join(JS[i:i + 1800].split())
        self.assertIn("${esc(r.focal)}, ${esc(r.aperture)}", seg)

    def test_the_inherit_option_names_the_row_it_would_inherit(self):
        """A bare "production default" is the phrasing that hid this
        decision for two days."""
        i = JS.index("function framingSelect")
        seg = " ".join(JS[i:i + 1800].split())
        self.assertIn("(from the grammar)", seg)

    def test_changing_the_grammar_redraws_the_framings(self):
        i = JS.index("function wireCameraRow")
        seg = " ".join(JS[i:i + 1200].split())
        self.assertIn("framingSelect(prefix", seg)

    def test_the_take_badge_states_the_optics_not_just_the_name(self):
        i = JS.index("shot-tag-framing")
        seg = " ".join(JS[i:i + 700].split())
        self.assertIn("camera_recipe.focal", seg)
        self.assertIn("camera_recipe.aperture", seg)


if __name__ == "__main__":
    unittest.main()
