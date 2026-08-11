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

    def test_composer_selection_is_the_amber(self):
        """The composer's selection outline spends the amber; unselected
        blocks carry no color until hovered."""
        self.assert_decls(".ov-block.sel", ["border-color: var(--accent)"])
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


if __name__ == "__main__":
    unittest.main()
