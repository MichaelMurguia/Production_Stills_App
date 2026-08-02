"""Connector registry, state derivation, filters, enable rules (N1) —
all against a temp install home; no network anywhere in this file."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import connectors, paths


def rec(mid, **kw):
    base = {
        "id": mid, "connector": mid.split(":")[0].replace("or", "openrouter"),
        "provider_model_id": mid.split(":", 1)[1], "label": mid,
        "developer": "OpenAI", "task": "image-to-image", "refs": True,
        "max_refs": 14, "max_px": None, "aspect_enum": None,
        "price_per_image": None, "status": "active", "supported": True,
    }
    base.update(kw)
    return base


class ConnectorStateTests(unittest.TestCase):
    def setUp(self):
        self._home = paths.HOME
        self._tmp = tempfile.TemporaryDirectory()
        paths.HOME = Path(self._tmp.name)

    def tearDown(self):
        paths.HOME = self._home
        self._tmp.cleanup()

    def seed(self, cid="openrouter", **c):
        state = connectors.load_state()
        state[cid] = c
        connectors.save_state(state)
        return state

    def test_not_connected_is_the_only_disconnected_term(self):
        pub = connectors.connector_public("openrouter")
        self.assertEqual(pub["status"], "NOT_CONNECTED")
        self.assertEqual(pub["identity"], "")
        self.assertEqual(pub["model_count"], 0)

    def test_synced_and_masked_key(self):
        self.seed(key="sk-or-abcdef123456", last_sync="2026-08-03T10:00:00Z",
                  catalog=[rec("or:openai/gpt-image-2")], enabled=["or:openai/gpt-image-2"])
        pub = connectors.connector_public("openrouter")
        self.assertEqual(pub["status"], "SYNCED")
        self.assertEqual(pub["enabled_count"], 1)
        self.assertNotIn("abcdef1234", pub["key_hint"])  # masked
        self.assertTrue(pub["key_hint"].startswith("sk-o"))

    def test_auth_error_reads_rejected_network_reads_no_network(self):
        self.seed(key="k", last_error={"kind": "auth", "detail": "401", "at": "x"})
        self.assertEqual(connectors.connector_public("openrouter")["status"], "REJECTED")
        self.seed(key="k", last_error={"kind": "network", "detail": "off", "at": "x"})
        self.assertEqual(connectors.connector_public("openrouter")["status"], "NO_NETWORK")

    def test_failing_key_keeps_cached_catalog_visible(self):
        self.seed(cid="fal", key="k", catalog=[rec("fal:fal-ai/flux-2/dev")],
                  last_error={"kind": "auth", "detail": "401", "at": "x"})
        pub = connectors.connector_public("fal")
        self.assertEqual(pub["status"], "REJECTED")
        self.assertEqual(pub["model_count"], 1)  # cache stays browsable

    def test_enable_disable_and_unsupported_shape(self):
        self.seed(cid="fal", key="k", catalog=[
            rec("fal:fal-ai/flux-2/dev", connector="fal"),
            rec("fal:hgs/soul", connector="fal", supported=False)])
        out = connectors.set_enabled("fal:fal-ai/flux-2/dev", True)
        self.assertTrue(out["enabled"])
        with self.assertRaises(connectors.ConnectorError):
            connectors.set_enabled("fal:hgs/soul", True)
        connectors.set_enabled("fal:fal-ai/flux-2/dev", False)
        self.assertEqual(connectors.enabled_records(), [])

    def test_disconnect_keeps_catalog_and_curation(self):
        self.seed(key="k", identity="you@studio.com",
                  catalog=[rec("or:openai/gpt-image-2")],
                  enabled=["or:openai/gpt-image-2"])
        connectors.disconnect("openrouter")
        pub = connectors.connector_public("openrouter")
        self.assertEqual(pub["status"], "NOT_CONNECTED")
        self.assertEqual(pub["model_count"], 1)
        self.assertEqual(pub["enabled_count"], 1)
        self.assertEqual(pub["identity"], "")

    def test_filters(self):
        records = [
            rec("or:a/one", refs=True, max_px=4096, price_per_image="0.13"),
            rec("or:b/two", refs=False, max_px=2048, price_per_image=None,
                task="text-to-image", label="Style Thing", developer="Krea"),
        ]
        self.assertEqual(len(connectors.filter_records(records, refs_only=True)), 1)
        self.assertEqual(len(connectors.filter_records(records, fourk_only=True)), 1)
        self.assertEqual(len(connectors.filter_records(records, priced_only=True)), 1)
        self.assertEqual(connectors.filter_records(records, query="style")[0]["id"], "or:b/two")
        self.assertEqual(len(connectors.filter_records(records, query="krea")), 1)

    def test_stats_single_source(self):
        self.seed(key="k", catalog=[
            rec("or:a/one", max_px=4096),
            rec("or:b/two", status="deprecated"),
            rec("or:c/three", refs=False, task="text-to-image")],
            enabled=["or:a/one", "or:b/two"])
        s = connectors.stats()
        self.assertEqual(s["total"], 3)
        self.assertEqual(s["enabled"], 2)
        self.assertEqual(s["anchor_refs"], 2)
        self.assertEqual(s["fourk"], 1)
        self.assertEqual(s["deprecated_enabled"], 1)

    def test_dev_tiles(self):
        self.assertEqual(connectors.dev_tile("Black Forest Labs"), "BFL")
        self.assertEqual(connectors.dev_tile("Some New Vendor"), "SNV")
        self.assertEqual(connectors.dev_tile(""), "???")


OR_MODELS = {"data": [
    {"id": "google/gemini-3-pro-image", "name": "Gemini 3 Pro Image",
     "architecture": {"input_modalities": ["text", "image"],
                      "output_modalities": ["image"]},
     "pricing": {"image_output": "0.13"}},
    {"id": "krea/krea-2", "name": "Krea 2",
     "architecture": {"input_modalities": ["text"],
                      "output_modalities": ["image"]},
     "pricing": {}},
]}


class OpenRouterTests(unittest.TestCase):
    def setUp(self):
        self._home = paths.HOME
        self._tmp = tempfile.TemporaryDirectory()
        paths.HOME = Path(self._tmp.name)

    def tearDown(self):
        paths.HOME = self._home
        self._tmp.cleanup()

    @staticmethod
    def fake_http(url, method="GET", headers=None, body=None, timeout=60):
        if url.endswith("/key"):
            return {"data": {"label": "studio key"}}
        if "/models" in url:
            return OR_MODELS
        if url.endswith("/auth/keys"):
            assert body["code"] == "CODE123" and body["code_verifier"]
            return {"key": "sk-or-v1-newkey0000"}
        raise AssertionError(f"unexpected url {url}")

    def test_sync_normalizes_and_sets_identity(self):
        pub = connectors.save_key("openrouter", "sk-or-x", http=self.fake_http)
        self.assertEqual(pub["status"], "SYNCED")
        self.assertEqual(pub["identity"], "studio key")
        recs = connectors.catalog_records()
        gem = next(m for m in recs if m["id"] == "or:google/gemini-3-pro-image")
        self.assertTrue(gem["refs"])
        self.assertEqual(gem["task"], "image-to-image")
        self.assertEqual(gem["max_refs"], connectors.APP_MAX_REFS)
        self.assertEqual(gem["price_per_image"], "0.13")
        self.assertIsNone(gem["max_px"])  # catalog silent — never invented
        krea = next(m for m in recs if m["id"] == "or:krea/krea-2")
        self.assertFalse(krea["refs"])
        self.assertEqual(krea["task"], "text-to-image")
        self.assertIsNone(krea["price_per_image"])  # zero/missing → None

    def test_failed_sync_keeps_last_good_catalog(self):
        connectors.save_key("openrouter", "sk-or-x", http=self.fake_http)

        def dead(url, **kw):
            import urllib.error
            raise urllib.error.URLError("no route")
        pub = connectors.sync("openrouter", http=dead)
        self.assertEqual(pub["status"], "NO_NETWORK")
        self.assertEqual(pub["model_count"], 2)  # cache survives

    def test_pkce_roundtrip(self):
        url = connectors.pkce_start("http://127.0.0.1:8000/connectors/openrouter/callback")
        self.assertIn("openrouter.ai/auth?", url)
        self.assertIn("code_challenge=", url)
        connectors.pkce_finish("CODE123", http=self.fake_http)
        pub = connectors.connector_public("openrouter")
        self.assertEqual(pub["status"], "SYNCED")
        self.assertTrue(pub["key_hint"].startswith("sk-o"))

    def test_generate_decodes_base64_image(self):
        import base64
        png = base64.b64encode(b"fakepngbytes").decode()

        def http(url, method="GET", headers=None, body=None, timeout=60):
            assert body["modalities"] == ["image", "text"]
            return {"choices": [{"message": {"images": [
                {"image_url": {"url": f"data:image/png;base64,{png}"}}]}}]}
        out = Path(self._tmp.name) / "out.png"
        connectors.openrouter_generate("k", "google/gemini-3-pro-image",
                                       "a prompt", [], out, http=http)
        self.assertEqual(out.read_bytes(), b"fakepngbytes")

    def test_generate_refusal_states_itself(self):
        def http(url, **kw):
            return {"choices": [{"message": {"content": "I can't render that."}}]}
        out = Path(self._tmp.name) / "out.png"
        with self.assertRaises(connectors.ConnectorError) as cm:
            connectors.openrouter_generate("k", "m", "p", [], out, http=http)
        self.assertIn("can't render", str(cm.exception))


FAL_PAGE = {"models": [
    {"endpoint_id": "fal-ai/flux-2/dev", "title": "FLUX.2 [dev]",
     "metadata": {"category": "image-to-image"}, "status": "active"},
    {"endpoint_id": "fal-ai/ideogram/v4/turbo", "title": "Ideogram 4 Turbo",
     "metadata": {"category": "text-to-image"}, "status": "active"},
    {"endpoint_id": "higgsfield-ai/soul/standard", "title": "Soul",
     "metadata": {"category": "text-to-image"}, "status": "active"},
], "has_more": False}


class FalTests(unittest.TestCase):
    def setUp(self):
        self._home = paths.HOME
        self._tmp = tempfile.TemporaryDirectory()
        paths.HOME = Path(self._tmp.name)

    def tearDown(self):
        paths.HOME = self._home
        self._tmp.cleanup()

    @staticmethod
    def fake_http(url, method="GET", headers=None, body=None, timeout=60):
        import urllib.error
        if "/requests/00000000" in url:
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        if "api.fal.ai/v1/models" in url:
            return FAL_PAGE
        raise AssertionError(f"unexpected url {url}")

    def test_sync_normalizes_families_and_support(self):
        pub = connectors.save_key("fal", "key_abc", http=self.fake_http)
        self.assertEqual(pub["status"], "SYNCED")
        recs = connectors.catalog_records()
        flux = next(m for m in recs if m["id"] == "fal:fal-ai/flux-2/dev")
        self.assertTrue(flux["refs"] and flux["supported"])
        self.assertEqual(flux["developer"], "Black Forest Labs")
        soul = next(m for m in recs if "soul" in m["id"])
        self.assertFalse(soul["supported"])  # shape not mapped — stated
        self.assertIsNone(flux["price_per_image"])  # fal publishes none

    def test_bad_key_reads_rejected(self):
        import urllib.error

        def http(url, **kw):
            raise urllib.error.HTTPError(url, 401, "no", {}, None)
        pub = connectors.save_key("fal", "bad", http=http)
        self.assertEqual(pub["status"], "REJECTED")

    def test_generate_queue_roundtrip_and_size(self):
        calls = []

        def http(url, method="GET", headers=None, body=None, timeout=60):
            calls.append(url)
            if url.endswith("flux-2/dev") and method == "POST":
                self.assertEqual(body["image_size"], {"width": 3840, "height": 1600})
                return {"request_id": "r1",
                        "status_url": "https://queue.fal.run/s",
                        "response_url": "https://queue.fal.run/r"}
            if url == "https://queue.fal.run/s":
                return {"status": "COMPLETED"}
            if url == "https://queue.fal.run/r":
                import base64
                b = base64.b64encode(b"falimg").decode()
                return {"images": [{"url": f"data:image/png;base64,{b}"}]}
            raise AssertionError(url)
        rec = {"provider_model_id": "fal-ai/flux-2/dev", "label": "FLUX.2 [dev]"}
        out = Path(self._tmp.name) / "o.png"
        connectors.fal_generate("k", rec, "prompt", [], "4K", "2.39:1", out,
                                http=http, sleep=lambda s: None)
        self.assertEqual(out.read_bytes(), b"falimg")

    def test_generate_queue_failure_is_stated(self):
        def http(url, method="GET", headers=None, body=None, timeout=60):
            if method == "POST":
                return {"request_id": "r1", "status_url": "https://queue.fal.run/s",
                        "response_url": "https://queue.fal.run/r"}
            return {"status": "FAILED", "detail": "boom"}
        rec = {"provider_model_id": "fal-ai/flux-2/dev", "label": "FLUX.2 [dev]"}
        with self.assertRaises(connectors.ConnectorError) as cm:
            connectors.fal_generate("k", rec, "p", [], "1K", "1:1",
                                    Path(self._tmp.name) / "o.png",
                                    http=http, sleep=lambda s: None)
        self.assertIn("FAILED", str(cm.exception))

    def test_adopt_record_enables_server_hit(self):
        self_state = connectors.load_state()
        self_state["fal"] = {"key": "k", "catalog": []}
        connectors.save_state(self_state)
        rec = connectors._fal_normalize(
            {"endpoint_id": "fal-ai/recraft/v4", "title": "Recraft v4",
             "metadata": {"category": "text-to-image"}}, "text-to-image")
        connectors.adopt_record(rec)
        out = connectors.set_enabled("fal:fal-ai/recraft/v4", True)
        self.assertTrue(out["enabled"])


if __name__ == "__main__":
    unittest.main()
