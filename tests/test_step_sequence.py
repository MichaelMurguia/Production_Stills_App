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

    def test_the_filmstrip_sits_beneath_at_the_same_ratio(self):
        self.assertIn('class="take-frame" style="aspect-ratio:${aspectCss}"', JS)
        self.assertIn("object-fit: contain", block(".take-frame img"))

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
        self.assertIn("NATIVE, NEVER UPSCALED", JS)
        self.assertIn("shot-tag-size", JS)


class TheVocabulary(unittest.TestCase):
    def test_three_type_sizes_and_the_largest_anchors_them(self):
        """§1.2 — 24 / 15 / 11.5. The measured fault was nine sizes inside
        five and a half pixels, which reads as one size with noise."""
        self.assertIn("font-size: 24px", block(".wb-card .wb-subject"))
        self.assertIn("font-size: 15px", block(".step-prose, .wb-card .cam-sum"))
        for sel in (".step-label", ".step-meta", ".wb-facts"):
            self.assertIn("font-size: 11.5px", block(sel))

    def test_the_subject_beats_the_panel_h2_label(self):
        """.panel h2 sets 11px uppercase Courier; without the extra
        specificity the 24px anchor silently lost and the whole scale
        collapsed to a continuum again."""
        self.assertIn(".wb-card .wb-subject", CSS)
        b = block(".wb-card .wb-subject")
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
        b = block(".wb-card .verb, .wb-card .text-act")
        for decl in ("color: var(--ink)", "text-decoration: underline",
                     "text-decoration-color: var(--ink-dim)",
                     "text-underline-offset: 3px", "white-space: nowrap",
                     "font-family: var(--sans)"):
            self.assertIn(decl, b)

    def test_every_verb_aligns_to_one_right_edge(self):
        self.assertIn("margin-left: auto", block(".step-acts"))

    def test_the_step_number_is_the_spine(self):
        """§1.6 — a label gutter says what KIND of row this is; a number
        says where you are in the work."""
        b = block(".step-num")
        self.assertIn("flex: 0 0 46px", b)
        self.assertIn("font-size: 11.5px", b)
        self.assertIn("color: var(--ok)", block(".step-done .step-num"))

    def test_hairline_and_band_share_extents(self):
        """§1.5 — a rule that stops short of a visible band reads as a bug."""
        b = block(".step")
        self.assertIn("border-top: 1px solid var(--hairline)", b)
        self.assertIn("padding: 18px 22px", b)
        self.assertNotIn("margin", block(".step-band"))

    def test_prose_measures_are_capped(self):
        """§1.9 — extra width goes to rails and grid columns, never to
        line length."""
        self.assertIn("max-width: 720px", block(".step-prose, .wb-card .cam-sum"))
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

    def test_the_marker_is_a_pair_never_a_bare_dot(self):
        """A bare dot reads as absence rather than as the off state of a
        pair, and #4a4d52 is disabled ink that must carry no readable text."""
        self.assertIn('content: "\\25CB"', block('.ref-row input[type="checkbox"]::before'))
        on = block('.ref-row input[type="checkbox"]:checked::before')
        self.assertIn('content: "\\2713"', on)
        self.assertIn("color: var(--ok)", on)

    def test_the_always_on_anchors_never_sit_among_the_toggles(self):
        i = JS.index('<span class="anchors-k">STYLE ANCHORS</span>')
        self.assertIn("ALWAYS ON", JS[i:i + 900])
        self.assertIn("SET ON PRODUCTION DESIGN", JS[i:i + 900])
        j = JS.index('class="ref-groups"')
        self.assertLess(j, i, "the toggles are their own list, above")

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


if __name__ == "__main__":
    unittest.main()
