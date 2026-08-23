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


def block(sel: str) -> str:
    bodies = re.findall(re.escape(sel) + r"\s*{([^}]*)}", CSS)
    assert bodies, f"missing rule: {sel}"
    return chr(10).join(bodies)


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
        """Asserted against the DOCUMENTS now (2026-08-22). These two were
        arrays in app.js carrying a one-line desc and a ~60-character
        directive; they are libraries in docs/ with the depth
        cinematography has had since 2026-08-16. The properties this test
        has always checked are unchanged — a fence, a directive, real
        content — only where they are read from."""
        from app import style_docs
        for lib, least in (("rendering", 9), ("texture", 5),
                           ("cinematography", 8)):
            st = style_docs.styles(lib)
            self.assertGreaterEqual(len(st), least, f"{lib} is thin")
            for x in st:
                self.assertTrue(x["avoid"], f"{lib}/{x['name']} states no fence")
                self.assertTrue(x["value"], f"{lib}/{x['name']} writes no directive")
                self.assertGreater(len(x["prompt"]), 200,
                                   f"{lib}/{x['name']} has no in-depth prompt")

    def test_the_plates_survived_the_move_to_documents(self):
        """A plate is drawn artwork keyed by style name, so it cannot live
        in markdown — it stays in the client and is looked up. Every style
        that had one must still find one."""
        from app import style_docs
        i = JS.index("const STYLE_PLATES = ")
        plates = JS[i:JS.index(";", i)]
        for lib in ("rendering", "texture"):
            for x in style_docs.styles(lib):
                self.assertIn('"' + x["name"] + '"', plates,
                              f"{x['name']} lost its plate")

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

    def test_the_escape_hatch_is_one_control_below_the_grid(self):
        """B7: it was drawn TWICE — a grid cell and a field inside the
        modal — which `one-control-two-presentations` already forbids. A
        set-member tile classifies by fill (§1.3), and an escape hatch is
        not a member of the set it escapes."""
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertNotIn("rs-own-card", seg, "no longer a cell")
        self.assertIn("rs-own-row", seg)
        self.assertIn('id="rs-own"', seg)
        self.assertIn('data-f="add-img"', seg, "the image and the words together")
        self.assertIn("OR IN YOUR OWN WORDS", seg)
        # it sits AFTER the grid closes
        self.assertLess(seg.index("</div>"), seg.index("rs-own-row"))
        b = re.search(r"\.rs-own-row \{([^}]*)\}", CSS).group(1)
        self.assertIn("border-top", b, "after a hairline")

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

    def test_one_renderer_draws_the_cell_and_the_card(self):
        """B1: they were two drawings of one thing and were drifting. The
        fix is not to reconcile them but to stop having two."""
        self.assertEqual(JS.count("function styleCard(st,"), 1)
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn("${styleCard(st)}", seg)
        self.assertIn("styleCard(hit, { chosen: true })", JS)
        body = JS[JS.index("function styleCard(st,"):]
        self.assertIn("stylePlate(st.plate, st.shot, st.name)", body)

    def test_the_picture_leads_at_both_scales(self):
        j = JS.index("function styleCard(st,")
        body = JS[j:JS.index(chr(10) + "}" + chr(10), j)]
        i_pic = body.index("${picture}")
        self.assertLess(i_pic, body.index("rs-name"))
        self.assertLess(body.index("rs-name"), body.index("rs-desc"))

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
        self.assertIn("await loadRenderStyles(); await adoptHouseStyle();", JS,
                      "the library loads before its house style is adopted")
        self.assertIn("async function adoptHouseStyle", JS)
        self.assertIn('out[0].key = "house"', JS,
                      "style 1 of the rendering document is the house slot")
        i = JS.index("async function adoptHouseStyle")
        seg = JS[i:i + 900]
        self.assertIn("/api/bible/house-style", seg)
        self.assertIn("card._adopted", seg, "captured once, not per open")
        self.assertIn("if (!h?.has_bible) return", seg,
                      "a production with nothing drawn keeps the shipped text")
        # all three libraries load through one path now (2026-08-22)
        self.assertIn("if (styles === RENDER_STYLES) { await loadRenderStyles();"
                      " await adoptHouseStyle(); }", JS)

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
        self.assertIn("styleCard(hit,", seg, "the same component, B1")
        self.assertIn("btn.after(box)", seg, "under the button, not above")

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

    def test_the_provenance_leads_and_is_separated(self):
        """B6 (RULE_PASS 2026-08-16): a generated entry and an authored one
        must not look identical. Provenance is the FIRST line with a
        hairline under it — position alone does not disclose."""
        i = JS.index("async function adoptHouseStyle")
        seg = JS[i:i + 1200]
        self.assertIn("FROM THIS PRODUCTION", seg)
        self.assertIn("card.source", seg)
        j = JS.index("function styleCard(st,")
        body = JS[j:JS.index(chr(10) + "}" + chr(10), j)]
        k = body.index("st.source ?")
        self.assertLess(k, body.index("rs-name"), "first, not buried")
        self.assertIn("rs-seam", body, "and a hairline after it")

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
        self.assertIn("async function loadStyleLibrary", JS)
        self.assertIn("loadCinemaStyles = () => loadStyleLibrary", JS)
        self.assertIn("/api/styles/${library}", JS)
        self.assertIn('loadStyleLibrary("cinematography", CINEMA_STYLES)', JS)
        for gone in ("Hard & Directional", "Overcast Flat", "Practical-Lit"):
            self.assertNotIn(gone, JS, f"{gone} outlived the replacement")

    def test_the_card_shows_what_the_user_asked_for(self):
        """B4 cut it from seven roles to four; the key question and the
        operating principle moved behind `Read the grammar`, and the card
        keeps the picture, the name, the words and the films."""
        i = JS.index("function styleCard(st,")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        for probe in ("rs-frames", "rs-name", "rs-desc", "rs-films",
                      "rs-prompt-link"):
            self.assertIn(probe, seg, f"the card is missing {probe}")
        r = JS.index("function openGrammarReader(st) {")
        rd = JS[r:JS.index(chr(10) + "}" + chr(10), r)]
        for probe in ("rs-sub", "rs-q", "rs-principle"):
            self.assertIn(probe, rd, f"the reading view is missing {probe}")

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
        self.assertIn("function openGrammarReader(st) {", JS)
        i = JS.index('$$(".rs-prompt-link", ov)')
        self.assertIn("e.stopPropagation()", JS[i:i + 400])
        self.assertGreater(i, JS.index("function openStylePicker("))
        self.assertIn("openGrammarReader(st)", JS[i:i + 400])

    def test_the_subtitle_is_a_label_not_a_signal(self):
        """Eight amber subtitles on one surface is eight of nothing."""
        b = re.search(r"\.rs-sub \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertNotIn("--accent", b.group(1))

    def test_the_endpoint_serves_it(self):
        self.assertIn('@app.get("/api/styles/{library}")', MAIN)


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

    def test_a_style_with_no_frames_states_it_and_shows_no_cells(self):
        i = JS.index("function styleCard(st,")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn("REFERENCE FRAMES — NOT YET IN THE LIBRARY", seg)
        self.assertNotIn("rs-cell-empty", seg)


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
        i = JS.index("function styleCard(st,")
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

    def test_a_grammar_never_pads_to_three(self):
        """B3 REFUSED the dashed cells. Canon forbids reserving the shape
        of the missing thing; the one exception earns it by stating the
        blocker, and a dashed cell states nothing."""
        j = JS.index("function styleCard(st,")
        body = JS[j:JS.index(chr(10) + "}" + chr(10), j)]
        self.assertNotIn("rs-cell-empty", body)
        self.assertNotIn("length: 3", body, "no padding")
        self.assertIn("shots.length", body, "only the frames that exist")
        self.assertIn("REFERENCE FRAMES — NOT YET IN THE LIBRARY", body)
        self.assertNotIn("rs-cell-empty", CSS)

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


class TheModeIsOnDiskNotInMemory(unittest.TestCase):
    """User 2026-08-16: "understand the diff mode between local and online
    iteration — also collect changes and push when stated". Context gets
    compacted; a file does not."""

    SKILL = ROOT / ".claude/skills/iterate/SKILL.md"

    def test_the_skill_exists_and_is_invocable(self):
        self.assertTrue(self.SKILL.exists())
        head = self.SKILL.read_text(encoding="utf-8")[:400]
        self.assertIn("name: iterate", head)
        self.assertIn("description:", head)

    def test_absent_state_means_online(self):
        """A fresh clone, a cron run or another agent must behave exactly
        as before this skill existed."""
        src = self.SKILL.read_text(encoding="utf-8")
        self.assertIn("Absent file ⇒ **online**", src)

    def test_the_two_things_that_never_bend_are_named(self):
        src = self.SKILL.read_text(encoding="utf-8")
        self.assertIn("Tests stay green every commit", src)
        self.assertIn("logs its row", src)
        self.assertIn("batching is about deploys", src.lower())

    def test_the_ship_chain_keeps_its_order(self):
        """stage_release archives HEAD — running it before the commit
        ships stale content, which has happened twice."""
        src = self.SKILL.read_text(encoding="utf-8")
        i = src.index("## `/iterate ship`")
        seg = src[i:src.index("## `/iterate online`")]
        for step in ("Both suites green", "Bump VERSION", "Commit the bump",
                     "stage_release.py", "Commit the zips", "Poll"):
            self.assertIn(step, seg)
        self.assertLess(seg.index("Commit the bump"), seg.index("stage_release.py"))
        self.assertIn("A push is not a deploy", seg)

    def test_what_must_ship_anyway_is_listed(self):
        src = self.SKILL.read_text(encoding="utf-8")
        for must in ("live tenant", "boot migration", "storefront",
                     "security fix"):
            self.assertIn(must, src)

    def test_the_state_file_never_enters_git(self):
        ig = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".claude/iteration.json", ig)

    def test_claude_md_points_at_it(self):
        md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(".claude/iteration.json", md)
        self.assertIn("Read it before any change to code", md)


