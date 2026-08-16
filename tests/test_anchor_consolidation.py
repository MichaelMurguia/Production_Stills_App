"""One question per anchor (user 2026-08-16: "we now have duplicative
entries and we should consolidate").

The look interview and the style anchors were the same four questions
asked in two media. `Medium & finish` and Board Rendering's SETS line were
the same three words; `Palette & light` was one box answering two
different anchors. The fix is not a third list — it is folding the words
INTO the anchor card they duplicate, so each anchor has a picture half and
a words half, and the interview keeps only what no anchor can hold: the
touchstones, the never-list, and notes."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
WIZ = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")

ANCHORS = {
    "WORLD_TEXTURE": "wiz-texture",
    "COLOR_PALETTE": "wiz-palette",
    "CINEMATOGRAPHY_STYLE": "wiz-light",
    "BOARD_RENDERING_STYLE": "wiz-medium",
}


def card(role: str) -> str:
    i = HTML.index(f'<div class="wiz-col" data-role="{role}">')
    return HTML[i:HTML.index('<div class="wiz-col"', i + 10)
                if f'<div class="wiz-col"' in HTML[i + 10:] else len(HTML)]


class TheInterviewIsGone(unittest.TestCase):
    """The interview asked the same four questions the anchors ask, in
    prose. Everything in it now lives where it acts: the per-axis words on
    their anchor card, the camera on Cinematography, the never-list on
    Board Rendering, the standing notes beside the Draft button — and
    `touchstones`, the one input no anchor fenced, is retired."""

    def test_every_anchor_carries_its_own_words(self):
        for role, fid in ANCHORS.items():
            seg = card(role)
            self.assertIn('class="wiz-words"', seg, f"{role} has no words half")
            self.assertIn(f'id="{fid}"', seg, f"{role} lost {fid}")

    def test_the_step_is_gone_rather_than_emptied(self):
        self.assertNotIn('<div class="grid-form">', HTML,
                         "the interview's form is not left standing empty")
        self.assertNotIn("wiz-touchstones", HTML)
        self.assertIn("FIVE STEPS", HTML)
        i = JS.index("const RAIL = [")
        seg = JS[i:i + 200]
        self.assertIn('[1, "Anchors"]', seg)
        self.assertNotIn("Interview", seg)

    def test_the_camera_sits_with_the_anchor_it_can_override(self):
        seg = card("CINEMATOGRAPHY_STYLE")
        self.assertIn('id="cam-default"', seg)
        self.assertIn('id="cam-default-row"', seg)

    def test_the_never_list_sits_on_the_section_it_feeds(self):
        """wizard.py routes it to Rendering Language -> Avoid, which is
        Board Rendering's section — it was a step away from it."""
        self.assertIn('id="wiz-never"', card("BOARD_RENDERING_STYLE"))
        self.assertIn("Avoid list", WIZ)

    def test_the_standing_notes_sit_beside_the_act_they_modify(self):
        i = HTML.index('id="wiz-notes"')
        step = HTML.rindex('<div class="panel step"', 0, i)
        self.assertIn('data-step="4"', HTML[step:step + 60],
                      "notes live with the bible draft, not upstream of it")
        self.assertIn('id="wiz-draft"', HTML[step:HTML.index("</div>", i)])

    def test_notes_is_kept_because_it_is_load_bearing(self):
        """User 2026-08-16: "if it is load bearing, why dont we keep it?"
        Right — step 03's answered questions ride the same key, and a
        standing rule with no box goes into an anchor field where it
        corrupts that anchor's scope."""
        i = JS.index("notes: [")
        self.assertIn("qaLines", JS[i:i + 120])


class TheValueStillReachesTheBible(unittest.TestCase):
    def test_the_server_persists_one_key_per_anchor(self):
        i = MAIN.index("_INTERVIEW_FIELDS = (")
        seg = MAIN[i:i + 200]
        for k in ("texture", "palette", "light", "medium", "never", "notes"):
            self.assertIn(f'"{k}"', seg)
        self.assertNotIn('"touchstones"', seg, "retired, and folded forward")

    def test_the_retired_answer_is_migrated_not_dropped(self):
        self.assertIn("def _fold_touchstones", MAIN)
        self.assertIn("_fold_touchstones_everywhere()", MAIN,
                      "a migration runs at boot; it is not offered")

    def test_the_two_new_answers_are_not_dropped_on_the_floor(self):
        """A key the drafting prompt never reads is a field that does
        nothing — which is worse than the duplication it replaced."""
        for probe in ("answers.get('texture')", "answers.get('light')",
                      "answers.get('palette')", "answers.get('medium')"):
            self.assertIn(probe, WIZ, probe)

    def test_each_answer_is_fenced_to_its_own_anchor(self):
        i = WIZ.index("WORLD_TEXTURE in words")
        seg = WIZ[i:i + 1400]
        self.assertIn("WORDS half of the anchor it names", seg)
        self.assertIn("feeds only its anchor's sections", seg)
        self.assertIn("the director's words win", seg,
                      "words and photos describe one thing; ties go to the "
                      "person who typed")

    def test_the_draft_payload_carries_all_four(self):
        i = JS.index("const answers = {")
        seg = JS[i:i + 900]
        for k in ("texture:", "palette:", "light:", "medium:"):
            self.assertIn(k, seg)


