"""One fact, one computation — the manifest, the count, and the arrange
room's SHORT verdict.

Adversarial review F5, F8, F22. Three places where the client computed
something the server already knew, and disagreed with it:

- The workbench manifest and `N OF 14` came from client arithmetic whose
  `isAutoStyle` knew two of the four auto-attach roles and had no per-role
  cap. It named plates that did not ride and omitted plates that did — on
  the screen where money is spent. `AUTO_ATTACH_HEADS`, in the SAME FILE,
  has held the correct four since 2026-08-03.
- The cap was a JS literal in two places, against
  `generate.MAX_REFERENCE_IMAGES` and `connectors.APP_MAX_REFS`.
- The arrange room computed "does this take fill this slot" twice: the tile
  against the CROPPED window, the drag HUD against the full take. The HUD
  was never pessimistic, so a user dragged a cropped panel, read OK, let
  go, and watched it flip to SHORT.

`DESIGN_SYSTEM.md` R2 already forbade the third: *"geometry is computed once
and declared… two implementations of one geometry is a drift bug with a
permanent maintenance cost."*"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


class TheServerResolvesTheManifest(unittest.TestCase):
    def test_the_resolver_is_reused_not_reimplemented(self):
        """It must answer with the code a render actually uses, or it is
        just a fourth opinion."""
        i = GEN.index("def resolved_attachments")
        seg = GEN[i:i + 1800]
        self.assertIn("_resolve_generation_inputs(spec_id, panel_id, ref_ids)", seg)

    def test_it_reports_the_cap_rather_than_the_client_knowing_it(self):
        i = GEN.index("def resolved_attachments")
        seg = GEN[i:i + 1800]
        self.assertIn('"max": MAX_REFERENCE_IMAGES', seg)
        self.assertIn('"over": len(refs) > MAX_REFERENCE_IMAGES', seg)

    def test_it_says_why_each_plate_rides(self):
        """Picked or always-on: the distinction the client kept getting
        wrong, so it is the server's to state."""
        i = GEN.index("def resolved_attachments")
        self.assertIn('"auto": r.get("id", "") not in set(ref_ids)', GEN[i:i + 1800])

    def test_the_endpoint_exists_and_has_a_caller(self):
        self.assertIn(
            '@app.get("/api/specs/{spec_id}/panels/{panel_id}/attachments")', MAIN)
        self.assertIn("/attachments?refs=", JS)

    def test_it_costs_nothing(self):
        """Resolution only — the disk work lives in _reference_image_paths,
        which is why this can answer on every tick."""
        i = GEN.index("def resolved_attachments")
        # body only — the docstring names the disk helper it deliberately avoids
        seg = GEN[GEN.index("_resolve_generation_inputs(spec_id, panel_id, ref_ids)", i):i + 1800]
        for forbidden in ("_reference_image_paths", "_render_ready", "open("):
            self.assertNotIn(forbidden, seg, forbidden)


class TheClientStoppedComputingIt(unittest.TestCase):
    def test_the_cap_is_not_a_client_literal(self):
        self.assertNotIn("OF 14 ATTACHED", JS)
        self.assertIn("OF ${m.max} ATTACHED", JS)

    def test_the_count_comes_from_the_server(self):
        self.assertIn("= ${m.count} OF ${m.max} ATTACHED", JS)

    def test_the_manifest_is_rendered_from_the_response(self):
        i = JS.index("const updateRefCount = () =>")
        seg = JS[i:i + 2600]
        self.assertIn("for (const a of m.attachments)", seg)
        self.assertNotIn("styleAnchors.length", seg,
                         "the client's own style tally is gone")

    def test_a_failure_says_so_rather_than_guessing(self):
        """A guessed manifest is what this replaced."""
        i = JS.index("const updateRefCount = () =>")
        seg = JS[i:i + 2600]
        self.assertIn("COULD NOT RESOLVE THE ATTACHMENTS", seg)

    def test_a_later_tick_wins(self):
        """It fires on every checkbox, so an out-of-order reply must not
        paint a stale manifest."""
        i = JS.index("const updateRefCount = () =>")
        seg = JS[i:i + 2600]
        self.assertIn("const seq = ++refCountSeq;", seg)
        self.assertIn("if (seq !== refCountSeq) return;", seg)

    def test_the_two_role_list_is_gone(self):
        """`isAutoStyle` had two of the four roles while AUTO_ATTACH_HEADS
        in the same file had all four."""
        self.assertIn("const isAutoStyle = r => AUTO_ATTACH_HEADS.includes(roleHead(r.role));",
                      JS)
        self.assertNotIn('["BOARD_RENDERING_STYLE", "CINEMATOGRAPHY_STYLE"]\n    .includes',
                         JS)

    def test_the_correct_list_is_still_the_only_one(self):
        self.assertEqual(JS.count("const AUTO_ATTACH_HEADS ="), 1)
        for role in ("WORLD_TEXTURE", "COLOR_PALETTE",
                     "CINEMATOGRAPHY_STYLE", "BOARD_RENDERING_STYLE"):
            i = JS.index("const AUTO_ATTACH_HEADS =")
            self.assertIn(role, JS[i:i + 200], role)


class TheArrangeRoomHasOneVerdict(unittest.TestCase):
    def test_short_is_computed_once(self):
        self.assertEqual(JS.count("const shortFor = (pid, r) =>"), 1)

    def test_both_readers_call_it(self):
        tile = JS[JS.index("const layout = (st, skipId"):JS.index("const paintChrome")]
        hud = JS[JS.index("const hudFor = (pid"):JS.index("const hudFor = (pid") + 1400]
        self.assertIn("shortFor(pid, r)", tile)
        self.assertIn("shortFor(pid, r)", hud)

    def test_neither_reader_re_derives_it(self):
        """The exact two expressions that disagreed: the tile read availW,
        the HUD read t.w."""
        tile = JS[JS.index("const layout = (st, skipId"):JS.index("const paintChrome")]
        hud = JS[JS.index("const hudFor = (pid"):JS.index("const hudFor = (pid") + 1400]
        for seg, name in ((tile, "tile"), (hud, "HUD")):
            self.assertNotIn("pw > t.w || ph > t.h", seg, name)
            self.assertNotIn("pw > availW + 1", seg, name)

    def test_the_verdict_uses_the_cropped_window(self):
        """The tile's rule was the correct one — the crop is what the plate
        actually shows — so the shared function keeps it."""
        i = JS.index("const shortFor = (pid, r) =>")
        seg = JS[i:i + 700]
        self.assertIn("winFor(cropFor(pid), pw / ph, t.w, t.h)", seg)
        self.assertIn("short: pw > availW + 1 || ph > availH + 1", seg)

    def test_the_hud_gained_the_actionable_number(self):
        """It said SHORT without saying short of WHAT — the tile always had
        the plate's real dimensions and the HUD did not."""
        hud = JS[JS.index("const hudFor = (pid"):JS.index("const hudFor = (pid") + 1400]
        self.assertIn("PLATE SHOWS ${availW} × ${availH}", hud)

    def test_a_take_with_no_pixels_is_not_short(self):
        """No approved take is a different state from an undersized one."""
        i = JS.index("const shortFor = (pid, r) =>")
        seg = JS[i:i + 700]
        self.assertIn("if (!t || !t.w) return", seg)
        self.assertIn("short: false", seg)


if __name__ == "__main__":
    unittest.main()
