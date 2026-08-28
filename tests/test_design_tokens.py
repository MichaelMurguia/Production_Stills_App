"""Mechanical token assertions (design-verify step 4, standing suite).

Every canonized or snippet-delivered component asserts the declarations
its mock/snippet states. CI runs this on every push — drift that slips
past eyes fails the build. When you change a component, change its
assertions IN THE SAME COMMIT; a red here means either your CSS or this
contract is wrong, and the design system decides which."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def block(sel: str) -> str:
    """Union of every rule body for this exact selector — grouped rules
    and reduced-motion overrides also declare it, so a single first-match
    would assert against the wrong body."""
    bodies = re.findall(re.escape(sel) + r"\s*{([^}]*)}", CSS)
    assert bodies, f"missing rule: {sel}"
    return "\n".join(bodies)


class TokenContractTests(unittest.TestCase):
    def assert_decls(self, sel, decls):
        b = block(sel)
        for d in decls:
            self.assertIn(d, b, f"{sel}: missing '{d}'")

    # -- the voice rule ----------------------------------------------------

    def test_mono_utility_exists(self):
        """Audit #1 (2026-08-04): .mono was used ~45 times but never
        defined — the app's Courier voice silently broke. Never again."""
        self.assert_decls(".mono", ["font-family: var(--mono)"])

    # -- first-run Settings (mock 18a + MOCK_PARITY D1-D8) -----------------

    def test_firstrun_containment(self):
        self.assert_decls("#settings-firstrun", [
            "background: var(--bg)", "border: 1px solid var(--line)",
            "padding: 30px"])

    def test_subnav_active_marker(self):
        self.assert_decls(".subnav button.active", [
            "border-bottom-color: var(--accent)", "background: var(--bg)"])

    # -- provider marquee (delivered snippet, 2026-08-04) ------------------

    def test_marquee_channel(self):
        self.assert_decls(".fr-marquee", [
            "max-width: 560px", "border: 1px solid var(--line-soft)",
            "background: var(--field)", "padding: 8px 0",
            "mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent)"])

    def test_marquee_track_loops_seamlessly(self):
        self.assert_decls(".mq-track", [
            "gap: 8px", "width: max-content",
            "animation: mq-scroll 36s linear infinite"])
        self.assertIn("translateX(-50%)", CSS)

    def test_marquee_tile(self):
        self.assert_decls(".mq-tile", [
            "flex: none", "border: 1px solid var(--line-soft)",
            "background: var(--bg2)", "padding: 6px 12px 6px 6px",
            "font-size: 11.5px", "color: var(--ink-dim)",
            "white-space: nowrap"])
        self.assert_decls(".mq-tile img", ["width: 22px", "height: 22px"])

    # -- AI-models notice (delivered snippet, 2026-08-04) ------------------

    def test_notice_column(self):
        self.assert_decls(".fr-notice", [
            "border-left: 1px solid var(--line-soft)", "padding-left: 34px",
            "gap: 26px", "user-select: none", "caret-color: transparent"])
        self.assert_decls(".fr-notice h3", [
            "font-size: 18px", "font-weight: 600", "color: var(--ink)"])
        self.assert_decls(".fr-notice p", [
            "font-size: 13.5px", "line-height: 1.7", "color: var(--ink-dim)"])
        self.assert_decls(".fr-notice p strong", [
            "color: var(--ink)", "font-weight: 600"])

    def test_notice_typewriter_grammar(self):
        self.assert_decls(".fr-cursor", [
            "width: 9px", "height: 17px", "background: var(--accent)",
            "animation: cursor-blink 1.15s steps(1) infinite"])
        self.assert_decls(".fr-rule", [
            "width: 34px", "height: 2px", "background: var(--accent)",
            "animation: rule-sweep 2.4s ease-out"])
        # A fading caret reads as a glitch: steps(1), opacity snaps.
        self.assertIn("@keyframes cursor-blink { 0%, 55% { opacity: 1; } 56%, 100% { opacity: 0; } }",
                      CSS)

    def test_reduced_motion_covers_the_animations(self):
        m = re.search(r"@media \(prefers-reduced-motion: reduce\).*?}", CSS, re.DOTALL)
        self.assertIsNotNone(m)
        self.assertIn(".mq-track { animation: none; }", CSS)
        self.assertIn(".fr-cursor { animation: none; }", CSS)

    # -- panel card (PANEL_CARD_PLAN) --------------------------------------

    def test_required_table_and_marks(self):
        self.assert_decls(".req-table", ["grid-template-columns: 1fr 1fr"])
        self.assert_decls(".req-mark.ok", ["color: var(--ok)"])
        self.assert_decls(".req-mark.hold", ["color: var(--hold)"])

    def test_stated_zero_state(self):
        self.assert_decls(".nomatch", ["border: 1px solid var(--bad)"])

    # -- the amber budget's known former leaks stay plugged ----------------

    def test_former_amber_leaks_stay_fixed(self):
        self.assert_decls(".shot-status.CANDIDATE", ["color: var(--hold)"])
        self.assert_decls(".loc-open.held", ["color: var(--hold)"])
        self.assert_decls(".pm-chip.open", ["color: var(--ok)"])
        self.assertNotIn(".toast { border-left: 3px solid var(--accent)", CSS.replace("\n", " "))

    def test_canonization_pass_rulings_hold(self):
        """R1/R2/R3/R16: two ambers only, tokenized alphas, no --warn,
        the debug tail styled."""
        self.assertNotIn("--warn:", CSS)
        self.assertNotIn("var(--warn)", CSS)
        self.assertNotIn("rgba(224, 163, 63, .06)", CSS)
        self.assertNotIn("rgba(224, 163, 63, .14)", CSS)
        self.assert_decls("option.opt-debug",
                          ["color: var(--ink-faint)", "font-family: var(--mono)"])
        self.assert_decls(".bf-slot", ["border: 1px solid var(--line)"])

    def test_two_mode_band(self):
        """BAND_CONDENSE snippet: condensed geometry, receded surfaces,
        survived progress borders, reduced-motion snap."""
        self.assert_decls("body.tool-mode nav#nav button", [
            "padding: 7px 18px 8px", "background: var(--bg)",
            "transition: padding 150ms ease-out, background 150ms ease-out"])
        self.assert_decls("body.tool-mode nav#nav .stage-l",
                          ["color: var(--ink-faint)", "font-weight: 600"])
        self.assertIn("body.tool-mode nav#nav .stage-sub,\nbody.tool-mode nav#nav .here-chip { display: none; }",
                      CSS)
        self.assert_decls("body.tool-mode nav#nav button:hover",
                          ["background: var(--panel)"])

    # -- settings control panel (SETTINGS_CONTROL_PANEL_PLAN, 2026-08-05) --

    def test_control_panel_economy(self):
        """P1: two Courier footnotes, a one-line MODELS summary, a live
        --ok square inside a role selector. The stat tiles and the role
        prose are deleted — a red on the NotIns means furniture crept
        back."""
        self.assert_decls(".sec-foot", [
            "font-family: var(--mono)", "color: var(--ink-faint)"])
        self.assert_decls(".models-line", [
            "border-top: 1px solid var(--line)", "font-family: var(--mono)"])
        self.assert_decls(".models-facts .m-bad", ["color: var(--bad)"])
        self.assert_decls(".role-sel.live::before", ["background: var(--ok)"])
        for gone in (".reach-tile", ".rec-chip", ".bill-warn", ".role-jobs",
                     ".cred-tag", ".cred-ident", ".cred-foot"):
            self.assertNotIn(gone, CSS)

    def test_brand_icon_tile_grammar(self):
        """P3: a third-party mark rides a transparent icon on a --field
        tile with a --line border; inline icons are 22px."""
        self.assert_decls(".cred-tile", [
            "background: var(--field)", "border: 1px solid var(--line)"])
        self.assert_decls(".prov-ico", ["width: 22px", "height: 22px"])

    def test_four_anchor_row(self):
        """User-directed 2026-08-05: the four style-anchor roles share
        one 4-track grid, THE MOVIE label spans its three columns, and
        the old boards group (whose lone card collapsed to a third of a
        third of the page) is gone."""
        self.assert_decls(".wiz-cols-anchors",
                          ["grid-template-columns: repeat(4, minmax(0,1fr))"])
        self.assert_decls(".wiz-span3", ["grid-column: span 3"])
        self.assertNotIn(".wiz-cols-board", CSS)

    def test_two_doors_one_section(self):
        """B1: amber marks only the recommended door; the alternative is
        a plain --line card."""
        self.assert_decls(".intake .intake-doors", [
            "grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr)"])
        self.assert_decls(".door", ["border: 1px solid var(--line)"])
        self.assert_decls(".door-auto", [
            "border-color: var(--accent-line)",
            "border-top: 2px solid var(--accent)"])
        self.assertNotIn("var(--accent)", block(".door-blank")
                         if ".door-blank {" in CSS else "",
                         "the blank door carries no amber")

    def test_the_help_affordance_is_discoverable(self):
        """B3: a tooltip nobody knows exists is not documentation."""
        self.assert_decls(".q-help", ["border: 1px solid var(--line)",
                                      "font-family: var(--mono)"])
        self.assert_decls(".q-card", ["background: var(--panel)",
                                      "border: 1px solid var(--line)"])

    def test_the_sheets_table_is_labelled(self):
        self.assert_decls(".spec-table thead th", [
            "background: var(--field)", "font-family: var(--mono)"])

    def test_take_bar_is_one_verdict_and_two_lists(self):
        """17a, superseding T2's one-grammar row and 14a's peer cluster:
        the code is not the authority on hierarchy — the decision is. One
        filled-amber verdict; USE and DERIVE as Courier-kickered lists of
        text acts; Reject --bad on hover only; wrap stays the last resort
        behind the DERIVE fold."""
        b = block(".act-bar")
        self.assertIn("flex-wrap: wrap", b)
        self.assertNotIn("overflow-x: auto", b)
        self.assertNotIn(".act-bar .ghost", CSS,
                         "the ghost-peer grammar is superseded")
        self.assertNotIn("border: 1px solid var(--ok)", CSS.split(".act-bar")[1]
                         if ".act-bar" in CSS else CSS,
                         "Approve is the amber verdict, not a green peer")
        self.assert_decls(".act-kicker", [
            "font-family: var(--mono)", "color: var(--ink-faint)"])
        self.assert_decls(".act-dim", ["color: var(--ink-dim)"])
        self.assert_decls(".act-reject:hover", ["color: var(--bad)"])
        self.assert_decls(".act-use, .act-derive, .act-right",
                          ["border-left: 1px solid var(--line)"])
        self.assert_decls(".act-spacer", ["flex: 1"])
        for sel in (".act-bar", ".act-zone", ".act-kicker", ".act-derive-menu"):
            self.assertNotIn("border-radius", block(sel), sel)
        # the fold renders ⋯ only when collapsed
        self.assert_decls(".act-more", ["display: none"])
        self.assert_decls(".derive-collapsed .act-more", ["display: inline"])

    def test_take_tags_ride_the_image(self):
        self.assert_decls(".stage-shot", ["position: relative"])
        self.assert_decls(".shot-tag", [
            "position: absolute", "background: rgba(11, 12, 14, .82)",
            "border: 1px solid var(--line)", "font-family: var(--mono)"])
        self.assert_decls(".shot-tag-state", ["top: 10px", "left: 10px"])
        # Corrected mock 14a: identity rides the TOP right, opposite state.
        self.assert_decls(".shot-tag-id", ["right: 10px", "top: 10px"])

    def test_hidden_always_wins(self):
        """A hiding utility that a component can out-order is not a
        utility. .wv-tag beat .hidden on source order and the Bible's
        save gate rendered on a saved Bible — the class was applied and
        the element still showed."""
        self.assertIn(".hidden { display: none !important; }", CSS)

    def test_swatch_act_sits_under_the_bible(self):
        """SWATCH_GENERATE_RULING: the act moved to step 5 as a bordered
        ghost row — it must not read as a column control any more, and
        it renders only when it has something to sit under (:not(:empty))."""
        self.assert_decls(".swatch-gen:not(:empty)", [
            "border: 1px solid var(--line)", "background: var(--bg2)",
            "display: flex"])
        self.assertNotIn("swatch-gen {", CSS,
                         "the old column-strip rule must be gone")

    def test_swatch_widget_tokens(self):
        """NON-CANON swatch widget (user-directed 2026-08-05): proposal
        chrome is Courier on tokens; the PROVISIONAL strip header is
        --hold (a proposal is a hold, not an error)."""
        self.assert_decls(".swatch-add", ["border: 1px dashed var(--line)"])
        self.assert_decls(".prop-head", [
            "color: var(--hold)", "border: 1px solid var(--hold)",
            "font-family: var(--mono)"])
        self.assert_decls(".sv-acts .ok-act", ["color: var(--ok)"])

    # -- production design v3 (PRODUCTION_DESIGN_V3_PLAN, 2026-08-06) ------

    def test_pd_v3_rail_and_headings(self):
        """D2: current chip bordered accent-line on --panel2, done numbers
        --ok; D1: Courier step headings and faint condition lines."""
        self.assert_decls(".rail-chip.current", [
            "border: 1px solid var(--accent-line)", "background: var(--panel2)"])
        self.assert_decls(".rail-chip.done .rail-num", ["color: var(--ok)"])
        self.assert_decls(".wiz-v3 h2", ["font-family: var(--mono)"])
        self.assert_decls(".step-cond", ["color: var(--ink-faint)"])

    def test_pd_v3_read_strip(self):
        """D3, amended by SCAN_CONSOLIDATION §1: five tiles, the only
        colored number is open questions, the logline rides an accent rule
        — and it now sits ABOVE the counts it explains, full width."""
        self.assert_decls(".read-tiles", ["grid-template-columns: repeat(5, 1fr)"])
        self.assert_decls(".read-num.attn", ["color: var(--accent)"])
        self.assert_decls(".read-logline", ["border-left: 2px solid var(--accent)"])
        self.assertNotIn(".reveal-strip", CSS)
        self.assert_decls(".read-strip", ["flex-direction: column"])
        self.assertNotIn("width: 360px", block(".read-logline"),
                         "the logline is not a sixth statistic in a column")

    def test_scan_tiles_are_baseline_rows(self):
        """§1 — a count is one line, not a stacked card: ~40px, a third off."""
        b = block(".read-tile")
        self.assert_decls(".read-tile", ["padding: 8px 14px", "align-items: baseline"])
        self.assertIn("display: flex", b)
        self.assert_decls(".read-num", ["font-size: 16px"])
        self.assertNotIn("display: block", block(".read-num"),
                         "number and label share a line now")

    def test_the_expand_row_exists_and_is_square(self):
        """§3 — the row that states a list's tail."""
        b = block(".loc-more")
        self.assertIn("display: flex", b)
        self.assertNotIn("border-radius", b)

    def test_the_environment_room_is_two_columns(self):
        """§2 — prose on the left, what inherits it on the right, and the
        blast radius pinned to the bottom of that column."""
        self.assert_decls(".envm-body", ["grid-template-columns: 1fr 300px"])
        self.assert_decls(".envm-prose", ["min-height: 150px"])
        self.assert_decls(".envm-ramp", ["height: 22px"])
        self.assert_decls(".envm-blast", ["margin-top: auto"])

    def test_pd_v3_labelled_table(self):
        """D4: one fixed track set for header row and rows; group headers
        on --field; the inner scroll cage is gone."""
        self.assert_decls(".wiz-loc-row, .loc-thead",
                          ["grid-template-columns: minmax(0,1fr) 240px 120px 190px"])
        self.assert_decls(".wiz-v3 .loc-group", ["background: var(--field)"])
        self.assert_decls(".wiz-v3 .loc-scroll", ["max-height: none"])

    def test_pd_v3_questions_grid(self):
        self.assert_decls(".q-grid", ["grid-template-columns: 1fr 1fr"])
        self.assert_decls(".q-grid .q-row.answered",
                          ["border-left: 2px solid var(--ok)"])

    def test_no_undocumented_hex_in_hover(self):
        # #f0bc63 exists exactly once: as the --accent-hover token itself.
        self.assertEqual(CSS.count("#f0bc63"), 1)
        self.assertIn("--accent-hover: #f0bc63", CSS)

    # -- backup / import in-flight strip (user-directed, 2026-08-06) -------

    def test_card_busy_strip_is_absent_when_idle(self):
        """The productions card hosts the canon .busy vocabulary while a
        backup packs or an import replaces. An empty host must not open a
        hole in the card's 12px column gap, and the strip supplies its own
        spacing — so the host collapses and .busy loses its top margin."""
        self.assert_decls(".prod-card [data-busy]:empty", ["display: none"])
        self.assert_decls(".prod-card .busy", ["margin-top: 0"])

    def test_the_busy_strip_it_reuses_is_unchanged(self):
        """Reuse, not reinvention: no second progress vocabulary may
        appear beside the canon one."""
        self.assert_decls(".busy", [
            "border-left: 3px solid var(--accent)", "background: var(--panel2)"])
        self.assertEqual(CSS.count("@keyframes busy-sweep"), 1)

    # -- swatch hero / recolour / generation wait (user-directed 2026-08-06) --

    def test_hero_chip_is_amber(self):
        """PALETTE_GROUPS_PLAN reversed the earlier reading: the hero IS
        the amber on a palette row. It is the one thing being asked for —
        a group with no hero says OPEN in amber, and the chosen band wears
        the amber outline in the viewer."""
        self.assert_decls(".sw-hero", [
            "font-family: var(--mono)", "color: var(--accent)",
            "border: 1px solid var(--accent-line)"])
        self.assert_decls(".sw-ramp-label .hero.open", ["color: var(--accent)"])
        self.assert_decls(".sv-ramp i.is-hero", ["outline: 2px solid var(--accent)"])

    def test_the_ramp_is_one_object(self):
        """A set that means something as a set renders as one object: the
        bands touch. No gap, no radius, no per-band margin, and an OUTLINE
        so nothing insets a band from the ramp's edge."""
        b = block(".sw-ramp")
        self.assertIn("display: flex", b)
        self.assertNotIn("gap", b)
        self.assertNotIn("border-radius", b)
        self.assertIn("outline: 1px solid var(--line)", b)
        self.assertNotIn("margin", block(".sw-ramp i"))
        self.assert_decls(".sw-ramp.is-open", ["outline-color: var(--accent)"])

    def test_the_card_grid_is_gone(self):
        """The ramp replaced it — leaving the rules behind would let the
        old 2-up grid come back on the next edit."""
        for dead in (".sw-card", ".sw-grid", ".sw-edit", ".lang-label"):
            self.assertNotIn(dead + " ", CSS, f"{dead} should have gone with the cards")

    def test_the_generation_wait_takes_its_own_row(self):
        """.swatch-gen wraps; the strip must break to a full row rather
        than squeeze the button, and vanish when idle."""
        self.assert_decls('.swatch-gen [data-f="sw-busy"]', ["flex-basis: 100%"])
        self.assert_decls('.swatch-gen [data-f="sw-busy"]:empty', ["display: none"])
        self.assert_decls(".swatch-gen .busy", ["margin-top: 0"])


    def test_colour_field_pairs_a_hex_with_a_picker(self):
        """Two views of one value. The hex half is Courier (machine data),
        and the native picker is stripped of OS chrome so it reads as part
        of the form — it stretches rather than guessing a height."""
        self.assert_decls(".mf-color", ["display: flex", "align-items: stretch"])
        self.assert_decls(".mf-color input[type=text]", ["font-family: var(--mono)"])
        self.assert_decls(".mf-color input[type=color]", [
            "appearance: none", "background: var(--field)",
            "border: 1px solid var(--line)"])
        self.assertIn(".mf-color input[type=color]::-webkit-color-swatch", CSS)
        self.assertIn(".mf-color input[type=color]:focus-visible", CSS,
                      "a picker reachable by keyboard must show focus")

    def test_an_unset_colour_is_hatched_not_black(self):
        """A picker defaulted to #000000 states black. The app's hatch is
        how it says "nothing here" everywhere else — fine gauge, since the
        swatch is under 60px."""
        b = block(".mf-color.is-unset input[type=color]::-webkit-color-swatch")
        self.assertIn("repeating-linear-gradient", b)
        self.assertIn("5px", b, "fine gauge for a surface under 60px")


    def test_review_all_gives_the_ramp_back_some_height(self):
        """Multi-language read: the ramp is context, the rows are the work."""
        self.assert_decls(".sv-many .sv-ramp", ["height: 56px"])
        self.assert_decls(".sv-body", ["overflow-y: auto"])
        self.assert_decls(".sv-many .sv-rows", ["overflow: visible"])

    def test_the_unopened_note_is_quiet_courier(self):
        """A stated condition, not an alarm — it is not amber and not --bad."""
        b = block(".sw-bar-note")
        self.assertIn("var(--ink-faint)", b)
        self.assertNotIn("--accent", b)
        self.assertNotIn("--bad", b)

    # -- the sheet grammar (SHEET_SYSTEM_PLAN §4/§11, 2026-08-10) ----------

    def test_sheet_ink_lives_only_under_sheet_data_style(self):
        """Sheet ink is the artifact's surface, not an app token: --sheet-*
        may be DECLARED only inside .sheet[data-style=…] rules, and never
        in :root. The paper hexes may appear nowhere else in the file."""
        root = block(":root")
        self.assertNotIn("--sheet-", root)
        for hx in ("#efe9dd", "#d9d4c8", "#1c4f7c", "#fbfbf9"):
            for m in re.finditer(re.escape(hx), CSS):
                start = CSS.rfind("{", 0, m.start())
                sel = CSS[CSS.rfind("}", 0, start) + 1:start].strip()
                self.assertIn('.sheet[data-style="', sel,
                              f"{hx} escaped the .sheet[data-style] namespace: {sel}")
        for m in re.finditer(r"--sheet-[a-z]+\s*:", CSS):
            start = CSS.rfind("{", 0, m.start())
            sel = CSS[CSS.rfind("}", 0, start) + 1:start].strip()
            self.assertIn(".sheet", sel,
                          f"--sheet-* declared outside .sheet: {sel}")

    def test_composer_room_tracks(self):
        self.assert_decls(".lb-room", [
            "grid-template-columns: 186px minmax(0, 1fr) 300px"])

    def test_composer_selection_is_an_outline_not_a_colour(self):
        """RULE_PASS_2 A5 (2026-08-18) reversed this: status owns colour,
        selection owns an outline. Amber marks the current stage, the one
        primary action and focus — a selected block is none of the three,
        and the arrange room had SIX ambers on one screen."""
        self.assert_decls(".ov-block.sel", ["border-color: var(--ink)"])
        self.assertNotIn("--accent", block(".ov-block.sel"))
        self.assert_decls(".ov-block", ["border: 1px solid transparent"])

    def test_composer_amber_stops_at_two(self):
        """Canon pass R1 (2026-08-10): the exemption was refused — the
        block chip is a label (tags-ride-the-image), AUTHORED is a plain
        Courier fact, and the stale acts are equal ghosts. Selection and
        the Export act are the composer's only ambers."""
        self.assert_decls(".ov-chip", ["background: rgba(11, 12, 14, .82)",
                                       "border: 1px solid var(--line)",
                                       "color: var(--ink)"])
        self.assertNotIn("--accent", block(".ov-chip"))
        b = block(".lb-chip.authored")
        self.assertNotIn("--accent", b)
        self.assertIn("border: 0", b)

    def test_no_second_bar_exists(self):
        """Canon pass R6: the coverage meter is the only meter — the
        storage bar is deleted and the Courier line carries the state."""
        self.assertNotIn(".stor-bar", CSS)
        self.assert_decls(".stor-line.bad", ["color: var(--bad)"])
        self.assert_decls(".stor-line.hold", ["color: var(--hold)"])

    def test_unanchored_register_is_a_labelled_table(self):
        """Canon pass R4: grid tracks per the ruling; header on --field."""
        self.assert_decls(".loc-reg-row", [
            "grid-template-columns: minmax(0, 1fr) 130px 210px 170px"])
        self.assert_decls(".loc-reg-cols", ["background: var(--field)"])

    def test_stale_binding_reads_bad_and_bound_reads_ok(self):
        self.assert_decls(".lb-chip.bad", ["border-color: var(--bad)"])
        self.assert_decls(".lb-chip.ok", ["border-color: var(--ok)"])

    def test_tray_and_rail_are_contained_panels(self):
        for sel in (".sheet-tray", ".sheet-rail"):
            self.assert_decls(sel, ["background: var(--panel)",
                                    "border: 1px solid var(--line)"])

    def test_no_radius_in_the_composer(self):
        """Square everywhere — the composer adds no rounding."""
        i = CSS.index("Lookbook shelf & sheet composer")
        self.assertNotIn("border-radius", CSS[i:])

    def test_style_picker_selection_is_ink_not_amber(self):
        """Board looks (2026-08-13, uncanonized): a chosen style is
        STATE — the card keylines in ink; amber stays with the primary
        action. Cards sit on the field like every other well."""
        self.assert_decls(".arr-style-card", [
            "background: var(--field)",
            "border: 1px solid var(--line-soft)"])
        self.assert_decls(".arr-style-card.on", [
            "border-color: var(--ink)"])
        self.assertNotIn("--accent", block(".arr-style-card.on"))
        self.assert_decls(".arr-style-img", ["background: var(--bg2)"])

    # -- tutorials (UNCANONIZED 2026-08-17) --------------------------------

    def test_tutorial_layer_sits_between_the_dialog_and_the_lightbox(self):
        """A step can point at something inside an app dialog (400), so the
        tour must outrank it; the cropper (480) and lightbox (500) are
        full-surface tools a tour has no business drawing over."""
        z = int(re.search(r"z-index:\s*(\d+)", block(".tut-layer")).group(1))
        self.assertGreater(z, 400)
        self.assertLess(z, 480)

    def test_the_tour_is_made_of_board_stock(self):
        """TUTORIAL_MATERIAL (ruled 2026-08-19). Removing the amber ring
        fixed a COLOUR collision and left a MATERIAL one — a --panel2 card
        beside a spotlit app card that is also a dark panel with a
        hairline. Dimming cannot fix that: it makes the app quieter, not
        the tour different. The tour stops being a panel."""
        self.assert_decls(".tut-pop", [
            "background: var(--sheet-paper)", "color: var(--sheet-ink)",
            "border: 4px solid var(--sheet-mat)"])
        self.assert_decls(".tut-mask", ["pointer-events: auto"])

    def test_it_reads_the_same_declaration_as_the_artifact(self):
        """So the tour's material cannot drift from the board stock it is
        made of — and the one sanctioned exception to `artifact ink, never
        chrome` is visible in the CSS rather than remembered."""
        self.assertIn('.sheet[data-style="ART_BOARD"], .tut-pop {', CSS)

    def test_over_a_dimmed_app_elevation_is_not_a_shadow(self):
        """Near-black on near-black is about one value step in 255."""
        self.assertNotIn("box-shadow", block(".tut-pop.tut-docked"))

    def test_the_tour_target_is_matted_not_lit(self):
        """Q1 (TUTORIAL_RULING, ruled 2026-08-18): the ring is REFUSED. A
        tour target is none of amber's three jobs — it is a thing POINTING
        at one. A passe-partout, not a highlight."""
        self.assertNotIn(".tut-ring", CSS)
        self.assert_decls(".tut-mount", [
            "border: 8px solid var(--field)",
            "outline: 1px solid var(--ink-faint)",
            "box-sizing: border-box"])
        # the mat is the BAND — a fill would put a lid on the hole
        self.assertIn("background: transparent", block(".tut-mount"))

    def test_hatch_has_exactly_one_job_on_the_tour_layer(self):
        """S10: the blocked target is the only state where the user is
        shown something they cannot touch, and the app already has the
        word for that."""
        self.assertIn("repeating-linear-gradient", block(".tut-mount.is-blocked"))

    def test_the_tour_layer_touches_no_chrome_amber_at_all(self):
        """TUTORIAL_MATERIAL: chrome amber has no place on parchment, so
        the rule now holds BY CONSTRUCTION rather than as a discipline the
        build has to remember. `.tut-adm-*` is the CMS — that is chrome and
        is not covered."""
        for m in re.finditer(r"(\.tut-(?!adm)[\w.\[\]=\"'-]*)\s*{([^}]*)}", CSS):
            for tok in ("--accent", "--accent-soft", "--accent-line",
                        "--accent-hover"):
                self.assertNotIn(tok, m.group(2),
                                 f"{m.group(1)} borrows chrome amber")

    def test_a_tour_spends_no_amber_except_on_its_own_foot(self):
        """§0: a tour is never the work, it points at the work. The only
        amber a tour may spend is a `.primary` on a step with no target,
        and that is decided in JS, not in a .tut-* rule."""
        for m in re.finditer(r"(\.tut-[\w.\[\]=\"-]*)\s*{([^}]*)}", CSS):
            self.assertNotIn("--accent", m.group(2),
                             f"{m.group(1)} spends amber on the tour layer")

    def test_the_dim_goes_down_not_sideways(self):
        """Q3: the old scrim was a PANEL colour over a darker ground, so it
        lightened the ground slightly and read as "slightly darker"."""
        self.assert_decls(".tut-mask", ["background: var(--ground)",
                                        "opacity: .92"])

    def test_the_held_line_is_type_and_rule_not_colour(self):
        """Emphasis on paper is weight and a rule — which is how the
        sheet's own masthead works. The sheet's accent is 3.15:1 on
        parchment: fine for a 2px rule, refused for type."""
        self.assert_decls(".tut-wait", [
            "letter-spacing: .1em", "text-transform: uppercase",
            "font-weight: 600", "color: var(--sheet-ink)",
            "border-top: 2px solid var(--sheet-accent)"])
        self.assert_decls(".tut-kicker", ["color: var(--sheet-dim-ui)"])

    def test_the_primary_act_inverts_rather_than_colouring(self):
        self.assert_decls(".tut-foot .primary", [
            "background: var(--sheet-ink)", "color: var(--sheet-paper)"])

    def test_tutorial_motion_is_reduced_motion_guarded(self):
        blocks = re.findall(
            r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", CSS, re.S)
        self.assertTrue(any(".tut-nudge" in b for b in blocks),
                        "the nudge must be silenced for reduced motion")

    def test_the_cms_step_card_sits_on_the_panel_ladder(self):
        """Transliterated from the board (turn 2a): #15181b is --bg2."""
        self.assert_decls(".tut-adm-step", [
            "background: var(--bg2)", "border: 1px solid var(--line)"])

    def test_the_cms_is_chrome_not_board_stock(self):
        """The 2026-08-19 material ruling is the TOUR layer's. The editor
        is chrome and stays on the app's own surfaces — a warm editor
        would claim to be the artifact it edits."""
        for sel in (".tut-adm-step", ".tut-adm-errors"):
            self.assertNotIn("--sheet-", block(sel))


class ArrangeRoomTests(unittest.TestCase):
    """RULE_PASS_2 Part A (ruled 2026-08-18). The room had SIX ambers on
    one screen and used the approval colour for autosave and the rejection
    colour for a frame that is merely too small. Status owns colour;
    selection owns an outline."""

    def assert_decls(self, sel, decls):
        b = block(sel)
        for d in decls:
            self.assertIn(d, b, f"{sel}: missing '{d}'")

    def test_selection_is_an_outline_not_the_accent(self):
        for sel in (".arr-tile.active", ".arr-tile.lifted", ".arr-tool.on",
                    ".arr-crop-box", ".arr-crop-box .bk", ".ov-block.sel"):
            self.assertNotIn("--accent", block(sel),
                             f"{sel} still spends the amber on selection")

    def test_a_report_has_no_amber(self):
        """.arr-chip is a readout following the pointer."""
        self.assertNotIn("--accent", block(".arr-chip"))
        self.assert_decls(".arr-chip", ["color: var(--ink)",
                                        "border: 1px solid var(--line)"])

    def test_a_short_frame_is_not_a_rejected_one(self):
        self.assertNotIn("rgba(224, 82, 66", block(".arr-tile.short::after"))
        self.assert_decls(".arr-verdict", ["color: var(--ink)"])
        self.assert_decls(".arr-bad", ["color: var(--ink)"])

    def test_a_control_at_rest_is_not_the_primary_act(self):
        self.assert_decls('.arr-ctls input[type="range"]',
                          ["accent-color: var(--ink)"])

    def test_size_tracks_consequence(self):
        """The claim arrow mutates OTHER tiles and was the smallest
        target in the room."""
        self.assert_decls(".arr-arrow", ["width: 28px", "height: 28px"])
        self.assert_decls(".arr-arrow svg", ["width: 14px", "height: 14px"])

    def test_the_corner_add_left_the_board(self):
        """It floated on the board's bottom-right, which is always some
        tile's bottom-right, four pixels off that tile's readout."""
        b = block(".arr-corner-add")
        self.assertNotIn("position: absolute", b)
        self.assertIn("height: 40px", b)


class BrandMarkTests(unittest.TestCase):
    """The wordmark links to the website (user 2026-08-18). It opens in a
    new tab on purpose: this is a work surface with renders in flight, and
    leaving the studio must never be a side effect of clicking the logo."""

    HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")

    def test_it_is_a_real_link_to_the_site(self):
        i = self.HTML.index('class="brand-title"')
        seg = self.HTML[i - 40:i + 320]
        self.assertIn("<a ", seg, "an anchor — focusable, and the browser's "
                                  "own open-in-new-tab works on it")
        self.assertIn('href="https://www.screenboardstudio.com"', seg)
        self.assertIn('target="_blank"', seg)
        self.assertIn('rel="noopener"', seg)

    def test_it_still_reads_as_the_wordmark(self):
        b = block(".brand-title")
        self.assertIn("text-decoration: none", b)
        self.assertIn("color: inherit", b)


class MiniMonoTests(unittest.TestCase):
    def test_mini_mono_is_courier(self):
        """.mini defaults to sans (short prose), but markup that ALSO says
        .mono means it — .mini used to win the order battle and silently
        rendered machine data proportional (found 2026-08-13, the
        correction-intake checklist)."""
        self.assertIn(".mini.mono { font-family: var(--mono); }", CSS)


class HarnessAuditTests(unittest.TestCase):
    """HARNESS_AUDIT_2026-08-14 — the first audit-by-use. Each contract
    pins a ruling that a source read alone failed to catch."""

    def assert_decls(self, sel, decls):
        b = block(sel)
        for d in decls:
            self.assertIn(d, b, f"{sel}: missing '{d}'")

    def test_a_record_has_no_status_colour(self):
        """U1: the carried-notes rail is history, not failure — no --bad
        anywhere in the block; ids Courier dim, the person's sentence
        Archivo ink as typed, status lines Courier faint."""
        self.assertNotIn("--bad", block(".carried"))
        self.assert_decls(".carried-id", [
            "font-family: var(--mono)", "color: var(--ink-dim)"])
        self.assert_decls(".carried-note", [
            "font-family: var(--sans)", "color: var(--ink)"])
        self.assert_decls(".carried-state", [
            "font-family: var(--mono)", "color: var(--ink-faint)"])

    def test_a_stopped_note_is_not_struck_through(self):
        self.assertNotIn("line-through", block(".carried.retired .carried-note"))

    def test_verbs_never_wrap(self):
        """U4/U5: a verb that wraps is not a verb any more."""
        self.assert_decls("button.ghost, a.ghost", ["white-space: nowrap"])
        self.assert_decls(".text-act", ["white-space: nowrap"])

    def test_camera_row_is_a_grid_that_never_orphans(self):
        """U6/R6: five peers break 3+2, never 4+1."""
        self.assert_decls(".cam-row", [
            "display: grid",
            "grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))"])
        self.assertIn("repeat(3, minmax(150px, 1fr))", CSS,
                      "the forced 3-column break below ~1000px")


class TourContrast(unittest.TestCase):
    """TUTORIAL_MATERIAL (2026-08-19): the sheet's inks are calibrated for
    PRINT — PIL draws them onto 3840×2160 artwork where a caption is
    physically large. Borrowed verbatim as 9px UI text on the same paper,
    `dim` measures 3.94:1 and the accent 3.15:1, which made the one line
    the tour says must not be missed the least legible thing on the card.
    Provenance was right; legibility was never checked. This is that
    check."""

    @staticmethod
    def _lum(h):
        h = h.lstrip("#")
        def ch(c):
            c /= 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

    @classmethod
    def ratio(cls, a, b):
        la, lb = cls._lum(a), cls._lum(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    def vars_(self):
        m = re.search(r'\.sheet\[data-style="ART_BOARD"\], \.tut-pop \{([^}]*)\}',
                      CSS, re.S)
        self.assertTrue(m, "the tour must read the artifact's own declaration")
        return dict(re.findall(r"(--sheet-[\w-]+):\s*(#[0-9a-f]{6})", m.group(1)))

    def test_every_text_colour_on_the_paper_clears_aa(self):
        v = self.vars_()
        paper = v["--sheet-paper"]
        for key in ("--sheet-ink", "--sheet-dim-ui"):
            r = self.ratio(paper, v[key])
            self.assertGreaterEqual(round(r, 2), 4.5,
                                    f"{key} is {r:.2f}:1 on the tour's paper")

    def test_the_sheet_accent_is_never_type(self):
        """It is 3.15:1 — carried in the mirror with that constraint so
        nobody reasonably reaches for it as a label."""
        v = self.vars_()
        self.assertLess(self.ratio(v["--sheet-paper"], v["--sheet-accent"]), 4.5)
        for sel in (".tut-title", ".tut-p", ".tut-wait", ".tut-kicker"):
            self.assertNotIn("color: var(--sheet-accent)", block(sel))


class NoUndocumentedHex(unittest.TestCase):
    """A hex outside `:root` must be sanctioned by a named ruling.

    `DESIGN_SYSTEM.md` says "use variables; never hardcode a hex in new
    CSS", and until 2026-08-17 nothing enforced it — so the newest CSS in
    the file broke it three times by re-typing a token's own value
    (`--line`, `--line-soft`, `--panel2`) and three more by inventing greys
    darker than `--field` (adversarial review F4).

    The exception list below IS the documentation: every literal names why
    it is allowed. Two shapes are legitimate —

      ARTIFACT INK. A rendered sheet or board is a PICTURE the app makes,
      not app chrome. Its paper and ink are subject matter (R4.6b), and
      binding them to chrome tokens would mean a chrome change repainting
      a customer's board.

      A NAMED RULING. A specific value settled by a plan or a user call,
      where the value itself is the decision.

    Anything else is drift, and the next `--line` change leaves a copy of
    the old one behind.
    """

    SANCTIONED = {
        # artifact ink — sheet render styles, R4.6b
        "#efe9dd": "GALLERY paper", "#e4ddd0": "GALLERY inset",
        "#1f1d19": "GALLERY ink", "#17181a": "CONTACT paper",
        "#e8e5dd": "CONTACT ink / board-frame title",
        "#d9d4c8": "NEWSPRINT paper", "#1a1814": "NEWSPRINT ink",
        "#1c4f7c": "BLUEPRINT paper", "#eef3f8": "BLUEPRINT ink",
        "#fbfbf9": "PLATE paper", "#1e1e1c": "PLATE ink",
        "#131418": "INK paper", "#e2ddd0": "INK inset",
        # RULE_PASS_2 B4 (2026-08-18) — the two look styles were outside
        # the mirror, which is the drift the mirror exists to prevent
        "#ece4d2": "ART_BOARD paper", "#ded4c0": "ART_BOARD mat",
        "#28221a": "ART_BOARD ink", "#101216": "TECH_DESIGN paper",
        "#e2e6eb": "TECH_DESIGN ink",
        # TUTORIAL_MATERIAL (2026-08-19) — the tour is made of board stock
        "#a6763a": "ART_BOARD accent — a 2px RULE only, 3.15:1 on paper",
        "#695e4c": "--sheet-dim-ui, a screen-calibrated derivation of "
                   "ART_BOARD's dim (3.94:1 as 9px UI text) — 5.02:1, "
                   "tour layer only, never a sheet ink",
        "#3a3124": "the parchment primary's hover — ink, lifted",
        # artifact ink — the board preview frame is a picture of a board
        "#2a2723": "board-frame ground", "#232019": "board-frame slot",
        "#9a978f": "board-frame subtitle",
        # named rulings
        "#4a4d52": "disabled ink, ruled",
        "#17191c": "locked cell, sanctioned in the plan",
        "#3a4048": "popover border, sanctioned in the plan",
        "#1c1f23": "popover ground, sanctioned in the plan",
        "#211b1b": "hatch-bad band A", "#1b1717": "hatch-bad band B",
        "#000": "the colour picker's empty state — no colour, not a colour",
    }

    def test_the_sheet_mirror_covers_every_render_style(self):
        """RULE_PASS_2 B4: two of eight styles had no DOM mirror, which is
        exactly the drift the mirror's own comment says it prevents. This
        reads the renderer, so a new style fails here until it is
        mirrored."""
        sys.path.insert(0, str(ROOT))
        from app.sheet_render import STYLE_INK
        for key in STYLE_INK:
            self.assertIn(f'.sheet[data-style="{key}"]', CSS,
                          f"{key} has no DOM mirror")

    def test_every_hex_outside_root_is_sanctioned(self):
        body = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        rest = body[body.index("}", body.index(":root")):]
        found = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{3,8}", rest)}
        unsanctioned = sorted(found - {k.lower() for k in self.SANCTIONED})
        self.assertEqual(unsanctioned, [],
                         "hex outside :root with no named ruling — use a token, "
                         "or add it to SANCTIONED with the ruling that allows it")

    def test_no_literal_duplicates_a_token(self):
        """The sharpest half: three literals WERE an existing token, so the
        next time that token moves, a copy of the old value stays behind."""
        body = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        root = body[body.index(":root"):body.index("}", body.index(":root"))]
        toks = {v.lower(): k for k, v in
                re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{3,8})", root)}
        rest = body[body.index("}", body.index(":root")):]
        dupes = sorted({h.lower() for h in re.findall(r"#[0-9a-fA-F]{3,8}", rest)}
                       & set(toks))
        self.assertEqual(dupes, [],
                         f"literal copies of a token: "
                         f"{[(d, toks[d]) for d in dupes]}")

    def test_the_sanctioned_list_is_not_a_dumping_ground(self):
        """Every entry must still appear. A stale one hides a real drift."""
        body = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        rest = body[body.index("}", body.index(":root")):].lower()
        for h in self.SANCTIONED:
            self.assertIn(h.lower(), rest, f"sanctioned hex no longer used: {h}")


class TheSceneSearchStatesRatherThanSignals(unittest.TestCase):
    """The breakdown door's search (2026-08-22) is the one place a field
    reports a saved reference under itself. Two things have to hold or the
    surface starts arguing with canon: the report is not a signal, and the
    list of results is not a set of primaries."""

    def block(self):
        i = CSS.index(".scene-find {")
        return CSS[i:CSS.index(".bb-ramp {", i)]

    def test_the_saved_pointer_is_a_confirmed_state_not_an_action(self):
        """`SCENE SAVED — … · LINE 2857` states a fact the scan will act
        on. Amber marks the one thing to DO, and this is not it — `--ok`
        is the token for a condition that has been met."""
        self.assertIn(".f-note.scene-ref { color: var(--ok); }", CSS)

    def test_the_results_carry_no_amber_at_all(self):
        """Amber in this door belongs to `Scan Screenplay`, which is the
        one primary in view. Twenty-one results wearing it would be
        twenty-two."""
        uses = [ln.strip() for ln in self.block().splitlines()
                if "--accent" in ln]
        self.assertEqual(uses, [], f"scene search ambers: {uses}")

    def test_a_result_is_machine_data_in_courier(self):
        """A slugline and a scene count are both machine data — the label
        is set in `--mono` and the count is the `.mono` sub."""
        self.assertIn("font-family: var(--mono)", self.block())

    def test_the_two_switches_read_as_quieter_than_the_matches(self):
        """`None` and `Paste a section` stand at the head of the list but
        they are not results — `--ink-dim` against the matches' `--ink`,
        and a rule under the pair where the count line is absent."""
        b = self.block()
        self.assertIn(".scene-hit.is-act .scene-hit-label { color: var(--ink-dim); }", b)
        self.assertIn(".scene-hit.is-act + .scene-hit:not(.is-act)", b)

    def test_a_swapped_row_actually_disappears(self):
        """`.door-row` is `display: grid`, which beats the hidden
        attribute — the selection row and the paste row occupy one slot
        and would otherwise both be on screen."""
        self.assertIn(".door-row[hidden] { display: none; }", CSS)

    def test_the_retired_no_match_line_left_the_stylesheet_too(self):
        """It said NO LOCATION OR SLUGLINE MATCHES THAT, then IT WILL BE
        READ AS THE BRIEF, and both were noise over a field still being
        typed in. A rule with no markup left is a pattern waiting to be
        re-adopted by whoever greps for it."""
        self.assertNotIn("scene-none", CSS)


class TheReadPanelIsLegibleAndHasOneAmber(unittest.TestCase):
    """The read surface (2026-08-20) is dense Courier at 10.5–12px over
    `--field`, and it is the only panel in the app whose whole job is to
    be watched. Both facts make it worth measuring rather than assuming.
    """

    ROOT = dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-f]{3,8})\b",
                           CSS.split(":root {")[1].split("\n}")[0]))

    @staticmethod
    def _lum(h):
        h = h.lstrip("#")
        def ch(c):
            c /= 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

    @classmethod
    def ratio(cls, a, b):
        la, lb = cls._lum(cls.ROOT.get(a, a)), cls._lum(cls.ROOT.get(b, b))
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    def test_the_ladder_and_the_page_clear_aa_for_body_ink(self):
        """`--ink-dim` is what the rows and the snapshot are set in."""
        for ground in ("--field", "--panel"):
            r = self.ratio(ground, "--ink-dim")
            self.assertGreaterEqual(round(r, 2), 4.5,
                                    f"--ink-dim on {ground} is {r:.2f}:1")

    def test_the_phase_and_note_lines_clear_large_text_aa(self):
        """`--ink-faint` carries the pending phases and the honesty note.
        They are letterspaced Courier caps, which AA treats as small text
        — 3:1 is the floor they must clear, and the note in particular is
        the sentence that keeps this surface honest, so it is asserted
        rather than eyeballed."""
        r = self.ratio("--panel", "--ink-faint")
        self.assertGreaterEqual(round(r, 2), 3.0,
                                f"--ink-faint on --panel is {r:.2f}:1")

    def test_a_done_bar_and_a_live_bar_are_told_apart(self):
        """Green `--ok` and amber `--accent` must not be near-equal in
        luminance, or the one live bar disappears into the finished ones
        for anyone who cannot separate them by hue."""
        a, b = self._lum(self.ROOT["--ok"]), self._lum(self.ROOT["--accent"])
        self.assertGreater(abs(a - b), 0.05,
                           "the live bar and a done bar are the same value")

    def test_the_panel_carries_exactly_one_amber(self):
        block = CSS.split(".rd {")[1]
        uses = [ln.strip() for ln in block.splitlines()
                if "--accent" in ln and not ln.strip().startswith(("*", "/*"))]
        self.assertEqual(len(uses), 1, f"read panel ambers: {uses}")

    def test_the_block_is_marked_uncanonized(self):
        i = CSS.index(".rd {")
        self.assertIn("UNCANONIZED — 2026-08-20", CSS[max(0, i - 1400):i])



