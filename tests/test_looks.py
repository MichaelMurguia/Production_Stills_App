"""Board looks (2026-08-13): a look is a persisted sheet-level property
that survives arrangement commits; dress is PURE DERIVATION resolved
from canon at derivation time. These tests are the feature's oracle:
persistence, identity, band math, freshness, readiness honesty, ink on
pixels, API contract — all against a throwaway home."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import ImageFont  # noqa: E402

from app import assemble, looks, paths, sheet, sheet_render, store  # noqa: E402
import app.main as appmain  # noqa: E402

from test_sheet import (_redirect_home, _restore_home,  # noqa: E402
                        _write_candidate, _write_spec)


def _seed_swatches(rows):
    """rows: [(language, name, hex)] — COLOR_PALETTE references, the
    shape wizard.parse_swatch_notes reads."""
    refs = [{"id": f"REF-{i:04d}", "role": "COLOR_PALETTE",
             "status": "APPROVED", "file": f"s{i}.png",
             "notes": f"{lang} · {name} · {hx} · bible"}
            for i, (lang, name, hx) in enumerate(rows, start=1)]
    paths.REF_INDEX.write_text(json.dumps(refs), encoding="utf-8")


class LooksHomeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-looks-"))
        _redirect_home(self.tmp)

    def tearDown(self):
        _restore_home()

    def _board(self, n=2):
        _write_spec(panels=[{"id": f"P{i}", "title": f"T{i}"}
                            for i in range(1, n + 1)])
        for i in range(1, n + 1):
            _write_candidate("SPEC-0001", f"CAND-{i:04d}", f"P{i}")
        return sheet.arrange_board("SPEC-0001")


class FontTests(unittest.TestCase):
    """Phase 0 — bundled OFL faces. Linux tenants rendered bitmap type
    for a month because _VOICES was Windows paths; the bundle is the fix
    and the hand voice only exists bundled."""

    def test_every_voice_resolves_a_bundled_truetype(self):
        fonts_dir = ROOT / "app" / "fonts"
        for voice in ("serif", "mono", "sans", "slab", "hand"):
            first = sheet_render._VOICES[voice][0]
            self.assertTrue(str(first).startswith(str(fonts_dir)),
                            f"{voice} must resolve bundled-first: {first}")
            self.assertTrue(Path(first).exists(), first)
            f = sheet_render._font(voice, 20)
            self.assertIsInstance(f, ImageFont.FreeTypeFont, voice)

    def test_each_family_ships_its_ofl(self):
        for fam in (ROOT / "app" / "fonts").iterdir():
            if fam.is_dir():
                self.assertTrue((fam / "OFL.txt").exists(),
                                f"{fam.name} must carry its license")


class LookModelTests(LooksHomeTest):
    def test_look_survives_arrangement_commit(self):
        # set_arrangement REPLACES every block; the look is a sibling and
        # must ride through untouched — this is the feature's foundation.
        rec = self._board(2)
        looks.set_look(rec["sheet_id"], "ART_BOARD")
        out = sheet.set_arrangement(rec["sheet_id"], {"rows": [
            {"h": 1, "cols": [{"w": 1, "cells": [{"id": "P1", "h": 1},
                                                 {"id": "P2", "h": 1}]}]},
        ]})
        self.assertEqual(out["look"]["key"], "ART_BOARD")

    def test_set_look_is_the_single_validation_door(self):
        rec = self._board(1)
        with self.assertRaises(sheet.SheetError):
            looks.set_look(rec["sheet_id"], "NO_SUCH_LOOK")
        with self.assertRaises(sheet.SheetError):
            looks.set_look(rec["sheet_id"], "ART_BOARD", {"bogus": True})
        plate = sheet.create_sheet("LOCATION", "PLATE", "SCREEN")
        with self.assertRaises(sheet.SheetError):
            looks.set_look(plate["sheet_id"], "ART_BOARD")
        looks.set_look(rec["sheet_id"], "TECH_DESIGN", {"profile": True})
        saved = sheet.get_sheet(rec["sheet_id"])
        self.assertTrue(saved["look"]["options"]["profile"])
        self.assertTrue(saved["look"]["options"]["spec_table"],
                        "unstated options take their defaults")
        cleared = looks.set_look(rec["sheet_id"], None)
        self.assertNotIn("look", cleared)

    def test_dressed_is_identity_without_a_look(self):
        rec = self._board(2)
        d = looks.dressed(rec)
        self.assertEqual(d, rec)
        self.assertIsNot(d, rec, "identity must still be a copy")

    def test_band_math_scales_blocks_and_never_overlaps(self):
        rec = self._board(2)
        sheet.set_arrangement(rec["sheet_id"], {"rows": [
            {"h": 1, "cols": [{"w": 0.5, "cells": [{"id": "P1", "h": 1}]},
                              {"w": 0.5, "cells": [{"id": "P2", "h": 1}]}]},
        ]})
        looks.set_look(rec["sheet_id"], "ART_BOARD")  # two bands
        stored = sheet.get_sheet(rec["sheet_id"])
        d = looks.dressed(stored)
        self.assertEqual(d["style"], "ART_BOARD")
        self.assertEqual(d["dress_annotations"], "hand")
        bands = [("PALETTE_BAND", 0.08), ("ATMOSPHERE", 0.045)]
        reserved = sum(h for _, h in bands) + looks.GAP * len(bands)
        keep_h = 1.0 - reserved
        for b0, b1 in zip(stored["blocks"], d["blocks"]):
            self.assertAlmostEqual(b1["frac"]["y"],
                                   round(b0["frac"]["y"] * keep_h, 4))
            self.assertAlmostEqual(b1["frac"]["h"],
                                   round(b0["frac"]["h"] * keep_h, 4))
        # dress lives strictly below the scaled panel area
        for el in d["dress"]:
            self.assertGreaterEqual(el["frac"]["y"], keep_h)
        # the arrangement itself is untouched — the room's truth
        self.assertEqual(d["arrangement"], stored["arrangement"])
        # and derivation never mutates its input
        self.assertEqual(stored, sheet.get_sheet(rec["sheet_id"]))

    def test_dress_data_is_fresh_at_derivation(self):
        rec = self._board(1)
        looks.set_look(rec["sheet_id"], "ART_BOARD")
        _seed_swatches([("BELT TECH", "Deep Sea", "#1B3A4B")])
        stored = sheet.get_sheet(rec["sheet_id"])
        strips = [e for e in looks.dressed(stored)["dress"]
                  if e["kind"] == "SWATCH_STRIP"]
        hexes = [s["hex"] for s in strips[0]["data"]["swatches"]]
        self.assertEqual(hexes, ["#1B3A4B"])
        _seed_swatches([("BELT TECH", "Deep Sea", "#1B3A4B"),
                        ("BELT TECH", "Signal Blue", "#3E7CB1")])
        strips = [e for e in looks.dressed(stored)["dress"]
                  if e["kind"] == "SWATCH_STRIP"]
        hexes = [s["hex"] for s in strips[0]["data"]["swatches"]]
        self.assertIn("#3E7CB1", hexes,
                      "a swatch added after set_look must appear — no "
                      "staleness bookkeeping")

    def test_readiness_judges_dress_geometry_but_never_dress_content(self):
        # A 3840×2160 take that exactly fills its slot goes SHORT once a
        # look shrinks the panel area — honesty about what ships. But the
        # blocked list must only ever name slots, never dress.
        rec = self._board(2)
        self.assertTrue(sheet.readiness(rec)["ready"])
        looks.set_look(rec["sheet_id"], "ART_BOARD")
        d = looks.dressed(sheet.get_sheet(rec["sheet_id"]))
        for e in sheet.readiness(d)["blocked"]:
            self.assertIn("slot_id", e,
                          f"dress must never add blocked entries: {e}")


class InkTests(LooksHomeTest):
    def test_swatch_cells_are_painted_with_their_hex(self):
        rec = self._board(1)
        _seed_swatches([("BELT TECH", "Signal Blue", "#3E7CB1")])
        looks.set_look(rec["sheet_id"], "ART_BOARD",
                       {"atmosphere": False})
        d = looks.dressed(sheet.get_sheet(rec["sheet_id"]))
        img = sheet_render.render_sheet(d, 0.25, allow_letterbox=True)
        colors = {c for _, c in img.getcolors(maxcolors=2 ** 20) or []}
        self.assertIn((0x3E, 0x7C, 0xB1), colors,
                      "the swatch cell must carry its exact hex")
        self.assertEqual(
            img.getpixel((2, 2)),
            sheet_render.STYLE_INK["ART_BOARD"]["paper"],
            "the ground must be the look's paper")

    def test_export_renders_the_dressed_sheet(self):
        rec = self._board(1)
        _seed_swatches([("BELT TECH", "Signal Blue", "#3E7CB1")])
        looks.set_look(rec["sheet_id"], "ART_BOARD")
        out = sheet_render.export_sheet(rec["sheet_id"], "png")
        from PIL import Image
        with Image.open(out) as img:
            self.assertEqual(
                img.getpixel((4, 4)),
                sheet_render.STYLE_INK["ART_BOARD"]["paper"])
        # the stored sheet is untouched — the look never bakes in
        self.assertEqual(sheet.get_sheet(rec["sheet_id"])["style"], "INK")

    def test_assembled_record_carries_the_look(self):
        rec = self._board(2)
        sheet.set_arrangement(rec["sheet_id"], {"rows": [
            {"h": 1, "cols": [{"w": 0.5, "cells": [{"id": "P1", "h": 1}]},
                              {"w": 0.5, "cells": [{"id": "P2", "h": 1}]}]},
        ]})
        looks.set_look(rec["sheet_id"], "TECH_DESIGN")
        paths.SPEC_LOCKS.write_text(json.dumps(
            {"SPEC-0001": {"hash": "t", "approved_at": store.utcnow()}}),
            encoding="utf-8")
        board = assemble.assemble_board("SPEC-0001", 1920, 1080)
        self.assertEqual(board["look"]["key"], "TECH_DESIGN")


class LookApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-looks-api-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)

    def tearDown(self):
        appmain.ACCESS_TOKEN = ""
        _restore_home()

    def _board(self):
        _write_spec(panels=[{"id": "P1", "title": "T1"}])
        _write_candidate("SPEC-0001", "CAND-0001", "P1")
        return sheet.arrange_board("SPEC-0001")

    def test_looks_catalog_is_served_and_never_captured_as_an_id(self):
        r = self.client.get("/api/sheets/looks")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([c["key"] for c in r.json()],
                         ["ART_BOARD", "TECH_DESIGN"])
        self.assertIn("palette_strip", r.json()[0]["options"])

    def test_put_look_persists_and_null_clears(self):
        rec = self._board()
        sid = rec["sheet_id"]
        r = self.client.put(f"/api/sheets/{sid}/look",
                            json={"key": "ART_BOARD",
                                  "options": {"materials": True}})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["look"]["options"]["materials"])
        r = self.client.put(f"/api/sheets/{sid}/look", json={"key": None})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("look", r.json())
        bad = self.client.put(f"/api/sheets/{sid}/look",
                              json={"key": "NOPE"})
        self.assertEqual(bad.status_code, 422)

    def test_render_look_override_never_persists(self):
        rec = self._board()
        sid = rec["sheet_id"]
        before = copy.deepcopy(sheet.get_sheet(sid))
        r = self.client.post(f"/api/sheets/{sid}/render",
                             json={"scale": 0.1,
                                   "look": {"key": "TECH_DESIGN"}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "image/png")
        self.assertEqual(sheet.get_sheet(sid), before,
                         "a preview override must never write")
        # and {"look": null} previews the naked sheet even when one is set
        looks.set_look(sid, "ART_BOARD")
        r = self.client.post(f"/api/sheets/{sid}/render",
                             json={"scale": 0.1, "look": None})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sheet.get_sheet(sid)["look"]["key"], "ART_BOARD")

    def test_readiness_endpoint_judges_the_dressed_sheet(self):
        rec = self._board()
        sid = rec["sheet_id"]
        base = self.client.get(f"/api/sheets/{sid}/readiness").json()
        self.assertTrue(base["ready"])
        looks.set_look(sid, "ART_BOARD")
        dressed_gate = self.client.get(f"/api/sheets/{sid}/readiness").json()
        want = sheet.readiness(looks.dressed(sheet.get_sheet(sid)))
        self.assertEqual(dressed_gate["ready"], want["ready"],
                         "the endpoint and the export gate must agree")


if __name__ == "__main__":
    unittest.main()
