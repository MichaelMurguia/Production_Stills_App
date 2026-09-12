"""The findings show what the read found, not just how much of it.

PRODUCTION_DESIGN_UI_PLAN_2026-08-28 §3.3, built 2026-08-31 — the other
half of the plan that was never built, alongside §3.4.

Three things it asks for that the findings did not do:

1. **Design languages as image-led cards**, not Courier chips. A design
   language is what a panel is ALLOWED to look like, and a row of words
   is the one presentation that shows none of it. The picture is real:
   references carry a language scope (`store.reference_language`), so a
   card leads with one actually scoped to it, and states its blank when
   there is none (B3).

2. **Environments as rows naming their locations in Courier**, not a grid
   of cards stating a COUNT of locations — the one fact about an
   environment you cannot act on.

3. **Subjects as chips with the act they lead to.** The SUBJECTS counter
   always pointed at step 03, but what it counted was never shown here,
   so the number was the whole of what the read said about the cast.

NOT built, and deliberately: the plan's 120px thumb on each environment
row. An environment has no picture anywhere in this app, and a slot that
can never fill is worse than no slot. Logged for the designer.

Also superseded: §3.3 puts the logline first at 20px. The user moved it
out of these findings entirely on 2026-08-31 — it rides above the whole
stage now. A pass that "finishes the plan" must not bring it back.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
NL = chr(10)


class DesignLanguagesLeadWithAPicture(unittest.TestCase):
    def test_they_are_cards_and_no_longer_chips(self):
        i = JS.index('const chip = document.createElement("span");')
        seg = JS[i:i + 400]
        self.assertIn('chip.className = "lang-card"', seg)
        self.assertNotIn('"chip" + (open', seg)

    def test_the_picture_is_an_approved_panel_in_that_language(self):
        """Real linkage, not decoration.

        It was a REFERENCE plate scoped to the language until 2026-09-12
        (user: "I have no idea what these blank spots are and neither
        will our users"). A reference is an input to a render and being
        scoped to a language is a vocabulary nothing on this screen
        teaches; a panel is what the language actually produced, and
        every production gets panels."""
        i = JS.index("const shot = wizLangArt[")
        seg = JS[i:i + 400]
        self.assertIn('String(w.name || "").trim().toUpperCase()', seg)
        self.assertIn('art.style.backgroundImage = `url("${shot}")`', seg)
        self.assertNotIn("wizRefs", seg)

    def test_the_server_derives_it_from_approved_panels(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = main.index('@app.get("/api/design-languages/examples")')
        seg = main[i:main.index('@app.get("/api/subjects/scenes")', i)]
        self.assertIn('cand.get("status") != "APPROVED"', seg)
        # A panel's own languages, or its sheet's when it states none —
        # the same fallback the render itself uses.
        self.assertIn('panel.get("design_languages")', seg)
        self.assertIn("or sheet", seg)
        self.assertIn("/api/specs/{sid}/candidates/{cid}/image", seg)

    def test_it_is_asked_for_once_and_repaints(self):
        """A language that HAS a panel must not paint its blank and stay
        wrong — the same rule the reference fetch already followed."""
        self.assertIn("if (!wizLangArtAsked) loadWizLangArt().then(renderWorlds);", JS)

    def test_a_language_with_no_panel_says_what_will_fill_it(self):
        """B3: a reserved shape is forbidden unless it says what keeps it
        empty. The old sentence named a mechanism ("no reference SCOPED
        to this language") instead of a next step, in a word the user had
        never been shown."""
        i = JS.index('art.className = "lang-shot"')
        seg = JS[i:i + 500]
        self.assertIn("Examples will appear here from your panels.", seg)
        self.assertNotIn("SCOPED", seg)
        b = CSS.split(NL + ".lang-shot.none {")[1].split("}")[0]
        self.assertIn("repeating-linear-gradient", b)

    def test_that_sentence_is_prose_and_readable(self):
        """Rule 2 — Archivo carries prose; Courier is for machine data.
        It was 9px uppercase Courier, which reads as an error code on a
        broken image."""
        b = CSS.split(NL + ".lang-shot.none i {")[1].split("}")[0]
        self.assertIn("font-family: var(--sans)", b)
        self.assertIn("font-size: 18px", b)
        # The section sets uppercase + tracking on `.fgroup` and it
        # INHERITS all the way down, so a sentence rendered as a wide
        # caps label until both were reset here (measured from the DOM,
        # 2026-09-12 — the stylesheet alone looked correct).
        self.assertIn("text-transform: none", b)
        self.assertIn("letter-spacing: 0", b)

    def test_the_header_names_the_thing_and_stops(self):
        """User, 2026-09-12. The explanation lives behind the `?`, which
        is what the `?` is for."""
        i = JS.index('<span class="uncast-label">DESIGN LANGUAGES')
        self.assertIn('DESIGN LANGUAGES' + NL, JS[i:i + 80])
        self.assertNotIn("WHAT A PANEL IS ALLOWED TO LOOK LIKE", JS)

    def test_the_help_names_no_other_productions_screenplay(self):
        """A development note, not app copy — the same fault the user cut
        from the period card on 2026-09-11."""
        i = JS.index("  langs: \"<b>A named visual world")
        seg = JS[i:JS.index("  envs:", i)]
        for leak in ("GRM", "Resistance", "Terra Nova"):
            self.assertNotIn(leak, seg, leak)
        self.assertLess(len(seg), 900, "it was three paragraphs; it is two")

    def test_confirm_and_drop_still_sit_on_the_card(self):
        """The chip's whole behaviour survives the shape change."""
        i = JS.index('const body = document.createElement("span");')
        seg = JS[i:i + 1400]
        self.assertIn('data-f="confirm"', seg)
        self.assertIn('data-f="drop"', seg)
        self.assertIn('$("[data-f=confirm]", body).onclick', JS)
        self.assertIn('$("[data-f=drop]", body).onclick', JS)

    def test_a_proposed_language_is_hold_and_dashed(self):
        b = CSS.split(NL + ".lang-card.proposed {")[1].split("}")[0]
        self.assertIn("dashed", b)
        self.assertIn("var(--hold)", b)
        self.assertNotIn("--accent", b)

    def test_the_shelf_is_fetched_once_if_nothing_else_has(self):
        """Otherwise a language that HAS a reference paints its stated
        blank and never corrects itself — the anchor-row bug again."""
        self.assertIn("if (!wizRefsAsked) loadWizRefs().then(renderWorlds);", JS)
        self.assertIn("wizRefs = refs;", JS)


class EnvironmentsNameTheirLocations(unittest.TestCase):
    def test_they_are_rows_not_a_grid_of_cards(self):
        self.assertNotIn("env-card", JS)
        self.assertNotIn("env-grid", JS)
        self.assertIn('card.className = "env-row"', JS)
        self.assertIn(".env-rows { display: flex; flex-direction: column;", CSS)

    def test_each_row_names_its_locations_in_courier(self):
        i = JS.index('<div class="env-locs mono">')
        seg = JS[i:i + 400]
        self.assertIn("locs.map(l =>", seg)
        b = CSS.split(NL + ".env-locs {")[1].split("}")[0]
        self.assertIn("letter-spacing", b)

    def test_an_environment_with_no_locations_says_so(self):
        i = JS.index('<div class="env-locs mono">')
        self.assertIn("NO LOCATION ASSIGNED", JS[i:i + 500])

    def test_the_count_is_kept_beside_the_names(self):
        """The names are what you act on; the count is still the thing the
        tile above links to."""
        i = JS.index('<div class="env-locs mono">')
        self.assertIn("${locs.length} LOCATION${locs.length === 1", JS[i:i + 700])

    def test_no_thumb_slot_was_built_that_cannot_fill(self):
        """§3.3 asks for a 120px thumb per row. An environment has no
        picture anywhere in this app. A slot that can never fill is worse
        than no slot (B3) — this is logged for the designer, not faked."""
        i = JS.index('card.className = "env-row"')
        seg = JS[max(0, i - 900):i]
        self.assertIn("nothing to put in it", seg)
        self.assertNotIn("env-shot", CSS)


class TheSubjectsRailShowsWhatItCounts(unittest.TestCase):
    def seg(self):
        i = JS.index('const subjRail = $("#wiz-subj-rail", host);')
        return JS[i:JS.index("// ---- environment cards", i)]

    def test_the_read_names_the_subjects_it_found(self):
        s = self.seg()
        self.assertIn('class="subj-rail"', s)
        self.assertIn("named.map(n =>", s)

    def test_a_subject_that_has_a_card_reads_differently(self):
        s = self.seg()
        self.assertIn('have.has(n.toUpperCase()) ? " cast" : ""', s)
        b = CSS.split(NL + ".subj-chip.cast {")[1].split("}")[0]
        self.assertIn("border-style: solid", b)
        dashed = CSS.split(NL + ".subj-chip {")[1].split("}")[0]
        self.assertIn("dashed", dashed)

    def test_cast_state_comes_from_the_shelf_not_from_the_read(self):
        """The cast screen and this rail must never disagree about who has
        a card, so both ask /api/subjects."""
        self.assertIn('api("/api/subjects").then(existing =>', self.seg())

    def test_it_offers_the_one_act_it_leads_to(self):
        s = self.seg()
        self.assertIn("Cast what is uncast", s)
        self.assertIn("go.onclick = openCast", s)

    def test_nothing_uncast_offers_nothing(self):
        self.assertIn("Every subject the read found is on a card.", self.seg())


class TheLoglineDoesNotComeBack(unittest.TestCase):
    """§3.3 opens with "logline at 20px prose" at the top of the findings.
    The user moved it out of the findings entirely on 2026-08-31 — it
    rides above the whole stage. A later pass reading the plan afresh must
    not restore it."""

    def test_the_findings_strip_holds_no_logline(self):
        i = JS.index('host.innerHTML = `' + NL + '      <div class="read-strip">')
        self.assertNotIn("read-logline", JS[i:JS.index("read-tiles", i)])

    def test_it_still_lives_in_its_own_section_above_the_stage(self):
        html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
        i = html.index('id="tpl-wizard"')
        seg = html[i:html.index("</template>", i)]
        self.assertLess(seg.index('id="wiz-logline"'), seg.index('data-step="1"'))


if __name__ == "__main__":
    unittest.main()
