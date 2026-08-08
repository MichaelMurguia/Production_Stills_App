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

    def column_fn(self) -> str:
        """The whole renderPaletteRows body — bounded by the next top-level
        declaration, not a guessed character count (a fixed slice silently
        stopped covering the function when it grew)."""
        i = JS.index("const renderPaletteRows")
        j = JS.index("\n  const refreshRefs", i)
        return JS[i:j]

    def test_the_column_draws_bands_from_notes_not_thumbnails(self):
        """§3 — parsed hexes, never the stored thumbnail."""
        body = self.column_fn()
        self.assertIn("swatchNotes(r.notes)", body)
        self.assertIn("bandStyle(sw)", body)
        self.assertNotIn("thumb=1&", body)

    def test_the_ramp_row_carries_no_destructive_act(self):
        """NON_CANON_REVIEW R4: a delete-forever control may not be the
        loudest mark on a row it can destroy. Removal moved into the
        viewer, where the whole group can be read before it goes."""
        body = self.column_fn()
        self.assertNotIn('data-f="del"', body)
        self.assertNotIn("&times;", body)
        self.assertNotIn('class="danger"', body)
        self.assertNotIn("askConfirm", body, "no confirm means no destruction here")

    def test_removal_lives_in_the_viewer_and_deletes_singly(self):
        """Still one at a time through the normal path, so the log records
        every one."""
        body = self.viewer_fn()
        self.assertIn('data-f="rm-group"', body)
        self.assertIn("for (const id of ids)", body)
        self.assertIn("Remove ${ids.length} reference", body)

    def viewer_fn(self) -> str:
        """Bounded at renderWizard — the viewer sits at module scope just
        above it since 2026-08-08; the old renderSwatchStrip bound would
        sweep in the whole wizard prelude."""
        i = JS.index("const openSwatchViewer")
        return JS[i:JS.index("\nasync function renderWizard", i)]

    def test_the_viewer_takes_a_list_of_groups(self):
        """One for a ramp click, all of them for Review all — one viewer,
        not two implementations that can drift."""
        body = self.viewer_fn()
        self.assertIn("openSwatchViewer = (groups", body)
        self.assertIn("const many = groups.length > 1", body)
        self.assertIn("groups.map(section)", body)

    def test_review_all_exists_and_states_what_is_unopened(self):
        """Approve all acts across languages the user may never have
        opened; the bar has to say so and offer the read."""
        self.assertIn('data-f="review"', JS)
        self.assertIn("Review all ${total}", JS)
        self.assertIn("LANGUAGE${r.groups.length === 1", JS)
        self.assertIn("UNOPENED", JS)
        self.assertIn("const seen = new Set()", JS)

    def test_the_approved_mode_swaps_the_verbs(self):
        """Approve is meaningless on an approved swatch; Reject there means
        demote out of canon, and is NOT the row's × (which deletes)."""
        body = self.viewer_fn()
        self.assertIn('data-f="ap">Approve</button>', body)
        self.assertIn('approved ? "" :', body)
        self.assertIn("Demote out of canon", body)
        self.assertIn('approved ? "APPROVED" : "PROPOSED, NOT CANON"', body)

    def test_approved_rows_open_the_viewer(self):
        """The rule the ramp canonized: members are one click away. The
        cross-block holder is gone — the viewer moved to MODULE scope
        (2026-08-08) so the Reference page could reuse it, which also
        retires the scope bug the holder guarded against."""
        body = self.column_fn()
        self.assertIn("openSwatchViewer(", body)
        self.assertIn("approved: true", body)
        self.assertNotIn("openPaletteViewer", JS,
                         "the holder pattern must not linger half-removed")

    def test_the_viewer_is_module_scope_and_page_agnostic(self):
        """One viewer, two pages. The page-specific facts ride opts:
        refresh (which view re-renders) and onRescan (absent where no
        engine picker exists — Rescan only renders where it can run)."""
        i = JS.index("const openSwatchViewer")
        head = JS[i:i + 300]
        self.assertIn("refresh = () => {}", head)
        self.assertIn("onRescan = null", head)
        body = self.viewer_fn()
        self.assertIn("many || !onRescan ?", body,
                      "no engine picker means no Rescan act")
        self.assertNotIn("refreshRefs", body,
                         "the viewer must not reach into a page's closure")

    def test_the_reference_shelf_uses_the_same_viewer(self):
        """The consolidation the user asked for (2026-08-08): the STYLE
        shelf's swatches group into ramps, quarantined ones keep the card
        so their governance stays visible, and clicking opens the ONE
        viewer with the Reference page's own refresh."""
        i = JS.index('shelf.key === "STYLE" ? shelfRefs.filter(isSwatch)')
        block = JS[i - 800:i + 3000]
        self.assertIn('r.status !== "REJECTED"', block,
                      "quarantined swatches keep the card")
        self.assertIn("pal-shelf", block)
        self.assertIn("openSwatchViewer(", block)
        self.assertIn("refresh: renderReferences", block)
        self.assertIn("row.swatches.every(sw => sw.approved)", block,
                      "a group with provisional members keeps its Approve verbs")

    def test_setting_a_hero_only_touches_its_own_group(self):
        """With every language on screen at once, a hero click must not
        reach into a neighbour."""
        body = self.viewer_fn()
        self.assertIn("const g = groupOf(refId)", body)
        self.assertIn("g.swatches.forEach(s => { s.hero = s.ref_id === refId; })", body)


    def test_review_all_sits_beside_the_columns_count(self):
        """NON_CANON_REVIEW R4: the count is what the verb acts on, so the
        header is where the two belong together — not under the rows."""
        body = self.column_fn()
        self.assertIn("Review all ${total}", body)
        self.assertIn("[data-f=state]", body, "anchored to the column's count badge")
        self.assertIn("badge.after(act)", body)
        self.assertIn("approved: true", body)
        self.assertIn("groups.length > 1", body,
                      "one group is already one click — no act needed")


if __name__ == "__main__":
    unittest.main()