class TheKeyModalSaysWhatItIsDoing(unittest.TestCase):
    """User-caught 2026-08-16: "the test and save process on the settings
    page in the small modal is not good. You click the button, long
    delay, no feedback." It made two network calls — a save, then a LIVE
    provider test — and changed nothing on screen for either, while
    staying clickable so a second press fired the pair again."""

    def body(self):
        i = JS.index("function authModal(key)")
        return JS[i:JS.index(chr(10) + "}" + chr(10), i)]

    def test_the_button_states_which_half_is_running(self):
        b = self.body()
        self.assertIn('setBusy(true, "Saving…")', b)
        self.assertIn('setBusy(true, "Testing…", testBtn)', b)
        self.assertIn("ok.disabled = on", b, "and cannot be pressed twice")

    def test_the_busy_label_lands_on_the_button_doing_the_work(self):
        """Found in use 2026-08-20: a Test relabelled SAVE to `Testing…`,
        which is the wrong button entirely."""
        b = self.body()
        self.assertIn("const setBusy = (on, label, which = null)", b)
        self.assertIn("const btn = which || ok", b)

    def test_the_modal_does_not_change_shape_while_it_tests(self):
        """User 2026-08-20: the progress element is right; the modal
        growing under it is not. The box is laid out whether it has
        something to say or not."""
        css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
        self.assertIn(".auth-modal .busy.busy-inline:empty { display: flex; }", css)
        self.assertIn(".auth-modal .busy.busy-inline { min-height:", css)

    def test_the_slow_half_says_it_is_a_live_call(self):
        b = self.body()
        self.assertIn("live", b)
        self.assertIn("few seconds", b)

    def test_elapsed_seconds_separate_slow_from_hung(self):
        """A3 ruled the threshold: elapsed appears only AFTER three
        seconds — before that it is noise, and its whole job is telling a
        slow call from a hung one."""
        b = self.body()
        self.assertIn('$(".elapsed", stateEl)', b)
        self.assertIn("Date.now() - t0", b)
        self.assertIn('secs >= 3 ? `${secs}s` : ""', b)

    def test_cancel_stays_live_so_the_modal_cannot_lock(self):
        """Disabling it was worse than the silence it replaced: a slow
        provider left no way out. Since 2026-08-20 Test stores nothing, so
        leaving mid-test costs nothing at all — and says so."""
        b = self.body()
        self.assertNotIn("cancel.disabled = on", b)
        self.assertIn("Stopped waiting — nothing was saved.", b)

    def test_testing_stores_nothing(self):
        """User 2026-08-20: Test saved the key first, so a credential
        EXISTED before the user agreed to keep it — the first-run
        walkthrough advanced on Test, and Cancel left the key behind.
        Only Save may write."""
        b = self.body()
        i = b.index("if (testBtn) testBtn.onclick")
        test_half = b[i:b.index('$("[data-mf=ok]", ov).onclick', i)]
        self.assertIn('json: { provider: P.test, key: k }', test_half,
                      "the unsaved key is proved by being sent, not stored")
        self.assertNotIn('"/api/settings"', test_half,
                         "Test must not write the key")

    def test_a_pass_is_only_recorded_for_a_key_the_studio_holds(self):
        """A green row for a credential that was never saved would be a
        lie on the settings page."""
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = main.index('@app.post("/api/settings/test")')
        seg = main[i:i + 1200]
        self.assertIn("record = not key", seg)
        self.assertIn("if record:", seg)

    def test_the_scrim_still_holds_mid_flight(self):
        b = self.body()
        self.assertIn("if (e.target === ov && !busy) done(null)", b)

    def test_a_failure_lands_in_the_modal_not_only_a_toast(self):
        """EVERY failure path, not just one — the modal gained a second
        act on 2026-08-20 when `Test & save` was split, and a toast can be
        missed while the user is looking here."""
        b = self.body()
        catches = [i for i in range(len(b)) if b.startswith("} catch (err) {", i)]
        self.assertGreaterEqual(len(catches), 2, "Test and Save each report")
        for i in catches:
            seg = b[i:i + 260]
            self.assertIn("setBusy(false", seg)
            self.assertIn('"bad"', seg)
            self.assertIn("err.message", seg)

    def test_test_and_save_are_two_acts(self):
        """User 2026-08-20: one button doing two things read as a single
        confusing act. Test answers and stays open; Save closes."""
        b = self.body()
        self.assertIn('data-mf="test"', b)
        self.assertIn('data-mf="ok"', b)
        # Save is a local write and nothing else — no live call rides it
        i = b.index('$("[data-mf=ok]", ov).onclick')
        save = b[i:]
        self.assertNotIn("/api/settings/test", save,
                         "Save must not smuggle the provider call back in")

    def test_an_empty_key_states_it_in_place(self):
        self.assertIn('say("Paste the key first.", "bad")', self.body())

    def test_it_adopts_the_one_busy_vocabulary(self):
        """A3: NOT a second vocabulary. `.busy` gained an inline life and
        the bespoke `.auth-state` markup is retired — a new class name for
        the same two facts is how a system grows a second way to say one
        thing."""
        b = self.body()
        self.assertIn('class="busy busy-inline"', b)
        self.assertIn('class="spinner"', b)
        self.assertIn('class="busy-label"', b)
        for gone in ("auth-state", "auth-spin", "auth-elapsed"):
            self.assertNotIn(gone, JS, gone)
            self.assertNotIn(gone, CSS, gone)
        self.assertIn(".busy.busy-inline {", CSS)


