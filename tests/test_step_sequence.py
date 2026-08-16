"""The step sequence — STEP_SEQUENCE_SPEC_2026-08-14, mock hier-4a.

Stage 04 is the reference implementation of the vocabulary: three type
sizes, fill classifies, verbs on one right edge, a numbered spine, two
states per step, and — outranking all of it — the image is the hero.

The aspect regression is the reason the spec exists: the Aspect select
hardcoded 16:9 while the panel head reported the LAST TAKE's ratio, so
Generate silently re-shaped a 21:9 hero panel and spent a 4K render on
the wrong slot shape."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def block(sel: str) -> str:
    bodies = re.findall(re.escape(sel) + r"\s*{([^}]*)}", CSS)
    assert bodies, f"missing rule: {sel}"
    return "\n".join(bodies)


class TheImageIsTheHero(unittest.TestCase):
    """§1.0 — this app makes movies. On any surface that has a picture the
    picture is the largest element on it, at the subject's own ratio."""

    def test_the_take_carries_the_panels_own_shape(self):
        self.assertIn('class="stage-shot stage-hero" style="aspect-ratio:${aspectCss}"', JS)
        self.assertIn("const aspectCss", JS)
        self.assertIn('.split(":").map(Number)', JS,
                      "the ratio is derived from the panel's shape, not guessed")

    def test_the_frame_never_lies_about_the_take(self):
        """aspect-ratio, never a fixed height; contain, never cover — a
        crop would hide pixels the user is judging."""
        b = block(".wb-card .stage-hero img")
        self.assertIn("object-fit: contain", b)
        self.assertIn("max-height: none", b)

    def test_the_filmstrip_is_film(self):
        """User 2026-08-15: the takes are frames of one shot, so the strip
        reads as film — a 35mm window per take with the image FITTED into
        it longest-edge first. The frame is the constant now; a strip that
        changed shape per panel read as a grid."""
        self.assertIn('class="take-frame"', JS)
        b = block(".take-frame")
        self.assertIn("aspect-ratio: 3 / 2", b)
        self.assertIn("object-fit: contain", block(".take-frame img"))
        # Perforations are a repeated inline-SVG TILE, not an asset and not
        # a decorative blend. They are the one rounded corner in the app:
        # a perf depicts a physical hole, it is not a control. And a hole
        # passes light, so it is LIGHTER than the base — drawn dark it
        # read as embossing and nobody saw film (user-caught 2026-08-15).
        roll = block(".filmroll")
        self.assertIn("data:image/svg+xml", roll)
        self.assertIn("rx=", roll, "a real perforation is rounded")
        self.assertIn("repeat-x", roll)
        self.assertIn("left bottom", roll, "perfs run along BOTH edges")

    def test_one_roll_serves_every_strip_of_frames(self):
        """The treatment belongs to "a row of frames", not to one page. It
        went on the takes strip alone and the user was looking at the
        BOARD strip on the breakdown the whole time (2026-08-15)."""
        self.assertIn('class="takes-row filmroll"', JS)
        self.assertIn('class="made-grid filmroll"', JS)

    def test_the_roll_carries_no_stock_branding(self):
        """The edge marking was retired 2026-08-15 (it cost two lines of
        height on a strip whose job is the pictures), but the rule that
        put OUR data there rather than a film-stock name still stands: a
        real stock name would be set dressing claiming something untrue
        about how these frames were made."""
        for brand in ("KODAK", "FUJI", "VISION3"):
            self.assertNotIn(brand, JS)
            self.assertNotIn(brand, CSS)

    def test_the_roll_hides_its_scrollbar_and_stays_reachable(self):
        """A bar drawn across a piece of film is chrome (user 2026-08-15).
        Hiding it is only honest if the strip can still be moved — both
        rolls drag."""
        b = block(".filmroll")
        self.assertIn("scrollbar-width: none", b)
        self.assertIn(".filmroll::-webkit-scrollbar", CSS)
        self.assertIn("dragScroll(madeStrip)", JS)
        self.assertIn("dragScroll(takesRoll)", JS)

    def test_a_drag_does_not_fire_a_click(self):
        """The pointerup that ends a drag would otherwise land as a click
        on the frame under it and open the lightbox."""
        i = JS.index("function dragScroll")
        seg = JS[i:JS.index("function seqStep")]
        self.assertIn("swallow = moved > 5", seg)
        self.assertIn("e.stopPropagation()", seg)

    def test_the_lightbox_ends_at_full_size_without_waiting(self):
        """User 2026-08-15: "I do not get the full sized image." It opened
        at the md tier and only fetched the raw file if you zoomed — which
        was the 2026-08-09 ruling against stalling on open. Both hold now:
        md paints immediately, the full image loads behind it and swaps in
        when decoded."""
        i = JS.index("function lbShow")
        seg = JS[i:JS.index("function lbStep")]
        self.assertIn('img.src = lbSize(item.src, "md")', seg,
                      "the fast tier still paints first")
        self.assertIn("new Image()", seg)
        self.assertIn("lb.full !== full", seg,
                      "a swap must not land on a take you stepped away from")
        self.assertIn("lb.atFull = true", seg)

    def test_strips_ask_for_the_thumbnail_tier(self):
        """Never pull a bigger file than the frame can show (user
        2026-08-15). The board strip was requesting md for a 300px cell."""
        i = JS.index('class="made-frame"')
        self.assertIn("image?size=thumb", JS[i:i + 300])
        j = JS.index('class="take-frame"')
        self.assertIn("image?size=thumb", JS[j:j + 300])

    def test_a_frame_click_shows_the_take_full_size(self):
        """The frame deliberately shows LESS than the take (it is a 35mm
        window with the image fitted in it), so the way to the rest has to
        be the obvious one: the click that selects it also opens it."""
        i = JS.index('$$("[data-take]", card)')
        seg = JS[i:i + 700]
        self.assertIn("openLightbox(takeItems", seg)
        self.assertIn("roomSel.staged[p.id] = id", seg,
                      "and it still makes that take the current one")

    def test_the_rail_holds_only_what_has_no_picture(self):
        """§2.15: the takes do NOT go in a side rail (the spec's own §2.5
        said they should; the mock and the user both ruled otherwise), and
        the rail's render dossier moved onto the act bar and the image."""
        i = JS.index('el.className = "board-side"')
        rail = JS[i:i + 3000]
        self.assertNotIn('<div class="rail-label">THIS RENDER</div>', rail)
        self.assertNotIn('<div class="rail-label">COMPILED PROMPT', rail)
        self.assertNotIn("side-prompt", rail)
        self.assertIn("ANCHORED TO", rail)
        self.assertIn("CARRIED NOTES", rail)

    def test_facts_about_an_image_ride_on_it(self):
        """Canon: facts about an image ride ON it. The run facts started in
        the act bar, where they cost ~400px and folded three real tools
        behind the ⋯ — the user reported the tools as gone (2026-08-14)."""
        self.assertIn("NATIVE, NEVER UPSCALED", JS)
        self.assertIn("shot-tag-size", JS)
        self.assertIn("shot-tag-run", JS)
        i = JS.index('<div class="act-bar">')
        self.assertNotIn("RUN ${", JS[i:i + 1400],
                         "the act bar carries tools, not captions")

    def test_a_tool_in_a_toolbar_is_a_button(self):
        """User ruling 2026-08-14. §1.4's ink+underline is right for a verb
        inline beside the fact it acts on; a BAR OF TOOLS at 11.5px/400
        read as footnotes and the tools were reported missing."""
        b = block(".seq .act-bar .text-act")
        self.assertIn("border: 1px solid var(--line)", b)
        self.assertIn("text-decoration: none", b)
        self.assertIn("font-size: 13.5px", b)
        self.assertIn("font-weight: 600", b)


