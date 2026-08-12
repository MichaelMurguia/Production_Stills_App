"""Every stage and selection is a shareable URL (user 2026-08-12):
/panels/SPEC-0001, /boards/SPEC-0001/BOARD-0002, /boards/SPEC-0001/arrange.

Server side: any non-API path boots the SAME version-stamped SPA document
as "/" (an unstamped fallback would reopen the stale-tab hole on shared
links), and the auth gate carries the destination through /login?next= so
a shared link survives sign-in. Client side: the router tables translate
paths to views, selections seed the persisted UI state, and history moves
keep the address honest."""
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

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
PY = (ROOT / "app/main.py").read_text(encoding="utf-8")

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


class DeepLinkServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-deep-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)

    def tearDown(self):
        appmain.ACCESS_TOKEN = ""
        _restore_home()

    def test_any_view_path_boots_the_stamped_spa(self):
        appmain.ACCESS_TOKEN = ""
        for path in ("/panels/SPEC-0001", "/boards/SPEC-0001/BOARD-0002",
                     "/boards/SPEC-0001/arrange", "/breakdowns/SPEC-0001",
                     "/production-design", "/reference"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertIn("text/html", r.headers.get("content-type", ""), path)
            self.assertIn('src="/app.js?v=', r.text,
                          f"{path} must serve the version-stamped document")
            self.assertIn("SB_BOOT_VERSION", r.text, path)

    def test_api_404_stays_json(self):
        r = self.client.get("/api/definitely-not-a-route")
        self.assertEqual(r.status_code, 404)
        self.assertIn("application/json", r.headers.get("content-type", ""))

    def test_the_gate_carries_the_destination(self):
        appmain.ACCESS_TOKEN = "sekrit"
        r = self.client.get("/panels/SPEC-0001", follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertEqual(r.headers["location"], "/login?next=/panels/SPEC-0001")
        # and "/" keeps the plain login address
        home = self.client.get("/", follow_redirects=False)
        self.assertEqual(home.headers["location"], "/login")

    def test_login_page_validates_next_client_side(self):
        # Same-origin paths only — "//evil.example" and absolute URLs
        # must fall back to "/". The guard is the regex in the login page.
        self.assertIn('/^\\/(?!\\/)/.test(rawNext)', PY)
        self.assertIn("location.replace(next)", PY)
        # the store handoff's hash strip keeps ?next= alive
        self.assertIn('"/login" + location.search', PY)


class DeepLinkClientWiring(unittest.TestCase):
    """Source pins for the SPA router — the path vocabulary is the
    product's, not the internal view names."""

    def test_the_path_vocabulary(self):
        for pair in ('specs: "breakdowns"', 'boards: "panels"',
                     'assembly: "boards"', 'wizard: "production-design"',
                     'references: "reference"', 'projects: "productions"'):
            self.assertIn(pair, JS)

    def test_routes_seed_selection_state(self):
        i = JS.index("function applyRoute")
        block = JS[i:i + 1200]
        self.assertIn('uiSet("openSpec", sel)', block)
        self.assertIn('uiSet("boardSpec", sel)', block)
        self.assertIn('uiSet("asmSpec", sel)', block)
        self.assertIn('uiSet("asm.room", sel)', block)
        self.assertIn('uiSet("openBoard", sub)', block)

    def test_history_stays_wired(self):
        self.assertIn('window.addEventListener("popstate"', JS)
        self.assertIn("applyRoute(location.pathname)", JS)
        # a drilled board is addressable
        self.assertIn('"/boards/"\n      + encodeURIComponent(b._spec.specification_id)',
                      JS)

    def test_selection_changes_update_the_address(self):
        # Every selection door calls syncUrl so a copied address is
        # always the page being looked at.
        self.assertGreaterEqual(JS.count("syncUrl(true)"), 5)

    def test_panel_links_scroll_to_the_panel(self):
        self.assertIn("_routePanel", JS)
        self.assertIn('scrollIntoView({ behavior: "smooth", block: "start" })',
                      JS)


if __name__ == "__main__":
    unittest.main()
