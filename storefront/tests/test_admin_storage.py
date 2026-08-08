"""Fleet storage on the admin page (user 2026-08-07).

A studio filled its volume and region repair died mid-write. The product
side was fixed the same day — renders refuse before the spend and Settings
carries a readout — but `/api/storage` on a tenant answers only that
studio's own session, so "how full is beltminer?" could only be answered
by opening each studio in turn.

The rule these hold: a studio that will not answer is UNREACHABLE, never
0 bytes free. A dead studio reading as a critically full one sends
somebody to fix the wrong thing during an incident.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-storage-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from app import main as m  # noqa: E402


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeClient:
    """Answers per door; a door mapped to an Exception raises it."""

    def __init__(self, doors):
        self.doors = doors
        self.asked = []

    async def get(self, url, **kw):
        door = url.rsplit("/api/", 1)[0]
        self.asked.append(door)
        out = self.doors.get(door)
        if isinstance(out, Exception):
            raise out
        return out


def ws(subdomain="studio", door="https://s.example.com", token="tok", wid=1):
    return {"id": wid, "subdomain": subdomain, "door": door, "token": token}


def ask(client, workspace):
    return asyncio.run(m._ask_storage(client, workspace))


GOOD = {"total": 5 << 30, "free": 4 << 30, "low": False,
        "breakdown": [{"kind": "Takes and boards", "bytes": 900 << 20},
                      {"kind": "References", "bytes": 20 << 20}]}


class AStudioThatAnswers(unittest.TestCase):
    def test_it_reports_free_total_and_the_largest_kind(self):
        c = FakeClient({"https://s.example.com": FakeResponse(200, GOOD)})
        row = ask(c, ws())
        self.assertEqual(row["state"], "OK")
        self.assertEqual(row["free"], 4 << 30)
        self.assertEqual(row["total"], 5 << 30)
        self.assertEqual(row["used_pct"], 20)
        self.assertIn("Takes and boards", row["top"])

    def test_it_is_asked_with_its_own_session(self):
        c = FakeClient({"https://s.example.com": FakeResponse(200, GOOD)})
        with mock.patch.object(FakeClient, "get", autospec=True) as g:
            g.return_value = FakeResponse(200, GOOD)
            asyncio.run(m._ask_storage(c, ws(token="secret")))
            self.assertEqual(g.call_args.kwargs["cookies"],
                             {"sb_session": "secret"})

    def test_below_the_render_floor_it_reads_refusing(self):
        payload = {**GOOD, "free": 100 << 20}
        c = FakeClient({"https://s.example.com": FakeResponse(200, payload)})
        self.assertEqual(ask(c, ws())["state"], "REFUSING")

    def test_the_floor_is_the_one_the_product_guards_on(self):
        """If these drift, the fleet view and the app disagree about when
        a studio has stopped working."""
        self.assertEqual(m.STORAGE_REFUSING, 350 * 1024 * 1024)

    def test_between_the_floor_and_a_gigabyte_it_reads_tight(self):
        payload = {**GOOD, "free": 600 << 20}
        c = FakeClient({"https://s.example.com": FakeResponse(200, payload)})
        self.assertEqual(ask(c, ws())["state"], "TIGHT")


class AStudioThatDoesNot(unittest.TestCase):
    def test_a_timeout_is_unreachable_not_empty(self):
        c = FakeClient({"https://s.example.com": TimeoutError("boom")})
        row = ask(c, ws())
        self.assertEqual(row["state"], "UNREACHABLE")
        self.assertIsNone(row["free"], "a dead studio must not read as full")

    def test_a_500_is_unreachable(self):
        c = FakeClient({"https://s.example.com": FakeResponse(500, {})})
        self.assertEqual(ask(c, ws())["state"], "UNREACHABLE")

    def test_a_studio_with_no_door_is_never_contacted(self):
        c = FakeClient({})
        row = ask(c, ws(door=""))
        self.assertEqual(row["state"], "UNREACHABLE")
        self.assertEqual(c.asked, [])

    def test_a_studio_that_cannot_measure_itself_is_unreachable(self):
        """The tenant returns total 0 when disk_usage fails — that is not
        an empty volume either."""
        c = FakeClient({"https://s.example.com":
                        FakeResponse(200, {"total": 0, "free": 0})})
        self.assertEqual(ask(c, ws())["state"], "UNREACHABLE")


class TheOrdering(unittest.TestCase):
    def test_worst_first(self):
        rows = [{"state": "OK", "free": 9 << 30},
                {"state": "UNREACHABLE", "free": None},
                {"state": "REFUSING", "free": 1 << 20},
                {"state": "TIGHT", "free": 700 << 20}]
        order = {"REFUSING": 0, "TIGHT": 1, "UNREACHABLE": 2, "OK": 3}
        rows.sort(key=lambda r: (order.get(r["state"], 9),
                                 r["free"] if r["free"] is not None else 1 << 62))
        self.assertEqual([r["state"] for r in rows],
                         ["REFUSING", "TIGHT", "UNREACHABLE", "OK"])

    def test_the_endpoint_sorts_the_same_way(self):
        src = (os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "app", "main.py"))
        with open(src, encoding="utf-8") as f:
            body = f.read()
        i = body.index("async def admin_storage")
        block = body[i:i + 2400]
        self.assertIn('"REFUSING": 0', block)
        self.assertIn("rows.sort", block)


class TheGate(unittest.TestCase):
    def test_it_is_behind_the_admin_gate(self):
        src = (os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "app", "main.py"))
        with open(src, encoding="utf-8") as f:
            body = f.read()
        i = body.index("async def admin_storage")
        self.assertIn("_admin_gate(request, token)", body[i:i + 900])

    def test_only_active_workspaces_are_queried(self):
        src = (os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "app", "main.py"))
        with open(src, encoding="utf-8") as f:
            body = f.read()
        i = body.index("async def admin_storage")
        self.assertIn('db.Workspace.status == "ACTIVE"', body[i:i + 2400])


class TheSizeFormat(unittest.TestCase):
    def test_it_reads_as_a_size(self):
        self.assertEqual(m._gb(5 << 30), "5.0 GB")
        self.assertEqual(m._gb(350 * 1024 * 1024), "350.0 MB")
        self.assertEqual(m._gb(0), "0 B")


class TheCapabilityProbe(unittest.TestCase):
    """Asked of Railway's schema rather than assumed — and narrow enough
    that it can never become arbitrary GraphQL behind the admin token."""

    def source(self) -> str:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "app", "railway.py")
        with open(p, encoding="utf-8") as f:
            return f.read()

    def test_the_query_takes_no_caller_input(self):
        src = self.source()
        i = src.index("def volume_capabilities")
        body = src[i:src.index("\ndef ", i + 1)]
        self.assertIn('_gql("""query {', body)
        self.assertIn("{})", body, "no variables are passed")
        self.assertNotIn("format(", body)
        self.assertNotIn("f\"\"\"", body, "the query is a literal, never built")

    def test_it_asks_for_the_three_things_that_decide_the_answer(self):
        body = self.source()
        for probe in ('__type(name: "Mutation")', '__type(name: "VolumeUpdateInput")',
                      '__type(name: "Volume")', '__type(name: "VolumeInstance")',
                      '__type(name: "VolumeInstanceUpdateInput")'):
            self.assertIn(probe, body)

    def test_the_endpoint_is_gated_and_states_an_unconfigured_account(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "app", "main.py")
        with open(p, encoding="utf-8") as f:
            body = f.read()
        i = body.index("def admin_railway_capabilities")
        block = body[i:i + 900]
        self.assertIn("_admin_gate(request, token)", block)
        self.assertIn('"configured": False', block)


if __name__ == "__main__":
    unittest.main()
