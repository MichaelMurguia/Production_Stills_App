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

    def test_no_undocumented_hex_in_hover(self):
        # #f0bc63 exists exactly once: as the --accent-hover token itself.
        self.assertEqual(CSS.count("#f0bc63"), 1)
        self.assertIn("--accent-hover: #f0bc63", CSS)


if __name__ == "__main__":
    unittest.main()