class AnAnchorIsAnsweredByEither(unittest.TestCase):
    def test_the_step_badge_counts_words_as_an_answer(self):
        i = JS.index("const ANCHOR_WORDS =")
        seg = JS[i:i + 600]
        for role in ANCHORS:
            self.assertIn(role, seg)
        self.assertIn("?.value.trim()).length", seg)

    def test_the_card_badge_never_reads_none_over_its_own_answer(self):
        i = JS.index("const inWords =")
        seg = JS[i - 400:i + 400]
        self.assertIn('"IN WORDS"', seg)
        self.assertIn("mine.length ? `${mine.length}`", seg,
                      "pictures still carry the count")

    def test_the_badge_is_resynced_when_the_words_arrive(self):
        """The interview loads after the cards render, so a badge read at
        render time is read too early."""
        self.assertIn("const syncAnchorBadges =", JS)
        i = JS.index("const syncAnchorBadges =")
        self.assertIn(r"/^\d+$/.test", JS[i:i + 400],
                      "a card with pictures keeps its count")
        self.assertGreaterEqual(JS.count("syncAnchorBadges()"), 3,
                                "called on load, on change, and on a pick")


class OnePickerServesEveryKnownVocabulary(unittest.TestCase):
    def test_there_is_one_picker_not_two(self):
        self.assertEqual(JS.count("function openStylePicker("), 1)
        self.assertNotIn("function openRenderStyleModal", JS)
        self.assertEqual(JS.count("const bindPicker ="), 1)
        self.assertEqual(JS.count("bindPicker(\""), 3,
                         "one helper: texture, cinematography, rendering")

    def test_every_catalogue_states_what_it_is_not_and_shows_it(self):
        for cat in ("RENDER_STYLES", "CINEMA_STYLES", "TEXTURE_STYLES"):
            i = JS.index(f"const {cat} = [")
            seg = JS[i:JS.index("\n];", i)]
            self.assertGreaterEqual(seg.count("name:"), 5,
                                    f"{cat} is thin")
            self.assertEqual(seg.count("name:"), seg.count("not:"),
                             f"every {cat} card states its fence")
            self.assertEqual(seg.count("name:"), seg.count("value:"),
                             f"every {cat} card writes a directive")
            self.assertEqual(seg.count("name:"), seg.count("plate:"),
                             f"every {cat} card carries its example plate")

    def test_the_definition_leads_and_names_what_it_is_not(self):
        i = JS.index('title: "Rendering style"')
        self.assertIn("not mood, not light, not cinematography", JS[i:i + 500])
        j = JS.index('title: "Cinematography"')
        seg = JS[j:j + 700]
        self.assertIn("not the palette", seg)
        self.assertIn("panel's hour", seg)
        self.assertIn("not the lens", seg,
                      "a cinematographer picks any lens to get the shot")

    def test_free_text_survived_the_catalogue(self):
        """These were text boxes. A catalogue that cannot say "something
        else" is a smaller field than the one it replaced."""
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index("\n}\n", i)]
        self.assertIn('id="rs-own"', seg)
        self.assertIn("own.value.trim() || picked", seg)

    def test_a_typed_answer_puts_the_cards_out(self):
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index("\n}\n", i)]
        self.assertIn('own.addEventListener("input"', seg)
        self.assertIn("picked = \"\"; mark();", seg,
                      "two answers must never be lit at once")

    def test_the_upload_route_goes_to_the_anchor_it_belongs_to(self):
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index("\n}\n", i)]
        self.assertIn('data-role="${uploadRole}"', seg)
        self.assertIn('uploadRole: "BOARD_RENDERING_STYLE"', JS)
        self.assertIn('uploadRole: "CINEMATOGRAPHY_STYLE"', JS)

    def test_selection_is_ink_not_amber(self):
        """§1.3 — a chosen style is STATE; amber stays with the one
        primary action."""
        b = re.search(r"\.rs-card\.on \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertIn("var(--ink)", b.group(1))
        self.assertNotIn("accent", b.group(1))

    def test_the_trigger_reads_as_a_field_not_a_verb(self):
        b = re.search(r"\.pick-btn \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertIn("text-align: left", b.group(1))
        self.assertIn("var(--sans)", b.group(1),
                      "a style NAME is hierarchy, not machine data")


class TheCardIsItsButton(unittest.TestCase):
    """User 2026-08-16: "Only have the button on the main page. Click it
    and you get the words with an associated example image of the style.
    In that panel will be Add your own and a plus button for adding an
    image and text." """

    def test_each_carded_anchor_shows_only_its_button(self):
        for role in ("WORLD_TEXTURE", "CINEMATOGRAPHY_STYLE",
                     "BOARD_RENDERING_STYLE"):
            seg = card(role)
            self.assertIn("pick-btn", seg, f"{role} has no button")
            for offpage in ('data-f="addbtn"', 'data-f="list"'):
                i = seg.index(offpage)
                self.assertIn("wiz-offpage", seg[max(0, i - 160):i],
                              f"{role}: {offpage} is still on the page")

    def test_what_is_hidden_stays_in_the_dom(self):
        """It is hidden, not deleted — the panel borrows these nodes with
        their bindings intact rather than re-creating and re-binding."""
        b = re.search(r"\.wiz-offpage \{([^}]*)\}", CSS)
        self.assertTrue(b and "display: none" in b.group(1))
        self.assertIn(".rs-extra > .wiz-offpage", CSS)

    def test_the_camera_and_the_never_list_travel_into_their_panel(self):
        self.assertIn("const travels = (sel)", JS)
        self.assertIn('travels("#cam-default")', JS)
        self.assertIn('travels("#wiz-never-row")', JS)
        i = JS.index("const travels = (sel)")
        seg = JS[i:i + 500]
        self.assertIn("onClose", seg, "and go home on the way out")
        self.assertIn("dataset.home", JS)

    def test_the_panel_carries_add_your_own_with_a_plus(self):
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn("rs-own-card", seg)
        self.assertIn("Add your own", seg)
        self.assertIn('data-f="add-img"', seg)
        self.assertIn('id="rs-own"', seg, "an image AND text")

    def test_the_plus_reaches_the_one_library(self):
        """Not a second uploader — the card's own input, clicked from
        where the user is."""
        i = JS.index('$("[data-f=add-img]", ov).onclick')
        self.assertIn('$("[data-f=addbtn]", col)?.click()', JS[i:i + 160])

    def test_attached_pictures_show_in_the_panel(self):
        i = JS.index("const showAttached =")
        seg = JS[i:i + 420]
        self.assertIn('[data-f=list] img', seg)
        self.assertIn("rs-thumb", seg)

    def test_every_catalogue_card_shows_its_plate(self):
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn("stylePlate(st.plate, st.shot)", seg,
                      "the diagram, or a captured image over it")
        self.assertIn('class="rs-frame"', seg)

    def test_a_plate_is_a_diagram_and_says_so(self):
        """We cannot ship stock imagery and a generated sample would be
        one engine's opinion of the style rather than the style."""
        self.assertIn("These are DIAGRAMS, not photographs", JS)
        i = JS.index("const PLATE = {")
        seg = JS[i:JS.index(chr(10) + "};", i)]
        self.assertNotIn("Gradient", seg)
        self.assertNotIn("gradient", seg, "canon forbids gradients")
        self.assertGreaterEqual(seg.count("light"), 7)
        self.assertGreaterEqual(seg.count("mark"), 9)


class TheProductionsOwnStyleIsCaptured(unittest.TestCase):
    """User 2026-08-16: "with my existing rendering style, is it still
    authoritative? We should capture my style and make it the Production
    Painting style." A production that has been rendering for weeks
    already HAS a rendering style, and it is not a phrase we wrote."""

    def test_the_authority_is_the_saved_bible_not_a_hardcoded_phrase(self):
        BIB = (ROOT / "app/bible.py").read_text(encoding="utf-8")
        self.assertIn("def house_style", BIB)
        i = BIB.index("def house_style")
        seg = BIB[i:]
        self.assertIn('sections.get("Rendering Language"', seg)
        self.assertIn('"Required"', seg,
                      "the Avoid list is not how the panels are drawn")

    def test_the_plate_is_a_panel_the_production_actually_made(self):
        BIB = (ROOT / "app/bible.py").read_text(encoding="utf-8")
        # bounded by the function, not a character count — this window has
        # walked off its assertion once already as house_style() grew
        i = BIB.index("def house_style")
        seg = BIB[i:]
        self.assertIn('c.get("status") == "APPROVED"', seg)
        self.assertIn("size=thumb", seg, "a card is not a full 4K render")

    def test_the_first_card_adopts_it_before_the_panel_opens(self):
        self.assertIn("async function adoptHouseStyle", JS)
        self.assertIn('key: "house"', JS)
        i = JS.index("async function adoptHouseStyle")
        seg = JS[i:i + 900]
        self.assertIn("/api/bible/house-style", seg)
        self.assertIn("card._adopted", seg, "captured once, not per open")
        self.assertIn("if (!h?.has_bible) return", seg,
                      "a production with nothing drawn keeps the shipped text")
        self.assertIn("if (styles === RENDER_STYLES) await adoptHouseStyle()", JS)

    def test_a_card_can_carry_a_real_image_over_its_diagram(self):
        i = JS.index("function stylePlate(")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn("shot || (file ?", seg,
                      "a captured plate outranks the manifest")
        self.assertIn("rs-shot", seg)

    def test_feeding_the_bible_back_is_deliberate(self):
        BIB = (ROOT / "app/bible.py").read_text(encoding="utf-8")
        i = BIB.index("def house_style")
        self.assertIn("instead of drifting off it", BIB[i:])


class TheChoiceIsVisibleWithoutReopening(unittest.TestCase):
    """User 2026-08-16: "once a Rendering style or Cinematography style is
    selected — show the card on the main tab in the correct area (under
    the selection button)." A choice you cannot see is a choice you reopen
    the panel to check."""

    def test_the_chosen_style_renders_under_its_button(self):
        i = JS.index('box.className = "rs-chosen"')
        seg = JS[i - 700:i + 700]
        self.assertIn("btn.after(box)", seg, "under the button, not above")
        self.assertIn("stylePlate(hit?.plate, hit?.shot)", seg,
                      "with its plate")
        self.assertIn("rs-desc", seg, "and its words")

    def test_it_clears_before_it_redraws(self):
        i = JS.index('box.className = "rs-chosen"')
        seg = JS[i - 700:i + 200]
        self.assertIn('$(".rs-chosen", col)?.remove()', seg)
        self.assertIn("if (!v) return", seg, "nothing chosen, nothing shown")

    def test_clicking_it_reopens_the_panel(self):
        """The thing you are looking at is the thing you would change."""
        i = JS.index('box.className = "rs-chosen"')
        self.assertIn("box.onclick = () => btn.click()", JS[i:i + 900])

    def test_a_typed_answer_shows_too(self):
        i = JS.index('box.className = "rs-chosen"')
        self.assertIn('"In your own words"', JS[i:i + 900])

    def test_its_prose_speaks_archivo_inside_a_courier_label(self):
        """It sits inside the anchor's label, whose voice is Courier caps
        for a FIELD NAME. A style description is prose (§1.1)."""
        b = re.search(r"\.rs-chosen \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertIn("var(--sans)", b.group(1))
        self.assertIn("text-transform: none", b.group(1))
        c = re.search(r"\.rs-src \{([^}]*)\}", CSS)
        self.assertIn("var(--mono)", c.group(1), "the provenance stays machine")


class TheCapturedCardShowsTheStyle(unittest.TestCase):
    """User-caught 2026-08-16: "the production painting card does not
    contain the description of the rendering style. It needs to." The
    bible's own words ARE the description; where they came from is a
    footnote, not the copy."""

    def test_the_description_is_the_bibles_text(self):
        i = JS.index("async function adoptHouseStyle")
        seg = JS[i:i + 1200]
        self.assertIn('card.desc = (h.lines || []).join(" · ") || h.words', seg)
        self.assertNotIn("Captured from this production", seg,
                         "that sentence described the capture, not the style")

    def test_the_provenance_is_a_footnote(self):
        i = JS.index("async function adoptHouseStyle")
        seg = JS[i:i + 1200]
        self.assertIn("FROM YOUR ART DIRECTION BIBLE", seg)
        self.assertIn("card.source", seg)

    def test_a_prose_bible_is_still_read(self):
        """An earlier pass took bullets only and returned nothing at all
        for a bible written as paragraphs."""
        BIB = (ROOT / "app/bible.py").read_text(encoding="utf-8")
        i = BIB.index("def house_style")
        seg = BIB[i:]
        self.assertIn("if not required.strip():", seg)
        self.assertIn('for cut in ("### Avoid", "Avoid")', seg,
                      "and the Avoid list still never gets in")


if __name__ == "__main__":
    unittest.main()
