"""Importing a backup INTO an existing production (2026-08-06).

Restore has always made a new production. Import is the destructive twin:
it sets a production the user already has to the version in a zip. The
production keeps its identity; only what a backup carries is replaced.
"""
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from app import backup, paths


def zip_of(name: str, files: dict[str, str], **meta) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps({"name": name, **meta}))
        for rel, body in files.items():
            z.writestr(rel, body)
    return buf.getvalue()


class ImportInto(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._home, self._projects = paths.HOME, paths.PROJECTS_DIR
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        self.base = paths.PROJECTS_DIR / "my-show"
        for top in backup.BACKUP_DIRS:
            (self.base / top).mkdir(parents=True)
        (self.base / "data" / "screenplay.txt").write_text("ORIGINAL", encoding="utf-8")
        (self.base / "data" / "gone.txt").write_text("replaced away", encoding="utf-8")
        (self.base / "project.json").write_text(
            json.dumps({"name": "My Show", "created_at": "2026-01-01T00:00:00+00:00",
                        "last_backup_at": "2026-08-01T00:00:00+00:00"}),
            encoding="utf-8")

    def tearDown(self):
        paths.HOME, paths.PROJECTS_DIR = self._home, self._projects
        shutil.rmtree(self.tmp, ignore_errors=True)

    def payload(self):
        return zip_of("Other Production", {
            "data/screenplay.txt": "IMPORTED",
            "data/new.txt": "arrived with the zip",
            "project_state/approval_log.md": "# approvals\n",
        })

    def test_content_is_replaced(self):
        backup.import_into("my-show", self.payload())
        d = self.base / "data"
        self.assertEqual((d / "screenplay.txt").read_text(encoding="utf-8"), "IMPORTED")
        self.assertTrue((d / "new.txt").exists())
        self.assertFalse((d / "gone.txt").exists(),
                         "files absent from the zip must not survive the import")

    def test_production_keeps_its_own_identity(self):
        r = backup.import_into("my-show", self.payload())
        meta = json.loads((self.base / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["name"], "My Show")
        self.assertEqual(meta["created_at"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(meta["imported_from"], "Other Production")
        self.assertEqual(r["slug"], "my-show")
        self.assertTrue(meta["imported_at"])

    def test_stale_backup_stamp_is_cleared(self):
        """The old stamp described work that is no longer here."""
        backup.import_into("my-show", self.payload())
        self.assertEqual(backup.last_backup_at("my-show"), "")
        self.assertIsNone(backup.days_since_backup("my-show"))

    def test_safety_zip_holds_the_pre_import_state(self):
        r = backup.import_into("my-show", self.payload())
        safety = self.base / r["safety_zip"]
        self.assertTrue(safety.exists())
        with zipfile.ZipFile(safety) as z:
            self.assertEqual(z.read("data/screenplay.txt").decode(), "ORIGINAL")
            self.assertIn("data/gone.txt", z.namelist())

    def test_safety_zip_does_not_count_as_the_users_backup(self):
        """Taking it must not make the shelf read BACKED UP TODAY."""
        backup.import_into("my-show", self.payload())
        self.assertEqual(backup.last_backup_at("my-show"), "")

    def test_only_the_newest_safety_zip_is_kept(self):
        """Three full copies of a production, on the volume the production
        lives on, is a lot of disk for insurance — and a studio filled its
        volume (2026-08-07). One copy, downloadable, is the useful amount."""
        for _ in range(5):
            backup.import_into("my-show", self.payload())
        zips = list(self.base.glob("pre-import-*.zip"))
        self.assertEqual(len(zips), 1)

    def test_the_kept_copy_is_the_newest(self):
        first = backup.import_into("my-show", self.payload())["safety_zip"]
        (self.base / "data" / "screenplay.txt").write_text("SECOND", encoding="utf-8")
        second = backup.import_into("my-show", self.payload())["safety_zip"]
        self.assertNotEqual(first, second)
        self.assertTrue((self.base / second).exists())
        self.assertFalse((self.base / first).exists())
        with zipfile.ZipFile(self.base / second) as z:
            self.assertEqual(z.read("data/screenplay.txt").decode(), "SECOND")

    def test_safety_zips_never_ride_into_a_backup(self):
        backup.import_into("my-show", self.payload())
        payload, _ = backup.make_backup("my-show")
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            self.assertFalse([n for n in z.namelist() if "pre-import" in n])

    def test_zip_slip_is_refused_and_nothing_is_touched(self):
        evil = io.BytesIO()
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("project.json", json.dumps({"name": "evil"}))
            z.writestr("data/../../escape.txt", "x")
        with self.assertRaises(backup.BackupError):
            backup.import_into("my-show", evil.getvalue())
        self.assertEqual((self.base / "data" / "screenplay.txt").read_text(encoding="utf-8"),
                         "ORIGINAL")

    def test_a_non_zip_is_refused_before_anything_moves(self):
        with self.assertRaises(backup.BackupError):
            backup.import_into("my-show", b"this is not a zip")
        self.assertEqual((self.base / "data" / "screenplay.txt").read_text(encoding="utf-8"),
                         "ORIGINAL")

    def test_unknown_production_raises(self):
        with self.assertRaises(KeyError):
            backup.import_into("no-such-show", self.payload())

    def test_no_staging_dirs_are_left_behind(self):
        backup.import_into("my-show", self.payload())
        for junk in (".import-staging", ".import-replaced"):
            self.assertFalse((self.base / junk).exists(), junk)

    def test_round_trip_through_a_real_backup(self):
        """The zip the app itself produces must import cleanly."""
        payload, _ = backup.make_backup("my-show")
        (self.base / "data" / "screenplay.txt").write_text("DRIFTED", encoding="utf-8")
        backup.import_into("my-show", payload)
        self.assertEqual((self.base / "data" / "screenplay.txt").read_text(encoding="utf-8"),
                         "ORIGINAL")


class InspectBackup(unittest.TestCase):
    def test_reports_what_the_archive_holds(self):
        info = backup.inspect_backup(zip_of("Other Production", {
            "data/a.txt": "a", "data/b.txt": "bb",
            "project_state/approval_log.md": "# approvals\n",
        }, last_backup_at="2026-08-02T00:00:00+00:00"))
        self.assertEqual(info["name"], "Other Production")
        self.assertEqual(info["files"], 4)  # 3 + project.json
        self.assertEqual(info["counts"]["data"], 2)
        self.assertEqual(info["counts"]["project_state"], 1)
        self.assertEqual(info["counts"]["context"], 0)
        self.assertEqual(info["backed_up_at"], "2026-08-02T00:00:00+00:00")

    def test_writes_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        before = list(tmp.rglob("*"))
        backup.inspect_backup(zip_of("X", {"data/a.txt": "a"}))
        self.assertEqual(list(tmp.rglob("*")), before)
        shutil.rmtree(tmp, ignore_errors=True)

    def test_refuses_a_non_backup(self):
        with self.assertRaises(backup.BackupError):
            backup.inspect_backup(b"not a zip")

    def test_refuses_unexpected_members(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("secrets/keys.json", "{}")
        with self.assertRaises(backup.BackupError):
            backup.inspect_backup(buf.getvalue())


# ------------------------------------------------------------ via the API
import sys  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

import app.main as appmain  # noqa: E402


class ImportApi(unittest.TestCase):
    """The route's own guards: the typed-name confirmation and the 404."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-import-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
                       paths.SETTINGS, paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        self.client = TestClient(appmain.app)
        self.client.post("/api/projects", json={"name": "My Show"})
        self.zip = zip_of("Other Production", {"data/screenplay.txt": "IMPORTED"})

    def tearDown(self):
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def files(self):
        return {"file": ("backup.zip", io.BytesIO(self.zip), "application/zip")}

    def test_inspect_describes_the_archive(self):
        r = self.client.post("/api/projects/import/inspect", files=self.files())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "Other Production")

    def test_wrong_confirmation_name_refuses(self):
        r = self.client.post("/api/projects/import", files=self.files(),
                             data={"slug": "my-show", "confirm_name": "wrong"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("My Show", r.json()["detail"])
        self.assertEqual(
            (paths.PROJECTS_DIR / "my-show" / "data" / "screenplay.txt").exists(), False)

    def test_correct_confirmation_imports(self):
        r = self.client.post("/api/projects/import", files=self.files(),
                             data={"slug": "my-show", "confirm_name": "My Show"})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["imported_from"], "Other Production")
        self.assertEqual(
            (paths.PROJECTS_DIR / "my-show" / "data" / "screenplay.txt")
            .read_text(encoding="utf-8"), "IMPORTED")

    def test_unknown_production_is_404(self):
        r = self.client.post("/api/projects/import", files=self.files(),
                             data={"slug": "nope", "confirm_name": "nope"})
        self.assertEqual(r.status_code, 404)

    def test_a_non_zip_is_422_not_500(self):
        r = self.client.post("/api/projects/import",
                             files={"file": ("x.zip", io.BytesIO(b"nope"), "application/zip")},
                             data={"slug": "my-show", "confirm_name": "My Show"})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
