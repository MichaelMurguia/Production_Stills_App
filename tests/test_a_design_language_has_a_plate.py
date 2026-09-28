"""A design language gets its own generated plate.

User, 2026-09-28: "For DESIGN LANGUAGES thumbnails, have a generate button
that will generate an image. Before art bible, the thumbnail a progress
spinner that says 'waiting for art bible'. Once the Art Bible is created,
thumbnails will generate and populate these panels."

The cards had shown an approved panel in the language, which does not
exist until weeks into a production, so every card was a stated blank.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, paths, store  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")
NL = chr(10)


class _Home(unittest.TestCase):
    """Never the real install."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._was = dict(HOME=paths.HOME, PROJECTS_DIR=paths.PROJECTS_DIR,
                         ACTIVE=paths.ACTIVE_PROJECT_FILE,
                         SETTINGS=paths.SETTINGS, slug=paths.ACTIVE_PROJECT)
        t = Path(self._tmp.name)
        paths.HOME = t
        paths.PROJECTS_DIR = t / "projects"
        paths.ACTIVE_PROJECT_FILE = t / "active_project.json"
        paths.SETTINGS = t / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        self._mock = generate.mock_enabled
        generate.mock_enabled = lambda: True
        store.save_wizard_analysis({"design_worlds": [
            {"name": "Salt Pan Nomads", "description": "Patched canvas, bone and brass."},
            {"name": "The Descent", "description": "Matte hulls.", "status": "PROPOSED"},
        ]})

    def tearDown(self):
        generate.mock_enabled = self._mock
        paths.HOME = self._was["HOME"]
        paths.PROJECTS_DIR = self._was["PROJECTS_DIR"]
        paths.ACTIVE_PROJECT_FILE = self._was["ACTIVE"]
        paths.SETTINGS = self._was["SETTINGS"]
        paths.set_project(self._was["slug"])
        self._tmp.cleanup()

    def bible(self, extra=""):
        generate.save_style_bible(
            "## Rendering Language" + NL + "Production painting; value groups carry form."
            + NL + extra)


