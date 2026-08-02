"""The wildcard tenant router: studio hosts proxy to their tenant's
railway service, storefront hosts pass through, unknown studios get a
stated 404, and the proxy never forwards anywhere but *.up.railway.app.

Run from storefront/:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
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

BASE = "screenboardstudio.com"


def _mk_workspace(sub, railway_url="https://tenant-p.up.railway.app",
                  ws_status="ACTIVE", p_status="PAID"):
    with db.session() as s:
        p = db.Purchase(kind="cloud", tier="personal", email="p@example.com",
                        stripe_session_id=f"cs_proxy_{sub}", status=p_status)
        s.add(p)
        s.commit()
        s.add(db.Workspace(purchase_id=p.id, status=ws_status, subdomain=sub,
                           railway_url=railway_url, url=f"https://{sub}.{BASE}"))
        s.commit()


class TenantProxyTests(unittest.TestCase):
    def setUp(self):
        settings.TENANT_DOMAIN_BASE = BASE
        self.addCleanup(lambda: setattr(settings, "TENANT_DOMAIN_BASE", ""))
        self.upstream_requests = []

        def upstream(request: httpx.Request) -> httpx.Response:
            self.upstream_requests.append(request)
            if request.url.path == "/api/healthz":
                return httpx.Response(200, json={"ok": True, "tenant": True})
            return httpx.Response(200, content=b"tenant says: " +
                                  request.url.path.encode())

        self.proxy = TenantProxy(store, transport=httpx.MockTransport(upstream))

    def client(self, host):
        return TestClient(self.proxy, base_url=f"https://{host}")

    def test_studio_host_proxies_to_railway_service(self):
        _mk_workspace("mesa-anvil")
        r = self.client(f"mesa-anvil.{BASE}").get("/api/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["tenant"])
        req = self.upstream_requests[-1]
        self.assertEqual(req.url.host, "tenant-p.up.railway.app",
                         "must forward to the tenant's own railway host")
        self.assertEqual(req.headers["x-forwarded-host"], f"mesa-anvil.{BASE}")

    def test_storefront_hosts_pass_through(self):
        for host in (f"www.{BASE}", BASE, "testserver"):
            r = self.client(host).get("/healthz")
            self.assertEqual(r.status_code, 200)
            self.assertIn("rev", r.json(), f"{host} should reach the store")
        self.assertEqual(self.upstream_requests, [],
                         "storefront traffic must never touch a tenant")

    def test_unknown_studio_is_a_stated_404(self):
        r = self.client(f"never-claimed.{BASE}").get("/")
        self.assertEqual(r.status_code, 404)
        self.assertIn("NO STUDIO AT THIS ADDRESS", r.text)
        # T1: full store chrome, the address as the H1, and a prefilled
        # claim path — the one failure page that sells.
        self.assertIn(f"never-claimed.{BASE}", r.text)
        self.assertIn("claim=never-claimed", r.text)
        self.assertIn("The pipeline", r.text)
        self.assertIn("LOOKING FOR A STUDIO YOU WERE INVITED TO?", r.text)
        # Served on a tenant host: every asset must name the store host.
        self.assertNotIn('href="/static', r.text)

    def test_inactive_or_unpaid_studios_do_not_serve(self):
        _mk_workspace("gone-studio", ws_status="REVOKED")
        _mk_workspace("unpaid-studio", p_status="CANCELED")
        for sub in ("gone-studio", "unpaid-studio"):
            r = self.client(f"{sub}.{BASE}").get("/")
            self.assertEqual(r.status_code, 404, sub)

    def test_never_proxies_off_railway(self):
        # A poisoned railway_url (e.g. pointing back at the branded base)
        # must not be followed — that would loop or exfiltrate.
        _mk_workspace("evil-loop", railway_url=f"https://evil-loop.{BASE}")
        r = self.client(f"evil-loop.{BASE}").get("/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.upstream_requests, [])

    def test_post_bodies_reach_the_tenant(self):
        _mk_workspace("post-studio")
        r = self.client(f"post-studio.{BASE}").post(
            "/api/projects", json={"name": "test"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.upstream_requests[-1].read(),
                         b'{"name":"test"}')
        self.assertEqual(self.upstream_requests[-1].method, "POST")
