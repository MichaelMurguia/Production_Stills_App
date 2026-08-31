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
        seg = between("The hero: the first attached picture", "hero.onclick")
        self.assertIn("styleFor(lib, words)", seg)
        self.assertNotIn("lib.find(", seg)

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


if __name__ == "__main__":
    unittest.main()
