"""Swatch labels, hero colours and recolour (user 2026-08-06).

Three rulings live here:

  * a citation is a LABEL, not a quotation — "cold GRM white light" is the
    shape wanted, a run-on sentence is not;
  * each design language names ONE hero colour, the one a production
    designer splashes through that faction's sets;
  * a swatch can be repainted in place, keeping its id — a new id would
    orphan every approval already recorded against it.
"""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app import paths, store, wizard  # noqa: E402


class ShortCite(unittest.TestCase):
    def test_a_good_label_survives_untouched(self):
        for good in ("cold GRM white light", "GT40 yellow", "Onyx Unit black"):
            self.assertEqual(wizard.short_cite(good), good)

    def test_a_run_on_sentence_is_cut_to_a_label(self):
        long = ("The GRM paints everything in a cold, institutional white "
                "light that flattens the human face.")
        out = wizard.short_cite(long)
        self.assertLessEqual(len(out.split()), 6)
        self.assertLessEqual(len(out), 44)
        self.assertNotIn(",", out)
        self.assertFalse(out.endswith("."))

    def test_quotes_and_trailing_punctuation_are_stripped(self):
        self.assertEqual(wizard.short_cite('"Onyx Unit black — the hull matte"'),
                         "Onyx Unit black")

    def test_empty_stays_empty(self):
        self.assertEqual(wizard.short_cite(""), "")
        self.assertEqual(wizard.short_cite(None), "")


class HeroParsing(unittest.TestCase):
    def parse(self, raw):
        return wizard.parse_swatch_proposals(json.dumps(raw))

    def test_one_hero_per_language_is_kept(self):
        g = self.parse([{"language": "RESISTANCE", "swatches": [
            {"name": "A", "hex": "#111111"},
            {"name": "B", "hex": "#222222", "hero": True},
        ]}])[0]
        self.assertEqual([s["hero"] for s in g["swatches"]], [False, True])

    def test_extra_heroes_are_demoted_not_dropped(self):
        g = self.parse([{"language": "GRM", "swatches": [
            {"name": "A", "hex": "#111111", "hero": True},
            {"name": "B", "hex": "#222222", "hero": True},
            {"name": "C", "hex": "#333333", "hero": True},
        ]}])[0]
        self.assertEqual([s["hero"] for s in g["swatches"]], [True, False, False])
        self.assertEqual(len(g["swatches"]), 3)

    def test_no_hero_is_left_alone_never_invented(self):
        g = self.parse([{"language": "BELTMINER TECH", "swatches": [
            {"name": "A", "hex": "#111111"}, {"name": "B", "hex": "#222222"},
        ]}])[0]
        self.assertFalse(any(s["hero"] for s in g["swatches"]))

    def test_each_language_gets_its_own_hero(self):
        gs = self.parse([
            {"language": "RESISTANCE", "swatches": [{"name": "A", "hex": "#111111", "hero": True}]},
            {"language": "GRM", "swatches": [{"name": "B", "hex": "#222222", "hero": True}]},
        ])
        self.assertEqual([g["swatches"][0]["hero"] for g in gs], [True, True])

    def test_citations_are_shortened_on_the_way_in(self):
        g = self.parse([{"language": "GRM", "swatches": [
            {"name": "A", "hex": "#111111",
             "cite": "Everything the GRM touches is lit cold, white and even, with no shadow to hide in."},
        ]}])[0]
        self.assertLessEqual(len(g["swatches"][0]["cite"].split()), 6)


class SwatchStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-sw-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
                       paths.SETTINGS, paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()

    def tearDown(self):
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def a_swatch(self, hexv="#8A4B2E", notes="RESISTANCE · OXIDE RUST · #8A4B2E · GT40 yellow"):
        return store.add_reference("oxide-rust.png", wizard.render_swatch_png(hexv),
                                   "COLOR_PALETTE", [], [], notes,
                                   source="swatch-proposal")

    def pixel(self, ref_id, xy=(10, 10)):
        with Image.open(store.reference_image_path(ref_id)) as im:
            return im.convert("RGB").getpixel(xy)

    def test_recolour_repaints_the_pixels(self):
        ref = self.a_swatch()
        self.assertEqual(self.pixel(ref["id"]), (0x8A, 0x4B, 0x2E))
        wizard.recolor_swatch(ref["id"], "#123456")
        self.assertEqual(self.pixel(ref["id"]), (0x12, 0x34, 0x56))

    def test_recolour_keeps_the_id_and_the_review_state(self):
        ref = self.a_swatch()
        store.set_reference_status(ref["id"], "APPROVED")
        out = wizard.recolor_swatch(ref["id"], "#123456")
        self.assertEqual(out["id"], ref["id"])
        self.assertEqual(out["status"], "APPROVED")

    def test_recolour_rewrites_only_the_hex_segment(self):
        ref = self.a_swatch()
        wizard.recolor_swatch(ref["id"], "#123456")
        self.assertEqual(store.get_reference(ref["id"])["notes"],
                         "RESISTANCE · OXIDE RUST · #123456 · GT40 yellow")

    def test_recolour_finds_the_hex_in_a_manual_swatch_shape(self):
        """Manual swatches note NAME · HEX · CITE — no language segment."""
        ref = self.a_swatch(notes="OXIDE RUST · #8A4B2E · GT40 yellow")
        wizard.recolor_swatch(ref["id"], "#123456")
        self.assertEqual(store.get_reference(ref["id"])["notes"],
                         "OXIDE RUST · #123456 · GT40 yellow")

    def test_recolour_preserves_a_hero_marker(self):
        ref = self.a_swatch(notes="RESISTANCE · OXIDE RUST · #8A4B2E · GT40 yellow · HERO")
        wizard.recolor_swatch(ref["id"], "#123456")
        self.assertTrue(store.get_reference(ref["id"])["notes"].endswith(" · HERO"))

    def test_recolour_can_add_and_drop_a_value_key_pair(self):
        ref = self.a_swatch()
        wizard.recolor_swatch(ref["id"], "#123456", "#ABCDEF")
        self.assertEqual(self.pixel(ref["id"], (500, 200)), (0xAB, 0xCD, 0xEF))
        self.assertIn("#123456 / #ABCDEF", store.get_reference(ref["id"])["notes"])
        wizard.recolor_swatch(ref["id"], "#123456")
        self.assertEqual(self.pixel(ref["id"], (500, 200)), (0x12, 0x34, 0x56))

    def test_recolour_updates_the_hash(self):
        ref = self.a_swatch()
        before = ref["sha256"]
        wizard.recolor_swatch(ref["id"], "#123456")
        self.assertNotEqual(store.get_reference(ref["id"])["sha256"], before)

    def test_a_bad_hex_is_refused_and_nothing_changes(self):
        ref = self.a_swatch()
        with self.assertRaises(Exception):
            wizard.recolor_swatch(ref["id"], "not-a-hex")
        self.assertEqual(self.pixel(ref["id"]), (0x8A, 0x4B, 0x2E))

    def test_only_a_palette_reference_can_be_recoloured(self):
        ref = store.add_reference("car.png", wizard.render_swatch_png("#111111"),
                                  "VEHICLE_GEOMETRY", [], [], "a car")
        with self.assertRaises(Exception):
            wizard.recolor_swatch(ref["id"], "#123456")

    def test_unknown_reference_raises(self):
        with self.assertRaises(KeyError):
            wizard.recolor_swatch("REF-9999", "#123456")

    def test_hero_marker_round_trips_through_persistence(self):
        groups = wizard.persist_swatch_proposals([{
            "language": "RESISTANCE",
            "swatches": [
                {"name": "A", "hex": "#111111", "pair_hex": None, "hero": False, "cite": "x"},
                {"name": "B", "hex": "#222222", "pair_hex": None, "hero": True, "cite": "y"},
            ]}])
        notes = {sw["name"]: store.get_reference(sw["ref_id"])["notes"]
                 for sw in groups[0]["swatches"]}
        self.assertTrue(notes["B"].endswith(" · HERO"))
        self.assertFalse(notes["A"].endswith(" · HERO"))
        # and the marker must be the LAST segment, so the client can pop it
        self.assertEqual(notes["B"].split(" · ")[-1], wizard.HERO_MARK)


if __name__ == "__main__":
    unittest.main()
