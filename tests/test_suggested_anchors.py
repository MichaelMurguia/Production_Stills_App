"""The screenplay proposes the look, and colour leaves step 01.

Two user-directed changes, 2026-08-29.

FIRST — an LLM reads the screenplay and proposes one world texture, one
cinematography grammar and one board rendering style. That does not
overturn the ruling that the anchors LEAD this stage (2026-08-07, the
director states the look before the machine reads anything); it adds a
second door for the director who would rather be shown three candidates
than face three empty cards. Everything it returns is a PROPOSAL with a
reason, and nothing is written until the director accepts it.

SECOND — colour is no longer one of them. Its palette is proposed FROM
the Bible by `generate_swatches`, so asking a director to choose a colour
language in step 01 asked for the answer ahead of the question. It is the
one anchor with no catalogue, for exactly that reason. It sits with the
Bible now.

What did NOT change: `AUTO_ATTACH_HEADS` is still four. A palette
reference still rides every render. Moving a card cannot change what
reaches a prompt.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import wizard  # noqa: E402

CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


class ItAsksForOneFromEachCatalogue(unittest.TestCase):
    def instr(self):
        return wizard._suggest_instructions("INT. HANGAR - NIGHT")

    def test_three_menus_and_no_fourth(self):
        """Colour is not a catalogue — its palette comes from the Bible."""
        t = self.instr()
        self.assertEqual(t.count("choose exactly one `key`"), 3)
        self.assertNotIn("COLOR PALETTE", t)

    def test_every_option_the_documents_define_is_offered(self):
        from app import style_docs
        t = self.instr()
        for lib in wizard.SUGGEST_LIBS:
            for st in style_docs.styles(lib):
                self.assertIn(st["key"], t, st["key"])

    def test_it_may_not_invent_an_option(self):
        self.assertIn("may not invent an option that is not listed", self.instr())

    def test_the_three_are_stated_to_be_independent(self):
        """A rendering style says nothing about the film; letting one
        drag the other two is how three decisions become one."""
        t = self.instr()
        self.assertIn("The three are independent", t)
        self.assertIn("Do not\nlet one drag the other two", t)

    def test_a_reason_must_name_this_screenplay(self):
        """A reason that fits any film is not a reason — it is the thing
        the director is meant to argue with."""
        self.assertIn("A reason that would fit any\nfilm is not a reason", self.instr())

    def test_the_screenplay_rides_as_text(self):
        """Never the upload. A PDF bills per page on every run."""
        src = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
        i = src.index("def suggest_anchors(")
        seg = src[i:i + 1800]
        self.assertIn("store.screenplay_text_cached()", seg)
        self.assertIn("autofill._draft(\n        provider, None, None,", seg)


class NothingUnverifiableSurvives(unittest.TestCase):
    def suggest(self, payload):
        from app import autofill, store
        was_draft, was_text = autofill._draft, store.screenplay_text_cached
        try:
            store.screenplay_text_cached = lambda: "INT. HANGAR - NIGHT"
            autofill._draft = lambda *a, **k: (payload, "fake")
            return wizard.suggest_anchors("gemini")["proposals"]
        finally:
            autofill._draft, store.screenplay_text_cached = was_draft, was_text

    def real_key(self, lib):
        from app import style_docs
        return style_docs.styles(lib)[0]["key"]

    def test_a_real_key_with_a_reason_survives(self):
        out = self.suggest({"texture": {"key": self.real_key("texture"),
                                        "why": "the salt eats everything"}})
        self.assertIn("texture", out)
        self.assertTrue(out["texture"]["value"])

    def test_an_invented_style_is_dropped(self):
        """An option nobody can open is worse than a shorter answer — no
        picker could ever show it."""
        self.assertEqual(self.suggest({"texture": {"key": "tex-invented",
                                                   "why": "x"}}), {})

    def test_a_style_with_no_reason_is_dropped(self):
        """A look nobody chose. The reason is the whole of what makes
        this a proposal rather than an assignment."""
        self.assertEqual(self.suggest({"texture": {"key": self.real_key("texture"),
                                                   "why": "  "}}), {})

    def test_junk_does_not_crash_it(self):
        self.assertEqual(self.suggest({"texture": "a string", "rendering": None}), {})

    def test_no_screenplay_text_refuses_and_says_why(self):
        from app import store
        was = store.screenplay_text_cached
        try:
            store.screenplay_text_cached = lambda: ""
            with self.assertRaises(Exception) as e:
                wizard.suggest_anchors("gemini")
            self.assertIn("never sent to a model", str(e.exception))
        finally:
            store.screenplay_text_cached = was


class AProposalIsNotAnAnswer(unittest.TestCase):
    def test_it_states_that_it_proposes_and_never_sets(self):
        self.assertIn("COSTS A MODEL CALL &middot; PROPOSES, NEVER SETS", HTML)

    def test_accepting_takes_the_same_path_a_manual_pick_takes(self):
        """One path into an anchor, not two: it writes the style's own
        value and fires the same change every reader already listens for."""
        i = JS.index("const showProposals =")
        seg = JS[i:i + 2200]
        self.assertIn("fld.value = p.value", seg)
        self.assertIn('new Event("change", { bubbles: true })', seg)

    def test_dismissing_leaves_the_card_alone(self):
        i = JS.index("const showProposals =")
        seg = JS[i:i + 2200]
        self.assertIn('$("[data-f=drop]", box).onclick = () => box.remove()', seg)

    def test_a_proposal_is_hold_and_never_amber(self):
        """It is the thing needing attention and says so in `--hold`, the
        same vocabulary a PROPOSED design language already uses. Amber on
        a card that already carries an overlay is two claims on one eye."""
        b = CSS.split("\n.ah-prop {")[1].split("}")[0]
        self.assertIn("var(--hold)", b)
        self.assertNotIn("--accent", b)
        self.assertIn("dashed", b)

    def test_the_overlay_is_opaque(self):
        """At 90% the card's own scrim read through it and the two
        collided. A proposal has to be legible before it can be argued
        with."""
        b = CSS.split("\n.ah-prop {")[1].split("}")[0]
        self.assertIn("background: var(--bg)", b)


class ColourLeftStepOne(unittest.TestCase):
    def step_of(self, needle):
        i = HTML.index(needle)
        return int(HTML.rfind('data-step="', 0, i) and
                   HTML[HTML.rfind('data-step="', 0, i) + 11])

    def test_step_one_holds_three_anchors(self):
        i = HTML.index('data-step="1"')
        j = HTML.index('data-step="2"')
        self.assertEqual(HTML[i:j].count("data-role="), 3)
        self.assertNotIn('data-role="COLOR_PALETTE"', HTML[i:j])

    def test_the_palette_sits_with_the_bible_that_proposes_it(self):
        i = HTML.index('data-step="4"')
        j = HTML.index('data-step="5"')
        self.assertIn('data-role="COLOR_PALETTE"', HTML[i:j])

    def test_it_says_why_it_is_there(self):
        self.assertIn("PROPOSED FROM THE BIBLE, NOT CHOSEN BEFORE IT", HTML)

    def test_the_swatch_result_no_longer_points_away(self):
        """The act and its result are one step apart no more."""
        self.assertIn("LANDS IN STEP 4 / COLOUR, BESIDE THIS", JS)

    def test_the_render_shelf_is_still_four(self):
        """A palette reference still rides every render. Moving a card
        cannot change what reaches a prompt."""
        self.assertIn('const AUTO_ATTACH_HEADS = ["WORLD_TEXTURE", "COLOR_PALETTE"', JS)
        from app import insights
        self.assertIn("COLOR_PALETTE", insights.STYLE_ANCHOR_ROLES)

    def test_the_step_badge_counts_what_the_step_shows(self):
        i = JS.index("const roles = AUTO_ATTACH_HEADS")
        self.assertIn('filter(r => r !== "COLOR_PALETTE")', JS[i:i + 200])


if __name__ == "__main__":
    unittest.main()
