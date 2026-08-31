"""A read names the draft it read, and a stage does not retract itself.

Two faults found in one sitting, 2026-08-31, both from work happening in
the wrong order.

FIRST — the resurrected read. The browser keeps its own copy of the
screenplay read so it is never trapped on one machine; finding the studio
without one, it uploads it back. That copy is keyed by project slug, and
an emptied project keeps its slug. So a browser holding the previous
read put it straight back into a freshly reset project — the activity log
shows `PUT /api/wizard/analysis` at 11:27:09 and `POST /api/screenplay`
at 11:29:37, the read arriving two minutes before the screenplay it was
supposed to be about. The stage then reported 17 locations and 4 design
languages for a read that never ran, and nothing on the page said it was
second-hand. User: "this appeared instantly. Cached? It did not go
through the reading process."

A read is about ONE DRAFT. It could not say which — the filename cannot
answer that, since a revised draft keeps its name.

SECOND — the flashing rail. `renderScreenplay` painted the template, then
awaited three fetches, then removed the Replace panel because there was
nothing to replace. Arriving at the stage therefore showed a full side
rail and took half of it away again.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


class AReadNamesItsDraft(unittest.TestCase):
    def test_the_read_records_the_draft_it_read(self):
        i = MAIN.index('analysis["analyzed_at"] = store.utcnow()')
        seg = MAIN[i:MAIN.index("store.save_wizard_analysis(analysis)", i)]
        self.assertIn('analysis["screenplay_sha256"] = sp.get("sha256", "")', seg)

    def test_the_filename_is_not_the_answer(self):
        """A revised draft keeps its name."""
        i = MAIN.index('analysis["screenplay_sha256"]')
        self.assertIn("a revised\n    # draft keeps its name", MAIN[max(0, i - 400):i])


class RecoveryMustNameWhatIsHere(unittest.TestCase):
    """The client guard: it decides whether to upload at all."""

    def seg(self):
        i = JS.index("const localAnalysis = wizACache();")
        return JS[i:JS.index("if (wizAnalysis) wizACacheSet(wizAnalysis);", i)]

    def test_it_restores_only_a_read_of_the_draft_that_is_here(self):
        s = self.seg()
        self.assertIn('const here = state.screenplay?.sha256 || "";', s)
        self.assertIn('const said = localAnalysis?.screenplay_sha256 || "";', s)
        self.assertIn("here && said === here", s)

    def test_an_empty_project_receives_nothing(self):
        """`here` is empty with no screenplay, so the guard is false —
        which is the exact case that produced the bug."""
        self.assertIn("!wizAnalysis && localAnalysis && here && said === here", self.seg())

    def test_a_read_that_cannot_prove_what_it_read_stays_put(self):
        """Not deleted — it stays in the cache. But it is not restored,
        and the honest answer is to run the read."""
        self.assertIn("is not restored", self.seg())


class TheServerRefusesAForeignRead(unittest.TestCase):
    """The last line of defence, not the only one: another client, an old
    tab, or a replayed request never reaches the browser guard."""

    def app(self):
        from fastapi.testclient import TestClient
        import app.main as appmain
        return TestClient(appmain.app)

    def setUp(self):
        # The established pattern: never the real install (tests/README
        # and test_app_api.py).
        import tempfile
        from app import paths, store
        self._tmp = tempfile.TemporaryDirectory()
        self._was = dict(HOME=paths.HOME, PROJECTS_DIR=paths.PROJECTS_DIR,
                         ACTIVE=paths.ACTIVE_PROJECT_FILE,
                         SETTINGS=paths.SETTINGS, slug=paths.ACTIVE_PROJECT)
        tmp = Path(self._tmp.name)
        paths.HOME = tmp
        paths.PROJECTS_DIR = tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = tmp / "active_project.json"
        paths.SETTINGS = tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        self.store = store

    def tearDown(self):
        from app import paths
        paths.HOME = self._was["HOME"]
        paths.PROJECTS_DIR = self._was["PROJECTS_DIR"]
        paths.ACTIVE_PROJECT_FILE = self._was["ACTIVE"]
        paths.SETTINGS = self._was["SETTINGS"]
        paths.set_project(self._was["slug"])
        self._tmp.cleanup()

    def put(self, body):
        return self.app().put("/api/wizard/analysis", json=body)

    def test_a_read_naming_no_draft_is_still_saved(self):
        """An edit made on the page carries no sha and must keep working."""
        self.assertEqual(self.put({"logline": "x"}).status_code, 200)

    def test_a_read_of_another_draft_is_refused_and_says_which(self):
        st = self.store.load_app_state()
        st["screenplay"] = {"file": "a.pdf", "sha256": "a" * 64}
        self.store.save_app_state(st)
        r = self.put({"logline": "x", "screenplay_sha256": "b" * 64})
        self.assertEqual(r.status_code, 409)
        self.assertIn("bbbbbbbb", r.json()["detail"])
        self.assertIn("aaaaaaaa", r.json()["detail"])

    def test_a_read_of_the_draft_that_is_here_is_saved(self):
        st = self.store.load_app_state()
        st["screenplay"] = {"file": "a.pdf", "sha256": "a" * 64}
        self.store.save_app_state(st)
        self.assertEqual(self.put({"logline": "x",
                                   "screenplay_sha256": "a" * 64}).status_code, 200)

    def test_an_empty_project_refuses_a_read_outright(self):
        """The exact shape of the bug: a read arriving before any
        screenplay does."""
        r = self.put({"logline": "x", "screenplay_sha256": "a" * 64})
        self.assertEqual(r.status_code, 409)
        self.assertIn("no screenplay here", r.json()["detail"])


class TheStageDoesNotRetractItself(unittest.TestCase):
    def test_it_asks_before_it_paints(self):
        i = JS.index("async function renderScreenplay() {")
        seg = JS[i:JS.index("const sp = state.screenplay;", i)]
        self.assertLess(seg.index('api("/api/state")'),
                        seg.index('useTemplate("tpl-screenplay")'))

    def test_the_replace_panel_is_removed_in_the_same_paint(self):
        """Not a tick later, which is what the eye caught."""
        i = JS.index("async function renderScreenplay() {")
        seg = JS[i:JS.index("const sp = state.screenplay;", i)]
        self.assertNotIn("await", seg[seg.index('useTemplate("tpl-screenplay")'):])

    def test_the_template_still_ships_both_panels(self):
        """The rail is right for a project that HAS a screenplay; the fix
        is when it paints, not what it holds."""
        html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
        i = html.index('id="tpl-screenplay"')
        seg = html[i:html.index("</template>", i)]
        self.assertIn('id="dash-screenplay"', seg)
        self.assertIn('id="screenplay-form"', seg)


if __name__ == "__main__":
    unittest.main()
