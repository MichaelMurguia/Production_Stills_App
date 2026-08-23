"""Debug tools (user request 2026-08-03): the mock engine — the whole
pipeline scan → bible → breakdown → panels → board on static content,
zero model calls — and the page-text override store."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app import generate, paths  # noqa: E402
import app.main as appmain  # noqa: E402

from test_app_api import _redirect_home, _restore_home  # noqa: E402

SCREENPLAY = """FADE IN:

INT. LUNCHEONETTE - DAY

AUGIE sits at the counter. Chrome and formica. A milkshake machine hums.

AUGIE
Nobody ever leaves this town.

WAITRESS
More coffee?

AUGIE
Nobody ever leaves this town.

EXT. DESERT CRATER - NIGHT

Stars. A fenced crater. AUGIE stands at the rim.

AUGIE
There it is.

WAITRESS
(from far away)
Closing time.

INT. LUNCHEONETTE - NIGHT

Empty booths. AUGIE alone with cold coffee.

AUGIE
One more cup.

FADE OUT.
"""


class DebugToolsBase(unittest.TestCase):
    def setUp(self):
        import os
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-debug-"))
        _redirect_home(self.tmp)
        # Debug tools are owner-linked: they exist only where this env
        # flag is set (the owner's machines / owner-provisioned studios).
        os.environ["SCREENBOARD_DEBUG_TOOLS"] = "1"
        self.addCleanup(lambda: os.environ.pop("SCREENBOARD_DEBUG_TOOLS", None))
        # The SHIPPED text layer is a real file in source (2026-08-23). Point
        # it at the throwaway home too, or these assertions start reading
        # whatever copy the product has actually published.
        shipped = self.tmp / "ui_text.json"
        real = appmain._shipped_text_path
        appmain._shipped_text_path = lambda: shipped
        self.addCleanup(lambda: setattr(appmain, "_shipped_text_path", real))
        self.client = TestClient(appmain.app)

    def tearDown(self):
        _restore_home()

    def _enable_mock(self):
        r = self.client.post("/api/settings", json={"debug_mock": True})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()


class MockEngineTests(DebugToolsBase):
    def test_toggle_gates_the_provider_everywhere(self):
        s = self.client.get("/api/settings").json()
        self.assertNotIn("mock", s["engines"])
        self.assertNotIn("mock", s["providers"])
        s = self._enable_mock()
        self.assertTrue(s["engines"]["mock"]["configured"])
        self.assertIn("MOCK", s["providers"]["mock"])
        # Off again: gone, and never left selected as the preferred engine.
        self.client.post("/api/settings", json={"preferred_provider": "mock"})
        s = self.client.post("/api/settings", json={"debug_mock": False}).json()
        self.assertNotIn("mock", s["providers"])
        self.assertNotEqual(s["preferred_provider"], "mock")

    def test_mock_refused_while_toggle_is_off(self):
        # A disabled debug engine must not be reachable by API guessing.
        # (Bible saved first so the provider gate, not the 423 production-
        # design gate, is what answers.)
        self.client.put("/api/style-bible", json={"text": "## L\nx\n"})
        r = self.client.post("/api/specs/autofill", json={
            "specification_id": "OFF_V001", "prompt": "x", "provider": "mock"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("provider", r.json()["detail"])

    def test_full_pipeline_at_zero_cost(self):
        """Scan → bible → breakdown → lock → panels → board, no model."""
        self._enable_mock()
        r = self.client.post("/api/screenplay", files={
            "file": ("mock_test.txt", SCREENPLAY.encode(), "text/plain")})
        self.assertEqual(r.status_code, 200, r.text)

        # Scene Scan: real sluglines, stamped MOCK, nothing billed.
        r = self.client.post("/api/wizard/analyze", json={"provider": "mock"})
        self.assertEqual(r.status_code, 200, r.text)
        analysis = r.json()
        self.assertEqual(analysis["model"], "mock/static-content")
        self.assertIn("MOCK", analysis["logline"])
        env_locs = [l for e in analysis["environments"] for l in e["locations"]]
        self.assertIn("LUNCHEONETTE", env_locs)
        self.assertIn("DESERT CRATER", env_locs)
        self.assertTrue(any(s["name"] == "Augie"
                            for s in analysis["subjects"]))

        # Bible draft: parses into the real section grammar, answers BIND.
        r = self.client.post("/api/wizard/draft-bible", json={
            "provider": "mock",
            "answers": {"medium": "gouache on board",
                        "touchstones": "1950s postcards"}})
        self.assertEqual(r.status_code, 200, r.text)
        md = r.json()["markdown"]
        self.assertIn("## Rendering Language", md)
        self.assertIn("gouache on board", md)
        self.assertIn("MOCK", md)
        self.assertEqual(self.client.put("/api/style-bible",
                                         json={"text": md}).status_code, 200)

        # Breakdown research pass: cites real sluglines, locks cleanly.
        r = self.client.post("/api/specs/autofill", json={
            "specification_id": "MOCKFLOW_V001", "provider": "mock",
            "prompt": "the luncheonette across its scenes"})
        self.assertEqual(r.status_code, 200, r.text)
        spec = r.json()
        self.assertIn("MOCK", spec["subject"])
        # The mock cites the real slugline, so every row SURVIVES the
        # citation verification added 2026-08-17 (review F21) rather than
        # demoting to WEAK_INFERENCE/HOLD and blocking the lock. The honesty
        # stamp lives in rationale; source is evidence, not a disclaimer.
        self.assertTrue(all("MOCK" in row["rationale"]
                            for row in spec["evidence_ledger"]))
        self.assertTrue(all(row["evidence_class"] == "SCRIPT_EXPLICIT"
                            and row["status"] == "PASS"
                            for row in spec["evidence_ledger"]),
                        "the mock must cite lines the screenplay really has")
        self.assertEqual(spec["citations"]["demoted"], 0)
        r = self.client.post("/api/specs/MOCKFLOW_V001/approve")
        self.assertEqual(r.status_code, 200, r.text)

        # Panels: one 4K mock take per panel, stamped, then approved.
        for p in spec["panels"]:
            r = self.client.post(
                f"/api/specs/MOCKFLOW_V001/panels/{p['id']}/generate",
                json={"provider": "mock", "image_size": "4K",
                      "aspect_ratio": "16:9"})
            self.assertEqual(r.status_code, 200, r.text)
            cand = r.json()
            self.assertEqual(cand["provider"], "mock")
            self.assertIn("no cost", cand["model_notes"].lower())
            self.assertEqual((cand["width"], cand["height"]), (3840, 2160))
            self.assertEqual(self.client.post(
                f"/api/specs/MOCKFLOW_V001/candidates/{cand['candidate_id']}/status",
                json={"status": "APPROVED"}).status_code, 200)

        # Board: slot map ready, assembly records the structural contract.
        sm = self.client.get("/api/specs/MOCKFLOW_V001/slot-map").json()
        self.assertTrue(sm["ready"], sm["not_ready"])
        b = self.client.post("/api/specs/MOCKFLOW_V001/assemble", json={})
        self.assertEqual(b.status_code, 200, b.text)
        board = b.json()
        self.assertEqual(set(board["rects"]), {p["id"] for p in spec["panels"]})
        img = paths.BOARDS_DIR / "MOCKFLOW_V001" / f"{board['candidate_id']}.png"
        with Image.open(img) as im:
            self.assertEqual(im.size, (3840, 2160))

    def test_mock_render_stamps_and_sizes(self):
        self._enable_mock()
        from app import mockflow
        out = self.tmp / "probe.png"
        notes = mockflow.render("test prompt", [], "2K", "4:3", out)
        self.assertIn("no cost", notes.lower())
        with Image.open(out) as im:
            self.assertEqual(im.size, (2560, 1920))


class OwnerGateTests(DebugToolsBase):
    """Without the env flag — every customer install — the tools do not
    exist: no tab data, no endpoints, no mock provider, even if a
    settings file claims debug_mock."""

    def test_everything_404s_without_the_flag(self):
        import os
        self._enable_mock()  # owner turns it on…
        os.environ.pop("SCREENBOARD_DEBUG_TOOLS", None)  # …customer install
        s = self.client.get("/api/settings").json()
        self.assertFalse(s["debug_tools"])
        self.assertNotIn("mock", s["providers"])
        self.assertNotIn("mock", s["engines"])
        self.assertEqual(self.client.post(
            "/api/settings", json={"debug_mock": True}).status_code, 404)
        # The READ is deliberately open (2026-08-23): the shipped layer is
        # published product copy and every studio renders it, debug tools or
        # not. Only the WRITES are owner-gated.
        self.assertEqual(self.client.get(
            "/api/debug/text-overrides").status_code, 200)
        self.assertEqual(self.client.post(
            "/api/debug/text-overrides/publish").status_code, 404)
        self.assertEqual(self.client.put(
            "/api/debug/text-overrides",
            json={"overrides": {}}).status_code, 404)
        self.assertEqual(self.client.delete(
            "/api/debug/text-overrides").status_code, 404)
        self.assertFalse(generate.mock_enabled(),
                         "a smuggled settings flag must not resurrect mock")


class TextOverrideTests(DebugToolsBase):
    def test_roundtrip_and_clear(self):
        r = self.client.get("/api/debug/text-overrides")
        self.assertEqual(r.json(), {"overrides": {}, "shipped": {}, "local": {}})
        r = self.client.put("/api/debug/text-overrides", json={
            "overrides": {"Approve board": "Sign off wall",
                          "  ": "never stored"}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["overrides"],
                         {"Approve board": "Sign off wall"})
        self.assertEqual(
            self.client.get("/api/debug/text-overrides").json()["overrides"],
            {"Approve board": "Sign off wall"})
        self.assertEqual(
            self.client.delete("/api/debug/text-overrides").status_code, 200)
        self.assertEqual(
            self.client.get("/api/debug/text-overrides").json()["overrides"], {})

    def test_a_clear_does_not_take_published_copy_with_it(self):
        """Clear empties this install's scratchpad. Published copy is
        removed by publishing its removal — otherwise one studio's tidy-up
        would look like the fleet losing its wording."""
        self.client.put("/api/debug/text-overrides",
                        json={"overrides": {"Approve board": "Sign off wall"}})
        self.assertTrue(self.client.post(
            "/api/debug/text-overrides/publish").json()["published"])
        r = self.client.delete("/api/debug/text-overrides").json()
        self.assertEqual(r["local"], {})
        self.assertEqual(r["overrides"], {"Approve board": "Sign off wall"})

    def test_put_rejects_non_object(self):
        r = self.client.put("/api/debug/text-overrides",
                            json={"overrides": ["not", "a", "map"]})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