class TheVocabulary(unittest.TestCase):
    def test_three_type_sizes_and_the_largest_anchors_them(self):
        """§1.2 — 24 / 15 / 11.5. The measured fault was nine sizes inside
        five and a half pixels, which reads as one size with noise."""
        self.assertIn("font-size: 24px", block(".seq .seq-subject"))
        self.assertIn("font-size: 15px", block(".step-prose, .seq .cam-sum"))
        for sel in (".step-label", ".step-meta", ".wb-facts"):
            self.assertIn("font-size: 11.5px", block(sel))

    def test_the_subject_beats_the_panel_h2_label(self):
        """.panel h2 sets 11px uppercase Courier; without the extra
        specificity the 24px anchor silently lost and the whole scale
        collapsed to a continuum again."""
        self.assertIn(".seq .seq-subject", CSS)
        b = block(".seq .seq-subject")
        self.assertIn("text-transform: none", b)
        self.assertIn("font-family: var(--sans)", b)

    def test_fill_classifies_and_a_tile_sits_above_its_ground(self):
        """§1.3 — a border cannot classify, because a tag and a button both
        carry one. --tile is one value above --bg2, so a set member never
        falls back to its border."""
        for tok in ("--band:", "--tile:", "--hairline:"):
            self.assertIn(tok, CSS, f"{tok} must be a token, not a loose hex")
        self.assertIn("background: var(--tile)", block(".obj-tile"))
        self.assertIn("background: var(--band)", block(".step-band"))
        def hexval(name):
            m = re.search(rf"--{name}:\s*#([0-9a-fA-F]{{6}})", CSS)
            return int(m.group(1), 16)
        ladder = [hexval(n) for n in ("field", "bg", "band", "bg2", "tile", "panel")]
        self.assertEqual(ladder, sorted(ladder),
                         "--band sits below the ground and --tile one step above")

    def test_a_verb_is_ink_underlined_and_never_wraps(self):
        """§1.4 — at 11.5px colour alone fails: an --ink-dim verb sits at
        the same value as the fact beside it, so "Change camera" read as
        part of the camera string."""
        b = block(".seq .verb, .seq .text-act")
        for decl in ("color: var(--ink)", "text-decoration: underline",
                     "text-decoration-color: var(--ink-dim)",
                     "text-underline-offset: 3px", "white-space: nowrap",
                     "font-family: var(--sans)"):
            self.assertIn(decl, b)

    def test_every_verb_aligns_to_one_right_edge(self):
        self.assertIn("margin-left: auto", block(".step-acts"))

    def test_the_step_number_is_the_spine(self):
        """§1.6 — a label gutter says what KIND of row this is; a number
        says where you are in the work. User 2026-08-16: the spine carries
        the LARGEST size in the scale, a deliberate second use of 24px
        beside the subject."""
        b = block(".step-num")
        self.assertIn("flex: 0 0 58px", b)
        self.assertIn("font-size: 24px", b)
        self.assertIn("font-family: var(--mono)", b,
                      "a step number is a machine fact")
        self.assertIn("color: var(--ok)", block(".step-done .step-num"))

    def test_an_approved_take_settles_every_step_of_its_panel(self):
        """User 2026-08-16: an approved take freezes the panel, so its
        steps are settled — not pending ticks the user never had to make.
        A frozen step offers no Confirm and no way to unconfirm; the way
        back is withdrawing the approval, an act on the take."""
        i = JS.index("function seqStep")
        seg = JS[i:JS.index("async function updateBand")]
        self.assertIn("done = done || frozen", seg)
        self.assertIn('${frozen && id ? `<span class="step-confirmed', seg,
                      "frozen states a fact — it is not a button, and the "
                      "act step (06 GENERATE) is not a confirmation at all")
        self.assertIn("done && id && !frozen", seg,
                      "only a TICK can be taken back")
        j = JS.index("const approvedTakes = panelCands")
        self.assertIn("frozen: approvedTakes.length > 0", JS[j:j + 420])
        k = JS.index("const confCount =")
        self.assertIn('c.status === "APPROVED"', JS[k:k + 220],
                      "the head count says so too")

    def test_hairline_and_band_share_extents(self):
        """§1.5 — a rule that stops short of a visible band reads as a bug."""
        b = block(".step")
        self.assertIn("border-top: 1px solid var(--hairline)", b)
        self.assertIn("padding: 18px 22px", b)
        self.assertNotIn("margin", block(".step-band"))

    def test_prose_measures_are_capped(self):
        """§1.9 — extra width goes to rails and grid columns, never to
        line length."""
        self.assertIn("max-width: 720px", block(".step-prose, .seq .cam-sum"))
        self.assertIn("max-width: 900px", block(".step-note"))

    def test_a_title_is_never_truncated(self):
        """§1.10 — "…Workshop Interior" and "…Workshop Exterior" are the
        same string once cut. Height is the cheap axis in a rail."""
        b = block(".rail-title")
        self.assertIn("white-space: normal", b)
        self.assertNotIn("text-overflow: ellipsis", b)

    def test_the_gutter_is_for_rows_not_blocks(self):
        """§1.8 — a label with a grid under it takes the full column."""
        self.assertIn("grid-template-columns: repeat(auto-fill, minmax(240px, 1fr))",
                      block(".obj-grid"))