class ProductionsIsASettingsTab(unittest.TestCase):
    """User 2026-08-16: "Move Productions into settings. Make it the first
    tab. Adjust the FTUE if needed to still go to AI Models on first visit
    even though we are making that the second tab." Both are "this
    install" — one was a header tool and the other a page."""

    def test_it_left_the_header(self):
        self.assertNotIn('data-view="projects"', HTML)
        self.assertIn('data-view="settings"', HTML)

    def test_it_is_the_first_tab(self):
        i = HTML.index('id="settings-subnav"')
        seg = HTML[i:HTML.index("</nav>", i)]
        subs = re.findall(r'data-sub="(\w+)"', seg)
        self.assertEqual(subs[0], "productions")
        self.assertEqual(subs[1], "api")

    def test_but_a_first_visit_still_lands_on_ai_and_engines(self):
        """Order and default are two different decisions. With no key,
        nothing else in the app can run."""
        i = HTML.index('id="settings-subnav"')
        seg = HTML[i:HTML.index("</nav>", i)]
        j = seg.index('data-sub="api"')
        self.assertIn('class="active"', seg[j:j + 60])
        self.assertNotIn('class="active"', seg[:j],
                         "Productions is first, not default")

    def test_the_tab_carries_the_whole_library(self):
        i = HTML.index('data-subview="productions"')
        seg = HTML[i:HTML.index('data-subview="api"')]
        for probe in ('id="prod-cards"', 'id="proj-new"', 'id="proj-restore"',
                      'id="prod-count"'):
            self.assertIn(probe, seg, probe)

    def test_its_own_template_is_gone_rather_than_orphaned(self):
        self.assertNotIn("tpl-projects", HTML)
        self.assertNotIn('useTemplate("tpl-projects")', JS)

    def test_settings_fills_the_tab(self):
        i = JS.index("async function renderSettings(")
        self.assertIn("renderProjectsView()", JS[i:i + 400])

    def test_the_old_path_still_opens_the_tab(self):
        """/productions is a link people have. It opens Settings on
        Productions rather than 404ing or landing on engines."""
        self.assertIn('projects: "productions"', JS)
        self.assertIn('projects: () => renderSettings("productions")', JS)
        i = JS.index("async function renderSettings(")
        self.assertIn("openTab || uiGet(", JS[i:i + 900])


