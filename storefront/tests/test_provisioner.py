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
                      "create_domain": 0, "redeploy": 0, "delete_service": 0}

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