class TwoStatesPerStep(unittest.TestCase):
    def test_only_two_states_and_both_reversible(self):
        """§1.7 — needs you, or confirmed. A confirmed step dims and stays
        fully legible: it is evidence you already ruled."""
        self.assertIn('data-confirm="${esc(id)}"', JS)
        self.assertIn('data-unconfirm="${esc(id)}"', JS)
        self.assertIn("✓ CONFIRMED", JS)
        self.assertNotIn("✓ REVIEWED", JS, "one word for one state")
        self.assertIn("color: var(--ink-dim)", block(".step-done .step-label"))

    def test_a_confirmation_never_outlives_what_it_confirmed(self):
        i = JS.index("const confSet =")
        b = JS[i:i + 320]
        self.assertIn('if (s !== "prompt") delete c.prompt', b,
                      "the prompt is compiled from 01-04, so any upstream "
                      "change unconfirms it")

    def test_confirmations_are_advisory_and_never_gate(self):
        """§2.4 — the gate is honest. A render is the end of a sequence,
        not a reward for finishing one."""
        self.assertIn("UNCONFIRMED — YOU CAN STILL RENDER", JS)
        i = JS.index('data-f="generate"')
        self.assertNotIn("confCount", JS[i - 400:i + 400],
                         "an unconfirmed step must not disable the act")


