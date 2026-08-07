"""Color swatches (NON-CANON widget, user-directed 2026-08-05): the
swatch reference endpoint renders pure solid pixels with the facts in the
notes; proposal parsing is strict; generation is gated on a saved Bible;
the mock engine derives groups from the Bible's own design languages.
All against a throwaway home."""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app import autofill, wizard  # noqa: E402
import app.main as appmain  # noqa: E402
from tests.test_app_api import _redirect_home, _restore_home  # noqa: E402

BIBLE = """# Demo — Locked Art Direction Bible

## Status
authoritative.

## Rendering Language
### Required
- gouache
### Avoid
- chrome

## Design Languages

## The Belt Miners
Keywords: miners, rig
**Design language:** rust-eaten hull plate, patched not replaced
- sodium practicals in the dig galleries

## Helion Corporate
Keywords: helion, corporate
**Design language:** surfaces that have never been touched
- brand color on every leased object

## Lighting Language
- hard single-source key
"""


class SwatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-swatch-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)
        self.client.post("/api/projects", json={"name": "Swatch Demo"})

    def tearDown(self):
        _restore_home()

    # ---- the swatch reference -------------------------------------------

    def test_swatch_is_a_solid_color_reference(self):
        r = self.client.post("/api/references/swatch",
                             json={"hex": "#8a4b2e", "name": "Oxide Rust",
                                   "cite": "rust-eaten hull plate",
                                   "approve": True})
        self.assertEqual(r.status_code, 200, r.text)
        ref = r.json()
        self.assertEqual(ref["role"], "COLOR_PALETTE")
        self.assertEqual(ref["status"], "APPROVED")
        self.assertIn("OXIDE RUST", ref["notes"])
        self.assertIn("#8A4B2E", ref["notes"])
        self.assertIn("rust-eaten", ref["notes"])
        img = Image.open(io.BytesIO(
            self.client.get(f"/api/references/{ref['id']}/image").content))
        self.assertEqual(img.convert("RGB").getpixel((10, 10)), (0x8A, 0x4B, 0x2E))
        self.assertEqual(img.convert("RGB").getpixel((630, 390)), (0x8A, 0x4B, 0x2E))

    def test_value_key_pair_renders_two_halves(self):
        r = self.client.post("/api/references/swatch",
                             json={"hex": "#D8D3C4", "pair_hex": "#5A564A"})
        self.assertEqual(r.status_code, 200, r.text)
        ref = r.json()
        self.assertEqual(ref["status"], "PROVISIONAL",
                         "no approve flag -> lands provisional")
        img = Image.open(io.BytesIO(
            self.client.get(f"/api/references/{ref['id']}/image").content)).convert("RGB")
        self.assertEqual(img.getpixel((10, 200)), (0xD8, 0xD3, 0xC4))
        self.assertEqual(img.getpixel((630, 200)), (0x5A, 0x56, 0x4A))

    def test_bad_hex_is_a_stated_422(self):
        for bad in ("", "#8a4b2", "red", "#8a4b2ezz"):
            r = self.client.post("/api/references/swatch", json={"hex": bad})
            self.assertEqual(r.status_code, 422, bad)

    # ---- hero, through the route (PALETTE_GROUPS_PLAN §4) ---------------

    def a_swatch(self, lang, name, hexv):
        r = self.client.post("/api/references/swatch",
                             json={"hex": hexv, "name": name, "approve": True})
        ref = r.json()
        # give it a language segment the way a proposal does
        from app import store
        store.update_reference_notes(
            {ref["id"]: f"{lang} · {name.upper()} · {hexv.upper()} · a label"})
        return ref["id"]

    def test_hero_route_sets_and_moves_the_mark(self):
        a = self.a_swatch("RESISTANCE", "A", "#111111")
        b = self.a_swatch("RESISTANCE", "B", "#222222")
        r = self.client.post(f"/api/references/{a}/hero")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["language"], "RESISTANCE")
        r = self.client.post(f"/api/references/{b}/hero")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["cleared"], [a])
        refs = {x["id"]: x["notes"] for x in self.client.get("/api/references").json()}
        self.assertFalse(refs[a].endswith("HERO"))
        self.assertTrue(refs[b].endswith("HERO"))

    def test_hero_on_a_non_swatch_is_a_stated_400(self):
        from app import store, wizard as wz
        ref = store.add_reference("car.png", wz.render_swatch_png("#111111"),
                                  "VEHICLE_GEOMETRY", [], [], "a car")
        r = self.client.post(f"/api/references/{ref['id']}/hero")
        self.assertEqual(r.status_code, 400)
        self.assertIn("swatch", r.json()["detail"])

    def test_hero_on_an_unknown_reference_is_404(self):
        self.assertEqual(self.client.post("/api/references/REF-9999/hero").status_code, 404)

    # ---- proposal parsing ------------------------------------------------

    def test_parse_clamps_and_drops_bad_hexes(self):
        text = """```json
        [{"language": "The Belt Miners", "swatches": [
            {"name": "ok", "hex": "8a4b2e", "cite": "c"},
            {"name": "bad", "hex": "nope", "cite": "c"},
            {"name": "pair", "hex": "#D8D3C4", "pair_hex": "#5A564A", "cite": "c"}]},
         {"language": "Empty", "swatches": [{"hex": "zz"}]}]
        ```"""
        groups = wizard.parse_swatch_proposals(text)
        self.assertEqual(len(groups), 1, "the all-bad group vanishes")
        self.assertEqual([s["hex"] for s in groups[0]["swatches"]],
                         ["#8A4B2E", "#D8D3C4"])
        self.assertEqual(groups[0]["swatches"][1]["pair_hex"], "#5A564A")

    def test_parse_refuses_garbage(self):
        for garbage in ("", "no json here", "[]", '[{"language": "x", "swatches": []}]'):
            with self.assertRaises(autofill.AutofillError):
                wizard.parse_swatch_proposals(garbage)

    # ---- generation gates and the mock path ------------------------------

    def test_generation_without_a_bible_is_a_stated_409(self):
        r = self.client.post("/api/wizard/swatches", json={"provider": "mock"})
        self.assertEqual(r.status_code, 409)
        self.assertIn("Bible", r.json()["detail"])

    def test_mock_groups_come_from_the_bibles_design_languages(self):
        import os
        os.environ["SCREENBOARD_DEBUG_TOOLS"] = "1"
        self.addCleanup(os.environ.pop, "SCREENBOARD_DEBUG_TOOLS", None)
        self.client.put("/api/style-bible", json={"text": BIBLE})
        self.client.post("/api/settings", json={"debug_mock": True})
        r = self.client.post("/api/wizard/swatches", json={"provider": "mock"})
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        langs = [g["language"] for g in data["groups"]]
        self.assertIn("The Belt Miners", langs)
        self.assertIn("Helion Corporate", langs)
        for g in data["groups"]:
            for s in g["swatches"]:
                self.assertTrue(s["name"].startswith("MOCK "),
                                "mock proposals must be MOCK-stamped")
                self.assertRegex(s["hex"], r"^#[0-9A-F]{6}$")
                self.assertTrue(s["cite"])
                self.assertTrue(s["ref_id"].startswith("REF-"),
                                "D8: every proposal persists as a reference")
        self.assertEqual(data["model"], "mock/static-content")
        # D8 ruling: proposals are PROVISIONAL refs with provenance, and a
        # rejection is a status record — a judgement the product keeps.
        total = sum(len(g["swatches"]) for g in data["groups"])
        refs = self.client.get("/api/references").json()
        pend = [x for x in refs if x.get("source") == "swatch-proposal"]
        self.assertEqual(len(pend), total)
        self.assertTrue(all(x["status"] == "PROVISIONAL" for x in pend))
        first = pend[0]["id"]
        r2 = self.client.post(f"/api/references/{first}/status",
                              json={"status": "REJECTED",
                                    "reason": "swatch proposal rejected in review"})
        self.assertEqual(r2.status_code, 200, r2.text)
        again = {x["id"]: x for x in self.client.get("/api/references").json()}
        self.assertEqual(again[first]["status"], "REJECTED")


