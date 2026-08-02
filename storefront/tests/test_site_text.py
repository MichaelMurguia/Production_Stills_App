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
        # And the account page carries the owner controls.
        acct = _client(OWNER).get("/account").text
        self.assertIn("PAGE TEXT EDITING", acct)
        self.assertNotIn("PAGE TEXT EDITING",
                         _client("stranger@example.com").get("/account").text)


if __name__ == "__main__":
    unittest.main()
