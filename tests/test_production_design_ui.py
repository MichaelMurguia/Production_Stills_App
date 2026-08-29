"""PRODUCTION_DESIGN_UI_PLAN_2026-08-28 — the standing contracts.

An appearance pass, so these pin the rules the plan states rather than
the pixels: what carries amber, what states a cost, what is Courier and
what is prose, and — the one the plan is most insistent about — that
nothing here invents progress.

Three of the plan's instructions were NOT followed, and each is recorded
in `docs/RETIRED_PLANS.md` with its reason. Two are renames the user made
on 2026-08-28, after the plan was written. The third is the camera
grammar row, which both mocks show and which was retired on 2026-08-25
with evidence: a production-wide default nobody chose, contradicting the
cinematography grammar, which defeated the framing axis for two days of
renders. The user's ruling on 2026-08-29 was to leave it retired.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def block(sel):
    """The rule for exactly this selector.

    Anchored to the line start, or `.ah-state {` also matches inside
    `.ah-role, .ah-state {` and the test reads the wrong rule."""
    return CSS.split(chr(10) + sel)[1].split("}")[0]


class TheImageIsTheHero(unittest.TestCase):
    """§2.6 / §3.2. An anchor is a LOOK, and the card led with its name."""

    def test_the_card_is_the_picture_at_its_stated_ratio(self):
        b = block(".anchor-hero {")
        self.assertIn("aspect-ratio: 1.586", b)

    def test_the_whole_card_is_one_control(self):
        self.assertIn('<button type="button" class="anchor-hero"', HTML)
        self.assertEqual(HTML.count('class="anchor-hero"'), 4)

    def test_the_state_is_amber_until_the_anchor_is_set(self):
        """§2.3 — amber is the primary action or something needing
        attention. An unset anchor is the second; a set one is neither."""
        self.assertIn("var(--accent)", block(".ah-state {"))
        self.assertIn("var(--ink-dim)", block(".ah-state.set {"))

    def test_a_card_with_no_picture_states_it(self):
        """B3 — a reserved shape is forbidden unless it states the
        blocker keeping it empty."""
        self.assertIn("repeating-linear-gradient", block(".ah-shot.none {"))
        i = JS.index('$("[data-f=hero-name]"')
        self.assertIn("Not set", JS[i - 900:i + 200])

    def test_the_cards_carry_no_ground_of_their_own(self):
        b = block(".wiz-cols-anchors .wiz-col {")
        self.assertIn("background: none", b)
        self.assertIn("border: 0", b)


class TheJurisdictionMovedToThePicker(unittest.TestCase):
    """§3.2 ruling — the SETS / NOT pair belongs where the boundary is
    actually being decided."""

    def test_no_anchor_card_states_it_any_more(self):
        self.assertNotIn('<p class="hint">SETS', HTML)

    def test_all_three_catalogue_pickers_do(self):
        self.assertEqual(JS.count("sets: \""), 3)
        self.assertIn('<p class="rs-juris mono">SETS ${esc(sets)}', JS)

    def test_the_palette_modal_does_too(self):
        i = JS.index("const openPaletteModal =")
        seg = JS[i:i + 2200]
        self.assertIn("SETS hue", seg)
        self.assertIn("NOT framing", seg)

    def test_the_jurisdiction_is_courier(self):
        """Rule 2 — a scope the machine asserts, not prose."""
        self.assertIn("var(--mono)", block(".rs-juris {"))


class TheThingsThatSpendSayThatTheyDo(unittest.TestCase):
    """§2.4 — a price found afterwards is a bill."""

    def test_every_spending_verb_has_its_cost_beside_it(self):
        for phrase in ("COSTS A MODEL CALL", "THIS SPENDS MONEY"):
            self.assertIn(phrase, HTML, phrase)

    def test_the_cost_is_courier_and_never_amber(self):
        b = block(".cost {")
        self.assertIn("var(--ink-faint)", b)
        self.assertNotIn("--accent", b)

    def test_the_self_check_states_that_it_costs_and_never_edits(self):
        self.assertIn("ADVISORY &middot; IT NEVER EDITS &middot; NOT RUN ON SAVE", HTML)


class OneChoiceOneControl(unittest.TestCase):
    """§2.4 — segmented pickers are bordered spans; the current one gets
    an amber BORDER, not a fill."""

    def test_the_current_segment_takes_a_border_and_not_a_fill(self):
        b = block(".seg-opt.on {")
        self.assertIn("border-color: var(--accent)", b)
        self.assertNotIn("background", b)

    def test_a_locked_or_gated_segment_is_not_amber(self):
        """A read that has already run, and a stated "no model" gate, are
        neither a primary action nor something needing attention."""
        b = block(".seg.locked .seg-opt.on {")
        self.assertIn("var(--line)", b)
        i = JS.index("const paintProviderSeg =")
        self.assertIn('sel.disabled ? " locked" : ""', JS[i:i + 900])

    def test_the_select_is_still_the_one_source_of_truth(self):
        """Two stores for one answer is how the two drift."""
        self.assertIn('id="wiz-provider" class="seg-source"', HTML)
        self.assertIn("display: none", block(".seg-source {"))
        i = JS.index("const paintProviderSeg =")
        self.assertIn("sel.value = o.value", JS[i:i + 1400])


class TheLadderStillInventsNothing(unittest.TestCase):
    """§4 — "Do not fake the progress against a timer.\""""

    def test_a_stage_bar_is_binary(self):
        """Empty, current, done. Nothing creeps, because nothing here is
        measured continuously."""
        for sel, token in ((".rl-phase span.now .rl-bar {", "--accent"),
                           (".rl-phase span.done .rl-bar {", "--ok")):
            self.assertIn(token, block(sel), sel)
        self.assertIn("height: 2px", block(".rl-bar {"))

    def test_no_percentage_and_no_animation(self):
        i = JS.index("const runLadder = {")
        seg = JS[i:JS.index("const theBible = {", i)]
        # Not a bare "%": the clock's `s % 60` is a modulo, not a
        # percentage. What is forbidden is a width driven from data and
        # anything that eases toward a number nobody counted.
        for word in ("style.width", "@keyframes", "requestAnimationFrame",
                     "transition: width", "width: ${"):
            self.assertNotIn(word, seg, word)

    def test_green_only_where_something_is_genuinely_complete(self):
        """§2.3 — `#6fae7a` green means done, and only ever appears on a
        state that is genuinely complete."""
        self.assertIn("var(--ok)", block(".rl-phase span.done b {"))
        self.assertNotIn("--ok", block(".rl-phase span {"))


