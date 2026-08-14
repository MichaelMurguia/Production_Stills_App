"""The four-anchor ruling (2026-08-03): three movie parameters + one board
parameter auto-attach, capped per role; board layout is assembly grammar.

Amended 2026-08-13 (user sign-off): subject references attach BEFORE the
style shelf — the GT40 board's hover jet plate rode as "image 7 of 8"
behind the anchors and lost. Role scoping, not position, binds style.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from app import generate, store


def ref(rid, role, added, status="APPROVED"):
    return {"id": rid, "role": role, "status": status, "added_at": added}


class StyleAnchorTests(unittest.TestCase):
    def test_four_anchor_shelf(self):
        self.assertEqual(store.AUTO_STYLE_ROLES,
                         {"WORLD_TEXTURE", "COLOR_PALETTE",
                          "CINEMATOGRAPHY_STYLE", "BOARD_RENDERING_STYLE"})
        self.assertEqual(store.MOVIE_STYLE_ROLES,
                         ("WORLD_TEXTURE", "COLOR_PALETTE", "CINEMATOGRAPHY_STYLE"))
        self.assertNotIn("BOARD_LAYOUT_STYLE", store.AUTO_STYLE_ROLES)

    def test_attach_cap_newest_first_and_layout_excluded(self):
        refs = [
            ref("REF-1", "CINEMATOGRAPHY_STYLE", "2026-08-01T10:00:00"),
            ref("REF-2", "CINEMATOGRAPHY_STYLE", "2026-08-02T10:00:00"),
            ref("REF-3", "CINEMATOGRAPHY_STYLE", "2026-08-03T10:00:00"),
            ref("REF-4", "COLOR_PALETTE", "2026-08-01T10:00:00"),
            ref("REF-5", "BOARD_LAYOUT_STYLE", "2026-08-01T10:00:00"),
            ref("REF-6", "WORLD_TEXTURE", "2026-08-01T10:00:00", status="PROVISIONAL"),
        ]
        with patch.object(store, "_load_refs", return_value=refs):
            out = store.auto_style_references()
        ids = {r["id"] for r in out}
        # Cap: only the newest two cinematography anchors ride.
        self.assertIn("REF-3", ids)
        self.assertIn("REF-2", ids)
        self.assertNotIn("REF-1", ids)
        # Palette rides; layout never; unapproved never.
        self.assertIn("REF-4", ids)
        self.assertNotIn("REF-5", ids)
        self.assertNotIn("REF-6", ids)


class SubjectRefsRideFirst(unittest.TestCase):
    """The 2026-08-13 reordering, pinned end to end: explicit subject refs
    keep their checkbox order at the head; the style shelf follows; a
    lighting study's geometry anchor still leads everything."""

    def _resolve(self, geometry=""):
        spec = {"specification_id": "S", "panels": [{"id": "P01"}],
                **({"geometry_ref": geometry} if geometry else {})}
        subject = ref("REF-40", "VEHICLE_GEOMETRY", "2026-08-01T10:00:00")
        anchors = [ref("REF-90", "CINEMATOGRAPHY_STYLE", "2026-08-02T10:00:00"),
                   ref("REF-91", "COLOR_PALETTE", "2026-08-02T10:00:00")]
        geo = ref("REF-77", "LOCATION_GEOMETRY", "2026-08-01T10:00:00")
        with patch.object(store, "get_spec", return_value=spec), \
             patch.object(store, "spec_locked", return_value=True), \
             patch.object(store, "get_reference",
                          side_effect=lambda rid: {"REF-40": subject,
                                                   "REF-77": geo}.get(rid)), \
             patch.object(store, "auto_style_references", return_value=anchors):
            _s, _p, refs = generate._resolve_generation_inputs(
                "S", "P01", ["REF-40"])
        return [r["id"] for r in refs]

    def test_subject_before_the_style_shelf(self):
        self.assertEqual(self._resolve(), ["REF-40", "REF-90", "REF-91"])

    def test_the_prompt_numbers_the_subject_first(self):
        subject = ref("REF-40", "VEHICLE_GEOMETRY", "2026-08-01T10:00:00")
        anchor = ref("REF-90", "CINEMATOGRAPHY_STYLE", "2026-08-02T10:00:00")
        lines = "\n".join(generate._reference_role_lines([subject, anchor]))
        self.assertIn("Attached image 1 (REF-40", lines)
        self.assertIn("Attached image 2 (REF-90", lines)

    def test_lighting_geometry_still_leads(self):
        self.assertEqual(self._resolve(geometry="REF-77"),
                         ["REF-77", "REF-40", "REF-90", "REF-91"])


class UserPaletteOwnsTheRole(unittest.TestCase):
    """2026-08-13 (user): the workbench used to attach ALL swatches (one
    suffix-less checkbox carried the whole palette — 19 references).
    Swatches are now picked individually; a picked palette replaces the
    auto shelf's palette top-up entirely, and no pick means the shelf's
    capped newest-2 ride as ruled 2026-08-03."""

    def _resolve(self, ref_ids):
        spec = {"specification_id": "S", "panels": [{"id": "P01"}]}
        lib = {
            "REF-40": ref("REF-40", "VEHICLE_GEOMETRY", "2026-08-01T10:00:00"),
            "REF-50": ref("REF-50", "COLOR_PALETTE", "2026-08-01T10:00:00"),
            "REF-51": ref("REF-51", "COLOR_PALETTE", "2026-08-02T10:00:00"),
        }
        anchors = [ref("REF-90", "CINEMATOGRAPHY_STYLE", "2026-08-02T10:00:00"),
                   ref("REF-98", "COLOR_PALETTE", "2026-08-03T10:00:00"),
                   ref("REF-99", "COLOR_PALETTE", "2026-08-03T11:00:00")]
        with patch.object(store, "get_spec", return_value=spec), \
             patch.object(store, "spec_locked", return_value=True), \
             patch.object(store, "get_reference", side_effect=lib.get), \
             patch.object(store, "auto_style_references", return_value=anchors):
            _s, _p, refs = generate._resolve_generation_inputs(
                "S", "P01", ref_ids)
        return [r["id"] for r in refs]

    def test_picked_swatches_replace_the_auto_palette(self):
        self.assertEqual(self._resolve(["REF-40", "REF-50", "REF-51"]),
                         ["REF-40", "REF-50", "REF-51", "REF-90"],
                         "exactly these swatches — the shelf's newest-2 "
                         "palette top-up stands down")

    def test_no_pick_keeps_the_capped_auto_palette(self):
        self.assertEqual(self._resolve(["REF-40"]),
                         ["REF-40", "REF-90", "REF-98", "REF-99"])


class SwatchSelectorWiring(unittest.TestCase):
    JS = (Path(__file__).resolve().parents[1] / "app/static/app.js") \
        .read_text(encoding="utf-8")

    def test_swatches_leave_the_generic_groups(self):
        self.assertIn('roleHead(r.role) !== "COLOR_PALETTE"', self.JS)
        self.assertIn("const swatchRefs", self.JS)

    def test_the_selector_sits_in_the_gen_row_and_feeds_the_send(self):
        self.assertIn('data-f="swatch-menu"', self.JS)
        self.assertIn("checkedSwatches()", self.JS)
        self.assertIn("NONE SELECTED = AUTO", self.JS)


if __name__ == "__main__":
    unittest.main()
