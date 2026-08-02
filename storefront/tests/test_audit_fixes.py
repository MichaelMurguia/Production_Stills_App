"""Regression tests for the 2026-08-02 storefront audit batch: unpaid
sessions never fulfill, refunds close the door, canceled services are
never abandoned running, subdomain claims cannot race, OAuth state is
browser-bound, and admin tokens travel in headers.

Run from storefront/:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-test-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

import app.main as main  # noqa: E402
from app import auth, db, provisioner, settings  # noqa: E402
from app.main import _fulfill, available_versions, store  # noqa: E402


class StripeLike:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def cloud_session(sid, sub_id, payment_status="paid", payment_intent="pi_x"):
    return types.SimpleNamespace(
        id=sid, metadata=StripeLike(plan="cloud-personal"),
        mode="subscription",
        customer_details=StripeLike(email="audit@example.com"),
        customer="cus_audit", subscription=sub_id,
        payment_status=payment_status, payment_intent=payment_intent)


def webhook_event(etype, obj):
    return {"type": etype, "data": {"object": obj}}


class WebhookMoneyGateTests(unittest.TestCase):
    """Finding 1/10: fulfillment must follow the money, not the event."""

    def _post_webhook(self, event, session=None):
        client = TestClient(store)
        with mock.patch.object(main.stripe.Webhook, "construct_event",
                               return_value=event), \
             mock.patch.object(main.stripe.checkout.Session, "retrieve",
                               return_value=session), \
             mock.patch.object(main.provisioner, "reconcile",
                               return_value={}):
            return client.post("/stripe/webhook", content=b"{}",
                               headers={"stripe-signature": "t"})

    def test_unpaid_completed_session_does_not_fulfill(self):
        s_obj = cloud_session("cs_audit_unpaid", "sub_au1",
                              payment_status="unpaid")
        r = self._post_webhook(
            webhook_event("checkout.session.completed",
                          {"id": "cs_audit_unpaid"}), s_obj)
        self.assertEqual(r.status_code, 200)
        with db.session() as s:
            self.assertIsNone(s.scalar(select(db.Purchase).where(
                db.Purchase.stripe_session_id == "cs_audit_unpaid")))

    def test_async_payment_succeeded_fulfills(self):
        s_obj = cloud_session("cs_audit_async", "sub_au2")
        r = self._post_webhook(
            webhook_event("checkout.session.async_payment_succeeded",
                          {"id": "cs_audit_async"}), s_obj)
        self.assertEqual(r.status_code, 200)
        with db.session() as s:
            p = s.scalar(select(db.Purchase).where(
                db.Purchase.stripe_session_id == "cs_audit_async"))
            self.assertIsNotNone(p)
            self.assertEqual(p.stripe_payment_intent, "pi_x")

    def test_refund_closes_the_door(self):
        _fulfill(cloud_session("cs_audit_refund", "sub_au3",
                               payment_intent="pi_refund_me"))
        r = self._post_webhook(
            webhook_event("charge.refunded",
                          {"payment_intent": "pi_refund_me"}))
        self.assertEqual(r.status_code, 200)
        with db.session() as s:
            p = s.scalar(select(db.Purchase).where(
                db.Purchase.stripe_payment_intent == "pi_refund_me"))
            self.assertEqual(p.status, "REFUNDED")


class _FakeRailway:
    """String-returning fake — reconcile sweeps every cloud purchase in
    the shared test DB, so returned values must be storable."""

    def __init__(self):
        self.deleted = []

    def create_service(self, name):
        return "svc_fake"

    def create_volume(self, service_id, mount):
        return "vol_fake"

    def upsert_variables(self, service_id, variables):
        pass

    def set_start_command(self, service_id, cmd):
        pass

    def configure_graceful_deploys(self, service_id):
        pass

    def create_domain(self, service_id):
        return "fake.up.railway.app"

    def redeploy(self, service_id):
        pass

    def service_domains(self, service_id):
        return ["fake.up.railway.app"]

    def list_custom_domains(self, service_id):
        return []

    def delete_custom_domain(self, domain_id):
        pass

    def delete_service(self, service_id):
        self.deleted.append(service_id)


class RevokeDisciplineTests(unittest.TestCase):
    """Finding 3/16: REVOKED only after the service is truly gone, and a
    revoked studio releases its name."""

    def _mk(self, sid, service_id="svc_1", status="CANCELED",
            subdomain="audit-held-name"):
        with db.session() as s:
            p = db.Purchase(kind="cloud", email="r@example.com",
                            stripe_session_id=sid, status=status)
            s.add(p)
            s.commit()
            ws = db.Workspace(purchase_id=p.id, status="ACTIVE",
                              subdomain=subdomain,
                              railway_service_id=service_id)
            s.add(ws)
            s.commit()
            pid = p.id
        # The suite shares one DB — a lingering CANCELED+ACTIVE row would
        # be revoked again by later files' reconcile sweeps.
        def _cleanup():
            with db.session() as s:
                ws = s.scalar(select(db.Workspace).where(
                    db.Workspace.purchase_id == pid))
                if ws and ws.status != "REVOKED":
                    ws.status = "REVOKED"
                    s.commit()
        self.addCleanup(_cleanup)
        return pid

    def _ws(self, pid):
        with db.session() as s:
            ws = s.scalar(select(db.Workspace).where(
                db.Workspace.purchase_id == pid))
            s.expunge_all()
            return ws

    def test_unconfigured_railway_never_marks_revoked(self):
        pid = self._mk("cs_audit_rvk1", subdomain="audit-rvk-one")
        with mock.patch.object(settings, "railway_configured",
                               return_value=False), \
             mock.patch.object(provisioner, "_domain_serves",
                               return_value=False):
            provisioner.reconcile(railway=_FakeRailway())
        ws = self._ws(pid)
        self.assertNotEqual(ws.status, "REVOKED",
                            "a live service must never be abandoned running")
        self.assertIn("cancel pending", ws.detail)

    def test_revoke_releases_the_subdomain(self):
        pid = self._mk("cs_audit_rvk2", subdomain="audit-rvk-two")
        fake = _FakeRailway()
        with mock.patch.object(settings, "railway_configured",
                               return_value=True), \
             mock.patch.object(provisioner, "_domain_serves",
                               return_value=False):
            provisioner.reconcile(railway=fake)
        ws = self._ws(pid)
        self.assertEqual(ws.status, "REVOKED")
        self.assertIn("svc_1", fake.deleted)
        self.assertEqual(ws.subdomain, "",
                         "revoked studios must not squat claimable names")


class SubdomainClaimRaceTests(unittest.TestCase):
    """Finding 4: the DB, not a check-then-set, is the referee."""

    def test_partial_unique_index_blocks_duplicates(self):
        with db.session() as s:
            for i, sid in enumerate(("cs_audit_dup1", "cs_audit_dup2")):
                p = db.Purchase(kind="cloud", email="d@example.com",
                                stripe_session_id=sid)
                s.add(p)
                s.commit()
                s.add(db.Workspace(purchase_id=p.id,
                                   subdomain="audit-same-name"))
                if i == 0:
                    s.commit()
                else:
                    with self.assertRaises(IntegrityError):
                        s.commit()
                    s.rollback()

    def test_empty_subdomains_stay_exempt(self):
        with db.session() as s:
            for sid in ("cs_audit_e1", "cs_audit_e2"):
                p = db.Purchase(kind="cloud", email="e@example.com",
                                stripe_session_id=sid)
                s.add(p)
                s.commit()
                s.add(db.Workspace(purchase_id=p.id, subdomain=""))
                s.commit()  # must not raise


class OAuthStateTests(unittest.TestCase):
    """Finding 2: the callback must come from the browser that started."""

    def test_state_valid_only_with_matching_cookie(self):
        state = auth.make_state()
        self.assertTrue(auth.check_state(state, state))
        self.assertFalse(auth.check_state(state, ""))
        self.assertFalse(auth.check_state(state, auth.make_state()))
        self.assertFalse(auth.check_state("tampered." + state, state))

    def test_state_expires(self):
        state = auth.make_state()
        with mock.patch.object(auth.time, "time",
                               return_value=time.time() + auth.STATE_TTL + 5):
            self.assertFalse(auth.check_state(state, state))


class AdminHeaderTokenTests(unittest.TestCase):
    """Finding 13: the token can travel in a header, not just the URL."""

    def test_authorization_header_opens_the_gate(self):
        client = TestClient(store)
        with mock.patch.object(settings, "ADMIN_EXPORT_TOKEN", "tok-audit"):
            r = client.get("/admin/export",
                           headers={"Authorization": "Bearer tok-audit"})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(
                client.get("/admin/export",
                           headers={"Authorization": "Bearer wrong"}
                           ).status_code, 404)
            self.assertEqual(client.get("/admin/export").status_code, 404)


class MagicLinkThrottleTests(unittest.TestCase):
    """Finding 14: one mail a minute per address, uniform response."""

    def test_rapid_repeat_sends_one_mail(self):
        client = TestClient(store)
        sent = []
        with mock.patch.object(main.mailer, "configured",
                               return_value=True), \
             mock.patch.object(main.mailer, "send",
                               side_effect=lambda *a, **k: sent.append(a)):
            for _ in range(3):
                r = client.post("/auth/email",
                                data={"email": "throttle@example.com"})
                self.assertEqual(r.status_code, 200)
        self.assertEqual(len(sent), 1)
        with db.session() as s:
            rows = s.scalars(select(db.LoginToken).where(
                db.LoginToken.email == "throttle@example.com")).all()
            self.assertEqual(len(rows), 1)


class VersionSortTests(unittest.TestCase):
    """Finding 8: a non-numeric segment must not 500 the account page."""

    def test_mixed_segments_sort_without_typeerror(self):
        from pathlib import Path
        tmp = Path(tempfile.mkdtemp(prefix="versions-"))
        for name in ("screenboard-studio-2026.08.01.33.zip",
                     "screenboard-studio-2026.08.01-rc.zip",
                     "screenboard-studio-2026.07.30.2.zip"):
            (tmp / name).touch()
        with mock.patch.object(settings, "DOWNLOAD_FILE",
                               tmp / "screenboard-studio.zip"):
            versions = [v for v, _ in available_versions()]
        self.assertEqual(len(versions), 3)
        self.assertEqual(versions[-1], "2026.07.30.2")


class SuccessGarbageIdTests(unittest.TestCase):
    """Finding 15: a mangled receipt link redirects home, never 500s."""

    def test_bad_session_id_redirects(self):
        client = TestClient(store, follow_redirects=False)
        with mock.patch.object(
                main.stripe.checkout.Session, "retrieve",
                side_effect=main.stripe.StripeError("no such session")):
            r = client.get("/success?session_id=cs_garbage")
        self.assertEqual(r.status_code, 307)
        self.assertEqual(r.headers["location"], "/")


if __name__ == "__main__":
    unittest.main()