class ReferencesStateTheirReason(unittest.TestCase):
    """§2.3 — references are not a free choice: the app has already ticked
    them and can say why. An unticked row without a reason makes an
    override a guess; with one it is an informed act."""

    def test_both_rules_exist_but_never_in_one_state(self):
        i = JS.index("const refWhy =")
        b = JS[i:i + 320]
        self.assertIn("lastTake ?", b)
        self.assertIn("RODE THE PREVIOUS TAKE", b)
        self.assertIn("MATCHES A REQUIRED OBJECT", b)

    def test_the_off_rows_state_theirs_too(self):
        self.assertIn("ref-off-head", JS)
        self.assertIn("DID NOT RIDE THE PREVIOUS TAKE", JS)

    def test_the_marker_is_a_pair_and_affords_the_click(self):
        """§2.3 ruled the off marker ○ rather than a bare dot, because a
        dot reads as ABSENCE instead of as the off state of a pair. An
        empty bordered box keeps that — it is still the off half of a pair
        — and adds what ○ lacked: it looks like something you can click.
        The user could not find the way to attach a reference until it did
        (2026-08-14: "nothing there lets me ADD a ref")."""
        b = block('.ref-row input[type="checkbox"]')
        self.assertIn("border: 1px solid var(--line)", b)
        self.assertIn("cursor: pointer", b)
        self.assertNotIn("border: none", b)
        on = block('.ref-row input[type="checkbox"]:checked::before')
        self.assertIn('content: "\\2713"', on)
        self.assertIn("color: var(--ok)", on)
        self.assertIn("background: var(--tile)", block(".ref-row:hover"),
                      "the whole row is the hit target and says so")

    def test_a_tick_confirms_itself(self):
        """A glyph flipping is not feedback that an act landed."""
        i = JS.index('$(".ref-groups", card).addEventListener')
        seg = JS[i:i + 1100]
        self.assertIn('row.classList.toggle("on", on)', seg)
        self.assertIn("ATTACHED — RIDES THE NEXT TAKE", seg)

    def test_the_always_on_anchors_never_sit_among_the_toggles(self):
        i = JS.index('<span class="anchors-k">STYLE ANCHORS</span>')
        self.assertIn("ALWAYS ON", JS[i:i + 900])
        self.assertIn("SET ON PRODUCTION DESIGN", JS[i:i + 900])
        j = JS.index('class="ref-groups"')
        self.assertLess(j, i, "the toggles are their own list, above")

    def test_which_plates_is_answerable_without_a_mouse(self):
        """User-asked 2026-08-14: "I can't tell what references are being
        used for the panel." The rows named their GROUP and count; the
        plate ids lived in a hover title, and the verb called Show ids
        revealed the style anchors' ids ONLY."""
        i = JS.index("const groupRow =")
        self.assertIn("idSpan(use)", JS[i:i + 900],
                      "every row names the plates it will attach — the ones "
                      "actually chosen, not the whole group")
        j = JS.index("const showIds =")
        seg = JS[j:j + 500]
        self.assertIn('card.classList.toggle("ids-open")', seg,
                      "the verb reveals every row's ids, not just anchors")
        self.assertIn("display: inline", block(".ids-open .ref-ids"))

    def test_one_rendering_of_a_plate_set(self):
        """The rail and the reference rows state the same fact, so they
        share one function — a consecutive run collapses to its ends."""
        self.assertEqual(JS.count("function idSpan("), 1)
        i = JS.index('class="anchor-ids mono"')
        self.assertIn("idSpan(ids)", JS[i:i + 120])

    def test_counts_never_mix_an_image_against_a_group_denominator(self):
        i = JS.index("refCount.textContent")
        b = JS[i:i + 260]
        self.assertIn("SUBJECT +", b)
        self.assertIn("OF 14 ATTACHED", b)


