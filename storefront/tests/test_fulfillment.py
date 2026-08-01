"""Fulfillment invariants: idempotency on stripe_session_id, detached-safe
returns, and Stripe-shaped (attribute-only, no dict .get()) field access.

Run from storefront/:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Point the app at a throwaway database BEFORE app modules import settings.
_tmpdir = tempfile.mkdtemp(prefix="storefront-test-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/")

from app import db            # noqa: E402
from app.main import _fulfill  # noqa: E402


class StripeLike:
    """Attribute access only — real StripeObjects raise on dict .get()."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def session_obj(sid, plan, mode, email, subscription=None):
    return types.SimpleNamespace(
        id=sid,
        metadata=StripeLike(plan=plan),
        mode=mode,
        customer_details=StripeLike(email=email),
        customer="cus_test",
        subscription=subscription,
    )


class FulfillmentTests(unittest.TestCase):
    def test_download_idempotent_and_detached_safe(self):
        fake = session_obj("cs_dl_1", "download-personal", "payment", "b@example.com")
        first = _fulfill(fake)   # webhook path: creates row + license
        second = _fulfill(fake)  # success page path: existing branch
        self.assertEqual(second.kind, "download")
        self.assertEqual(second.tier, "personal")
        self.assertEqual(second.email, "b@example.com")
        self.assertIsNotNone(second.license)
        self.assertEqual(first.license.token, second.license.token,
                         "same session must never mint a second license")

    def test_cloud_idempotent_no_license(self):
        fake = session_obj("cs_cl_1", "cloud-business", "subscription",
                           "c@example.com", subscription="sub_1")
        _fulfill(fake)
        again = _fulfill(fake)
        self.assertEqual((again.kind, again.tier), ("cloud", "business"))
        self.assertEqual(again.stripe_subscription_id, "sub_1")
        self.assertIsNone(again.license)

    def test_missing_metadata_falls_back_to_mode(self):
        fake = types.SimpleNamespace(
            id="cs_nometa_1", metadata=None, mode="subscription",
            customer_details=None, customer=None, subscription="sub_2",
        )
        p = _fulfill(fake)
        self.assertEqual(p.kind, "cloud")
        self.assertEqual(p.email, "")


if __name__ == "__main__":
    unittest.main()
