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

    def test_it_does_not_narrate_that_the_cards_are_shared(self):
        """It used to say EVERY CARD HERE IS A CARD ON REFERENCE /
        SUBJECTS on the header. True, and a rule about how the system is
        wired — documentation, not a line beside a roster
        (COPY_DISCIPLINE test 3, 2026-09-13). The screen still owns no
        data, which is the fact that mattered and is asserted below."""
        i = JS.index("const renderCastRoster =")
        seg = JS[i:JS.index("const renderCastDetail =", i)]
        self.assertNotIn("EVERY CARD HERE IS A CARD", seg)
        self.assertNotIn('api("/api/subjects", { method: "POST"', seg)


class TheUncastAreAList(unittest.TestCase):
    """They have no picture, and a list is the honest shape for a thing
    with nothing to show."""

    def test_they_are_chips_and_not_cards(self):
        """The dashed chip IS the statement. The sentence that used to
        follow it — "THESE HAVE NO PICTURE, SO THEY ARE A LIST" —
        explained the shape to a reader who could already see it
        (COPY_DISCIPLINE test 1, 2026-09-13)."""
        b = block(".cast-chip {")
        self.assertIn("dashed", b)
        i = JS.index("const renderCastRoster =")
        seg = JS[i:JS.index("const renderCastDetail =", i)]
        self.assertIn("UNCAST &mdash; NO CARD YET", seg)
        self.assertNotIn("SO THEY ARE A LIST", seg)

    def test_the_manual_door_sits_in_the_same_block(self):
        i = JS.index('<div class="cast-uncast">')
        seg = JS[i:i + 1800]
        self.assertIn('id="cast-add"', seg)
        self.assertIn('id="cast-add-name"', seg)

    def test_nothing_uncast_is_stated_rather_than_blank(self):
        i = JS.index("const renderCastRoster =")
        self.assertIn("Nothing uncast", JS[i:JS.index("const renderCastDetail =", i)])

    def test_every_door_goes_through_the_one_path(self):
        """One way to cast, whichever door you came in by (2026-08-16).
        The screen writes no card itself — it calls `castOne`, which is
        the same call bulk casting makes.

        The path changed on 2026-09-12 (CAST_CHARACTER_SCREEN §1): the
        roster's chips and its manual field cast in ONE gesture into the
        empty detail screen, rather than opening a modal to ask again for
        words the read already supplied."""
        i = JS.index("const renderCastRoster =")
        seg = JS[i:JS.index("const renderCastDetail =", i)]
        self.assertEqual(seg.count("castInto("), 2)   # the chip and the manual row
        self.assertNotIn("castModal(", seg)
        self.assertNotIn('api("/api/subjects", { method: "POST"', seg)


class TheDetailIsAScreen(unittest.TestCase):
    def test_it_is_not_a_modal(self):
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        self.assertNotIn("modal-scrim", seg)
        self.assertIn('data-f="back"', seg)

    def test_the_picture_is_the_largest_thing_on_it(self):
        """§3.4: "The subject's picture is the largest thing on it, at the
        subject's own ratio." The rule is that it LEADS its own column and
        keeps its ratio — not a particular pixel width. It was 560px,
        which was a number of my own choosing rather than the mock's: a
        1:1.25 portrait at 560 is 700px tall, and the specification beside
        it ended a third of the way down, which makes the page a picture
        with a caption. 380 is the mock's proportion."""
        b = block(".cast-detail {")
        self.assertIn("grid-template-columns: minmax(0, 380px)", b)
        hero = block(".cd-hero {")
        self.assertIn("aspect-ratio: .8", hero)
        self.assertIn('.cast-detail[data-kind="VEHICLE"] .cd-hero', CSS)

    def test_it_states_what_rides_every_prompt(self):
        """RIDES AS left with CAST_CHARACTER_SCREEN (2026-09-12): it
        restated the role line already in the header, and §3's mock shows
        APPEARS IN / LIVES ON and nothing else."""
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        for lab in ("WHO THIS IS", "WHAT RIDES EVERY PROMPT", "LIVES ON"):
            self.assertIn(lab, seg, lab)

    def test_alternates_are_a_filmstrip_ending_in_generate_another(self):
        """The slot said ADD ANOTHER and opened the upload — a second copy
        of the button already beside it. §3.4 calls for GENERATE ANOTHER,
        and 2026-08-31 built the door that makes that true."""
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        self.assertIn('class="cd-alt', seg)
        self.assertIn('class="cd-more"', seg)
        self.assertIn("GENERATE<br>ANOTHER", seg)

    def test_a_subject_with_no_photograph_states_the_blocker(self):
        """B3, and the most consequential empty state in the app: this
        picture is what every prompt of this subject is held to.

        CAST_CHARACTER_SCREEN §2 replaced the hatched panel and its
        paragraph with the frame itself: `NO PICTURE` in amber in the
        header, a dashed 9:16 slot, and the two acts inside it. The slot
        is not reserved-and-silent — it carries the only primary on the
        screen."""
        i = JS.index("const renderCastDetail =")
        seg = JS[i:JS.index("const renderCastScreen =", i)]
        self.assertIn("NO PICTURE", seg)
        self.assertIn('<div class="cd-frame-acts">', seg)
        self.assertIn("dashed", block(".cd-frame {"))

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