class ALockedStageExplainsRatherThanRefuses(unittest.TestCase):
    """User-caught 2026-08-16: "I moused over the collapsed header bar, I
    got the 'no' symbol. That's wrong." Clicking a locked stage opens a
    popover naming its blocker — the handler even refreshes the band
    first so a stale lock cannot refuse wrongly. `not-allowed` claimed the
    one thing that is not true of it."""

    def test_the_cursor_offers_the_explanation(self):
        b = re.search(r"#nav button\.s-locked \{([^}]*)\}", CSS).group(1)
        self.assertIn("cursor: help", b)
        self.assertNotIn("not-allowed", b)

    def test_it_is_still_not_a_destination(self):
        """`help` is not permission — the cell remains aria-disabled and
        the click yields a popover, never navigation."""
        self.assertIn('btn.setAttribute("aria-disabled", isLocked ? "true" : "false")', JS)
        i = JS.index("if (lockedStages.has(view)) {")
        self.assertIn("lockPopover(view)", JS[i:i + 400])

    def test_the_genuinely_inert_things_keep_the_no_symbol(self):
        """A frame that states a gate and does nothing on click is a
        different case, and keeps not-allowed."""
        self.assertIn("cursor: not-allowed", block(".made-gated"))


class CastingOpensAModalNotAFileExplorer(unittest.TestCase):
    """User 2026-08-16: "When you click a character to cast, currently it
    pops open a file explorer. Too jarring... instead of adding that to
    the list, it should open in a modal. Once you save it, the card goes
    where it is now."

    Two abrupt things happened: the button wrote the card with no chance
    to look at what the read proposed, and the card's `+` tile was a bare
    file input, so the OS picker arrived over the app with nothing having
    been confirmed."""

    def body(self):
        i = JS.index("function castModal(rec, onDone)")
        return JS[i:JS.index(chr(10) + "}" + chr(10), i)]

    def test_the_cast_button_opens_the_modal(self):
        self.assertIn('$("[data-f=cast]", card).onclick = () => castModal(rec, onChange)', JS)

    def test_nothing_is_created_until_it_is_cast(self):
        b = self.body()
        i = b.index('ok.onclick')
        self.assertIn('api("/api/subjects", { method: "POST"', b[i:],
                      "the write lives behind the button, not the open")
        self.assertNotIn('api("/api/subjects", { method: "POST"', b[:i])
        self.assertIn("Nothing is created until you cast it", b)

    def test_it_carries_what_the_read_proposed_and_lets_it_be_edited(self):
        b = self.body()
        for f in ("[data-f=kind]", "[data-f=subtitle]", "[data-f=traits]"):
            self.assertIn(f, b, f)
        self.assertIn("rec.subtitle", b)
        self.assertIn("rec.traits", b)

    def test_photos_are_chosen_here_and_uploaded_on_cast(self):
        b = self.body()
        # the picking moved into the shared tray; casting only reads it
        self.assertIn("const tray = photoTray(thumbs,", b)
        self.assertIn("const picked = tray.files()", b)
        self.assertIn("they upload when you cast", b)
        i = b.index("ok.onclick")
        self.assertIn("/reference`, { method: \"POST\", body: fd }", b[i:],
                      "and only then")

    def test_the_upload_path_is_the_cards_own_not_a_second_one(self):
        b = self.body()
        self.assertIn("/api/subjects/${created.id}/reference", b)

    def test_it_reports_while_it_writes(self):
        b = self.body()
        self.assertIn('say("Creating the card…", "work")', b)
        self.assertIn("Attaching photo ${i + 1} of ${picked.length}", b)
        self.assertIn('class="busy busy-inline"', b,
                      "the one busy vocabulary, per A3")

    def test_a_partial_failure_says_which_half_got_through(self):
        b = self.body()
        i = b.index("} catch (err) {")
        self.assertIn("say(err.message", b[i:i + 300])
        self.assertIn("card may already exist", b)


