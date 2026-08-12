"""The fleet updates itself when a push deploys the storefront (user
ruling 2026-08-12: "update automatically when you push changes").

Invariants: a boot on a new commit pushes every ACTIVE studio to that
commit; a boot on the same commit touches nothing; a partial failure
leaves the marker behind so the next boot retries; outside Railway
(no RAILWAY_GIT_COMMIT_SHA) nothing runs.

Run from storefront/:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-test-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from sqlalchemy import delete, select  # noqa: E402

from app import db, provisioner, settings  # noqa: E402


class FakeRailway:
    def __init__(self, fail=False):
        self.fail = fail
        self.deploys = []
        self.last_deploy_sha = ""

    def configure_graceful_deploys(self, service_id):
        pass

    def deploy_latest(self, service_id, commit_sha=""):
        if self.fail:
            raise RuntimeError("railway said no")
        self.deploys.append(service_id)
        self.last_deploy_sha = commit_sha


def configure_railway(on=True):
    settings.RAILWAY_API_TOKEN = "tok" if on else ""
    settings.RAILWAY_PROJECT_ID = "proj" if on else ""
    settings.RAILWAY_ENVIRONMENT_ID = "env" if on else ""


class FleetAutoUpdateTests(unittest.TestCase):
    def setUp(self):
        db.init_db()
        configure_railway(True)
        with db.session() as s:
            s.execute(delete(db.FleetState))
            s.commit()
        self.ws_service = f"svc-{uuid.uuid4().hex[:8]}"
        with db.session() as s:
            p = db.Purchase(kind="cloud", tier="personal",
                            email="fleet@example.com",
                            stripe_session_id=f"cs_{uuid.uuid4().hex[:10]}",
                            status="PAID")
            s.add(p)
            s.flush()
            s.add(db.Workspace(purchase_id=p.id, status="ACTIVE",
                               railway_service_id=self.ws_service))
            s.commit()
            self.purchase_id = p.id

    def tearDown(self):
        configure_railway(False)
        with db.session() as s:
            s.execute(delete(db.FleetState))
            ws = s.scalar(select(db.Workspace).where(
                db.Workspace.purchase_id == self.purchase_id))
            if ws:
                s.delete(ws)
            p = s.get(db.Purchase, self.purchase_id)
            if p:
                s.delete(p)
            s.commit()

    def _marker(self):
        with db.session() as s:
            st = s.get(db.FleetState, 1)
            return st.last_updated_sha if st else None

    def test_a_new_commit_updates_the_fleet_and_stamps_the_marker(self):
        fake = FakeRailway()
        with mock.patch.dict(os.environ,
                             {"RAILWAY_GIT_COMMIT_SHA": "abc1234"}):
            out = provisioner.auto_update_tenants(railway=fake)
        self.assertIn(self.ws_service, fake.deploys)
        self.assertEqual(fake.last_deploy_sha, "abc1234",
                         "tenants must build the storefront's own commit")
        self.assertFalse(out["failed"])
        self.assertEqual(self._marker(), "abc1234")

    def test_the_same_commit_touches_nothing(self):
        # Other suite files leave their own ACTIVE workspaces in the
        # shared test DB, so assert no ADDITIONAL deploys, not a count.
        fake = FakeRailway()
        with mock.patch.dict(os.environ,
                             {"RAILWAY_GIT_COMMIT_SHA": "abc1234"}):
            provisioner.auto_update_tenants(railway=fake)
            after_first = len(fake.deploys)
            out = provisioner.auto_update_tenants(railway=fake)
        self.assertIn("skipped", out)
        self.assertEqual(len(fake.deploys), after_first,
                         "a restart on the same commit must not rebuild")

    def test_a_failed_rollout_retries_on_the_next_boot(self):
        bad = FakeRailway(fail=True)
        with mock.patch.dict(os.environ,
                             {"RAILWAY_GIT_COMMIT_SHA": "abc1234"}):
            out = provisioner.auto_update_tenants(railway=bad)
            self.assertTrue(out["failed"])
            self.assertIsNone(self._marker(),
                              "the marker must not advance past a failure")
            good = FakeRailway()
            out2 = provisioner.auto_update_tenants(railway=good)
        self.assertIn(self.ws_service, good.deploys)
        self.assertFalse(out2["failed"])
        self.assertEqual(self._marker(), "abc1234")

    def test_no_commit_sha_means_no_run(self):
        # Local dev and the test suite have no RAILWAY_GIT_COMMIT_SHA.
        fake = FakeRailway()
        env = {k: v for k, v in os.environ.items()
               if k != "RAILWAY_GIT_COMMIT_SHA"}
        with mock.patch.dict(os.environ, env, clear=True):
            out = provisioner.auto_update_tenants(railway=fake)
        self.assertIn("skipped", out)
        self.assertEqual(fake.deploys, [])

    def test_startup_spawns_the_auto_update(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "app",
                               "main.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("_fleet_update_on_start", src)
        self.assertIn("provisioner.auto_update_tenants()", src)


if __name__ == "__main__":
    unittest.main()
