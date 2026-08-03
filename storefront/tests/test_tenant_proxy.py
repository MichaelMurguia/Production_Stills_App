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

    def test_netloc_trickery_never_passes_the_allowlist(self):
        # endswith on a string-sliced netloc once let
        # https://evil.com?x=.up.railway.app through — the hostname must
        # come from a real URL parse.
        _mk_workspace("query-trick",
                      railway_url="https://evil.com?x=.up.railway.app")
        r = self.client(f"query-trick.{BASE}").get("/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.upstream_requests, [])

    def test_inbound_forwarded_headers_are_stripped(self):
        _mk_workspace("honest-chain")
        r = self.client(f"honest-chain.{BASE}").get(
            "/", headers={"x-forwarded-host": "spoofed.example",
                          "x-forwarded-for": "6.6.6.6"})
        self.assertEqual(r.status_code, 200)
        req = self.upstream_requests[-1]
        # The proxy is the sole authority on forwarding facts.
        self.assertEqual(req.headers["x-forwarded-host"],
                         f"honest-chain.{BASE}")
        self.assertNotIn("6.6.6.6",
                         req.headers.get("x-forwarded-for", ""))

    def test_never_proxies_off_railway(self):
        # A poisoned railway_url (e.g. pointing back at the branded base)
        # must not be followed — that would loop or exfiltrate.
        _mk_workspace("evil-loop", railway_url=f"https://evil-loop.{BASE}")
        r = self.client(f"evil-loop.{BASE}").get("/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.upstream_requests, [])

    def test_unreachable_studio_reassures_and_rechecks(self):
        # T2: a paying customer locked out mid-session — stripped chrome,
        # the work's safety first, honest status, 503 + Retry-After.
        _mk_workspace("dead-studio",
                      railway_url="https://tenant-dead.up.railway.app")

        def flaky(request: httpx.Request) -> httpx.Response:
            if request.url.host == "tenant-dead.up.railway.app":
                raise httpx.ConnectError("refused")
            return httpx.Response(200, content=b"ok")

        proxy = TenantProxy(store, transport=httpx.MockTransport(flaky))
        r = TestClient(proxy, base_url=f"https://dead-studio.{BASE}").get("/")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.headers.get("retry-after"), "15")
        self.assertIn("YOUR STUDIO DID NOT ANSWER", r.text)
        self.assertIn("Dead Studio", r.text, "H1 names the studio")
        self.assertIn("Nothing you approved\n  is at risk"
                      .replace("\n  ", " "), r.text.replace("\n  ", " "))
        self.assertIn("SAFE &mdash; STORED SEPARATELY", r.text)
        self.assertIn("RECHECKING AUTOMATICALLY EVERY 15 SECONDS", r.text)
        self.assertIn("help@screenboardstudio.com", r.text)
        # Nothing to buy on a trust page: no nav, no pricing, no footer.
        self.assertNotIn("Pricing", r.text)
        self.assertNotIn("The pipeline", r.text)
        # No proxy success yet in this process → the LAST ANSWERED row
        # drops rather than guessing.
        self.assertNotIn("LAST ANSWERED", r.text)

    def test_railway_edge_errors_never_reach_a_browser_raw(self):
        """Regression (a12-oxcart, 2026-08-05): during a fleet update the
        tenant answers through Railway's edge with the platform's bare
        error page, and the proxy streamed it verbatim onto the branded
        domain. Browser navigations must get the styled unreachable page;
        API clients keep the true upstream status."""
        _mk_workspace("mid-deploy")

        def edge(request):
            return httpx.Response(502, content=b"Application failed to respond")

        proxy = TenantProxy(store, transport=httpx.MockTransport(edge))
        c = TestClient(proxy, base_url=f"https://mid-deploy.{BASE}")
        r = c.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
        self.assertEqual(r.status_code, 503)
        self.assertIn("retry-after", r.headers)
        self.assertNotIn(b"Application failed to respond", r.content,
                         "raw infrastructure must never reach a browser")
        r2 = c.get("/api/healthz", headers={"Accept": "application/json"})
        self.assertEqual(r2.status_code, 502,
                         "non-HTML clients keep the true status")

    def test_edge_stamped_404_intercepted_but_app_404_passes(self):
        _mk_workspace("edge-404")

        def edge(request):
            if request.url.path == "/gone":
                return httpx.Response(404, content=b"app knows this is missing")
            return httpx.Response(404, content=b"Application not found",
                                  headers={"x-railway-fallback": "true"})

        proxy = TenantProxy(store, transport=httpx.MockTransport(edge))
        c = TestClient(proxy, base_url=f"https://edge-404.{BASE}")
        r = c.get("/", headers={"Accept": "text/html"})
        self.assertEqual(r.status_code, 503)
        self.assertNotIn(b"Application not found", r.content)
        r2 = c.get("/gone", headers={"Accept": "text/html"})
        self.assertEqual(r2.status_code, 404)
        self.assertIn(b"app knows", r2.content,
                      "the app's own 404s are its business and pass through")

    def test_last_answered_appears_after_a_good_response(self):
        _mk_workspace("blinky-studio",
                      railway_url="https://tenant-blink.up.railway.app")
        state = {"up": True}

        def blinky(request: httpx.Request) -> httpx.Response:
            if request.url.host == "tenant-blink.up.railway.app":
                if not state["up"]:
                    raise httpx.ConnectError("refused")
                return httpx.Response(200, content=b"ok")
            return httpx.Response(200, content=b"ok")

        proxy = TenantProxy(store, transport=httpx.MockTransport(blinky))
        c = TestClient(proxy, base_url=f"https://blinky-studio.{BASE}")
        self.assertEqual(c.get("/api/healthz").status_code, 200)
        state["up"] = False
        r = c.get("/")
        self.assertEqual(r.status_code, 503)
        self.assertIn("LAST ANSWERED", r.text)
        self.assertIn("AGO", r.text)

    def test_post_bodies_reach_the_tenant(self):
        _mk_workspace("post-studio")
        r = self.client(f"post-studio.{BASE}").post(
            "/api/projects", json={"name": "test"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.upstream_requests[-1].read(),
                         b'{"name":"test"}')
        self.assertEqual(self.upstream_requests[-1].method, "POST")
