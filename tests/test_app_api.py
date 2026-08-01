"""Functional pass over the app's API surface via TestClient: the cloud
auth gate, the projects lifecycle, and healthz — all against a throwaway
home so the real install is never touched."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import paths  # noqa: E402
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


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-api-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)

    def tearDown(self):
        appmain.ACCESS_TOKEN = ""
        _restore_home()

    def test_healthz_is_always_open(self):
        appmain.ACCESS_TOKEN = "sekrit"
        r = self.client.get("/api/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_auth_gate_when_token_set(self):
        appmain.ACCESS_TOKEN = "sekrit"
        page = self.client.get("/", follow_redirects=False)
        self.assertEqual(page.status_code, 303)
        self.assertEqual(page.headers["location"], "/login")
        self.assertEqual(self.client.get("/api/specs").status_code, 401)
        self.assertEqual(self.client.post(
            "/api/login", json={"token": "wrong"}).status_code, 401)
        ok = self.client.post("/api/login", json={"token": "sekrit"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.client.get("/api/specs").status_code, 200,
                         "the session cookie must open the API")

    def test_no_token_means_no_gate(self):
        appmain.ACCESS_TOKEN = ""
        self.assertEqual(self.client.get("/api/specs").status_code, 200)
        login = self.client.get("/login", follow_redirects=False)
        self.assertEqual(login.status_code, 303, "login page hides when auth is off")

    def test_projects_lifecycle(self):
        r = self.client.get("/api/projects").json()
        self.assertEqual(r["active"], "")
        made = self.client.post("/api/projects", json={"name": "Second Film"})
        self.assertEqual(made.status_code, 200)
        self.assertEqual(made.json()["active"], "second-film")
        self.assertEqual(self.client.get("/api/specs").json(), [],
                         "a fresh project starts empty")
        dup = self.client.post("/api/projects", json={"name": "Second Film"})
        self.assertEqual(dup.status_code, 409)
        back = self.client.post("/api/projects/activate", json={"slug": ""})
        self.assertEqual(back.json()["active"], "")
        missing = self.client.post("/api/projects/activate", json={"slug": "nope"})
        self.assertEqual(missing.status_code, 404)
        bad = self.client.post("/api/projects", json={"name": "   "})
        self.assertEqual(bad.status_code, 422)


if __name__ == "__main__":
    unittest.main()
