"""Regression tests for the 2026-08-02 product-app audit batch: path
traversal guards, canvas bounds, corrupt-state resilience, model-JSON
shape, quarantine enforcement, and restore staging."""
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

from app import assemble, autofill, backup, generate, paths, store  # noqa: E402
import app.main as appmain  # noqa: E402

from test_app_api import _redirect_home, _restore_home  # noqa: E402


class AuditFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-audit-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)

    def tearDown(self):
        _restore_home()

    # -- path traversal ----------------------------------------------------

    def test_activate_rejects_traversal_slugs(self):
        for slug in ("..", "C:/Users/x", "../other", ".hidden"):
            r = self.client.post("/api/projects/activate", json={"slug": slug})
            self.assertEqual(r.status_code, 404, slug)

    def test_backup_rejects_traversal_slugs(self):
        r = self.client.get("/api/projects/backup", params={"slug": "C:/Users/x"})
        self.assertEqual(r.status_code, 404)

    def test_spec_path_refuses_dot_led_ids(self):
        # '..' matched the old regex; delete_spec builds an rmtree target
        # from this id — data/ itself was one call-order change away.
        for bad in ("..", ".hidden", "..evil"):
            with self.assertRaises((KeyError, ValueError), msg=bad):
                store._spec_path(bad)
        self.assertTrue(str(store._spec_path("LOC_V001")).endswith("LOC_V001.json"))

    # -- canvas bounds -----------------------------------------------------

    def test_canvas_bounds_are_stated(self):
        for w, h in ((60000, 60000), (100, 100), (3840, 200)):
            with self.assertRaises(assemble.AssemblyError):
                assemble.check_canvas(w, h)
        assemble.check_canvas(3840, 2160)  # the default must pass
        assemble.check_canvas(4500, 2400)  # print-leaning preset too

    # -- corrupt state never bricks the app --------------------------------

    def test_corrupt_settings_set_aside_not_fatal(self):
        paths.SETTINGS.write_text("{truncated", encoding="utf-8")
        self.assertEqual(generate.load_settings(), {})
        self.assertFalse(paths.SETTINGS.exists())
        self.assertTrue(paths.SETTINGS.with_suffix(".json.corrupt").exists())

    def test_corrupt_subjects_set_aside_not_fatal(self):
        paths.ensure_dirs()
        paths.SUBJECTS.write_text("[oops", encoding="utf-8")
        self.assertEqual(store.list_subjects(), [])
        self.assertTrue(paths.SUBJECTS.with_suffix(".json.corrupt").exists())

    # -- model JSON shape --------------------------------------------------

    def test_parse_json_rejects_non_object(self):
        with self.assertRaises(autofill.AutofillError):
            autofill._parse_json('["a", "b"]')
        with self.assertRaises(autofill.AutofillError):
            autofill._parse_json('"just a string"')
        self.assertEqual(autofill._parse_json('{"ok": 1}'), {"ok": 1})

    # -- quarantine is enforced, not advisory ------------------------------

    def test_quarantined_file_does_not_resolve_for_active_records(self):
        png = io.BytesIO()
        from PIL import Image
        Image.new("RGB", (64, 64), (200, 60, 60)).save(png, "PNG")
        ref = store.add_reference("anchor.png", png.getvalue(),
                                  "SCENE_REFERENCE", [], [])
        rid = ref["id"]
        p = store.reference_image_path(rid)
        self.assertIsNotNone(p)
        # Simulate index/disk disagreement: file quarantined, record active.
        (paths.REF_QUARANTINE).mkdir(parents=True, exist_ok=True)
        p.rename(paths.REF_QUARANTINE / p.name)
        self.assertIsNone(store.reference_image_path(rid),
                          "an active record must never serve from quarantine")
        self.assertIsNotNone(
            store.reference_image_path(rid, include_quarantine=True))

    # -- counters ----------------------------------------------------------

    def test_next_counter_is_sequential_and_persisted(self):
        a = store.next_counter("cand_counter", "CAND")
        b = store.next_counter("cand_counter", "CAND")
        self.assertNotEqual(a, b)
        self.assertEqual(int(b.split("-")[1]), int(a.split("-")[1]) + 1)
        self.assertEqual(store.load_app_state()["cand_counter"],
                         int(b.split("-")[1]))

    # -- restore staging ---------------------------------------------------

    def _zip(self, members: dict[str, bytes]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for name, content in members.items():
                z.writestr(name, content)
        return buf.getvalue()

    def test_restore_failure_leaves_no_half_project(self):
        payload = self._zip({
            "project.json": json.dumps({"name": "Broken"}).encode(),
            "data/app_state.json": b"{}",
            "evil/../x": b"nope",  # traversal member → BackupError mid-list
        })
        with self.assertRaises(backup.BackupError):
            backup.restore_backup(payload)
        left = [d.name for d in paths.PROJECTS_DIR.iterdir()] \
            if paths.PROJECTS_DIR.exists() else []
        self.assertNotIn("broken", left)
        self.assertFalse(any(n.startswith(".restore-") for n in left),
                         "staging dirs must never survive a failed restore")

    def test_restore_success_and_dot_dirs_hidden_from_shelf(self):
        payload = self._zip({
            "project.json": json.dumps({"name": "Restored Film"}).encode(),
            "data/app_state.json": b"{}",
        })
        out = backup.restore_backup(payload)
        self.assertEqual(out["name"], "Restored Film")
        (paths.PROJECTS_DIR / ".restore-leftover").mkdir(parents=True)
        slugs = [p["slug"] for p in paths.list_projects()]
        self.assertIn(out["slug"], slugs)
        self.assertNotIn(".restore-leftover", slugs)


if __name__ == "__main__":
    unittest.main()


class StaleOriginFixTests(unittest.TestCase):
    """The railway-host origin can never pin an old build again (user-hit
    twice, 2026-08-04): direct browser hits redirect to the branded
    address, and index.html version-stamps its asset URLs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-origin-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)

    def tearDown(self):
        appmain.PUBLIC_URL = ""
        _restore_home()

    def test_index_version_stamps_assets(self):
        html = self.client.get("/").text
        ver = (Path(__file__).resolve().parents[1] / "VERSION").read_text().strip()
        self.assertIn(f'src="/app.js?v={ver}"', html)
        self.assertIn(f'href="/styles.css?v={ver}"', html)

    def test_railway_host_redirects_to_branded(self):
        appmain.PUBLIC_URL = "https://my-studio.screenboardstudio.com"
        r = self.client.get("/?x=1", follow_redirects=False,
                            headers={"host": "tenant-9.up.railway.app"})
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.headers["location"],
                         "https://my-studio.screenboardstudio.com/?x=1")
        # Proxied traffic (our router sets X-Forwarded-Host) passes.
        r2 = self.client.get("/", follow_redirects=False,
                             headers={"host": "tenant-9.up.railway.app",
                                      "x-forwarded-host": "my-studio.screenboardstudio.com"})
        self.assertNotEqual(r2.status_code, 301)
        # /api stays direct — healthz probes and the door depend on it.
        r3 = self.client.get("/api/healthz", follow_redirects=False,
                             headers={"host": "tenant-9.up.railway.app"})
        self.assertEqual(r3.status_code, 200)