class ThePalettePicker(unittest.TestCase):
    """Regression, user-caught 2026-08-14: every chip drew #666666 and
    every name read RESISTANCE / GRM. The picker had its own inline notes
    reader that took the hex from index 1, but the canonical shape is
    `language · name · hex[/pair] · cite` — so it read the NAME as the hex
    (falling back to grey) and the LANGUAGE as the name."""

    def test_it_reads_through_the_canonical_parser(self):
        i = JS.index('data-f="swatch-menu"')
        b = JS[max(0, i - 3000):i]
        self.assertIn("swatchNotes(r.notes)", b)
        self.assertIn("if (!sw.hex) continue", b,
                      "a swatch with no parseable hex is skipped, never "
                      "drawn as grey")

    def test_no_hand_rolled_notes_parser_survives(self):
        self.assertNotIn('"#666666"', JS,
                         "the grey fallback WAS the bug being reported "
                         "(the hex may still appear in the comment that "
                         "records it, never as a value)")
        i = JS.index('data-f="swatch-menu"')
        b = JS[max(0, i - 2600):i]
        self.assertNotIn('split("·")', b,
                         "notes are split on ' · ', and only swatchNotes "
                         "knows where the hex actually sits")

    def test_a_palette_attaches_whole_never_colour_by_colour(self):
        """User ruling 2026-08-14, and canon since 2026-08-06: a set that
        means something as a set renders as ONE object — the ramp IS the
        swatch, the colours are its inside. The first build of this picker
        offered a grid of individual colours, which is the exact shape the
        canon names as wrong."""
        i = JS.index('data-f="swatch-menu"')
        b = JS[max(0, i - 3000):i + 2200]
        self.assertIn('data-ids="${esc(JSON.stringify(ids))}"', b,
                      "a row carries its whole group's ids")
        self.assertNotIn("data-sid", b, "no per-colour control survives")
        self.assertIn("A PALETTE ATTACHES WHOLE", b)

    def test_it_reuses_the_canonical_ramp(self):
        """The shelf's own component, not a second drawing of a palette:
        luminance order, hero band at flex:2, pair split top/bottom."""
        i = JS.index('data-f="swatch-menu"')
        b = JS[max(0, i - 3000):i + 2200]
        self.assertIn("rampOrder(row.swatches).map(band)", b)
        self.assertIn('class="sw-ramp pal-ramp"', b)

    def test_selecting_a_row_attaches_every_id_in_its_group(self):
        i = JS.index("const checkedSwatches =")
        self.assertIn("JSON.parse(x.dataset.ids)", JS[i:i + 260])

    def test_the_summary_names_the_palette_it_chose(self):
        """The palette is the object; a colour count is its inside, not
        its identity."""
        i = JS.index("const summary = () =>")
        b = JS[i:i + 900]
        self.assertIn("pal-sum-ramp", b)
        self.assertIn("PALETTES", b)
        self.assertIn("AUTO ·", b)


