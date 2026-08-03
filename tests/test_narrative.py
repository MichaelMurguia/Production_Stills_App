"""F6 backend (narrative via OpenRouter/Claude): the narrative role runs
on the stored Anthropic key or the OpenRouter connection — dispatch,
gating, settings surface, and the test endpoint, all with fake HTTP."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient  # noqa: E402

from app import autofill, connectors, generate, narrative, wizard  # noqa: E402
import app.main as appmain  # noqa: E402

from test_app_api import _redirect_home, _restore_home  # noqa: E402

DRAFT_JSON = {"subject": "Test board", "board_type": "LOCATION",
              "setting": {"int_ext": "INT", "location": "CABIN"},
              "scene": "A cabin.", "render_intent": "painterly",
              "panels": [{"id": "P01", "title": "Cabin", "purpose": "see it",
                          "required_objects": ["cabin"],
                          "scale": "WIDE", "allocation_percent": 100}],
              "evidence_ledger": [{"panel_id": "P01", "object": "cabin",
                                   "evidence_class": "SCRIPT_EXPLICIT",
                                   "source": "sc. 1", "confidence": 0.9,
                                   "status": "PASS", "rationale": "stated"}]}


def fake_anthropic(url, method="GET", headers=None, body=None, timeout=0):
    if url.endswith("/models"):
        return {"data": [{"id": "claude-sonnet-5"}]}
    return {"content": [{"type": "text", "text": json.dumps(DRAFT_JSON)}]}


def fake_openrouter(url, method="GET", headers=None, body=None, timeout=0):
    return {"choices": [{"message": {"content": json.dumps(DRAFT_JSON)}}]}


class NarrativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-narr-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)

    def tearDown(self):
        _restore_home()

    def _save_anthropic(self):
        r = self.client.post("/api/settings",
                             json={"anthropic_api_key": "sk-ant-test"})
        self.assertEqual(r.status_code, 200)
        return r.json()

    def _connect_openrouter(self):
        state = connectors.load_state()
        state.setdefault("openrouter", {})["key"] = "sk-or-test"
        connectors.save_state(state)

    # -- availability & gating --------------------------------------------

    def test_choices_follow_credentials(self):
        self.assertEqual(autofill.narrative_choices(), {"gemini", "openai"})
        self._save_anthropic()
        self.assertIn("anthropic", autofill.narrative_choices())
        self._connect_openrouter()
        self.assertIn("openrouter", autofill.narrative_choices())

    def test_autofill_rejects_unavailable_narrative_provider(self):
        self.client.put("/api/style-bible", json={"text": "## L\nx\n"})
        r = self.client.post("/api/specs/autofill", json={
            "specification_id": "NARR_V001", "prompt": "the cabin",
            "provider": "anthropic"})
        self.assertEqual(r.status_code, 422)

    def test_complete_without_key_is_stated(self):
        with self.assertRaises(narrative.NarrativeError):
            narrative.anthropic_complete(b"doc", "text/plain", "x")
        with self.assertRaises(narrative.NarrativeError):
            narrative.openrouter_complete(b"doc", "text/plain", "x")

    # -- dispatch ----------------------------------------------------------

    def test_anthropic_draft_parses_json(self):
        self._save_anthropic()
        with mock.patch.object(narrative, "_http_json", fake_anthropic):
            draft, model = autofill._draft("anthropic", b"INT. CABIN - DAY",
                                           "text/plain", "instructions")
        self.assertEqual(draft["subject"], "Test board")
        self.assertEqual(model, "claude-sonnet-5")

    def test_openrouter_draft_parses_json(self):
        self._connect_openrouter()
        with mock.patch.object(connectors, "_http_json", fake_openrouter):
            draft, model = autofill._draft("openrouter", b"INT. CABIN - DAY",
                                           "text/plain", "instructions")
        self.assertEqual(draft["panels"][0]["id"], "P01")
        self.assertIn("OpenRouter", model)

    def test_openrouter_refuses_image_only_pdfs_stated(self):
        self._connect_openrouter()
        with self.assertRaises(narrative.NarrativeError) as cm:
            narrative.openrouter_complete(b"%PDF", "application/pdf", "x")
        self.assertIn("image-only", str(cm.exception))

    def test_bible_draft_via_anthropic(self):
        self._save_anthropic()
        md = "## Rendering Language\nGouache. MOCKLESS.\n"

        def bible_http(url, method="GET", headers=None, body=None, timeout=0):
            return {"content": [{"type": "text", "text": md}]}
        with mock.patch.object(narrative, "_http_json", bible_http), \
             mock.patch.object(autofill, "_screenplay_bytes",
                               return_value=(b"INT. CABIN", "text/plain")):
            out = wizard.draft_bible({}, provider="anthropic")
        self.assertIn("## Rendering Language", out["markdown"])
        self.assertEqual(out["model"], "claude-sonnet-5")

    # -- settings surface --------------------------------------------------

    def test_settings_surface_and_role_persistence(self):
        s = self._save_anthropic()
        self.assertTrue(s["engines"]["anthropic"]["configured"])
        self.assertEqual(s["narrative_provider"], "openai")
        s = self.client.post("/api/settings",
                             json={"narrative_provider": "anthropic"}).json()
        self.assertEqual(s["narrative_provider"], "anthropic")
        self.assertEqual(self.client.post(
            "/api/settings",
            json={"narrative_provider": "or:not-a-thing"}).status_code, 422)

    def test_test_endpoint_records_anthropic(self):
        self._save_anthropic()
        with mock.patch.object(narrative, "_http_json", fake_anthropic):
            r = self.client.post("/api/settings/test",
                                 json={"provider": "anthropic"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["model"], "claude-sonnet-5")
        eng = self.client.get("/api/settings").json()["engines"]["anthropic"]
        self.assertTrue(eng["last_test"]["ok"])

if __name__ == "__main__":
    unittest.main()
