"""Provisioning invariants: cloud fulfillment queues a workspace; reconcile
converges PENDING → ACTIVE exactly once with a configured Railway; missing
config is a stated gate, not a crash; cancellation revokes; the whole
machine is idempotent.

Run from storefront/:  python -m unittest discover -s tests -v
"""
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

from sqlalchemy import select      # noqa: E402

from app import db, provisioner, settings  # noqa: E402
from app.main import _fulfill              # noqa: E402


class StripeLike:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def cloud_session(sid, subscription):
    return types.SimpleNamespace(
        id=sid, metadata=StripeLike(plan="cloud-personal"),
        mode="subscription", customer_details=StripeLike(email="t@example.com"),
        customer="cus_t", subscription=subscription)


class FakeRailway:
    """Counts every mutation so idempotency shows up as call counts."""

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = {"create_service": 0, "create_volume": 0,
                      "upsert_variables": 0, "set_start_command": 0,
                      "create_domain": 0, "redeploy": 0, "delete_service": 0,
                      "deploy_latest": 0}

    def _hit(self, name):
        self.calls[name] += 1
        if self.fail:
            raise RuntimeError("railway said no")

    def create_service(self, name):
        self._hit("create_service")
        return f"svc-{self.calls['create_service']}"

    def create_volume(self, service_id, mount_path):
        self._hit("create_volume")
        return "vol-1"

    def upsert_variables(self, service_id, variables):
        self._hit("upsert_variables")
        self.variables = {**getattr(self, "variables", {}), **variables}
        self.last_variables = variables

    def set_start_command(self, service_id, cmd):
        self._hit("set_start_command")

    def create_domain(self, service_id):
        self._hit("create_domain")
        return "tenant-x.up.railway.app"

    def redeploy(self, service_id):
        self._hit("redeploy")

    def delete_service(self, service_id):
        self._hit("delete_service")

    def deploy_latest(self, service_id, commit_sha=""):
        self._hit("deploy_latest")
        self.last_deploy_sha = commit_sha

    def configure_graceful_deploys(self, service_id):
        self.calls["configure_graceful_deploys"] =             self.calls.get("configure_graceful_deploys", 0) + 1
        if self.fail:
            raise RuntimeError("railway said no")


def configure_railway(on=True):
    settings.RAILWAY_API_TOKEN = "tok" if on else ""
    settings.RAILWAY_PROJECT_ID = "proj" if on else ""
    settings.RAILWAY_ENVIRONMENT_ID = "env" if on else ""