class TheAspectRegression(unittest.TestCase):
    """The live defect the sequence surfaced (§2.4). P01 is a hero panel
    whose last take rendered 3136 × 1344 (21:9) while the Aspect select
    read 16:9 — three facts in three places, so nothing contradicted
    anything and a wasted render was one click away."""

    def test_the_select_opens_on_the_panels_established_shape(self):
        self.assertIn("const panelAspect = panelCands[0]?.aspect_ratio", JS)
        self.assertIn("a.id === panelAspect ? \"selected\" : \"\"", JS)
        self.assertNotIn('a.id === "16:9" ? "selected"', JS,
                         "the hardcoded default is the bug")

    def test_the_panel_shape_outranks_the_install_wide_memory(self):
        i = JS.index('const remembered = k === "aspect"')
        self.assertIn("panelCands.length ? null : gen[k]", JS[i:i + 160])

    def test_a_mismatch_is_stated_where_it_can_still_be_prevented(self):
        i = JS.index("ASPECT DOES NOT MATCH THE PANEL")
        b = JS[max(0, i - 600):i + 400]
        self.assertIn("aspectWarn", b)
        self.assertIn("THE LAST TAKE RENDERED", b)
        self.assertIn("color: var(--bad)", block(".gen-warn"))


class TheVocabularyStaysInsideItsSurface(unittest.TestCase):
    """User-caught 2026-08-16: "the formatting of the Script Scene Scan
    section of production-design has been messed up". The wizard has owned
    `.panel.step` since long before this vocabulary — a numbered PANEL with
    its number in a ::before gutter. An unscoped `.step { display: flex }`
    turned every wizard panel into a flex row and scattered its contents
    into columns. A shared class name is not a shared component."""

    def test_the_step_row_is_scoped_to_the_sequence_container(self):
        self.assertIn(".steps .step { display: flex", CSS)
        self.assertNotIn(chr(10) + ".step { display: flex", CSS,
                         "unscoped, it captures the wizard's panels")

    def test_the_band_is_scoped_with_it(self):
        self.assertIn(".steps .step-band {", CSS)
        self.assertNotIn(chr(10) + ".step-band {", CSS)

    def test_the_wizard_keeps_its_own_numbered_panel(self):
        self.assertIn(".panel.step { position: relative; padding-left: 46px; }",
                      CSS)
        self.assertIn(".panel.step::before", CSS)

    def test_both_sequence_surfaces_supply_that_container(self):
        """The scope only holds if every seqStep() lands inside it."""
        self.assertGreaterEqual(JS.count('<div class="steps">'), 2)


