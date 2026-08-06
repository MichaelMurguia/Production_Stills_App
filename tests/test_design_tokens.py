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

    def test_action_bar_grammar(self):
        self.assert_decls(".act-bar", ["border: 1px solid var(--line)"])
        self.assert_decls(".act-right", ["border-left: 1px solid var(--line)"])
        self.assert_decls(".act-bar .act-approve-btn", [
            "border: 1px solid var(--ok)", "color: var(--ok)"])

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

    def test_take_row_wraps_and_its_verbs_are_peers(self):
        """T1/T2: horizontal scroll on navigation hides actions the user
        then cannot find, and six verbs that are all ghost in the source
        must all be ghost buttons on screen."""
        b = block(".act-bar")
        self.assertIn("flex-wrap: wrap", b)
        self.assertNotIn("overflow-x: auto", b,
                         "the row must wrap, never scroll")
        self.assert_decls(".act-bar .ghost, .act-bar .danger",
                          ["border: 1px solid var(--line)"])
        self.assert_decls(".act-bar .act-approve-btn",
                          ["border: 1px solid var(--ok)", "color: var(--ok)"])

    def test_take_tags_ride_the_image(self):
        self.assert_decls(".stage-shot", ["position: relative"])
        self.assert_decls(".shot-tag", [
            "position: absolute", "background: rgba(11, 12, 14, .82)",
            "border: 1px solid var(--line)", "font-family: var(--mono)"])
        self.assert_decls(".shot-tag-state", ["top: 10px", "left: 10px"])
        self.assert_decls(".shot-tag-id", ["right: 10px", "bottom: 10px"])

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
        self.assert_decls(".sw-cite", ["border-left: 2px solid var(--line)"])
        self.assert_decls(".sw-acts .ok-act", ["color: var(--ok)"])

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
        """D3: five tiles, the only colored number is open questions, the
        logline rides an accent rule; the old reveal strip is gone."""
        self.assert_decls(".read-tiles", ["grid-template-columns: repeat(5, 1fr)"])
        self.assert_decls(".read-num.attn", ["color: var(--accent)"])
        self.assert_decls(".read-logline", ["border-left: 2px solid var(--accent)"])
        self.assertNotIn(".reveal-strip", CSS)

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


if __name__ == "__main__":
    unittest.main()
