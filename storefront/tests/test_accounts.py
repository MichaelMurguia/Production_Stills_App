"""Account lifecycle: magic links are single-use and uniform, sessions come
from signed cookies, the account page lists the email's purchases, Google
routes gate when unconfigured, and logout clears."""
from __future__ import annotations

import os
import re
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-test-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from fastapi.testclient import TestClient  # noqa: E402

from app import auth, mailer, settings  # noqa: E402
from app.main import _fulfill, app  # noqa: E402


class StripeLike:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def dl_session(sid, email):
    return types.SimpleNamespace(
        id=sid, metadata=StripeLike(plan="download-business"), mode="payment",
        customer_details=StripeLike(email=email), customer="cus", subscription=None)


class AccountFlowTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sent = []
        self._send = mailer.send
        self._host, self._from = settings.SMTP_HOST, settings.SMTP_FROM
        settings.SMTP_HOST, settings.SMTP_FROM = "smtp.test", "care@test"
        mailer.send = lambda to, subject, body: self.sent.append((to, body))
        settings.SESSION_SECRET = "test-secret"

    def tearDown(self):
        mailer.send = self._send
        settings.SMTP_HOST, settings.SMTP_FROM = self._host, self._from
        settings.SESSION_SECRET = ""
        settings.GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_SECRET = ""

    def _link(self):
        m = re.search(r"/auth/verify\?token=[\w-]+", self.sent[-1][1])
        self.assertIsNotNone(m, "mail must carry the magic link")
        return m.group(0)

    def test_pages_render_and_google_hides_when_unconfigured(self):
        for p in ("/signin", "/signup"):
            r = self.client.get(p)
            self.assertEqual(r.status_code, 200)
            self.assertNotIn("/auth/google", r.text)
        self.assertEqual(self.client.get("/auth/google", follow_redirects=False).status_code, 404)
        settings.GOOGLE_CLIENT_ID = "cid"
        settings.GOOGLE_CLIENT_SECRET = "sec"
        r = self.client.get("/signin")
        self.assertIn("/auth/google", r.text)
        g = self.client.get("/auth/google", follow_redirects=False)
        self.assertEqual(g.status_code, 303)
        self.assertIn("accounts.google.com", g.headers["location"])

    def test_magic_link_full_lifecycle(self):
        _fulfill(dl_session("cs_acc_dl", "flow@example.com"))
        r = self.client.post("/auth/email", data={"email": "flow@example.com", "mode": "signup"})
        self.assertIn("Check your inbox", r.text)
        link = self._link()
        v = self.client.get(link, follow_redirects=False)
        self.assertEqual(v.status_code, 303)
        self.assertEqual(v.headers["location"], "/account")
        acct = self.client.get("/account")
        self.assertIn("flow@example.com", acct.text)
        self.assertIn("DOWNLOAD BUSINESS", acct.text)
        self.assertIn("/download/", acct.text)
        # header flips to signed-in
        self.assertIn("Sign out", self.client.get("/").text)
        # link is single-use
        again = self.client.get(link)
        self.assertIn("EXPIRED OR ALREADY USED", again.text.upper())

    def test_uniform_response_any_address(self):
        a = self.client.post("/auth/email", data={"email": "nobody@example.com", "mode": "signin"})
        b = self.client.post("/auth/email", data={"email": "flow@example.com", "mode": "signin"})
        self.assertEqual(a.text, b.text)

    def test_logout_clears_session(self):
        self.client.post("/auth/email", data={"email": "out@example.com", "mode": "signin"})
        self.client.get(self._link())
        self.assertIn("out@example.com", self.client.get("/account").text)
        self.client.post("/auth/logout")
        self.assertNotIn("out@example.com", self.client.get("/account").text)

    def test_session_cookie_is_tamper_proof(self):
        self.assertIsNone(auth.read_session("evil@example.com|9999999999|forged"))
        good = auth.make_session("me@example.com")
        self.assertEqual(auth.read_session(good), "me@example.com")
        self.assertIsNone(auth.read_session(good.replace("me@", "you@")))


if __name__ == "__main__":
    unittest.main()
