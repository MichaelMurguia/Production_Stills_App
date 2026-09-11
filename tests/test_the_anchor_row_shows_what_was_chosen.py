"""The anchor cards wear the look they were set to.

User, 2026-08-30: *"the anchors are not showing the correct preview
images, which makes me wonder if they are properly selected at all."*

They were properly selected. Three separate faults made the row lie about
it, and each one alone was enough:

1. **The row painted before the fields were filled.** `refreshRefs()` runs
   at the top of `renderWizard`; the interview that holds the anchors' own
   words loaded two thousand lines further down. Every load painted from
   three empty inputs, so a stored anchor showed the "nothing here"
   hatching and only corrected itself if some later act happened to redraw
   the row.

2. **The row painted before the catalogues arrived.** The style libraries
   are fetched from their markdown documents; nothing waited for them, so
   every lookup missed an empty array.

3. **The hero looked for photographs only.** Five of the ten board
   rendering styles have a drawn plate and no photographed frame — they
   could not have shown a picture even with the first two fixed.

And one rule that had drifted into two copies: which catalogue entry a
stored value IS. The picker had it; the hero grew its own, slightly
different. That is how a card ends up wearing a picture that belongs to
something else.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
NL = chr(10)


def between(start: str, end: str) -> str:
    """A window bounded by two real landmarks, never by a line count — a
    fixed offset stops meaning what it meant the next time the file grows.
    """
    i = JS.index(start)
    return JS[i:JS.index(end, i)]


class OneMatcherNotTwo(unittest.TestCase):
    def test_the_resolver_exists_once(self):
        self.assertEqual(JS.count("function styleFor("), 1)

    def test_the_picker_asks_it(self):
        seg = between("const bindPicker = ", "btn.textContent = hit")
        self.assertIn("const hit = styleFor(styles, v)", seg)
        # The picker's own copy of the prefix rule is gone, not shadowed.
        self.assertNotIn("styles.find(x => x.value === v)", seg)

    def test_the_hero_asks_the_same_one(self):
        """It asks `anchorWords` now (2026-09-11) — that lookup moved when
        the BADGE turned out to need the same answer, and to have been
        getting a different one from a second implementation."""
        seg = between("The hero: the first attached picture", "hero.onclick")
        self.assertIn("const chosen = picked", seg)
        self.assertNotIn("lib.find(", seg)
        self.assertIn("const picked = anchorWords(col).picked;", JS)

    def test_it_still_recognises_the_captured_house_card(self):
        """Its value is re-derived from the bible on every open, so a
        bible that gained a line would otherwise stop matching its own
        answer (user-caught 2026-08-16)."""
        seg = between("function styleFor(", "\nfunction styleArt(")
        self.assertIn('x.key === "house"', seg)
        self.assertIn("slice(0, 110)", seg)

    def test_nothing_matches_nothing(self):
        seg = between("function styleFor(", "\nfunction styleArt(")
        self.assertIn("if (!v) return null", seg)


class EveryStyleCanShowItself(unittest.TestCase):
    """The catalogues are read from markdown at runtime, so this asserts
    against the documents rather than against a list in a test."""

    def styles(self, lib):
        from app import style_docs
        return style_docs.styles(lib)

    def plate_keys(self):
        i = JS.index("const STYLE_PLATES = {")
        return set(re.findall(r'"([^"]+)":\s*"[^"]+"', JS[i:JS.index("}", i)]))

    def shot_keys(self):
        import json
        return set(json.loads(
            (ROOT / "app/static/style-plates/index.json").read_text(encoding="utf-8")))

    def test_every_style_has_either_a_photograph_or_a_drawn_plate(self):
        drawn, shot = self.plate_keys(), self.shot_keys()
        missing = [f"{lib}/{st['key']}"
                   for lib in ("texture", "cinematography", "rendering")
                   for st in self.styles(lib)
                   if st["key"] not in shot and st["name"] not in drawn]
        self.assertEqual(missing, [], f"no picture at all: {missing}")

    def test_five_renderings_rest_entirely_on_the_drawn_plate(self):
        """The reason the photograph-only hero showed nothing. Stated as a
        number so that shooting frames for them is visible here."""
        shot = self.shot_keys()
        only_drawn = [st["key"] for st in self.styles("rendering")
                      if st["key"] not in shot]
        self.assertEqual(len(only_drawn), 5, only_drawn)


class TheHeroTakesTheDrawnPlate(unittest.TestCase):
    def seg(self):
        return between("function styleArt(", "\nfunction plateShots(")

    def test_a_photograph_wins(self):
        self.assertIn("if (shots.length) return { src: shots[0], drawn: false }",
                      self.seg())

    def test_then_the_house_cards_own_panel(self):
        self.assertIn("if (st.shot) return { src: st.shot, drawn: false }", self.seg())

    def test_then_the_drawn_plate_as_a_picture(self):
        """The catalogue cell inlines the SVG; the hero paints a
        background-image and needs a URL, so the same markup goes over as
        a data URI rather than being drawn a second way."""
        s = self.seg()
        self.assertIn("PLATE[st.plate]", s)
        self.assertIn('"data:image/svg+xml," + encodeURIComponent(svg)', s)
        self.assertIn("drawn: true", s)

    def test_and_otherwise_nothing_which_the_card_states(self):
        self.assertIn("return null", self.seg())
        self.assertIn('shot.classList.toggle("none", !art)', JS)

    def test_a_diagram_is_shown_whole_and_a_frame_is_not(self):
        """`cover` on a 68x56 diagram crops the one thing it says."""
        b = CSS.split("\n.ah-shot.drawn {")[1].split("}")[0]
        self.assertIn("background-repeat: no-repeat", b)
        self.assertNotIn("cover", b)
        self.assertIn('shot.classList.toggle("drawn", !!art?.drawn)', JS)


class TheRowWaitsForWhatItReads(unittest.TestCase):
    def test_the_anchors_own_words_load_before_the_row_paints(self):
        """Fault 1. The order is the fix, so the order is the test."""
        self.assertLess(JS.index('const IV = { "#wiz-texture"'),
                        JS.index("  await refreshRefs();"))

    def test_and_they_are_awaited_not_fired_off(self):
        seg = between('const IV = { "#wiz-texture"', "  await refreshRefs();")
        self.assertIn('await api("/api/wizard/interview")', seg)

    def test_a_first_run_with_nothing_saved_still_paints(self):
        seg = between('const IV = { "#wiz-texture"', "  await refreshRefs();")
        self.assertIn("catch { /* first run — nothing saved yet */ }", seg)

    def test_the_catalogues_are_in_hand_before_the_row_paints(self):
        """Fault 2. All four, including the house style's own capture —
        the house card is precisely the one whose value is prefix-matched,
        and without it a production that captured its own look would see
        its anchor reported as words rather than as a card."""
        seg = between("The heroes below name a catalogue style",
                      'for (const col of $$(".wiz-col[data-role]"))')
        for loader in ("loadTextureStyles()", "loadCinemaStyles()",
                       "loadPlateShots()", "loadRenderStyles().then(adoptHouseStyle)"):
            self.assertIn(loader, seg, loader)
        self.assertIn("await Promise.all", seg)

    def test_that_wait_costs_one_fetch_a_session_not_one_a_refresh(self):
        """refreshRefs runs on every upload, approval and deletion."""
        self.assertIn("PLATE_SHOTS ??= fetch", JS)
        self.assertIn("if (!card || card._adopted) return;", JS)


class TheLabelsSurviveAPicture(unittest.TestCase):
    def test_the_top_pair_has_a_scrim_like_the_bottom_pair(self):
        """Only a problem once the pictures started arriving: the role
        label washed out over a bright sky."""
        b = CSS.split("\n.anchor-hero::before {")[1].split("}")[0]
        self.assertIn("linear-gradient(to bottom", b)
        self.assertIn("pointer-events: none", b)

    def test_it_sits_under_the_labels_and_over_the_picture(self):
        top = CSS.split("\n.anchor-hero::before {")[1].split("}")[0]
        lab = CSS.split("\n.ah-role, .ah-state {")[1].split("}")[0]
        self.assertIn("z-index: 1", top)
        self.assertIn("z-index: 2", lab)


class TheTakeoverLetsThePageThrough(unittest.TestCase):
    """User, 2026-08-30: *"needs to be translucent showing the panel
    behind — maybe .75 opacity — otherwise it is too disconcerting."*

    Opaque, it read as the app having gone away. Translucent, the lock
    reads as a pause."""

    def body(self):
        return CSS.split("\n.sp-takeover {")[1].split("}")[0]

    def test_it_is_translucent(self):
        b = self.body()
        self.assertIn("75%", b)
        self.assertIn("transparent", b)
        self.assertNotIn("background: var(--bg);", b)

    def test_it_still_covers_the_page_it_locks(self):
        b = self.body()
        self.assertIn("position: fixed", b)
        self.assertIn("inset: 0", b)




class AProposalShowsTheLookItProposes(unittest.TestCase):
    """User, 2026-08-30, on a freshly read screenplay: *"preview images
    are still not showing on the anchor cards."*

    They were the PROPOSED cards. A proposal named a style in words over
    an opaque panel, so the one card in the app whose whole job is "here
    is a look, do you want it" was the one card showing no look."""

    def test_a_standing_proposal_is_state_the_row_reads(self):
        """Not just a box appended to a card. refreshRefs runs again on
        every upload, approval and deletion, and a repaint that knew
        nothing about the proposal would reset the picture and the badge
        underneath a proposal box still sitting on top of them."""
        self.assertLess(JS.index("let wizProposals = {};"),
                        JS.index("const refreshRefs = async () => {"))
        self.assertEqual(JS.count("let wizProposals"), 1)

    def test_the_proposed_style_resolves_the_same_way_a_chosen_one_does(self):
        """Through the same matcher — a proposal cannot show a picture a
        pick would not. The chosen half moved into `anchorWords`
        (2026-09-11) when the badge turned out to need it too."""
        seg = between("A proposal names a style.", 'hero.classList.toggle("proposed"')
        self.assertIn("styleFor(lib, prop.value)", seg)
        # Never over a real choice: an anchor the director set wins.
        self.assertIn("const chosen = picked", seg)
        self.assertIn("|| (!words && prop", seg)

    def test_the_card_does_not_report_none_while_showing_a_proposal(self):
        seg = between("A card showing a proposed look must not also report NONE.",
                      "/* The hero: the first attached picture")
        self.assertIn('propped ? "PROPOSED"', seg)

    def test_the_proposal_speaks_in_hold_not_amber(self):
        """Amber would be the third colour on a card already carrying two,
        saying the word its own kicker says two lines below."""
        self.assertIn(".ah-state.prop { color: var(--hold); }", CSS)
        kick = CSS.split("\n.ah-prop-kick {")[1].split("}")[0]
        self.assertIn("var(--hold)", kick)

    def test_one_scrim_at_a_time(self):
        """The proposal's kicker, name and reason ARE the card's scrim
        while it stands; the card's own would be a second one saying
        nearly the same thing over the same picture."""
        self.assertIn(".anchor-hero.proposed .ah-scrim { display: none; }", CSS)
        self.assertIn('hero.classList.toggle("proposed", !!prop);', JS)

    def test_both_answers_end_the_proposal_and_repaint(self):
        seg = between("const showProposals =", "const showTakeover =")
        self.assertEqual(seg.count("delete wizProposals[ANCHOR_ROLE[field]];"), 2)
        self.assertEqual(seg.count("refreshRefs();"), 3, "use, dismiss, and first paint")


