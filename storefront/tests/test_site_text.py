"""Owner page-text rewrites (debug tool 2026-08-03): public reads — the
overrides ARE the page copy — but writes exist only for signed-in
OWNER_EMAILS accounts, and the editor script ships only to them."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-test-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from fastapi.testclient import TestClient  # noqa: E402

from app import auth, settings  # noqa: E402
from app.main import store  # noqa: E402

OWNER = "owner-texts@example.com"


def _client(email=None):
    c = TestClient(store)
    if email:
        c.cookies.set(auth.SESSION_COOKIE, auth.make_session(email))
    return c


class SiteTextTests(unittest.TestCase):
    def setUp(self):
        self._saved = settings.OWNER_EMAILS
        settings.OWNER_EMAILS = {OWNER}
        self.addCleanup(lambda: setattr(settings, "OWNER_EMAILS", self._saved))
        _client(OWNER).delete("/api/site-text")

    def test_writes_are_owner_only(self):
        body = {"overrides": {"The pipeline": "The method"}}
        self.assertEqual(_client().put("/api/site-text", json=body)
                         .status_code, 404)
        self.assertEqual(_client("stranger@example.com")
                         .put("/api/site-text", json=body).status_code, 404)
        self.assertEqual(_client("stranger@example.com")
                         .delete("/api/site-text").status_code, 404)

    def test_owner_roundtrip_is_public_to_read(self):
        r = _client(OWNER).put("/api/site-text", json={
            "overrides": {"The pipeline": "The method", " ": "never stored"}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["overrides"], {"The pipeline": "The method"})
        # Anonymous visitors read the overrides — they ARE the page copy.
        self.assertEqual(_client().get("/api/site-text").json()["overrides"],
                         {"The pipeline": "The method"})
        self.assertEqual(_client(OWNER).delete("/api/site-text").status_code, 200)
        self.assertEqual(_client().get("/api/site-text").json()["overrides"], {})

    def test_put_rejects_non_object(self):
        r = _client(OWNER).put("/api/site-text",
                               json={"overrides": ["nope"]})
        self.assertEqual(r.status_code, 422)

    def test_editor_script_ships_only_to_the_owner(self):
        anon = _client().get("/").text
        self.assertIn("/api/site-text", anon,
                      "every visitor applies the overrides")
        self.assertNotIn("sbStoreTextEdit", anon,
                         "the editor must be invisible to visitors")
        owner = _client(OWNER).get("/").text
        self.assertIn("sbStoreTextEdit", owner)
        # The controls live on /admin (moved 2026-08-06 — the account page
        # is the customer's view of their purchases, not a console); the
        # editor SCRIPT still ships on every page so Alt-click works
        # wherever the owner is standing.
        admin = _client(OWNER).get("/admin").text
        self.assertIn("DEBUG TOOLS", admin)
        self.assertIn("owner-textedit", admin)
        self.assertEqual(
            _client("stranger@example.com").get("/admin").status_code, 404)
        self.assertNotIn("owner-textedit",
                         _client(OWNER).get("/account").text)


if __name__ == "__main__":
    unittest.main()


class RenameDoorTruthTests(unittest.TestCase):
    """A rename must be true on the very next render, and the released
    name forwards until reclaimed (user-caught 2026-08-04: renamed,
    refreshed, was handed the old address, then a 404)."""

    BASE = "screenboardstudio.com"

    def setUp(self):
        import uuid
        from app import db as adb
        settings.TENANT_DOMAIN_BASE = self.BASE
        self.addCleanup(lambda: setattr(settings, "TENANT_DOMAIN_BASE", ""))
        uid = uuid.uuid4().hex[:8]
        self.old_name = f"old-slug-{uid}"
        self.new_name = f"oxcart-{uid}"
        with adb.session() as s:
            p = adb.Purchase(kind="cloud", email="rename@example.com",
                             stripe_session_id=f"cs_rename_{uid}")
            s.add(p)
            s.commit()
            self.ws = adb.Workspace(
                purchase_id=p.id, status="ACTIVE", subdomain=self.old_name,
                railway_url="https://tenant-r.up.railway.app",
                url=f"https://{self.old_name}.{self.BASE}", domain_live=1)
            s.add(self.ws)
            s.commit()
            self.wid = self.ws.id

    def _row(self):
        from app import db as adb
        with adb.session() as s:
            w = s.get(adb.Workspace, self.wid)
            _ = (w.url, w.subdomain, w.prev_subdomain, w.domain_live)
            s.expunge_all()
            return w

    def test_rename_updates_the_door_in_the_same_commit(self):
        c = _client("rename@example.com")
        r = c.post("/studio/name", data={"workspace_id": self.wid,
                                         "name": self.new_name},
                   follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertIn("named=1", r.headers["location"])
        w = self._row()
        self.assertEqual(w.subdomain, self.new_name)
        self.assertEqual(w.url, f"https://{self.new_name}.{self.BASE}",
                         "the door must be true before any reconcile runs")
        self.assertEqual(w.prev_subdomain, self.old_name)

    def test_released_name_forwards_until_reclaimed(self):
        import httpx
        from app import db as adb
        from app.tenant_proxy import TenantProxy
        c = _client("rename@example.com")
        c.post("/studio/name", data={"workspace_id": self.wid,
                                     "name": self.new_name})
        proxy = TenantProxy(store, transport=httpx.MockTransport(
            lambda req: httpx.Response(200, content=b"studio")))
        tc = TestClient(proxy, base_url=f"https://{self.old_name}.{self.BASE}")
        r = tc.get("/api/state?x=1", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["location"],
                         f"https://{self.new_name}.{self.BASE}/api/state?x=1")
        # The moment someone claims the released name, they own it.
        with adb.session() as s:
            import uuid as _u
            p2 = adb.Purchase(kind="cloud", email="claimer@example.com",
                              stripe_session_id=f"cs_claim_{_u.uuid4().hex[:8]}")
            s.add(p2)
            s.commit()
            s.add(adb.Workspace(purchase_id=p2.id, status="ACTIVE",
                                subdomain=self.old_name,
                                railway_url="https://tenant-c.up.railway.app"))
            s.commit()
        r2 = tc.get("/", follow_redirects=False)
        self.assertEqual(r2.status_code, 200,
                         "a claimed name always wins over a forward")


class ComingSoonGateTests(unittest.TestCase):
    """Pre-launch gate (2026-08-05): pages serve the overlay until the
    password lands; infrastructure never gates."""

    def setUp(self):
        self._saved = settings.PREVIEW_PASSWORD
        settings.PREVIEW_PASSWORD = "open-sesame"
        self.addCleanup(lambda: setattr(settings, "PREVIEW_PASSWORD", self._saved))

    def test_pages_gate_until_unlocked(self):
        c = TestClient(store)
        for path in ("/", "/pipeline", "/signin", "/account"):
            r = c.get(path)
            self.assertEqual(r.status_code, 200)
            self.assertIn("coming soon", r.text.lower(), path)
            self.assertIn("HAVE THE KEY?", r.text, path)
        self.assertEqual(c.post("/auth/email", data={"email": "x@y.z"})
                         .status_code, 403)

    def test_infrastructure_never_gates(self):
        c = TestClient(store)
        self.assertIn("rev", c.get("/healthz").json())
        self.assertIn("overrides", c.get("/api/site-text").json())
        self.assertEqual(c.get("/robots.txt").status_code, 200)

    def test_wrong_password_stated_right_password_unlocks(self):
        c = TestClient(store)
        r = c.post("/preview/unlock", data={"password": "nope"})
        self.assertIn("NOT IT", r.text)
        r = c.post("/preview/unlock", data={"password": "open-sesame"},
                   follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertIn("sb_preview", r.headers.get("set-cookie", ""))
        home = c.get("/")
        self.assertNotIn("HAVE THE KEY?", home.text)
        self.assertIn("pricing", home.text.lower())

    def test_gate_off_when_unset(self):
        settings.PREVIEW_PASSWORD = ""
        c = TestClient(store)
        self.assertNotIn("HAVE THE KEY?", c.get("/").text)

    def test_tenant_studios_never_gate(self):
        import uuid
        import httpx
        from app import db as adb
        from app.tenant_proxy import TenantProxy
        settings.TENANT_DOMAIN_BASE = "screenboardstudio.com"
        self.addCleanup(lambda: setattr(settings, "TENANT_DOMAIN_BASE", ""))
        sub = f"gate-{uuid.uuid4().hex[:6]}"
        with adb.session() as s:
            p = adb.Purchase(kind="cloud", email="gate@example.com",
                             stripe_session_id=f"cs_gate_{uuid.uuid4().hex[:8]}")
            s.add(p)
            s.commit()
            s.add(adb.Workspace(purchase_id=p.id, status="ACTIVE",
                                subdomain=sub,
                                railway_url="https://tenant-g.up.railway.app"))
            s.commit()
        proxy = TenantProxy(store, transport=httpx.MockTransport(
            lambda req: httpx.Response(200, content=b"studio alive")))
        r = TestClient(proxy,
                       base_url=f"https://{sub}.screenboardstudio.com").get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "studio alive",
                         "a paying customer's studio never sees the gate")