class TheFramingFieldAndTag(unittest.TestCase):
    """A2 (2026-08-25). Two additions to surfaces that already existed:
    a select in the camera row, and a tag in the take's badge stack.

    Both had to be measured rather than eyeballed, and one caught a real
    fault: at 150px the framing select truncated to `Extreme emotion`,
    hiding the optics that are the entire reason the control exists.
    """

    def test_the_framing_field_spans_the_row_and_can_shrink(self):
        """`min-width: 0` on the ITEM, not only the select. A grid item's
        automatic minimum is its min-content width, and a select's
        min-content is its longest OPTION — so without this the track
        grows to fit `Threatening / confrontational proximity — 24–32mm,
        f/2.8–4` and the row overflows the card."""
        block = CSS.split(".cam-field-wide {")[1].split("}")[0]
        self.assertIn("grid-column: 1 / -1", block)
        self.assertIn("min-width: 0", block)
        sel = CSS.split(".cam-field-wide select {")[1].split("}")[0]
        self.assertIn("width: 100%", sel)

    def test_the_framing_tag_joins_the_stack_it_belongs_to(self):
        """Same right edge and the next step up from the grammar tag —
        they are the same kind of fact and are read together."""
        block = CSS.split(".shot-tag-framing {")[1].split("}")[0]
        self.assertIn("right: 10px", block)
        self.assertIn("bottom: 82px", block)
        for other, bottom in (("prompt", "58px"), ("grammar", "34px")):
            seg = CSS.split(f".shot-tag-{other} {{")[1].split("}")[0]
            self.assertIn(f"bottom: {bottom}", seg)

    def test_the_framing_tag_is_dim_ink_like_its_neighbours(self):
        block = CSS.split(".shot-tag-framing {")[1].split("}")[0]
        self.assertIn("var(--ink-dim)", block)

    def test_it_is_not_amber_and_not_a_verdict(self):
        """Amber marks the current stage, the one primary action, and
        focus. What lens a take rode is none of those."""
        block = CSS.split(".shot-tag-framing {")[1].split("}")[0]
        self.assertNotIn("--accent", block)
        self.assertNotIn("--bad", block)

    def test_a_ladder_row_states_only_what_landed(self):
        """An unfilled row keeps its em dash in `--ink-faint`; a filled
        one goes `--ink`. A row that printed 0 before its value arrived
        would be claiming a measurement nobody made — the fault this
        project spent a week removing from three other surfaces."""
        empty = CSS.split(".rl-row .rl-val {")[1].split("}")[0]
        self.assertIn("var(--ink-faint)", empty)
        filled = CSS.split(".rl-row.in .rl-val {")[1].split("}")[0]
        self.assertIn("var(--ink)", filled)

    def test_the_ladder_has_no_progress_bar(self):
        """Where a phase is one model call there is nothing to measure,
        and a creeping bar would be a picture of an intention. The check
        is on the JS, not the CSS: a bar is drawn by setting a width from
        data, and `max-width` on the container is not that."""
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        i = js.index("const runLadder = {")
        seg = js[i:js.index("const theBible = {", i)]
        for word in ("style.width", "busy-bar", "@keyframes", "requestAnimationFrame"):
            self.assertNotIn(word, seg, word)

    def test_a_ladder_is_capped_so_its_phases_stay_together(self):
        block = CSS.split(".rl {")[1].split("}")[0]
        self.assertIn("max-width", block)

    def test_only_a_failure_is_painted_bad(self):
        block = CSS.split(".rl-failed .rd-note {")[1].split("}")[0]
        self.assertIn("var(--bad)", block)
        rows = CSS.split(".rl-row {")[1].split("}")[0]
        self.assertNotIn("--bad", rows)
        self.assertNotIn("--accent", rows)

    def test_the_framing_note_speaks_prose_not_machine(self):
        """Rule 2: Courier carries machine data, Archivo carries prose.
        The note is a sentence, and it sits inside `.cam-field`, whose
        `> span` rule is the AXIS LABEL — Courier, caps, letterspaced.
        Correct for the word ANGLE, wrong for a sentence, and it rendered
        as a machine warning until the voice was reset. The selector has
        to out-specify that rule, which `.cam-note` alone does not."""
        self.assertIn(".cam-field > .cam-note {", CSS)
        block = CSS.split(".cam-field > .cam-note {")[1].split("}")[0]
        self.assertIn("var(--sans)", block)
        self.assertIn("text-transform: none", block)
        self.assertIn("letter-spacing: normal", block)

    def test_the_tag_is_not_a_button(self):
        """The grammar tag opens a document; a framing is one table row
        and the tag already states all of it. A control that opens
        nothing new teaches people not to click."""
        block = CSS.split(".shot-tag-framing {")[1].split("}")[0]
        self.assertNotIn("cursor: pointer", block)
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        i = js.index("shot-tag-framing")
        self.assertIn("<span", js[i - 40:i + 10])

if __name__ == "__main__":
    unittest.main()