class OneTrayForBothWaysIn(unittest.TestCase):
    """"Finish casting modal" (user 2026-08-16). The card they
    photographed was already CAST — its `+` tile was still a bare file
    input, so the OS picker arrived over the app the instant it was
    touched. Casting and an existing card now share one tray."""

    def test_the_plus_on_a_cast_card_is_a_button_not_a_file_input(self):
        i = JS.index('data-f="add-photos"')
        seg = JS[i - 200:i + 200]
        self.assertIn('<button type="button" class="subj-slot"', seg)
        self.assertNotIn('<input type="file"', seg)
        self.assertIn('photoTrayModal(s, onChange)', JS)

    def test_the_tray_is_one_function_not_two_copies(self):
        self.assertEqual(JS.count("function photoTray(host,"), 1)
        # both callers use it
        self.assertIn("const tray = photoTray(thumbs,", JS)
        self.assertIn('const tray = photoTray($("[data-f=thumbs]", ov),', JS)

    def test_nothing_uploads_until_the_act(self):
        i = JS.index("function photoTray(host,")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertNotIn("api(", seg, "the tray only picks and shows")
        self.assertIn("URL.createObjectURL", seg, "and shows what was picked")

    def test_attach_is_dead_until_something_is_chosen(self):
        i = JS.index("async function photoTrayModal")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn('data-f="ok" disabled', seg)
        self.assertIn("ok.disabled = !fs.length", seg)
        self.assertIn("Attach ${fs.length} photo", seg, "and counts them")

    def test_it_names_the_role_the_photos_will_take(self):
        i = JS.index("async function photoTrayModal")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn("SUBJECT_ROLE_OF[s.kind]", seg)
        self.assertIn("grouped under this exact name", seg)

    def test_a_partial_failure_is_stated_in_both_modals(self):
        for fn in ("function castModal(rec, onDone)", "async function photoTrayModal"):
            i = JS.index(fn)
            seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
            j = seg.index("} catch (err) {")
            self.assertIn('say(err.message, "bad")', seg[j:j + 300], fn)