class ProvisionerTests(unittest.TestCase):
    def tearDown(self):
        configure_railway(False)

    def _workspace_for(self, purchase_id):
        with db.session() as s:
            ws = s.scalar(select(db.Workspace).where(
                db.Workspace.purchase_id == purchase_id))
            if ws:
                _ = (ws.status, ws.detail, ws.access_token, ws.url,
                     ws.railway_service_id)
                s.expunge_all()
            return ws

    def test_unconfigured_is_a_stated_gate(self):
        configure_railway(False)
        p = _fulfill(cloud_session("cs_prov_1", "sub_p1"))
        self.assertIsNotNone(p.workspace, "cloud fulfillment must queue a workspace")
        provisioner.reconcile(railway=FakeRailway())
        ws = self._workspace_for(p.id)
        self.assertEqual(ws.status, "PENDING")
        self.assertIn("not configured", ws.detail)

    def test_provision_once_then_idempotent(self):
        configure_railway(True)
        p = _fulfill(cloud_session("cs_prov_2", "sub_p2"))
        fake = FakeRailway()
        provisioner.reconcile(railway=fake)
        ws = self._workspace_for(p.id)
        self.assertEqual(ws.status, "ACTIVE")
        self.assertEqual(ws.url, "https://tenant-x.up.railway.app")
        self.assertEqual(fake.last_variables["SCREENBOARD_ACCESS_TOKEN"],
                         ws.access_token)
        self.assertEqual(fake.last_variables["SCREENBOARD_HOME"], "/workspace")
        provisioner.reconcile(railway=fake)  # second run must not rebuild
        self.assertEqual(fake.calls["create_service"], 1)
        self.assertEqual(fake.calls["create_volume"], 1)

    def test_failure_is_recorded_and_retried(self):
        configure_railway(True)
        p = _fulfill(cloud_session("cs_prov_3", "sub_p3"))
        provisioner.reconcile(railway=FakeRailway(fail=True))
        ws = self._workspace_for(p.id)
        self.assertEqual(ws.status, "FAILED")
        self.assertIn("railway said no", ws.detail)
        good = FakeRailway()
        provisioner.reconcile(railway=good)  # retry converges
        ws = self._workspace_for(p.id)
        self.assertEqual(ws.status, "ACTIVE")

    def test_fleet_update_pushes_current_build_to_active_tenants(self):
        configure_railway(True)
        p = _fulfill(cloud_session("cs_prov_5", "sub_p5"))
        fake = FakeRailway()
        provisioner.reconcile(railway=fake)
        out = provisioner.update_tenants(railway=fake)
        self.assertGreaterEqual(fake.calls["deploy_latest"], 1)
        # Deploys must never kill a render mid-flight: drain config is
        # (re)applied before every fleet build.
        self.assertGreaterEqual(fake.calls.get("configure_graceful_deploys", 0), 1)
        self.assertGreaterEqual(len(out["updated"]), 1)
        # A failing update is recorded on the row and reported, not raised
        bad = FakeRailway(fail=True)
        out = provisioner.update_tenants(railway=bad)
        self.assertGreaterEqual(len(out["failed"]), 1)
        ws = self._workspace_for(p.id)
        self.assertIn("update failed", ws.detail)

    def test_every_studio_gets_an_at_rest_wrap_key(self):
        """2026-08-23. The key wraps that studio's API keys on its volume,
        and is held as a VARIABLE precisely so the volume does not carry
        the key that opens it."""
        configure_railway(True)
        p = _fulfill(cloud_session("cs_prov_sec1", "sub_sec1"))
        fake = FakeRailway()
        provisioner.reconcile(railway=fake)
        key = fake.variables.get("SCREENBOARD_SECRET_KEY")
        self.assertTrue(key)
        ws = self._workspace_for(p.id)
        self.assertEqual(ws.secret_key, key)

    def test_an_already_active_studio_is_backfilled(self):
        """The bug this test exists for, caught during the 2026-08-23
        rollout: `_provision` runs only for PENDING/FAILED workspaces, so
        the variable reached NEW studios and no existing one — which was
        all of them. Without the standing upgrade the feature would have
        shipped and applied to nobody, silently, while the studio kept its
        keys in plaintext."""
        configure_railway(True)
        p = _fulfill(cloud_session("cs_prov_sec2", "sub_sec2"))
        provisioner.reconcile(railway=FakeRailway())
        ws = self._workspace_for(p.id)
        self.assertEqual(ws.status, "ACTIVE")
        # A FRESH fake: nothing carried over, so anything present had to be
        # re-sent on this reconcile through the ACTIVE path.
        fake2 = FakeRailway()
        provisioner.reconcile(railway=fake2)
        self.assertEqual(getattr(fake2, "variables", {}).get("SCREENBOARD_SECRET_KEY"),
                         ws.secret_key)

    def test_the_key_is_never_rotated(self):
        """Rotating it would make every credential already stored on that
        volume unreadable, and the studio would lose its API keys with no
        stated cause."""
        configure_railway(True)
        p = _fulfill(cloud_session("cs_prov_sec3", "sub_sec3"))
        provisioner.reconcile(railway=FakeRailway())
        first = self._workspace_for(p.id).secret_key
        for _ in range(3):
            provisioner.reconcile(railway=FakeRailway())
        self.assertEqual(self._workspace_for(p.id).secret_key, first)

    def test_two_studios_do_not_share_a_key(self):
        configure_railway(True)
        a = _fulfill(cloud_session("cs_prov_sec4", "sub_sec4"))
        b = _fulfill(cloud_session("cs_prov_sec5", "sub_sec5"))
        provisioner.reconcile(railway=FakeRailway())
        self.assertNotEqual(self._workspace_for(a.id).secret_key,
                            self._workspace_for(b.id).secret_key)

    def test_a_railway_refusal_does_not_stall_the_reconcile(self):
        """Variables are best-effort with a retry next pass — a studio that
        cannot take the key today must not block the rest of the fleet."""
        configure_railway(True)
        _fulfill(cloud_session("cs_prov_sec6", "sub_sec6"))
        provisioner.reconcile(railway=FakeRailway())
        provisioner.reconcile(railway=FakeRailway(fail=True))  # must not raise

    def test_owner_studios_get_debug_tools_customers_never(self):
        """User ruling 2026-08-03: debug tools are linked to the owner's
        account — the flag rides provisioning for OWNER_EMAILS purchases
        only; a customer studio never receives it."""
        from app import settings as st
        configure_railway(True)
        # Customer first: no flag.
        p = _fulfill(cloud_session("cs_prov_own1", "sub_own1"))
        fake = FakeRailway()
        provisioner.reconcile(railway=fake)
        self.assertNotIn("SCREENBOARD_DEBUG_TOOLS", fake.variables)
        # Owner: the same email, now on the owner list.
        old_owners = st.OWNER_EMAILS
        st.OWNER_EMAILS = {"t@example.com"}
        self.addCleanup(lambda: setattr(st, "OWNER_EMAILS", old_owners))
        p2 = _fulfill(cloud_session("cs_prov_own2", "sub_own2"))
        fake2 = FakeRailway()
        provisioner.reconcile(railway=fake2)
        self.assertEqual(fake2.variables.get("SCREENBOARD_DEBUG_TOOLS"), "1")
        ws = self._workspace_for(p2.id)
        self.assertEqual(ws.status, "ACTIVE")
        # Standing upgrade: an ALREADY-ACTIVE owner studio gains the flag
        # on the next reconcile (fresh fake proves it re-upserts).
        fake3 = FakeRailway()
        provisioner.reconcile(railway=fake3)
        self.assertEqual(getattr(fake3, "variables", {}).get(
            "SCREENBOARD_DEBUG_TOOLS"), "1")

    def test_cancellation_revokes(self):
        configure_railway(True)
        p = _fulfill(cloud_session("cs_prov_4", "sub_p4"))
        fake = FakeRailway()
        provisioner.reconcile(railway=fake)
        with db.session() as s:
            row = s.get(db.Purchase, p.id)
            row.status = "CANCELED"
            s.commit()
        provisioner.reconcile(railway=fake)
        ws = self._workspace_for(p.id)
        self.assertEqual(ws.status, "REVOKED")
        self.assertEqual(fake.calls["delete_service"], 1)
        provisioner.reconcile(railway=fake)  # revoke is idempotent too
        self.assertEqual(fake.calls["delete_service"], 1)


if __name__ == "__main__":
    unittest.main()