class ItRendersFromTheBible(_Home):
    def test_it_refuses_before_the_bible(self):
        with self.assertRaises(generate.GenerationError) as e:
            generate.language_plate("Salt Pan Nomads", "mock")
        self.assertIn("Art Direction Bible", str(e.exception))
        self.assertEqual(generate.load_language_plates()["plates"], [])

    def test_it_renders_and_records_a_plate(self):
        self.bible()
        out = generate.language_plate("Salt Pan Nomads", "mock")
        self.assertEqual(out["status"], "ready")
        self.assertEqual(out["key"], "salt-pan-nomads")
        p = generate.language_plate_path("salt-pan-nomads")
        self.assertTrue(p and p.exists())
        rec = generate.load_language_plates()["plates"][0]
        self.assertEqual(rec["name"], "Salt Pan Nomads")

    def test_it_uses_the_bibles_section_when_there_is_one(self):
        self.bible(NL + "## Salt Pan Nomads" + NL + "Rope lashings, sun-bleached hide.")
        self.assertTrue(generate.language_plate("salt pan nomads", "mock")["from_bible_section"])

    def test_it_falls_back_to_the_reads_words(self):
        self.bible()
        self.assertFalse(generate.language_plate("Salt Pan Nomads", "mock")["from_bible_section"])

    def test_an_unknown_language_is_refused(self):
        self.bible()
        with self.assertRaises(generate.GenerationError):
            generate.language_plate("Nobody", "mock")

    def test_a_failure_is_recorded_so_it_is_not_retried_on_its_own(self):
        self.bible()
        real = generate.mockflow.render
        generate.mockflow.render = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("engine down"))
        try:
            with self.assertRaises(generate.GenerationError):
                generate.language_plate("Salt Pan Nomads", "mock")
        finally:
            generate.mockflow.render = real
        rec = generate.load_language_plates()["plates"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("engine down", rec["error"])
        self.assertIsNone(generate.language_plate_path("salt-pan-nomads"))

    def test_two_at_once_is_refused_not_raced(self):
        self.bible()
        generate._LANG_BUSY["salt-pan-nomads"] = "Salt Pan Nomads"
        try:
            with self.assertRaises(generate.LanguagePlateBusy):
                generate.language_plate("Salt Pan Nomads", "mock")
            self.assertEqual(generate.load_language_plates()["rendering"], ["Salt Pan Nomads"])
        finally:
            generate._LANG_BUSY.clear()

    def test_every_engine_is_dispatched(self):
        """subject_portrait sends connector and custom engines to Gemini;
        this does not."""
        i = GEN.index("def language_plate(")
        seg = GEN[i:GEN.index("class LanguagePlateBusy", i)]
        for call in ("_render_custom(", "_render_connector(", "_render_openai(",
                     "_render_openai_chat(", "_render_gemini(", "mockflow.render("):
            self.assertIn(call, seg, call)


class TheRoutes(_Home):
    def client(self):
        from fastapi.testclient import TestClient
        import app.main as appmain
        return TestClient(appmain.app)

    def test_generate_list_and_serve(self):
        self.bible()
        c = self.client()
        r = c.post("/api/design-languages/plates", json={"name": "Salt Pan Nomads",
                                                          "provider": "mock"})
        self.assertEqual(r.status_code, 200, r.text)
        listed = c.get("/api/design-languages/plates").json()
        self.assertEqual([p["key"] for p in listed["plates"]], ["salt-pan-nomads"])
        img = c.get("/api/design-languages/plates/salt-pan-nomads/image")
        self.assertEqual(img.status_code, 200)

    def test_before_the_bible_is_a_stated_422(self):
        r = self.client().post("/api/design-languages/plates",
                               json={"name": "Salt Pan Nomads", "provider": "mock"})
        self.assertEqual(r.status_code, 422)

    def test_a_missing_plate_is_404(self):
        self.assertEqual(self.client().get(
            "/api/design-languages/plates/nothing/image").status_code, 404)


class ThePage(unittest.TestCase):
    def cards(self):
        i = JS.index("The picture, in order: this language's generated plate")
        return JS[i:JS.index("chip.append(art);", i)]

    def test_before_the_bible_it_waits_with_a_spinner(self):
        s = self.cards()
        self.assertIn('fill = wait("Waiting for art bible");', s)
        self.assertIn('<span class="spinner"></span>', s)

    def test_each_card_has_a_generate_button(self):
        s = self.cards()
        self.assertIn('gen.className = "lang-gen";', s)
        self.assertIn('ready ? "Regenerate" : "Generate"', s)
        self.assertIn("e.stopPropagation()", s, "generating is not expanding")

    def test_the_bible_save_starts_them(self):
        i = JS.index("const saveBible = async")
        self.assertIn("renderWorlds();", JS[i:i + 1500])

    def test_only_confirmed_languages_render_on_their_own_and_once(self):
        i = JS.index("const langAutoQueue = () => {")
        seg = JS[i:i + 700]
        self.assertIn('w.status !== "PROPOSED"', seg)
        self.assertIn("!plateFor(w.name)", seg, "a failed plate is not retried on its own")
        self.assertIn("wizLangAutoTried", seg)
        self.assertIn("!wizLangPlatesLoaded", seg, "never before the list is known")

    def test_the_page_never_derives_the_key(self):
        """One slug rule, server-side (the /one-rule skill)."""
        self.assertNotIn("replace(/[^a-z0-9]+/g", JS[JS.index("A generated plate per design language"):
                                                       JS.index("const langPollServer")])

    def test_the_button_sits_in_the_corner(self):
        self.assertIn(".lang-gen { position: absolute;", CSS)


class TheDevGuardCoversEveryKeyTheAppReads(unittest.TestCase):
    """Found building this: generate._client falls back to GOOGLE_API_KEY
    and dev.py did not blank it. The plates render on their own, so a
    guard with a hole in it could now spend without a click."""

    def test_google_api_key_is_blanked(self):
        dev = (ROOT / "scripts/dev.py").read_text(encoding="utf-8")
        for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
            self.assertIn(f'"{k}"', dev, k)


if __name__ == "__main__":
    unittest.main()
