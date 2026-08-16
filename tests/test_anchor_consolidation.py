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

import json
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
        for cat in ("RENDER_STYLES", "TEXTURE_STYLES"):
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
        seg = JS[j:j + 800]
        self.assertIn("not the palette", seg)
        self.assertIn("own hour", seg)
        self.assertIn("not genre", seg, "the document's own framing")
        self.assertIn("whatever lens gets the shot", seg,
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

    def test_the_picture_sits_above_the_words(self):
        """User 2026-08-16: "This needs to have picture on top and text
        underneath" — the same reading order as the catalogue card it is
        a copy of."""
        b = re.search(r"\.rs-chosen \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertIn("flex-direction: column", b.group(1))
        f = re.search(r"\.rs-chosen \.rs-frame \{([^}]*)\}", CSS)
        self.assertIn("width: 100%", f.group(1), "the plate is not a stamp")

    def chosen(self):
        # bindPicker's sync(), not the first sync() in the file
        b = JS.index("const bindPicker =")
        i = JS.index("const sync = () => {", b)
        return JS[i:JS.index(chr(10) + "    };", i)]

    def test_the_chosen_style_renders_under_its_button(self):
        seg = self.chosen()
        self.assertIn("btn.after(box)", seg, "under the button, not above")
        self.assertIn("stylePlate(hit?.plate, hit?.shot)", seg,
                      "with its plate")
        self.assertIn("rs-desc", seg, "and its words")

    def test_it_clears_before_it_redraws(self):
        seg = self.chosen()
        self.assertIn('$(".rs-chosen", col)?.remove()', seg)
        self.assertIn("if (!v) return", seg, "nothing chosen, nothing shown")

    def test_clicking_it_reopens_the_panel(self):
        """The thing you are looking at is the thing you would change."""
        self.assertIn("box.onclick = () => btn.click()", self.chosen())

    def test_a_typed_answer_shows_too(self):
        self.assertIn('"In your own words"', self.chosen())

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


class TheAnswerIsStillRecognisedTomorrow(unittest.TestCase):
    """User-caught 2026-08-16: a saved house-style answer came back as
    "In your own words" with an empty plate. Its value is re-derived from
    the bible on every open, so a bible that gained a line stopped
    matching what the field held — and the card lost its own answer."""

    def test_the_house_card_matches_on_its_head_not_the_whole_string(self):
        for i in (JS.index("const head = t =>"),
                  JS.index("const head = t =>", JS.index("const head = t =>") + 5)):
            seg = JS[i:i + 420]
            self.assertIn('x.key === "house"', seg)
            self.assertIn("startsWith(head(", seg)

    def test_the_panel_lights_the_card_it_matched(self):
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn('st === hit ? " on" : ""', seg,
                      "not an exact-value compare that the head match "
                      "already knows is wrong")
        self.assertIn("let picked = hit ? hit.value", seg,
                      "and Use this keeps the matched card, not stale text")

    def test_the_capture_never_cuts_a_word_in_half(self):
        """The user saw a directive end "Board layo"."""
        BIB = (ROOT / "app/bible.py").read_text(encoding="utf-8")
        i = BIB.index("def house_style")
        seg = BIB[i:]
        self.assertNotIn('joined[:400]', seg)
        self.assertIn("Cap on a boundary, never mid-word", seg)
        self.assertIn("for ln in lines:", seg)


class TheGrammarsComeFromTheDocument(unittest.TestCase):
    """User 2026-08-16: "Find CINEMATOGRAPHY_STYLES.md in docs. We should
    replace our cinematography styles with this." Read, not copied — the
    document is the source of truth the user maintains, so editing it
    updates the picker and there is never a second list to keep in step."""

    def setUp(self):
        sys.path.insert(0, str(ROOT))
        from app import cinematography
        self.cine = cinematography

    def test_all_eight_parse_with_every_field_the_card_shows(self):
        got = self.cine.styles()
        self.assertEqual(len(got), 8)
        for st in got:
            for f in ("name", "subtitle", "question", "description",
                      "principle", "prompt", "value"):
                self.assertTrue(st[f].strip(), f"{st['name']} has no {f}")
            self.assertEqual(len(st["films"]), 5,
                             f"{st['name']}: the section rule is not a film")
            self.assertTrue(st["avoid"], f"{st['name']} states no fence")

    def test_the_directive_carries_mechanics_not_film_titles(self):
        """The document's own Usage Note: reference films stay human-facing
        context; generation relies on mechanics and operating principle."""
        for st in self.cine.styles():
            for film in st["films"]:
                self.assertNotIn(film, st["value"], st["name"])
            self.assertIn(st["principle"].rstrip(".")[:40], st["value"])

    def test_nothing_is_hardcoded_in_the_front_end(self):
        self.assertIn("const CINEMA_STYLES = [];", JS)
        self.assertIn("async function loadCinemaStyles", JS)
        self.assertIn("/api/cinematography/styles", JS)
        for gone in ("Hard & Directional", "Overcast Flat", "Practical-Lit"):
            self.assertNotIn(gone, JS, f"{gone} outlived the replacement")

    def test_the_card_shows_what_the_user_asked_for(self):
        i = JS.index("function richCardBody(st)")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        for probe in ("rs-sub", "rs-q", "rs-desc", "rs-principle",
                      "rs-frames", "rs-films", "rs-prompt-link"):
            self.assertIn(probe, seg, f"the card is missing {probe}")
        self.assertIn("length: 3", seg, "three film frames")

    def test_a_frame_opens_in_the_lightbox_without_choosing_the_style(self):
        # inside the picker — another modal binds the same attribute
        k = JS.index("function openStylePicker(")
        i = JS.index('$$("[data-lb]", ov)', k)
        seg = JS[i:i + 600]
        self.assertIn("e.stopPropagation()", seg)
        self.assertIn("openLightbox(", seg)
        self.assertIn("set.indexOf(img)", seg, "arrows step between frames")

    def test_the_prompt_opens_to_read_rather_than_riding_the_render(self):
        """It runs to a page. The directive is the principle and the
        mechanics; the prompt is reference."""
        self.assertIn("function openPromptReader", JS)
        i = JS.index('$$(".rs-prompt-link", ov)')
        self.assertIn("e.stopPropagation()", JS[i:i + 400])
        self.assertGreater(i, JS.index("function openStylePicker("))
        self.assertIn("openPromptReader(", JS[i:i + 400])

    def test_the_subtitle_is_a_label_not_a_signal(self):
        """Eight amber subtitles on one surface is eight of nothing."""
        b = re.search(r"\.rs-sub \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertNotIn("--accent", b.group(1))

    def test_the_endpoint_serves_it(self):
        self.assertIn('@app.get("/api/cinematography/styles")', MAIN)


class TheFramesAreReal(unittest.TestCase):
    """User 2026-08-16: "Add the thumbnails in the /docs folder to the
    adventure cine style." Masters live in docs/Cinematography/; the app
    serves web-sized derivatives listed in the plate manifest."""

    def test_the_manifest_names_three_frames_for_classical_adventure(self):
        mf = json.loads((ROOT / "app/static/style-plates/index.json")
                        .read_text(encoding="utf-8"))
        got = mf.get("cine-classical-adventure")
        self.assertIsInstance(got, list, "three frames, not one plate")
        self.assertEqual(len(got), 3)
        for f in got:
            p = ROOT / "app/static/style-plates" / f
            self.assertTrue(p.exists(), f)
            self.assertLess(p.stat().st_size, 250_000,
                            f"{f} is a master, not a web derivative")
            self.assertTrue(f.endswith(".webp"), f"{f} is not WebP")

    def test_the_key_matches_what_the_document_slugs_to(self):
        from app import cinematography
        keys = {s["key"] for s in cinematography.styles()}
        mf = json.loads((ROOT / "app/static/style-plates/index.json")
                        .read_text(encoding="utf-8"))
        for k in mf:
            if k.startswith("cine-"):
                self.assertIn(k, keys, f"{k} matches no grammar in the doc")

    def test_a_style_with_no_frames_still_reads(self):
        i = JS.index("function richCardBody(st)")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn("rs-cell-empty", seg)
        self.assertIn("shots[i]", seg, "only the slots that exist get an img")


class ACardHoldsButtonsSoItIsNotOne(unittest.TestCase):
    """Caught 2026-08-16 the moment real frames landed: the card was a
    <button> containing the prompt link's <button>, which is invalid — the
    parser hoists the inner one OUT and the card comes apart on screen.
    The frames made it visible; it was wrong from the day the rich card
    shipped."""

    def test_the_card_is_a_div_with_the_keyboard_put_back(self):
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn('<div class="rs-card', seg)
        self.assertNotIn('<button type="button" class="rs-card', seg)
        self.assertIn('role="button" tabindex="0"', seg)
        self.assertIn("c.onkeydown", seg)
        self.assertIn('e.key === "Enter" || e.key === " "', seg)

    def test_its_own_buttons_are_still_buttons(self):
        i = JS.index("function richCardBody(st)")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn('<button type="button" class="text-act rs-prompt-link"', seg)

    def test_a_div_gets_back_what_a_button_gave_for_free(self):
        b = re.search(r"\.rs-card \{([^}]*)\}", CSS)
        self.assertIn("font: inherit", b.group(1))
        self.assertIn(".rs-card:focus-visible", CSS)


class NoMastersInTheRepo(unittest.TestCase):
    """User 2026-08-16: "Nah webp these. make them small." Three 2.5 MB
    PNGs cost 8 MB for pictures nothing displays above 1280px — and they
    ship inside the release zip."""

    def test_the_reference_folder_holds_no_masters(self):
        d = ROOT / "docs" / "Cinematography"
        if not d.exists():
            return
        for f in d.iterdir():
            if f.is_file():
                self.assertEqual(f.suffix.lower(), ".webp", f.name)
                self.assertLess(f.stat().st_size, 250_000, f.name)

    def test_the_recipe_states_the_size(self):
        r = (ROOT / "app/static/style-plates/README.md").read_text(encoding="utf-8")
        self.assertIn("1280px on the long edge", r)
        self.assertIn("Masters do not belong in the repo", r)


class TheStripReadsOnThePage(unittest.TestCase):
    """User 2026-08-16: "In the main Production Design page, under
    Cinematography, it should show a 3 panel strip." A grammar has three
    reference frames; one plate cannot stand for three."""

    def chosen(self):
        # bindPicker's sync(), not the first sync() in the file
        b = JS.index("const bindPicker =")
        i = JS.index("const sync = () => {", b)
        return JS[i:JS.index(chr(10) + "    };", i)]

    def test_the_chosen_grammar_shows_its_three_frames(self):
        seg = self.chosen()
        self.assertIn("hit?.rich ? plateShots(hit.key)", seg)
        self.assertIn("length: 3", seg)
        self.assertIn("rs-cell-empty", seg, "a missing frame is a dashed cell")
        self.assertIn("rs-frame\">${stylePlate(", seg,
                      "a plain style still shows its single plate")

    def test_a_frame_opens_full_size_instead_of_reopening_the_panel(self):
        seg = self.chosen()
        self.assertIn("box.onclick = () => btn.click()", seg)
        j = seg.index('$$("[data-lb]", box)')
        self.assertIn("e.stopPropagation()", seg[j:j + 300])
        self.assertIn("openLightbox(", seg[j:j + 400])

    def test_the_strip_is_three_across(self):
        b = re.search(r"\.rs-chosen \.rs-frames \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertIn("repeat(3, 1fr)", b.group(1))


class TheLightboxIsTheTopmostSurface(unittest.TestCase):
    """User-caught 2026-08-16: "when you click the thumbs to full sized
    shows behind the modal". The lightbox was z-index 100 and every modal
    is 400 — it had ALWAYS opened behind them; the reference viewer has
    the same bug, and real frames were just the first time anyone looked."""

    def test_it_outranks_a_modal(self):
        lb = re.search(r"\.lightbox \{([^}]*)\}", CSS).group(1)
        sc = re.search(r"\.modal-scrim \{([^}]*)\}", CSS, re.S).group(1)
        z = lambda b: int(re.search(r"z-index:\s*(\d+)", b).group(1))
        self.assertGreater(z(lb), z(sc))

    def test_the_cropper_does_too(self):
        cr = re.search(r"\.cropper \{([^}]*)\}", CSS).group(1)
        sc = re.search(r"\.modal-scrim \{([^}]*)\}", CSS, re.S).group(1)
        z = lambda b: int(re.search(r"z-index:\s*(\d+)", b).group(1))
        self.assertGreater(z(cr), z(sc))

    def test_the_order_is_written_down(self):
        self.assertIn("STACKING ORDER, stated once so it stops drifting", CSS)


class TheLabelsAnswerWhatTheyDoToARender(unittest.TestCase):
    """User 2026-08-16: "'Each becomes a bible section' — who cares.
    Rather: what does it affect in panel generation?" Both labels named
    their filing destination instead of their effect."""

    def test_the_old_filing_labels_are_gone(self):
        self.assertNotIn("EACH BECOMES A BIBLE SECTION", JS)
        self.assertNotIn("THE VISUAL RULES A PLACE INHERITS", JS)

    def test_both_carry_a_help_card(self):
        for k in ("langs", "envs"):
            self.assertIn(f'data-help="{k}"', JS)
            self.assertIn(f"  {k}:", JS)

    def test_the_copy_states_the_effect_on_a_render(self):
        i = JS.index("const WIZ_HELP = {")
        seg = JS[i:JS.index(chr(10) + "};", i)]
        self.assertIn("What it does to a render", seg)
        self.assertEqual(seg.count("What it does to a render"), 2,
                         "both answer the question, not one")
        # and the facts match the code
        self.assertIn("environments never", seg.lower(),
                      "generate._style_context: environments never infer")
        self.assertIn("override", seg, "a panel overrides its sheet")

    def test_the_help_binder_is_shared_rather_than_copied_again(self):
        self.assertIn("function bindHelpButtons(root, texts)", JS)
        self.assertIn("bindHelpButtons(host, WIZ_HELP)", JS)


class TheLocalLoopExists(unittest.TestCase):
    """User 2026-08-16: "we should iterate locally for a bunch of these
    polish items so its fast"."""

    def test_the_script_is_there_and_guards_the_obvious_ways_to_lose_time(self):
        p = ROOT / "scripts" / "dev.py"
        self.assertTrue(p.exists())
        src = p.read_text(encoding="utf-8")
        self.assertIn('HOME = ROOT / ".devhome"', src)
        self.assertIn("def port_is_taken", src)
        self.assertIn("def free_port", src)
        self.assertIn("def find_install", src)
        self.assertIn("webbrowser.open(url)", src)
        self.assertIn("def newest_download", src)
        self.assertIn("from app import backup", src)
        self.assertIn("backup.restore_backup", src,
                      "the app's own validated restore, not a bare "
                      "extractall — traversal guard, real project name, "
                      "no slug collision, staged rename")
        self.assertIn("sys.path.insert(0, str(ROOT))", src,
                      "scripts/ cannot import app without it")
        self.assertIn("def clone_install", src)
        for k in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
            self.assertIn(k, src)


    def test_no_arguments_is_the_whole_interface(self):
        """User 2026-08-16: "make the local loop EASY — batch file and we
        are in local mode." Finding an install, choosing a port and
        opening a browser are the program's job, not the user's."""
        src = (ROOT / "scripts" / "dev.py").read_text(encoding="utf-8")
        i = src.index("def main() -> int:")
        seg = src[i:]
        self.assertIn("if not a.from_install and not a.restore", seg,
                      "a bare run still finds real content")
        self.assertIn("free_port(a.port)", seg,
                      "a busy port moves aside instead of refusing")
        bat = (ROOT / "dev.bat").read_text(encoding="utf-8")
        self.assertIn(r".\dev.bat", bat,
                      "PowerShell needs the prefix, and the file that "
                      "documents itself should say so")
        self.assertIn('cd /d "%~dp0"', bat, "double-clickable from anywhere")

    def test_the_dev_home_never_enters_git(self):
        ig = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".devhome/", ig)

    def test_it_does_not_ship(self):
        rel = (ROOT / "scripts" / "stage_release.py").read_text(encoding="utf-8")
        i = rel.index("INCLUDE = [")
        self.assertNotIn("scripts", rel[i:rel.index("]", i)])


if __name__ == "__main__":
    unittest.main()
