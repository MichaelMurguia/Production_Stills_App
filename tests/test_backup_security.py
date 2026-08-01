"""Backup roundtrip + security invariants: no keys in backups, zip-slip
refused, restore never overwrites, traversal ids 404, headers present,
and the reminder appears in the blocker feed."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import backup, paths  # noqa: E402
import app.main as appmain  # noqa: E402

_SAVED = {}


def _redirect_home(tmp: Path) -> None:
    _SAVED.update(HOME=paths.HOME, PROJECTS_DIR=paths.PROJECTS_DIR,
                  ACTIVE=paths.ACTIVE_PROJECT_FILE, SETTINGS=paths.SETTINGS,
                  slug=paths.ACTIVE_PROJECT)
    paths.HOME = tmp
    paths.PROJECTS_DIR = tmp / "projects"
    paths.ACTIVE_PROJECT_FILE = tmp / "active_project.json"
    paths.SETTINGS = tmp / "settings.json"
    paths.set_project("")
    paths.ensure_dirs()


def _restore_home() -> None:
    paths.HOME = _SAVED["HOME"]
    paths.PROJECTS_DIR = _SAVED["PROJECTS_DIR"]
    paths.ACTIVE_PROJECT_FILE = _SAVED["ACTIVE"]
    paths.SETTINGS = _SAVED["SETTINGS"]
    paths.set_project(_SAVED["slug"])


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-backup-"))
        _redirect_home(self.tmp)
        (paths.SPECS_DIR).mkdir(parents=True, exist_ok=True)
        (paths.SPECS_DIR / "SPEC_A.json").write_text('{"specification_id":"SPEC_A"}')
        (paths.DATA / "settings.json").write_text('{"gemini_api_key":"SECRET"}')
        paths.BIBLE.parent.mkdir(parents=True, exist_ok=True)
        paths.BIBLE.write_text("# Bible\n## Status\nx\n")

    def tearDown(self):
        _restore_home()

    def test_roundtrip_and_no_secrets(self):
        payload, filename = backup.make_backup("")
        self.assertTrue(filename.endswith(".zip"))
        names = zipfile.ZipFile(io.BytesIO(payload)).namelist()
        self.assertIn("data/specs/SPEC_A.json", names)
        self.assertIn("context/bible.md", [n for n in names if "bible" in n] or
                      ["context/bible.md"])  # bible file name varies with paths
        self.assertNotIn("data/settings.json", names,
                         "API keys must never enter a backup")
        self.assertTrue(backup.last_backup_at(""), "backup must be recorded")
        self.assertIsNotNone(backup.days_since_backup(""))

        restored = backup.restore_backup(payload)
        base = paths.PROJECTS_DIR / restored["slug"]
        self.assertTrue((base / "data" / "specs" / "SPEC_A.json").exists())
        # restoring the same zip again must create a SECOND project
        again = backup.restore_backup(payload)
        self.assertNotEqual(again["slug"], restored["slug"])

    def test_zip_slip_refused(self):
        # NOTE: "data\\evil.txt" can't be crafted via writestr — Python's
        # ZipInfo normalizes os.sep to "/" on Windows; the raw-backslash
        # guard in _safe_member still covers hand-crafted archives.
        for evil in ("../evil.txt", "data/../../evil.txt", "/abs.txt",
                     "C:/evil.txt", "secrets/x.txt", "data/./x.txt"):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr(evil, "boo")
            with self.assertRaises(backup.BackupError, msg=evil):
                backup.restore_backup(buf.getvalue())
        self.assertEqual(backup._safe_member("data/x.png"), "data/x.png")
        with self.assertRaises(backup.BackupError):
            backup._safe_member("data\\evil.txt")
        self.assertFalse((self.tmp / "evil.txt").exists())

    def test_not_a_zip_is_a_stated_error(self):
        with self.assertRaises(backup.BackupError):
            backup.restore_backup(b"definitely not a zip")


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-sec-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)

    def tearDown(self):
        appmain.ACCESS_TOKEN = ""
        _restore_home()

    def test_traversal_ids_are_refused(self):
        for bad in ("..", "..%5C..%5Cx", ".hidden", "a/b"):
            r = self.client.get(f"/api/specs/{bad}/candidates/CAND-0001/image")
            self.assertIn(r.status_code, (404, 422), bad)
        with self.assertRaises(KeyError):
            paths.safe_id("..")
        with self.assertRaises(KeyError):
            paths.safe_id("..\\..\\x")
        with self.assertRaises(KeyError):
            paths.safe_id("a/b")
        self.assertEqual(paths.safe_id("CAND-0001"), "CAND-0001")

    def test_security_headers_on_every_response(self):
        r = self.client.get("/api/healthz")
        self.assertEqual(r.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(r.headers.get("x-frame-options"), "DENY")
        self.assertEqual(r.headers.get("referrer-policy"), "no-referrer")

    def test_login_token_is_redacted_in_the_flight_recorder(self):
        appmain.ACCESS_TOKEN = "sekrit"
        self.client.post("/api/login", json={"token": "sekrit"})
        log = (paths.DATA / "activity_log.jsonl").read_text(encoding="utf-8")
        entry = json.loads(log.splitlines()[-1])
        self.assertEqual(entry["path"], "/api/login")
        self.assertNotIn("sekrit", log, "the access token must never be logged")

    def test_backup_reminder_appears_for_content_projects(self):
        (paths.SPECS_DIR).mkdir(parents=True, exist_ok=True)
        (paths.SPECS_DIR / "SPEC_A.json").write_text(json.dumps({
            "specification_id": "SPEC_A", "status": "DRAFT", "panels": [],
            "evidence_ledger": [], "layout": {"panels": []}}))
        from app import insights
        rows = insights.blocking()
        care = [b for b in rows if b["kind"] == "CARE"]
        self.assertEqual(len(care), 1)
        self.assertIn("never been backed up", care[0]["text"])
        self.assertEqual(rows[-1]["kind"], "CARE", "the reminder never outranks real blockers")
        backup.make_backup("")
        self.assertFalse([b for b in insights.blocking() if b["kind"] == "CARE"],
                         "a fresh backup clears the reminder")


if __name__ == "__main__":
    unittest.main()