class TheHouseSlotKeepsItsPhotographs(unittest.TestCase):
    """Rendering slot 0 is the HOUSE slot: the client renames that style's
    key to "house" and keeps the document's own key on `docKey`. The plate
    manifest is written against the documents, so it files that style's
    photographs under the original key — and asking for them by `key`
    returned nothing.

    The first rendering style in the catalogue was therefore the one style
    that could never show its photograph, in the picker cell as much as on
    the anchor card. It is also the style the screenplay read proposed."""

    def test_the_manifest_is_asked_by_the_documents_key(self):
        self.assertIn("const plateKey = st => st.docKey || st.key;", JS)

    def test_every_caller_asks_that_way(self):
        self.assertEqual(JS.count("plateShots(st.key)"), 0)
        self.assertEqual(JS.count("plateShots(x.key)"), 0)
        for caller in ("plateShots(plateKey(st)).slice(0, 3)",
                       "const shots = plateShots(plateKey(st));",
                       "!plateShots(plateKey(x)).length"):
            self.assertIn(caller, JS, caller)

    def test_the_slot_still_carries_the_documents_key(self):
        seg = between("const loadRenderStyles = async ()", "\n// UNCANONIZED")
        self.assertIn("out[0].docKey = out[0].key;", seg)
        self.assertIn('out[0].key = "house";', seg)

    def test_the_style_it_stands_on_has_photographs_to_lose(self):
        """If this ever stops being true the bug above stops being one,
        and this test should be deleted rather than adjusted."""
        import json
        m = json.loads(
            (ROOT / "app/static/style-plates/index.json").read_text(encoding="utf-8"))
        from app import style_docs
        first = style_docs.styles("rendering")[0]
        self.assertIn(first["key"], m, first["key"])




