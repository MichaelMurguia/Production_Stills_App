"""Tier A invariants: license recovery is anti-enumeration and env-gated,
legal pages exist, the entitlement export hides without its token and never
leaks with a wrong one."""
from __future__ import annotations

import os
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

from app import mailer, settings  # noqa: E402
from app.main import _fulfill, app  # noqa: E402


class StripeLike:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def dl_session(sid, email):
    return types.SimpleNamespace(
        id=sid, metadata=StripeLike(plan="download-personal"), mode="payment",
        customer_details=StripeLike(email=email), customer="cus", subscription=None)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sent = []
        self._send, self._host, self._from = mailer.send, settings.SMTP_HOST, settings.SMTP_FROM

    def tearDown(self):
        mailer.send = self._send
        settings.SMTP_HOST, settings.SMTP_FROM = self._host, self._from
        settings.ADMIN_EXPORT_TOKEN = ""

    def _configure_mail(self):
        settings.SMTP_HOST, settings.SMTP_FROM = "smtp.test", "care@test"
        mailer.send = lambda to, subject, body: self.sent.append((to, subject, body))

    def test_legal_pages_and_footer_links(self):
        for path in ("/terms", "/privacy", "/recover"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
        self.assertIn("/recover", self.client.get("/terms").text)

    def test_unconfigured_recovery_is_a_stated_gate(self):
        r = self.client.post("/recover", data={"email": "x@example.com"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("isn't set up yet", r.text)

    def test_recovery_is_uniform_and_mails_only_the_owner(self):
        self._configure_mail()
        p = _fulfill(dl_session("cs_rec_1", "owner@example.com"))
        hit = self.client.post("/recover", data={"email": "owner@example.com"})
        miss = self.client.post("/recover", data={"email": "stranger@example.com"})
        self.assertEqual(hit.status_code, miss.status_code)
        self.assertEqual(hit.text, miss.text,
                         "responses must not reveal whether an address has purchases")
        self.assertEqual(len(self.sent), 1)
        to, subject, body = self.sent[0]
        self.assertEqual(to, "owner@example.com")
        self.assertIn(p.license.token, body)
        self.assertIn("/download/", body)

    def test_export_hides_without_token_and_refuses_wrong_one(self):
        _fulfill(dl_session("cs_exp_1", "export@example.com"))
        self.assertEqual(self.client.get("/admin/export").status_code, 404)
        settings.ADMIN_EXPORT_TOKEN = "s3cret-export"
        self.assertEqual(
            self.client.get("/admin/export?token=wrong").status_code, 404)
        r = self.client.get("/admin/export?token=s3cret-export")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("purchases", data)
        self.assertIn("licenses", data)
        self.assertIn("workspaces", data)
        self.assertTrue(any(p["stripe_session_id"] == "cs_exp_1"
                            for p in data["purchases"]))


if __name__ == "__main__":
    unittest.main()