class TheBreakdownHasTwoDoors(unittest.TestCase):
    """User 2026-08-22: "I want two separate columns."

    This REVERSES C1 (RULE_PASS_2 C, ruled 2026-08-18), which merged the
    auto door and the blank sheet into one form. A user instruction
    outranks a design ruling; the reversal is logged in DESIGN_SYSTEM.md's
    uncanonized table so the next pass does not re-merge them from the
    same reasoning.

    That reasoning is answered rather than ignored. It said the two doors
    "called the same endpoint with the same brief field" and the blank one
    "was a strict superset" — so the doors are now genuinely different
    acts calling different endpoints, and the blank one carries no brief,
    no paste and no panel list at all.
    """

    def auto(self):
        i = HTML.index('<form id="spec-auto-form">')
        return HTML[i:HTML.index("</form>", i)]

    def blank(self):
        i = HTML.index('<form id="spec-new-form">')
        return HTML[i:HTML.index("</form>", i)]

    def test_there_are_two_doors_in_one_section(self):
        i = HTML.index('class="intake-doors"')
        seg = HTML[i:i + 6000]
        self.assertIn('class="door door-auto"', seg)
        self.assertIn('class="door door-blank"', seg)

    def test_each_states_its_nature_once(self):
        """Canon (2026-08-06): each door states its nature in Courier
        beside its name."""
        i = HTML.index('class="intake-doors"')
        seg = HTML[i:i + 6000]
        self.assertIn("READS THE SCREENPLAY", seg)
        self.assertIn("YOU FILL EVERYTHING", seg)

    def test_amber_marks_the_stronger_door(self):
        """The merge's own complaint was that "amber sat on the superseded
        one — the app recommended the weaker door in its scarcest signal".
        Amber is on the door that reads the screenplay, and the blank
        sheet's submit is a ghost."""
        self.assertIn('class="door door-auto"', HTML)
        self.assertIn(".door-auto { border-color: var(--accent-line)", CSS)
        self.assertIn('class="ghost" id="spec-new-go"', HTML)
        self.assertIn('class="primary" id="spec-auto-go"', HTML)

    def test_the_generative_fields_belong_to_the_generative_door(self):
        a, b = self.auto(), self.blank()
        for probe in ("What should I get?", "Or paste a section",
                      "Panels to include"):
            self.assertIn(probe, a, probe)
            self.assertNotIn(probe, b, f"{probe} must not be in the blank door")

    def test_typing_finds_scenes_as_you_go(self):
        """User, 2026-08-22: "search is not auto-filling scenes when I type
        them in — it should auto-populate based on scene names in the
        screenplay."

        This reverses the same day's "do not run until the submit": the
        results were moved onto the button, and the user wanted the
        suggestions back. What the button does now is READ the saved scene,
        not run the search."""
        i = JS.index('sceneIn.addEventListener("input"')
        seg = JS[i:i + 260]
        self.assertIn("draw();", seg)
        self.assertIn('sceneIn.addEventListener("focus", draw)', JS)
        self.assertNotIn("__sceneSearchAsk", JS)

    def test_the_verb_is_scan_screenplay(self):
        self.assertIn('id="spec-auto-go">Scan Screenplay', HTML)
        i = JS.index("const syncAlternatives = ")
        seg = JS[i:i + 1200]
        self.assertIn('"Scan Screenplay"', seg)
        self.assertIn("Break down the pasted section", seg)

    def test_only_the_title_lands_in_the_search_field(self):
        """User, 2026-08-22: "whatever lands in that What should I get
        field is awkward — when they select the scene, just put the scene
        title in there."

        A 150-character composed brief in a one-line input is unreadable
        and unsearchable, and it made the field mean two things at once.
        It means one now: the reference."""
        i = JS.index("const choose = row =>")
        seg = JS[i:i + 2200]
        self.assertIn("sceneIn.value = scenePick.label", seg)
        self.assertIn("label: row.scene.heading", seg)
        self.assertIn("label: row.loc.location", seg)

    def test_the_brief_moves_to_the_row_below_and_stays_editable(self):
        """"All the other information, put it in a section below the
        select field." It is still what the scan asks for, so it is a
        field rather than a caption — the composed sentence is a starting
        point, not a verdict."""
        self.assertIn('id="spec-auto-brief"', HTML)
        i = JS.index("const choose = row =>")
        self.assertIn("box.value = scenePick.brief", JS[i:i + 2200])
        j = JS.index('$("#spec-auto-form").addEventListener("submit"')
        self.assertIn('$("#spec-auto-brief")?.value.trim() || pick.brief',
                      JS[j:j + 900])

    def test_a_selection_takes_the_paste_slot_and_gives_it_back(self):
        """"Have it take the place of the Or paste a section area. If they
        remove the selection, the Or Paste A Section section comes back."
        They are alternatives anyway — a pasted section REPLACES the
        screenplay, a picked scene points into it."""
        i = JS.index("const syncAlternatives = ")
        seg = JS[i:i + 1400]
        self.assertIn("pickRow.hidden = !scenePick", seg)
        self.assertIn("pasteRow.hidden = !!scenePick", seg)
        self.assertIn(".door-row[hidden] { display: none; }", CSS)

    def test_the_list_carries_none_and_paste_above_the_matches(self):
        """User, 2026-08-22: "at the top of the selection search should be
        None"; then "next to it put Paste a section, which will activate
        the Paste a section section and deactivate What should I get."

        With a selection made the paste row is off screen, so the list is
        the only way to reach it — a switch you cannot reach is not one."""
        i = JS.index("const STANDING = [")
        seg = JS[i:i + 400]
        self.assertIn('kind: "none"', seg)
        self.assertIn('kind: "paste"', seg)
        self.assertLess(seg.index('"none"'), seg.index('"paste"'))
        j = JS.index("const choose = row =>")
        body = JS[j:j + 2200]
        self.assertIn('if (row.kind === "none") { clearPick(); return; }', body)
        self.assertIn("pasting = true;", body)

    def test_paste_mode_is_stated_not_inferred_from_the_box(self):
        """The list can switch the door into paste mode while the box is
        still empty, and "has text" cannot tell that from "not chosen
        yet". Emptying the box is the one way back out."""
        i = JS.index("const syncAlternatives = ")
        self.assertIn("const usingPaste = pasting || !!paste.value.trim();",
                      JS[i:i + 1400])
        j = JS.index('$("#spec-auto-source")?.addEventListener("input"')
        self.assertIn("pasting = false;", JS[j:j + 400])

    def test_typing_over_the_title_drops_the_pick_but_not_the_words(self):
        """Two questions, two functions. Typing means search again, so the
        pointer goes and the keystrokes stay; removing the selection
        empties the field as well, because a title left behind still reads
        as chosen."""
        i = JS.index('sceneIn.addEventListener("input"')
        self.assertIn("if (scenePick) dropPick();", JS[i:i + 220])
        j = JS.index("clearPick = () => {" + chr(10) + "        dropPick();")
        seg = JS[j:j + 260]
        self.assertIn("dropPick();", seg)
        self.assertIn('sceneIn.value = ""', seg)

    def test_an_orphaned_brief_is_never_sent_with_the_next_pick(self):
        """A hand-edited brief whose scene was dropped sits in a hidden
        row. It would be invisible and still submitted."""
        i = JS.index("const dropPick = () => {")
        self.assertIn('box.value = ""', JS[i:i + 320])

    def test_the_scan_sends_the_pointer_for_a_scene_only(self):
        """A location board wants all of its scenes, which is the
        matched-by-name path; only a scene has one line to point at."""
        i = JS.index('$("#spec-auto-form").addEventListener("submit"')
        seg = JS[i:i + 2200]
        self.assertIn('pick && pick.kind === "scene" ? pick : null', seg)
        self.assertIn("scene_line: ref ? ref.line", seg)
        self.assertIn("scene_heading: ref ? ref.heading", seg)

    def test_the_doors_source_lives_in_one_place(self):
        """It was about to be inferred in three — the row visibility, the
        disable state and the submit. One variable, read by all of them."""
        self.assertEqual(JS.count("let scenePick = null;"), 1)
        self.assertEqual(JS.count("window.__scenePick = () => scenePick;"), 1)
        self.assertNotIn("__sceneRef", JS)

    def test_a_no_match_still_says_nothing_unless_something_is_picked(self):
        """An unmatched brief is a perfectly good brief, and two versions
        of a message here were noise over a field still being typed in.
        The one exception is a live selection: the list is then the only
        way back out of it."""
        i = JS.index("if (!matches.length && !scenePick)")
        self.assertIn("closeHits(); return;", JS[i:i + 120])
        self.assertNotIn("NOTHING MATCHES ${esc(", JS)

    def test_the_brief_field_is_the_search(self):
        """User, 2026-08-22: "What should I get is our search field. If it
        matches a scene its listed. If not, the user can just type and
        that is what is passed to the engine."

        A native datalist was tried first and withdrawn: it filters however
        the browser feels like it, cannot rank, and cannot show that TERRA
        NOVA is a location holding seven scenes."""
        a = self.auto()
        self.assertIn('id="spec-auto-subject"', a)
        self.assertIn('id="spec-auto-scene-hits"', a)
        self.assertNotIn("datalist", a)
        self.assertIn('const sceneIn = $("#spec-auto-subject")', JS)

    def test_every_typed_word_must_appear_somewhere(self):
        """"terra" finds all seven Terra Nova locations; "terra bridge"
        finds the one. Order does not matter and neither does position —
        that is what makes it a search rather than a prefix filter."""
        i = JS.index("const search = q =>")
        seg = JS[i:i + 900]
        self.assertIn("words.every", seg)
        self.assertIn("hay.includes(w)", seg)

    def test_locations_lead_the_results(self):
        """"Terra Nova" is usually a request for the place rather than one
        scene in it, and a location result composes a board over all of
        its scenes."""
        i = JS.index("const search = q =>")
        seg = JS[i:i + 1100]
        self.assertLess(seg.index('kind: "loc"'), seg.index('kind: "scene"'))

    def test_there_is_one_brief_composer_per_kind(self):
        """The deep link from the coverage map and the search compose the
        same sentences; two copies drifted once already."""
        self.assertEqual(JS.count("const sceneBrief = "), 1)
        self.assertEqual(JS.count("const locationBrief = "), 1)

    def test_a_written_brief_is_not_searched(self):
        """User, 2026-08-22: "if I pick a scene and then click into the
        field I get strange text." Picking writes a 150-character sentence
        into the field; focusing it searched for that sentence, found
        nothing, and shouted the whole brief back in capitals.

        Length is the test rather than a "was picked" flag — a query is
        short, and the moment the field holds a written brief there is
        nothing to look up, however it got there."""
        i = JS.index("const QUERY_MAX")
        seg = JS[i:i + 700]
        self.assertIn("QUERY_MAX = 80", seg)
        self.assertIn("t.length <= QUERY_MAX", seg)
        self.assertIn("if (!isQuery(sceneIn.value)) { closeHits(); return; }", JS)

    def test_choosing_does_not_re_enter_the_search(self):
        """choose() used to dispatch a synthetic input event to refresh the
        alternatives, which walked straight back into draw() with the new
        brief in hand."""
        i = JS.index("const choose = row =>")
        seg = JS[i:i + 1200]
        self.assertIn("syncAlternatives();", seg)
        self.assertNotIn("dispatchEvent", seg)

    def test_the_brief_and_the_paste_are_alternatives(self):
        """User: they "should act as radio buttons — you cant do both".
        They are genuinely exclusive downstream: source_text REPLACES the
        screenplay, so a brief alongside it would name material the model
        has been told not to look at."""
        i = JS.index("const syncAlternatives = ")
        seg = JS[i:i + 1200]
        self.assertIn("brief.disabled = usingPaste", seg)
        self.assertIn("paste.disabled = usingBrief", seg)
        self.assertIn('classList.toggle("is-off"', seg)
        self.assertIn(".door-row.is-off", CSS)

    def test_the_verb_says_which_alternative_is_live(self):
        i = JS.index("const syncAlternatives = ")
        seg = JS[i:i + 1200]
        self.assertIn("Break down the pasted section", seg)
        self.assertIn("Scan Screenplay", seg)

    def test_the_blank_door_is_not_a_superset(self):
        """The merge's central objection. It asks for a name and nothing
        that could be read."""
        b = self.blank()
        for gone in ("spec-new-source", "spec-new-panels", "spec-new-provider"):
            self.assertNotIn(gone, b, f"{gone} makes it a superset again")
        self.assertIn("NOTHING IS READ", b)
        self.assertIn("NO MODEL RUNS", HTML)

    def test_they_call_different_endpoints(self):
        """What actually makes them two acts rather than one form."""
        i = JS.index('$("#spec-auto-form").addEventListener("submit"')
        auto = JS[i:i + 1800]
        j = JS.index('$("#spec-new-form").addEventListener("submit"')
        blank = JS[j:j + 900]
        self.assertIn('api("/api/specs/autofill"', auto)
        self.assertNotIn('api("/api/specs/autofill"', blank)
        self.assertIn('api("/api/specs"', blank)

    def test_each_states_what_it_does_to_the_work(self):
        """A1: a label names its effect, not its filing destination.
        RULE_PASS_2 C5 took the first person out of it."""
        a = self.auto()
        self.assertIn("SCREENPLAY IS READ FOR IT", a)
        self.assertIn("PASTE WINS — SCRIPT NOT READ", a)
        self.assertIn("EMPTY — CONTENT DECIDES", a)
        self.assertIn("A NAME ONLY", a)

    def test_the_section_carries_a_way_to_read_the_screenplay(self):
        self.assertIn('id="spec-auto-open-screenplay"', self.auto())
        self.assertIn('window.open("/api/screenplay/file"', JS)

    def test_the_explaining_button_is_gone(self):
        """C3 (2026-08-18) survives every later change: a verb whose effect
        was to EMPTY a field and toast an explanation of what the
        now-empty field means."""
        self.assertNotIn("autopanels", JS)
        self.assertNotIn("autopanels", HTML)

    def test_the_submit_states_the_act_it_will_perform(self):
        """C2 survives: the door holds two acts and the verb says which."""
        i = JS.index("const syncAlternatives = ")
        self.assertIn("go.textContent", JS[i:i + 1200])

    def test_it_reports_while_it_drafts(self):
        i = JS.index('$("#spec-auto-form").addEventListener("submit"')
        seg = JS[i:i + 1800]
        self.assertIn("startBusy(", seg)
        self.assertIn("Reading the screenplay and drafting the breakdown", seg)

    def test_an_empty_auto_door_says_where_to_go(self):
        """It cannot make an empty sheet any more, so it must not fail
        silently — it names the door that can."""
        i = JS.index('$("#spec-auto-form").addEventListener("submit"')
        seg = JS[i:i + 900]
        self.assertIn("use Blank sheet beside it", seg)

    def test_each_door_keeps_its_own_draft(self):
        """One localStorage key would restore half a form into the wrong
        door."""
        self.assertIn('persistForm("autoSpecDraft"', JS)
        self.assertIn('persistForm("blankSpecDraft"', JS)


