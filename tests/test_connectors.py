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


if __name__ == "__main__":
    unittest.main()
