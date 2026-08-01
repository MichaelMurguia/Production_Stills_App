"""Board layout invariants: the aspect variant honors take ratios with a
uniform minimal residual, variants resolve per the ruling, and geometry
stays inside the canvas."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import assemble  # noqa: E402

PANELS = [{"id": f"P{i:02d}"} for i in range(1, 6)]
ASPECTS = {"P01": 16 / 9, "P02": 16 / 9, "P03": 9 / 16,
           "P04": 16 / 9, "P05": 16 / 9}


class AspectLayoutTests(unittest.TestCase):
    def _rects(self):
        return assemble._aspect_rects(PANELS, ASPECTS, 64, 214, 3712, 1882)

    def test_every_panel_gets_a_slot_inside_the_canvas(self):
        rects = self._rects()
        self.assertEqual(set(rects), {p["id"] for p in PANELS})
        for x, y, w, h in rects.values():
            self.assertGreaterEqual(x, 64)
            self.assertGreaterEqual(y, 214)
            self.assertLessEqual(x + w, 64 + 3712 + 1)
            self.assertLessEqual(y + h, 214 + 1882 + 1)
            self.assertGreater(w, 0)
            self.assertGreater(h, assemble.LABEL_H)

    def test_aspect_deviation_is_uniform_and_bounded(self):
        rects = self._rects()
        devs = []
        for pid, (x, y, w, h) in rects.items():
            slot_a = w / (h - assemble.LABEL_H)
            devs.append(slot_a / ASPECTS[pid])
        self.assertLess(max(devs) / min(devs), 1.05,
                        "residual crop must be uniform across panels")
        for d in devs:
            self.assertLess(abs(d - 1), 0.35, "crop should stay modest")

    def test_portrait_take_gets_a_portrait_slot(self):
        rects = self._rects()
        x, y, w, h = rects["P03"]
        self.assertLess(w / (h - assemble.LABEL_H), 1.0)

    def test_single_panel_fills_the_canvas(self):
        rects = assemble._aspect_rects([{"id": "P01"}], {"P01": 16 / 9},
                                       0, 0, 1000, 600)
        x, y, w, h = rects["P01"]
        self.assertEqual((x, y), (0, 0))
        self.assertEqual(w, 1000)


class VariantTests(unittest.TestCase):
    SPEC = {"panels": PANELS, "board_type": "LOCATION"}

    def test_default_maps_to_aspect(self):
        self.assertEqual(assemble.check_variant(self.SPEC, None), "aspect")
        self.assertEqual(assemble.check_variant(self.SPEC, "default"), "aspect")

    def test_named_variants_pass_through(self):
        for v in ("aspect", "allocation", "grid", "hero:P02"):
            self.assertEqual(assemble.check_variant(self.SPEC, v), v)

    def test_unknown_variant_and_hero_refused(self):
        with self.assertRaises(assemble.AssemblyError):
            assemble.check_variant(self.SPEC, "hero:P99")
        with self.assertRaises(assemble.AssemblyError):
            assemble.check_variant(self.SPEC, "mosaic")

    def test_lighting_study_always_grids(self):
        spec = {"panels": PANELS, "board_type": "LIGHTING_STUDY"}
        rects = assemble._variant_rects(spec, {}, ASPECTS, "aspect",
                                        0, 0, 3000, 1500)
        widths = {w for _, _, w, _ in rects.values()}
        self.assertEqual(len(widths), 1, "study panels stay equal — comparison is the point")


if __name__ == "__main__":
    unittest.main()