class TheBibleIsTwoColumns(unittest.TestCase):
    """§3.5."""

    def test_the_document_and_its_check_are_the_left_column(self):
        i = HTML.index('<div class="bible-cols">')
        j = HTML.index("</aside>", i)
        left = HTML[i:HTML.index("<aside", i)]
        self.assertIn('id="style-bible"', left)
        self.assertIn('id="bible-check"', left)
        right = HTML[HTML.index("<aside", i):j]
        self.assertIn('id="wiz-notes"', right)
        self.assertIn('id="swatch-gen"', right)

    def test_the_editor_says_the_one_thing_you_must_not_do(self):
        """The headings are parsed by app/bible.py; renaming one silently
        stops that section reaching renders."""
        self.assertIn("SECTION HEADINGS ARE PARSED &mdash; DO NOT RENAME", HTML)

    def test_the_verb_row_governs_the_whole_step(self):
        """It belongs to neither column, so it stays above both."""
        self.assertLess(HTML.index('id="wiz-draft"'), HTML.index('<div class="bible-cols">'))


class WhatTheUserOverruled(unittest.TestCase):
    """Three of the plan's instructions were not followed. Each is a
    later ruling, and each is pinned so a future pass does not quietly
    restore the plan's version."""

    def test_step_two_keeps_the_users_name(self):
        self.assertIn("<h2>Build Design Plan", HTML)
        self.assertNotIn("Script scene scan", HTML)

    def test_the_bible_verb_keeps_the_users_name(self):
        self.assertIn("Build Art Direction Bible", HTML)

    def test_the_camera_grammar_row_stays_retired(self):
        """Both mocks show it. It was retired 2026-08-25 because a
        production-wide default nobody chose contradicted the
        cinematography grammar and defeated the framing axis for two days
        of renders. User ruling 2026-08-29: leave it."""
        self.assertNotIn('id="cam-default"', HTML)
        self.assertNotIn("CAMERA GRAMMAR", HTML)


if __name__ == "__main__":
    unittest.main()