class EveryDoorIntoCastingIsTheModal(unittest.TestCase):
    """Finishing the casting modal. Three doors existed — the proposal
    card's `Cast`, a cast card's `+`, and the manual `+ Cast` row — and
    the manual one still wrote the card on click and then fired a file
    picker whose selector had already gone stale, so it silently did
    nothing at all."""

    def test_the_manual_row_opens_the_modal(self):
        i = JS.index('$("#wiz-subj-add").onclick')
        seg = JS[i:i + 700]
        self.assertIn("castModal({ name", seg)
        self.assertNotIn('api("/api/subjects", { method: "POST"', seg,
                         "it no longer writes on click")

    def test_the_stale_picker_selector_is_gone(self):
        self.assertNotIn("[data-f=up]", JS,
                         "the input it reached for no longer exists")

    def test_the_uncast_chip_opens_it_too(self):
        """The fourth door, and the one most likely to be used."""
        i = JS.index("chip.onclick")
        self.assertIn("castModal(r, refreshAll)", JS[i:i + 200])

    def test_all_four_doors_reach_one_component(self):
        self.assertEqual(JS.count("castModal("), 4,
                         "one definition, three callers")
        self.assertEqual(JS.count("photoTrayModal("), 2,
                         "one definition, one caller")


if __name__ == "__main__":
    unittest.main()
