"""A key the provider does not recognise reads "That is not a valid key."

User-hit 2026-10-04, in the connect-a-key modal: the previous error
message was still on the clipboard, got pasted as the key, and Test
answered with OpenAI's raw 401 body — `OpenAI refused it: openai
connection failed: Error code: 401 - {'error': {'message': "Incorrect API
key provided: OpenAI r****nai'..."` — which echoed the bad key back and
told the user nothing they could act on. The ruling: "That needs a
graceful error message, 'That is not a valid key'."

Two halves. A value no provider could have issued (whitespace, non-ASCII)
is refused before any call, on Test AND Save. A key the provider answers
"not one of mine" to — OpenAI 401, Gemini's 400 API_KEY_INVALID,
Anthropic's 401 — becomes the same sentence naming the provider. A
failure that is NOT the key's fault (network, quota, missing model) keeps
its own message; calling those "not a valid key" would send the user to
re-paste a key that was fine.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient  # noqa: E402

from app import generate, narrative  # noqa: E402
import app.main as appmain  # noqa: E402
from test_app_api import _redirect_home, _restore_home  # noqa: E402

PASTED_ERROR = ("OpenAI refused it: openai connection failed: "
                "No module named 'openai'")


class _OpenAIAuthError(Exception):
    """The shape of openai.AuthenticationError: a status_code, and a body
    that echoes the key."""
    status_code = 401


class _GeminiClientError(Exception):
    """The shape of google.genai.errors.ClientError for a bad key: 400,
    with the reason in the body."""
    code = 400


class NotAValidKey(unittest.TestCase):
    def setUp(self):
        _redirect_home(Path(tempfile.mkdtemp(prefix="sb-key-")))
        self.client = TestClient(appmain.app)

    def tearDown(self):
        _restore_home()

    def probe(self, provider="openai", key="sk-proj-abc123", raises=None):
        def fake(p, k):
            if raises:
                raise raises
            return {"ok": True, "provider": p, "model": "m"}
        with mock.patch.object(generate, "test_connection", side_effect=fake) as tc:
            r = self.client.post("/api/settings/test",
                                 json={"provider": provider, "key": key})
        return r, tc

    # -- refused before any call ------------------------------------------

    def test_a_pasted_error_message_is_not_sent_anywhere(self):
        r, tc = self.probe(key=PASTED_ERROR)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"], "That is not a valid key.")
        tc.assert_not_called()

    def test_save_refuses_it_too_and_keeps_nothing(self):
        r = self.client.post("/api/settings",
                             json={"openai_api_key": PASTED_ERROR})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"], "That is not a valid key.")
        s = self.client.get("/api/settings").json()
        self.assertFalse(s["openai_api_key_set"])

    def test_clearing_a_key_is_still_allowed(self):
        self.client.post("/api/settings", json={"openai_api_key": "sk-proj-abc"})
        r = self.client.post("/api/settings", json={"openai_api_key": ""})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["openai_api_key_set"])

    def test_real_key_shapes_are_not_malformed(self):
        for k in ("sk-proj-Ab3_x-9", "AIzaSyD-abc_123", "sk-ant-api03-xyz",
                  "  sk-padded-by-the-clipboard  ", ""):
            self.assertFalse(generate.malformed_key(k), k)
        for k in (PASTED_ERROR, "sk-abc def", "sk-—dash", "sk-abc\tdef"):
            self.assertTrue(generate.malformed_key(k), k)

    # -- the provider's own refusal ----------------------------------------

    def test_openai_401_becomes_the_sentence_and_does_not_echo_the_key(self):
        err = _OpenAIAuthError("Error code: 401 - {'error': {'message': "
                               "\"Incorrect API key provided: sk-proj-******123.\"")
        r, _ = self.probe(raises=err)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"],
                         "That is not a valid key — OpenAI did not accept it.")
        self.assertNotIn("sk-proj", r.text)

    def test_gemini_api_key_invalid_becomes_the_sentence(self):
        err = _GeminiClientError("400 INVALID_ARGUMENT. {'error': {'message': "
                                 "'API key not valid. Please pass a valid API key.', "
                                 "'details': [{'reason': 'API_KEY_INVALID'}]}}")
        r, _ = self.probe(provider="gemini", key="AIzaSyD-abc", raises=err)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"],
                         "That is not a valid key — Gemini did not accept it.")

    def test_anthropic_401_through_the_real_test_path(self):
        def refuse(*a, **k):
            raise urllib.error.HTTPError(narrative.ANTHROPIC_API, 401,
                                         "Unauthorized", None, None)
        with mock.patch.object(narrative, "_http_json", side_effect=refuse):
            r = self.client.post("/api/settings/test",
                                 json={"provider": "anthropic", "key": "sk-ant-x"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"],
                         "That is not a valid key — Anthropic did not accept it.")

    def test_a_stored_key_records_the_sentence_not_the_body(self):
        self.client.post("/api/settings", json={"openai_api_key": "sk-proj-abc123"})
        err = _OpenAIAuthError("Incorrect API key provided: sk-proj-******123")
        r, _ = self.probe(key="", raises=err)
        self.assertEqual(r.status_code, 400)
        last = self.client.get("/api/settings").json()["engines"]["openai"]["last_test"]
        self.assertFalse(last["ok"])
        self.assertEqual(last["detail"],
                         "That is not a valid key — OpenAI did not accept it.")

    # -- not the key's fault: keeps its own message ------------------------

    def test_a_network_failure_is_not_called_a_bad_key(self):
        r, _ = self.probe(raises=ConnectionError("Connection refused"))
        self.assertEqual(r.status_code, 502)
        self.assertNotIn("not a valid key", r.json()["detail"])

    def test_a_quota_refusal_is_not_called_a_bad_key(self):
        class _Quota(Exception):
            status_code = 429
        r, _ = self.probe(raises=_Quota("insufficient_quota"))
        self.assertEqual(r.status_code, 502)
        self.assertNotIn("not a valid key", r.json()["detail"])


class TheModalShowsTheSentenceAsIs(unittest.TestCase):
    def test_a_400_is_not_prefixed_with_the_providers_refusal(self):
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        i = js.index('await api("/api/settings/test", {\n          method: "POST", json: { provider: P.test, key: k } });')
        catch = js[i:i + 2500]
        self.assertIn("err.status === 400 ? err.message", catch)


if __name__ == "__main__":
    unittest.main()