class GreenMeansApproved(unittest.TestCase):
    """User-caught 2026-08-16: "selecting the new take made it green border
    without it being approved. Green should be for approved."

    Two orthogonal facts were sharing one encoding — status and selection
    — so a take you had merely clicked read as canon. Status owns COLOUR;
    selection owns an ink OUTLINE, drawn outside the frame so it composes
    with any status instead of replacing it."""

    def test_selection_is_never_the_approval_colour(self):
        for sel in (".take.shown", ".take.shown .take-frame"):
            b = block(sel)
            self.assertNotIn("--ok", b, f"{sel} still borrows approval green")
            self.assertIn("outline", b)
            self.assertIn("var(--ink)", b)

    def test_approval_keeps_it(self):
        self.assertIn("var(--ok)", block(".take.approved"))
        self.assertIn("var(--ok)", block(".take.approved .take-frame"))

    def test_the_two_can_be_true_at_once(self):
        """An approved take you are looking at must read as BOTH — which
        is exactly what a shared encoding made impossible."""
        self.assertNotIn(".take.shown.approved", CSS,
                         "no special case is needed once they differ")

    def test_the_caption_states_the_durable_fact(self):
        """SHOWN first won the caption outright, so an approved take you
        were looking at lost its APPROVED word altogether."""
        i = JS.index("const word = ")
        seg = JS[i:i + 320]
        self.assertIn('c.status === "APPROVED" ? "APPROVED"', seg)
        self.assertLess(seg.index("APPROVED"), seg.index("SHOWN"))

    def test_the_caption_colour_follows_the_same_split(self):
        self.assertIn(".take.shown .take-cap { color: var(--ink); }", CSS)
        self.assertIn(".take.approved .take-cap { color: var(--ok); }", CSS)
        self.assertIn(".filmstrip .take.shown .take-cap { color: var(--ink); }", CSS)


class SettledIsNotConfirmed(unittest.TestCase):
    """RULE_PASS_2026-08-16 A8. `✓ CONFIRMED` is the user's word and offers
    Unconfirm; a frozen step is the WORK's word. Rendering both the same
    claims an action the user did not take, and the head's count is what
    makes it matter."""

    def test_a_frozen_step_reads_settled(self):
        i = JS.index("function seqStep({")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        self.assertIn("✓ SETTLED", seg)
        j = seg.index("frozen && id")
        self.assertNotIn("✓ CONFIRMED", seg[j:seg.index("</span>", j)])

    def test_the_users_own_tick_still_says_confirmed_and_offers_the_way_back(self):
        i = JS.index("function seqStep({")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        j = seg.index("done && id && !frozen")
        self.assertIn("✓ CONFIRMED", seg[j:j + 400])
        self.assertIn("data-unconfirm", seg[j:j + 400])

    def test_settled_carries_no_verb(self):
        i = JS.index("function seqStep({")
        seg = JS[i:JS.index(chr(10) + "}" + chr(10), i)]
        j = seg.index("frozen && id")
        self.assertIn("<span", seg[j:j + 200], "a span, never a button")

    def test_the_head_does_not_report_an_act_nobody_took(self):
        self.assertIn('approvedTakes.length ? "SETTLED" : "CONFIRMED"', JS)
        self.assertIn('boardFrozen ? "SETTLED" : "CONFIRMED"', JS)

    def test_settled_offers_its_explanation(self):
        self.assertIn("cursor: help", block(".step-settled"))


if __name__ == "__main__":
    unittest.main()
