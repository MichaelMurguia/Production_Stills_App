"""The read stops pretending to take a minute, and the logline leads.

Three user-directed changes, 2026-08-31, from watching a real read.

FIRST — the walk. The scene ticker spent sixty seconds replaying a parse
that had already finished, and gave every scene the identical interval.
That uniformity is what gave it away: "each scene is the exact same
length of time." Ten seconds now, and no two rows the same.

The parse being a replay is not a deception — every line in it was
genuinely parsed out of the screenplay, locally, before the first row
appeared. But the PACE was always a choice, and a minute made the surface
the slow part of a read whose real cost is the model call behind it.

SECOND — the finish panel. It spent seven seconds showing a count and a
route to Production Design, then removed itself. A primary action on a
timer is gone if you look away, with no way back. The route now lives on
the stage for as long as a read exists; the panel shows nothing and goes.

THIRD — the logline. It sat inside step 2's tally of what the read
produced. It is not a tally: it is what the read understood the film to
BE, and every numbered step answers to it. Its own unnumbered section,
above the whole stage.
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

READ = JS.split("const theRead")[1].split("async function startTheRead")[0]
NL = chr(10)


class TheWalkTakesTenSecondsAndDoesNotTick(unittest.TestCase):
    def test_the_budget_is_ten_seconds(self):
        self.assertIn("10000 / Math.max(1, this.scenes.length)", READ)
        self.assertNotIn("60000 / Math.max(1", READ)

    def test_a_row_is_never_too_quick_to_read_nor_slow_enough_to_stall(self):
        self.assertIn("Math.max(160, Math.min(700,", READ)

    def test_no_two_rows_are_the_same_length(self):
        """The uniform interval was the tell."""
        i = READ.index("const jitter =")
        self.assertIn("Math.random()", READ[i:i + 120])
        self.assertIn("this.walk = setTimeout(() => this.step(), Math.round(jitter));",
                      READ)

    def test_the_jitter_cannot_produce_a_zero_or_a_stall(self):
        """0.55-1.45 of the dwell, which is 160-700ms: 88ms at the very
        fastest, just over a second at the very slowest."""
        i = READ.index("const jitter =")
        self.assertIn("(0.55 + Math.random() * 0.9)", READ[i:i + 120])

    def test_the_walk_is_still_a_replay_of_a_real_local_parse(self):
        """Nothing here invents content. The pace is a choice; the scenes
        and observations are not."""
        self.assertIn('api("/api/screenplay/digest")', READ)
        self.assertIn("this.scenes = (d && d.scenes) || []", READ)

    def test_the_clock_is_still_wall_time(self):
        """The one number on the surface that must never be paced."""
        self.assertIn("Math.round((Date.now() - this.t0) / 1000)", READ)


class TheFinishPanelKeepsNothing(unittest.TestCase):
    def test_it_shows_no_summary_and_no_buttons(self):
        i = READ.index('const tick = $("#rd-ticker", host);')
        seg = READ[i:READ.index('if (this.phase === "previewed")', i)]
        self.assertNotIn("rd-found", seg)
        self.assertNotIn("rd-go", seg)
        self.assertNotIn("DESIGN LANGUAGE(S)", seg)

    def test_it_still_leaves(self):
        i = READ.index("finish(analysis) {")
        seg = READ[i:READ.index(NL + "  fail(msg) {", i)]
        self.assertIn("this.dismiss()", seg)

    def test_the_result_still_survives_the_panel(self):
        """The toast carries the counts durably — the finding must outlive
        the surface that announced it."""
        i = READ.index("finish(analysis) {")
        seg = READ[i:READ.index(NL + "  fail(msg) {", i)]
        self.assertIn("The read found ${langs} design language(s)", seg)

    def test_a_failed_read_keeps_its_own_buttons(self):
        """A failure is not a receipt — it states a condition and links to
        where it is resolved, and that must not be on a timer either."""
        i = READ.index('if (this.phase === "failed") {')
        seg = READ[i:i + 900]
        self.assertIn("rd-dismiss", seg)
        self.assertIn("Connect a working key", seg)


class TheRouteIsPermanent(unittest.TestCase):
    def seg(self):
        i = JS.index('$("#scr-downstream").innerHTML')
        return JS[i:JS.index("if (sp) renderLocations(state, langs);", i)]

    def test_it_lives_on_the_stage_under_the_counts_the_read_produced(self):
        self.assertIn('data-f="go-wizard"', self.seg())
        self.assertIn("Review the read on Prod. Design", self.seg())

    def test_it_appears_only_when_there_is_a_read_to_review(self):
        self.assertIn("analysis.analyzed_at ?", self.seg())

    def test_it_goes_where_it_says(self):
        self.assertIn('goWiz.onclick = () => showView("wizard")', self.seg())

    def test_it_is_not_amber(self):
        """Stage 01's one primary act is uploading a draft. A second amber
        button is two claims on the same eye."""
        self.assertIn('class="ghost ds-go"', self.seg())
        b = CSS.split(NL + ".ds-go {")[1].split("}")[0]
        self.assertNotIn("--accent", b)


class TheLoglineLeads(unittest.TestCase):
    def test_it_has_its_own_section_above_step_one(self):
        i = HTML.index('id="tpl-wizard"')
        seg = HTML[i:HTML.index("</template>", i)]
        self.assertLess(seg.index('id="wiz-logline"'), seg.index('data-step="1"'))

    def test_that_section_is_unnumbered_and_has_no_heading(self):
        """A numbered step promises something is done to it here. Nothing
        is."""
        i = HTML.index('id="wiz-logline"')
        seg = HTML[HTML.rindex("<div", 0, i):HTML.index("</div>", i) + 6]
        self.assertNotIn("data-step", seg)
        self.assertNotIn("<h2", seg)

    def test_it_left_the_read_strip(self):
        i = JS.index('host.innerHTML = `' + NL + '      <div class="read-strip">')
        seg = JS[i:JS.index("read-tiles", i)]
        self.assertNotIn("read-logline", seg)

    def test_it_arrives_intact(self):
        """Transliterated, not reinterpreted: the same markup, the same
        classes, the same words."""
        i = JS.index('const logHost = $("#wiz-logline");')
        seg = JS[i:JS.index("host.innerHTML = `", i)]
        self.assertIn('<div class="read-logline">', seg)
        self.assertIn('<span class="read-log-kicker">LOGLINE</span>', seg)
        self.assertIn("esc(analysis.logline)", seg)

    def test_it_keeps_its_amber_rule_and_its_measure(self):
        b = CSS.split(NL + ".read-logline {")[1].split("}")[0]
        self.assertIn("border-left: 2px solid var(--accent)", b)
        self.assertIn("max-width: 720px",
                      CSS.split(NL + ".read-logline p {")[1].split("}")[0])

    def test_a_read_with_no_logline_shows_no_empty_box(self):
        i = JS.index('const logHost = $("#wiz-logline");')
        seg = JS[i:JS.index("host.innerHTML = `", i)]
        self.assertIn('logHost.classList.toggle("hidden", !analysis.logline)', seg)

    def test_the_section_adds_no_second_frame_around_it(self):
        """`.read-logline` already carries the rule, the kicker and the
        padding it had in step 2."""
        b = CSS.split(NL + ".wiz-logline {")[1].split("}")[0]
        self.assertIn("padding: 0", b)
        self.assertIn("border: 0", b)


if __name__ == "__main__":
    unittest.main()
