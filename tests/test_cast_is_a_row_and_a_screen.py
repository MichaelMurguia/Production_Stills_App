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


class TheStepIsARow(unittest.TestCase):
    def test_the_step_holds_a_row_and_nothing_else(self):
        s = step("3")
        self.assertIn('id="wiz-cast-row"', s)
        # The wall that was here is gone: no roster, no uncast block, no
        # second manual-add row.
        self.assertNotIn('id="cast-screen"', s)
        self.assertNotIn("uncast-block", s)
        self.assertNotIn('id="wiz-subj-name"', s)

    def test_the_row_carries_what_the_plan_names(self):
        """Thumbnails, a rule, uncast chips, and Open the cast."""
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        for part in ("cast-row-thumbs", "cast-row-rule", "cast-row-chip",
                     "Open the cast"):
            self.assertIn(part, seg, part)

    def test_only_a_subject_with_a_picture_leads_the_rail(self):
        """B3: a row of hatched blanks says nothing the count beside it
        does not already say."""
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("subjects.filter(x => castRefsOf(x, refs).length).slice(0, 3)", seg)

    def test_it_does_not_repeat_the_count_the_badge_already_states(self):
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertNotIn("CAST &middot; ${uncast.length} UNCAST", seg)

    def test_uncast_chips_are_dashed_because_they_are_not_cards_yet(self):
        b = CSS.split(NL + ".cast-row-chip {")[1].split("}")[0]
        self.assertIn("dashed", b)

    def test_the_overflow_is_counted_rather_than_listed(self):
        i = JS.index("const renderCastRow = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("uncast.slice(0, 3)", seg)
        self.assertIn("uncast.length - 3", seg)


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