class AChosenStyleReadsAsChosen(unittest.TestCase):
    """User, 2026-09-11: "when I confirm Weathered it does not change
    'Proposed from the screenplay'. Isn't there a normal selected mode
    based on designs?"

    The accept worked — the interview held the Weathered value. What did
    not change was the BADGE, which said IN WORDS, the label for a
    sentence somebody typed. Choosing from the catalogue and describing a
    look in your own words are different acts.

    And the reason it never showed SELECTED even once the badge learned
    the word: `syncAnchorBadges` runs after `refreshRefs` and on every
    change, and it only knew NONE <-> IN WORDS. It set the badge correctly
    and then overwrote it a tick later. One question, two answers."""

    def words_fn(self):
        i = JS.index("const anchorWords = (col) => {")
        return JS[i:JS.index(NL + "  };", i)]

    def test_one_rule_answers_what_the_words_amount_to(self):
        self.assertEqual(JS.count("const anchorWords = (col) => {"), 1)
        s = self.words_fn()
        self.assertIn('return { label: "NONE", set: false };', s)
        self.assertIn('label: picked ? "SELECTED" : "IN WORDS"', s)

    def test_both_readers_ask_it(self):
        """The row's badge and the late syncer. They disagreed."""
        self.assertIn("const picked = anchorWords(col).picked;", JS)
        self.assertIn("const w = anchorWords(col);", JS)

    def test_the_late_syncer_no_longer_has_its_own_answer(self):
        i = JS.index("const syncAnchorBadges = () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("badge.textContent = w.label;", seg)
        self.assertNotIn('inWords ? "IN WORDS" : "NONE"', seg)

    def test_it_leaves_a_standing_proposal_alone(self):
        """It knows nothing about the references that decide the rest of
        the card's states, so it must not overwrite them either."""
        i = JS.index("const syncAnchorBadges = () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn('if (badge.textContent.trim() === "PROPOSED") continue;', seg)

    def test_it_still_leaves_a_picture_count_alone(self):
        i = JS.index("const syncAnchorBadges = () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("/^\\d/.test(badge.textContent.trim())", seg)

    def test_the_row_reports_selected_above_in_words(self):
        i = JS.index('badge.textContent = nMine')
        seg = JS[i:i + 420]
        self.assertLess(seg.index('picked ? "SELECTED"'), seg.index('inWords ? "IN WORDS"'))


class ThePeriodSaysWhatTheReadFound(unittest.TestCase):
    """User, 2026-09-11: "This is dumb: you can put text into the app based
    on specific screenplays. That's a development note, not an app
    message. Get rid of it. For period, auto fill from screenplay and
    allow author to edit it."

    The line named a failure from ONE production's screenplay. The read
    already asks for the period and already yields to a hand-set one; what
    was missing was the card saying so when the read came back empty."""

    def seg(self):
        i = JS.index('<span class="read-log-kicker">PERIOD</span>')
        return JS[i:JS.index("read-tiles", i)]

    def test_the_development_note_is_gone(self):
        for gone in ("WW2 aircraft", "far-future salt pan"):
            self.assertNotIn(gone, JS, gone)

    def test_an_unset_period_says_the_read_looked(self):
        self.assertIn("The read found no period stated in the screenplay",
                      self.seg())

    def test_a_set_period_states_the_rule_and_nothing_else(self):
        self.assertIn("Every render is held to this — nothing in frame may postdate it.",
                      self.seg())

    def test_unstated_is_not_treated_as_a_value(self):
        """The scan is TOLD to answer UNSTATED when the screenplay does not
        fix a period, and that string is truthy — so the card offered
        "Edit" and claimed every render was held to it."""
        s = self.seg()
        self.assertIn('wizNoPeriod(analysis.period) ? "State it" : "Edit"', s)
        self.assertIn("wizNoPeriod(analysis.period)", s)
        self.assertNotIn('analysis.period ? "Edit"', s)

    def test_the_read_still_asks_the_screenplay_for_it(self):
        w = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
        self.assertIn('"period": "WHEN this story is set', w)
        self.assertIn("Say UNSTATED if the screenplay genuinely does not fix a period", w)

    def test_a_hand_set_period_survives_a_re_read(self):
        """Auto-fill must never overrule the author — a scan that fails to
        find one would otherwise erase what they typed."""
        w = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
        self.assertIn('if _no_period(out.get("period")) and not _no_period(prior.get("period")):',
                      w)


if __name__ == "__main__":
    unittest.main()
