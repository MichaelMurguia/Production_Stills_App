"""Step 03 is a row on the stage, and the cast is a screen.

PRODUCTION_DESIGN_UI_PLAN_2026-08-28 §3.4, built 2026-08-31 after the
user said the step "was not the latest design from the latest handoff".

What it was: the whole roster rendered inline in the step, 1,546px tall,
with the uncast list appearing TWICE — once at the top of the step under
its own manual-add row, once at the bottom of the roster under a second
one. Two doors to one action, on one screen.

What §3.4 asks for: on the stage, step 03 is a ROW — cast thumbnails, a
rule, uncast chips, and Open the cast. The roster and ONE uncast list
live on the cast screen, which is "a screen, not a modal".

Nothing was dropped to get there. The retired block held bulk casting
("Cast these 8"), which the surviving list did not, so it moved across —
and it still casts by the same single-cast call, so nothing is created by
a route the single button does not also take.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
NL = chr(10)


def step(n: str) -> str:
    """One step's own markup — bounded at the next panel, not at the next
    step, because the cast screen is a panel that sits BETWEEN two steps
    and a step-to-step slice would swallow it."""
    i = HTML.index('id="tpl-wizard"')
    seg = HTML[i:HTML.index("</template>", i)]
    a = seg.index(f'data-step="{n}"')
    nxt = seg.find('<div class="panel', a)
    return seg[a:nxt if nxt > 0 else len(seg)]


class TheStepIsAnInteractiveRibbon(unittest.TestCase):
    """Corrected by the user 2026-09-01: "each thumb is clickable, and
    brings up the casting modal — you don't have to open the full cast.
    Opening the full cast should be optional. That ribbon of characters
    should be mouse draggable. 'Open the cast' should be a button, like
    the attached, not a text link."

    The first build made the row a PREVIEW — three photographed thumbs, a
    rule, three dashed chips, a text link. Nothing in it did anything, so
    every act still meant opening the roster. It is a working surface
    now."""

    def test_the_step_holds_the_ribbon_and_nothing_else(self):
        s = step("3")
        self.assertIn('id="wiz-cast-row"', s)
        self.assertNotIn('id="cast-screen"', s)
        self.assertNotIn("uncast-block", s)
        self.assertNotIn('id="wiz-subj-name"', s)

    def test_every_tile_acts(self):
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn('$$("[data-uncast]", rib).forEach(b => b.onclick', seg)
        self.assertIn('$$("[data-sid]", rib).forEach(b => b.onclick', seg)

    def test_an_uncast_tile_casts_in_place(self):
        """Without opening the roster — that is the whole point."""
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("castModal({ name: b.dataset.uncast", seg)

    def test_a_cast_tile_opens_its_own_card_not_the_roster(self):
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("castOpen = b.dataset.sid;", seg)
        self.assertIn('document.body.dataset.cast = "1";', seg)

    def test_it_shows_the_whole_cast_not_the_photographed_three(self):
        """A hatched tile under a name is not the empty shape B3 forbids —
        it is the state you would click to fix, and now the click is
        there."""
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("subjects.map(x => {", seg)
        self.assertNotIn(".slice(0, 3)", seg)

    def test_it_shows_twelve_and_does_not_scroll(self):
        """REVERSES the drag-to-scroll built 2026-09-01 (user-directed
        2026-09-10: "no scrolling for cast. Have those thumbnails larger,
        say 12 fills horizontally + Open Cast button").

        A row you have to drag hides most of a cast behind a gesture with
        no affordance, and pays for the hiding by making every tile too
        small to read."""
        self.assertIn("const CAST_ROW_N = 12;", JS)
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("tiles.slice(0, CAST_ROW_N)", seg)
        for gone in ("pointerdown", "pointermove", "scrollLeft", "dragging"):
            self.assertNotIn(gone, seg, gone)

    def test_the_twelve_fill_the_width(self):
        b = CSS.split(NL + ".cast-ribbon {")[1].split("}")[0]
        self.assertIn("grid-template-columns: repeat(12, minmax(0, 1fr))", b)
        self.assertNotIn("overflow-x", b)
        self.assertNotIn("touch-action", b)

    def test_what_the_twelve_do_not_show_is_counted_on_the_act(self):
        """Not hidden off-screen — counted, on the button that reaches
        it."""
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("const hidden = Math.max(0, tiles.length - CAST_ROW_N);", seg)
        self.assertIn("hidden ? ` <i class=\"mono\">+${hidden}</i>` : \"\"", seg)

    def test_a_cast_that_fits_says_nothing_extra(self):
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn('hidden ?', seg)
        self.assertIn('Math.max(0,', seg)

    def test_opening_the_full_cast_is_a_button(self):
        """It was a text link, which read as a caption on a row of
        pictures."""
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn('class="ghost cast-open" data-f="open-cast"', seg)
        self.assertNotIn('class="text-act" data-f="open-cast"', seg)

    def test_an_uncast_tile_is_dashed_because_it_is_not_a_card_yet(self):
        self.assertIn(".cast-tile.uncast .cast-tile-shot { border-style: dashed; }", CSS)


class TheCastIsAScreen(unittest.TestCase):
    def test_it_left_the_step_it_used_to_live_inside(self):
        i = HTML.index('id="tpl-wizard"')
        seg = HTML[i:HTML.index("</template>", i)]
        self.assertLess(seg.index('data-step="3"'), seg.index('id="cast-screen"'))
        self.assertLess(seg.index('id="cast-screen"'), seg.index('data-step="4"'))

    def test_it_replaces_the_stage_rather_than_floating_over_it(self):
        """§3.4: "a screen, not a modal" — every card on it is a card on
        Reference / Subjects, and looking at one is not a dialog."""
        self.assertIn('body[data-cast="1"] #cast-screen { display: block; }', CSS)
        self.assertIn('body[data-cast="1"] .panel.step', CSS)
        self.assertIn("#cast-screen { display: none; }", CSS)

    def test_the_flag_is_set_before_the_screen_renders(self):
        """The same lesson stage 01 learned: a stage hidden after it is
        drawn has already flashed."""
        i = JS.index("const openCast = () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertLess(seg.index('document.body.dataset.cast = "1"'),
                        seg.index("renderCastScreen()"))

    def test_there_is_a_way_back(self):
        self.assertIn('data-f="cast-back"', JS)
        self.assertIn('$("[data-f=cast-back]", host).onclick = closeCast;', JS)
        i = JS.index("const closeCast = () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("delete document.body.dataset.cast", seg)
        self.assertIn("renderCastRow()", seg)

    def test_leaving_the_screen_forgets_which_subject_was_open(self):
        """Otherwise reopening the cast lands on a detail nobody asked
        for."""
        for fn in ("const openCast = () => {", "const closeCast = () => {"):
            i = JS.index(fn)
            self.assertIn("castOpen = null;", JS[i:JS.index(NL + "  };", i)], fn)


class NoWayOfCastingWasLost(unittest.TestCase):
    def test_the_duplicate_door_is_gone(self):
        for dead in ("renderSubjectTags", "wiz-subj-tags", "wiz-subj-add",
                     "wiz-subj-name", "wiz-subj-kind"):
            self.assertNotIn(dead, JS, dead)
            self.assertNotIn(dead, HTML, dead)

    def test_bulk_casting_came_with_it(self):
        """It was the one thing the retired block had that the surviving
        list did not."""
        i = JS.index('$$("[data-bulk]", host)')
        seg = JS[i:i + 700]
        self.assertIn("castOne(u)", seg)
        self.assertIn("refreshCast()", seg)
        self.assertIn("cast${failed ?", seg)

    def test_bulk_casting_takes_the_single_cast_path(self):
        """Nothing is created by a route the single button does not also
        take."""
        self.assertEqual(JS.count("const castOne = r =>"), 1)
        i = JS.index("const castOne = r =>")
        self.assertIn('api("/api/subjects", { method: "POST"', JS[i:i + 300])

    def test_a_row_of_one_is_not_offered_a_bulk_button(self):
        """"Cast these 1" is the single button with more words."""
        i = JS.index('${rows.length > 1 ? `<button type="button" class="ghost uncast-bulk"')
        self.assertGreater(i, 0)

    def test_one_uncast_list_survives_and_it_is_the_screens(self):
        self.assertEqual(JS.count("cast-uncast"), 1)
        self.assertEqual(JS.count('id="cast-add"'), 1)


if __name__ == "__main__":
    unittest.main()
