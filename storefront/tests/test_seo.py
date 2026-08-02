"""SEO pass (user request 2026-08-03): public pages carry full head
metadata and structured data; private/transactional pages and every
tenant host say noindex; robots.txt and sitemap.xml exist and agree."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-test-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db, settings  # noqa: E402
from app.main import store  # noqa: E402
from app.tenant_proxy import TenantProxy  # noqa: E402

BASE = settings.BASE_URL.rstrip("/")


class PublicHeadTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(store)

    def test_index_head_is_complete(self):
        html = self.client.get("/").text
        self.assertIn('<meta name="description"', html)
        self.assertIn(f'<link rel="canonical" href="{BASE}/">', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:image"', html)
        self.assertIn('name="twitter:card"', html)
        self.assertNotIn('name="robots"', html,
                         "the landing page must be indexable")

    def test_index_structured_data_parses(self):
        html = self.client.get("/").text
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                      html, re.DOTALL)
        self.assertIsNotNone(m, "index must carry JSON-LD")
        data = json.loads(m.group(1))
        self.assertEqual(data["@type"], "SoftwareApplication")
        self.assertEqual({o["price"] for o in data["offers"]},
                         {"119.00", "249.99", "9.99", "29.99"},
                         "structured-data prices must match the page")

    def test_pipeline_has_own_description(self):
        html = self.client.get("/pipeline").text
        self.assertIn("stage by stage", html)
        self.assertIn(f'<link rel="canonical" href="{BASE}/pipeline">', html)

    def test_private_pages_are_noindex(self):
        for path in ("/signin", "/signup", "/account", "/recover"):
            html = self.client.get(path).text
            self.assertIn('<meta name="robots" content="noindex">', html, path)

    def test_robots_txt_and_sitemap_agree(self):
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Disallow: /account", robots.text)
        self.assertIn("Disallow: /admin/", robots.text)
        self.assertIn(f"Sitemap: {BASE}/sitemap.xml", robots.text)
        sm = self.client.get("/sitemap.xml")
        self.assertEqual(sm.status_code, 200)
        self.assertIn("application/xml", sm.headers["content-type"])
        for p in ("/", "/pipeline", "/terms", "/privacy"):
            self.assertIn(f"<loc>{BASE}{p}</loc>", sm.text)
        # Nothing robots disallows may appear in the sitemap.
        self.assertNotIn("/account", sm.text)
        self.assertNotIn("/signin", sm.text)


class TenantNoindexTests(unittest.TestCase):
    TBASE = "screenboardstudio.com"

    def setUp(self):
        settings.TENANT_DOMAIN_BASE = self.TBASE
        self.addCleanup(lambda: setattr(settings, "TENANT_DOMAIN_BASE", ""))

        def upstream(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"studio page")

        self.proxy = TenantProxy(store, transport=httpx.MockTransport(upstream))

    def _mk(self, sub):
        with db.session() as s:
            p = db.Purchase(kind="cloud", email="seo@example.com",
                            stripe_session_id=f"cs_seo_{sub}")
            s.add(p)
            s.commit()
            s.add(db.Workspace(
                purchase_id=p.id, status="ACTIVE", subdomain=sub,
                railway_url="https://tenant-seo.up.railway.app"))
            s.commit()

    def test_every_tenant_response_is_noindex(self):
        self._mk("seo-studio")
        client = TestClient(self.proxy, base_url=f"https://seo-studio.{self.TBASE}")
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("x-robots-tag"), "noindex",
                         "private studios must never be crawlable")
        r404 = TestClient(self.proxy,
                          base_url=f"https://nobody-here.{self.TBASE}").get("/")
        self.assertEqual(r404.status_code, 404)
        self.assertEqual(r404.headers.get("x-robots-tag"), "noindex")
        self.assertIn('content="noindex"', r404.text)


if __name__ == "__main__":
    unittest.main()