class PreviewRenderTests(unittest.TestCase):
    """The studio's side of the door preview (S1). It is the customer's
    artwork, so the endpoint sits behind the workspace token like
    everything else — never auth-exempt."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-preview-"))
        _redirect_home(self.tmp)
        self.addCleanup(_restore_home)
        self.client = TestClient(appmain.app)
        self.client.post("/api/projects", json={"name": "The Oxcart"})

    def test_it_is_not_in_the_auth_exempt_set(self):
        """An open endpoint would publish a customer's approved artwork
        to anyone who guessed the subdomain."""
        self.assertNotIn("/api/preview-render", appmain._AUTH_EXEMPT)

    def test_no_approved_panels_is_a_stated_empty(self):
        r = self.client.get("/api/preview-render")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["found"])
        self.assertEqual(r.json()["production"], "The Oxcart",
                         "'looked and found none' still names the studio")

    def test_an_approved_panel_is_returned_with_its_identity(self):
        from app import generate, paths, store as appstore
        spec = {"specification_id": "BOARD-0001", "subject": "diner",
                "mode": "CANON_EXTRACTION", "panels": [{"id": "P01"}]}
        appstore.create_spec_from_dict(spec)
        d = paths.BOARDS_DIR / "BOARD-0001"
        d.mkdir(parents=True, exist_ok=True)
        import json as _json
        for cid, status in (("CAND-0001", "REJECTED"), ("CAND-0002", "APPROVED")):
            (d / f"{cid}.json").write_text(_json.dumps({
                "candidate_id": cid, "status": status}), encoding="utf-8")
        r = self.client.get("/api/preview-render")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body["found"])
        self.assertEqual(body["candidate"], "CAND-0002",
                         "only APPROVED work goes on the door")
        self.assertEqual(body["board"], "BOARD-0001")
        self.assertEqual(body["production"], "The Oxcart")
        self.assertIn("/api/specs/BOARD-0001/candidates/CAND-0002/image",
                      body["image"])
        self.assertEqual(body["count"], 1)


if __name__ == "__main__":
    unittest.main()
