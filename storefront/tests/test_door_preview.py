"""The workspace door's render preview (TAKE_ACTIONS S1).

The door was saying NO RENDERS YET on a studio that had an approved
panel — a surface may claim "nothing here" only when it has looked
(user-caught 2026-08-06). These cover the looking, and the two
properties that make it safe: a studio's work is reachable only by its
own owner, and the studio's credential never leaves the server.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-door-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from fastapi.testclient import TestClient  # noqa: E402

from app import auth, db  # noqa: E402
import app.main as main  # noqa: E402
from app.main import store  # noqa: E402


def _studio(email: str, status: str = "ACTIVE") -> int:
    with db.session() as s:
        p = db.Purchase(kind="cloud", tier="personal", email=email,
                        stripe_session_id=f"cs_{uuid.uuid4().hex}", status="PAID")
        s.add(p)
        s.commit()
        ws = db.Workspace(purchase_id=p.id, status=status,
                          subdomain=f"s-{uuid.uuid4().hex[:6]}",
                          railway_url="https://tenant.up.railway.app",
                          url="https://s.screenboardstudio.com",
                          access_token="tok-" + uuid.uuid4().hex[:8])
        s.add(ws)
        s.commit()
        return ws.id


def _client(email: str | None = None) -> TestClient:
    c = TestClient(store, base_url="https://testserver")
    if email:
        with db.session() as s:
            from sqlalchemy import select
            if not s.scalar(select(db.Account).where(db.Account.email == email)):
                s.add(db.Account(email=email))
                s.commit()
        c.cookies.set(auth.SESSION_COOKIE, auth.make_session(email))
    return c


class FakeStudio:
    """Stands in for the tenant. Records what credential it was handed."""

    def __init__(self, payload, image=b"\x89PNG-bytes", status=200):
        self.payload, self.image, self.status = payload, image, status
        self.seen_cookies = []

    def install(self, case):
        import httpx
        fake = self

        class R:
            def __init__(self, url, cookies=None, **kw):
                fake.seen_cookies.append((str(url), (cookies or {}).get("sb_session")))
                self.status_code = fake.status
                self._url = str(url)
                self.headers = {"content-type": "image/png"}

            def json(self):
                return fake.payload

            @property
            def content(self):
                return fake.image

        real = httpx.get
        httpx.get = lambda url, **kw: R(url, **kw)
        case.addCleanup(setattr, httpx, "get", real)
        return self


class DoorPreviewTests(unittest.TestCase):
    def setUp(self):
        main._preview_cache.clear()
        self.email = f"door-{uuid.uuid4().hex[:8]}@example.com"
        self.ws = _studio(self.email)

    def test_an_approved_panel_is_found_and_described(self):
        FakeStudio({"found": True, "production": "The Oxcart",
                    "board": "BOARD-0001", "candidate": "CAND-0042",
                    "image": "/api/specs/BOARD-0001/candidates/CAND-0042/image"}
                   ).install(self)
        r = _client(self.email).get(f"/studio/{self.ws}/preview")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d["found"])
        self.assertEqual(d["production"], "The Oxcart")
        self.assertEqual(d["board"], "BOARD-0001")
        self.assertEqual(d["src"], f"/studio/{self.ws}/preview.img")

    def test_no_panels_is_a_stated_empty_not_an_error(self):
        FakeStudio({"found": False, "production": "The Oxcart"}).install(self)
        r = _client(self.email).get(f"/studio/{self.ws}/preview")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["found"])

    def test_the_preview_never_hands_the_credential_to_the_browser(self):
        """The store authenticates to the studio server-side.

        Note what this does NOT claim: the account page has always
        carried the token in the door link's URL fragment — that is how
        clicking Open signs you into your own studio, it is owner-gated,
        and fragments are never sent to a server. The property here is
        narrower and is the one the preview could have broken: nothing
        the preview returns carries the credential."""
        fake = FakeStudio({"found": True, "production": "P", "board": "B",
                           "image": "/api/x"}).install(self)
        c = _client(self.email)
        with db.session() as s:
            token = s.get(db.Workspace, self.ws).access_token
        meta = c.get(f"/studio/{self.ws}/preview")
        # The tenant was handed the token, server-side…
        self.assertTrue(any(cookie == token for _, cookie in fake.seen_cookies),
                        "the studio must be authenticated to at all")
        # …and neither preview response repeats it.
        self.assertNotIn(token, meta.text)
        self.assertNotIn(token,
                         c.get(f"/studio/{self.ws}/preview.img").content.decode(
                             "latin-1"))
        # The door link is the ONLY place it appears on the page.
        page = c.get("/account").text
        self.assertEqual(page.count(token), 2,
                         "the token belongs in the two door links only — "
                         "the preview must not add a third appearance")

    def test_only_the_owner_can_see_a_studios_work(self):
        FakeStudio({"found": True, "production": "P", "board": "B",
                    "image": "/api/x"}).install(self)
        stranger = _client(f"other-{uuid.uuid4().hex[:6]}@example.com")
        self.assertEqual(stranger.get(f"/studio/{self.ws}/preview").status_code, 404)
        self.assertEqual(stranger.get(f"/studio/{self.ws}/preview.img").status_code, 404)
        anon = _client()
        self.assertEqual(anon.get(f"/studio/{self.ws}/preview").status_code, 404)
        self.assertEqual(anon.get(f"/studio/{self.ws}/preview.img").status_code, 404)

    def test_the_image_is_proxied_through_the_store(self):
        FakeStudio({"found": True, "production": "P", "board": "B",
                    "image": "/api/specs/B/candidates/C/image"},
                   image=b"PNGDATA").install(self)
        r = _client(self.email).get(f"/studio/{self.ws}/preview.img")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"PNGDATA")
        self.assertIn("private", r.headers.get("cache-control", ""))

    def test_an_unreachable_studio_leaves_the_door_working(self):
        import httpx
        real = httpx.get

        def boom(*a, **k):
            raise OSError("timed out")
        httpx.get = boom
        self.addCleanup(setattr, httpx, "get", real)
        r = _client(self.email).get(f"/studio/{self.ws}/preview")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["found"], "a dead studio is 'no preview'")
        # And the account page itself still renders.
        self.assertEqual(_client(self.email).get("/account").status_code, 200)

    def test_the_answer_is_cached_so_a_reload_does_not_hammer_a_customer(self):
        fake = FakeStudio({"found": True, "production": "P", "board": "B",
                           "image": "/api/x"}).install(self)
        c = _client(self.email)
        for _ in range(3):
            c.get(f"/studio/{self.ws}/preview")
        meta_calls = [u for u, _ in fake.seen_cookies if "preview-render" in u]
        self.assertEqual(len(meta_calls), 1, "the studio is asked once per TTL")

    def test_a_revoked_studio_serves_nothing(self):
        dead = _studio(self.email, status="REVOKED")
        self.assertEqual(
            _client(self.email).get(f"/studio/{dead}/preview").status_code, 404)


if __name__ == "__main__":
    unittest.main()
