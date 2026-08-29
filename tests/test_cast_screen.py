"""The cast screen — a roster, and a detail that is a screen.

PRODUCTION_DESIGN_UI_PLAN §3.4, revised 2026-08-29.

The subject card led with its name and a row of chrome and put the
photograph in a strip below three controls. But the photograph IS the
reference — the thing every prompt of that subject is held to — and it
was the smallest element on its own card.

The detail is a screen and not a modal for the same reason: a modal
would put a scrim between a director and that one image.

This screen owns no data. Every card on it is a card on Reference /
Subjects, and it says so on the roster.
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
    return CSS.split(chr(10) + sel)[1].split("}")[0]


class ThePictureIsTheCard(unittest.TestCase):
    def test_a_character_and_a_vehicle_keep_their_own_ratios(self):
        """1:1.25 for a character, 1.85:1 for a vehicle or a prop, and
        never letterboxed into the other shape."""
        self.assertIn("aspect-ratio: .8", block(".cast-shot {"))
        self.assertIn("aspect-ratio: 1.85",
                      CSS.split('.cast-card[data-kind="VEHICLE"] .cast-shot,')[1].split("}")[0])

    def test_the_card_carries_no_chrome_of_its_own(self):
        b = block(".cast-card {")
        self.assertIn("background: none", b)
        self.assertIn("border: 0", b)

    def test_a_card_with_no_photograph_hatches_rather_than_reserving(self):
        self.assertIn("repeating-linear-gradient", block(".cast-shot.none {"))

    def test_the_roster_groups_by_kind(self):
        i = JS.index("const renderCastRoster =")
        seg = JS[i:JS.index("const renderCastDetail =", i)]
        self.assertIn('[["CHARACTER", "CHARACTERS"], ["VEHICLE", "VEHICLES"]', seg)
        self.assertIn("CAST", seg)

    def test_it_says_the_cards_are_not_its_own(self):
        i = JS.index("const renderCastRoster =")
        self.assertIn("EVERY CARD HERE IS A CARD ON REFERENCE / SUBJECTS",
                      JS[i:i + 1200])


class TheUncastAreAList(unittest.TestCase):
    """They have no picture, and a list is the honest shape for a thing
    with nothing to show."""

    def test_they_are_chips_and_not_cards(self):
        b = block(".cast-chip {")
        self.assertIn("dashed", b)
        i = JS.index("const renderCastRoster =")
        self.assertIn("THESE HAVE NO PICTURE, SO THEY ARE A LIST",
                      JS[i:JS.index("const renderCastDetail =", i)])

    def test_the_manual_door_sits_in_the_same_block(self):
        i = JS.index('<div class="cast-uncast">')
        seg = JS[i:i + 1800]
        self.assertIn('id="cast-add"', seg)
        self.assertIn('id="cast-add-name"', seg)

    def test_nothing_uncast_is_stated_rather_than_blank(self):
        i = JS.index("const renderCastRoster =")
        self.assertIn("Nothing uncast", JS[i:JS.index("const renderCastDetail =", i)])

    def test_every_door_goes_through_the_one_modal(self):
        """One way to cast, whichever door you came in by (2026-08-16).
        The screen writes no card itself."""
        i = JS.index("const renderCastRoster =")
        seg = JS[i:JS.index("const renderCastDetail =", i)]
        self.assertEqual(seg.count("castModal("), 2)
        self.assertNotIn('api("/api/subjects", { method: "POST"', seg)


class TheDetailIsAScreen(unittest.TestCase):
    def test_it_is_not_a_modal(self):
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        self.assertNotIn("modal-scrim", seg)
        self.assertIn('data-f="back"', seg)

    def test_the_picture_is_the_largest_thing_on_it(self):
        b = block(".cast-detail {")
        self.assertIn("minmax(0, 560px)", b)

    def test_it_states_what_rides_every_prompt(self):
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        for lab in ("WHO THIS IS", "WHAT RIDES EVERY PROMPT", "LIVES ON", "RIDES AS"):
            self.assertIn(lab, seg, lab)

    def test_alternates_are_a_filmstrip_ending_in_add_another(self):
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        self.assertIn('class="cd-alt', seg)
        self.assertIn('class="cd-more"', seg)

    def test_a_subject_with_no_photograph_states_the_blocker(self):
        """B3, and the most consequential empty state in the app: this
        picture is what every prompt of this subject is held to."""
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        self.assertIn("NO PHOTOGRAPH YET", seg)
        self.assertIn("repeating-linear-gradient", block(".cd-hero.none {"))

    def test_the_photograph_button_uses_the_shelf_s_own_chooser(self):
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        self.assertIn("photoTrayModal(s, refreshCast)", seg)


class ItIsAViewNotAStore(unittest.TestCase):
    def test_it_reads_the_shelf_every_time(self):
        i = JS.index("const renderCastScreen =")
        seg = JS[i:i + 700]
        self.assertIn('api("/api/subjects")', seg)
        self.assertIn('api("/api/references")', seg)

    def test_the_uncast_list_is_the_one_the_rest_of_the_stage_uses(self):
        i = JS.index("const renderCastScreen =")
        self.assertIn("uncastRecommendations(subjects)", JS[i:i + 700])

    def test_its_host_exists_and_the_old_grid_is_kept_hidden(self):
        """The grid component still backs the Reference shelf; this
        screen replaced its second host, not the component."""
        self.assertIn('id="cast-screen"', HTML)
        self.assertIn('id="wiz-subj-grid" class="subj-grid hidden"', HTML)


if __name__ == "__main__":
    unittest.main()
