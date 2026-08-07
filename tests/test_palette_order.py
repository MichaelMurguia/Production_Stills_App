"""Band order in a palette ramp (PALETTE_GROUPS_PLAN §1, §5).

The ordering lives in app.js, so these assert the RULE against a faithful
Python port plus the source that implements it. The rule: hero first at
double width, then light → dark by relative luminance, ties broken on the
hex string so a ramp never reshuffles between renders.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def luma(hexv: str) -> float:
    h = hexv.replace("#", "")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ramp_order(swatches: list[dict]) -> list[dict]:
    return sorted(swatches, key=lambda s: (not s.get("hero"),
                                           -luma(s["hex"]), s["hex"]))


class OrderingRule(unittest.TestCase):
    def test_light_to_dark(self):
        out = ramp_order([{"hex": "#000000"}, {"hex": "#FFFFFF"}, {"hex": "#808080"}])
        self.assertEqual([s["hex"] for s in out], ["#FFFFFF", "#808080", "#000000"])

    def test_hero_is_first_however_dark_it_is(self):
        out = ramp_order([{"hex": "#FFFFFF"}, {"hex": "#101010", "hero": True},
                          {"hex": "#808080"}])
        self.assertEqual(out[0]["hex"], "#101010")
        self.assertEqual([s["hex"] for s in out[1:]], ["#FFFFFF", "#808080"])

    def test_ties_break_on_the_hex_so_the_order_is_stable(self):
        """Two colours of equal luminance must not swap between renders."""
        a, b = {"hex": "#FF0000"}, {"hex": "#FE0206"}
        first = [s["hex"] for s in ramp_order([a, b])]
        second = [s["hex"] for s in ramp_order([b, a])]
        self.assertEqual(first, second)

    def test_luminance_uses_the_srgb_weights(self):
        """Green reads far lighter than blue at the same value — a naive
        average would order these wrongly."""
        out = ramp_order([{"hex": "#0000FF"}, {"hex": "#00FF00"}])
        self.assertEqual([s["hex"] for s in out], ["#00FF00", "#0000FF"])

    def test_a_pair_sorts_on_its_primary_hex(self):
        out = ramp_order([{"hex": "#FFFFFF"},
                          {"hex": "#202020", "pair_hex": "#FEFEFE"}])
        self.assertEqual(out[-1]["hex"], "#202020")


class SourceImplementsTheRule(unittest.TestCase):
    def test_luma_uses_the_stated_coefficients(self):
        m = re.search(r"const lumaOf = .*?\n};", JS, re.S)
        self.assertIsNotNone(m, "lumaOf missing")
        for coeff in ("0.2126", "0.7152", "0.0722"):
            self.assertIn(coeff, m.group(0))

    def test_ramp_order_puts_hero_first_then_luma_then_hex(self):
        m = re.search(r"const rampOrder = .*?\);", JS, re.S)
        self.assertIsNotNone(m, "rampOrder missing")
        body = m.group(0)
        self.assertLess(body.index("hero"), body.index("lumaOf"),
                        "hero must dominate luminance")
        self.assertLess(body.index("lumaOf"), body.index("a.hex <"),
                        "the hex tiebreak must come last")

    def test_the_hero_band_is_double_width(self):
        self.assertIn("flex:${sw.hero ? 2 : 1}", JS)

    def test_a_pair_is_one_band_split_top_and_bottom(self):
        """A pair is ONE swatch, so it gets one band's width."""
        m = re.search(r"const bandStyle = .*?;\n", JS, re.S)
        self.assertIn("linear-gradient", m.group(0))
        self.assertIn("50%", m.group(0))

    def test_the_app_never_promotes_a_hero_by_itself(self):
        """A rejected hero leaves the group OPEN — the user chooses."""
        self.assertNotIn("autoPromote", JS)
        self.assertIn("the app never guesses one after the fact", JS)

    def test_one_ramp_per_group_and_one_band_per_swatch(self):
        """The strip renders a group as ONE object, not a grid of cards."""
        self.assertIn('<div class="sw-ramp"', JS)
        self.assertIn("rampOrder(g.swatches).map(band).join", JS)
        self.assertNotIn("sw-grid", JS)
        self.assertNotIn("sw-card", JS)

    def test_a_group_with_no_hero_reads_open(self):
        self.assertIn('"OPEN"', JS)
        self.assertIn("HERO ${esc(hero.hex)}", JS)

    def test_the_column_draws_bands_from_notes_not_thumbnails(self):
        """§3 — parsed hexes, never the stored thumbnail."""
        i = JS.index("const renderPaletteRows")
        body = JS[i:i + 2600]
        self.assertIn("swatchNotes(r.notes)", body)
        self.assertIn("bandStyle(sw)", body)
        self.assertNotIn("thumb=1&", body)

    def test_removing_a_grouped_row_deletes_each_reference_singly(self):
        """So the approval log records every one."""
        i = JS.index("const renderPaletteRows")
        body = JS[i:i + 3200]
        self.assertIn("for (const id of ids)", body)
        self.assertIn("Remove ${ids.length} references?", body)


if __name__ == "__main__":
    unittest.main()
