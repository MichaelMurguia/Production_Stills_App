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

    def test_ui_never_runs_stale(self):
        # Regression (2026-08-01): a hosted studio kept serving an old
        # app.js from browser cache after the server updated. Every UI
        # response must demand revalidation; API responses are untouched.
        appmain.ACCESS_TOKEN = ""
        for path in ("/", "/styles.css", "/app.js"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertEqual(r.headers.get("cache-control"), "no-cache", path)
        api = self.client.get("/api/healthz")
        self.assertNotEqual(api.headers.get("cache-control"), "no-cache")

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

    def test_breakdowns_gated_on_production_design(self):
        # User ruling 2026-08-01: no bible, no breakdowns — stated as 423,
        # enforced on both creation paths, cleared by saving the bible.
        r = self.client.post("/api/specs", json={"specification_id": "TEST_SHEET_V001",
                                                 "subject": "A test"})
        self.assertEqual(r.status_code, 423)
        self.assertIn("Art Direction Bible", r.json()["detail"])
        r = self.client.post("/api/specs/autofill",
                             json={"specification_id": "TEST_SHEET_V001",
                                   "prompt": "x"})
        self.assertEqual(r.status_code, 423)
        self.client.put("/api/style-bible",
                        json={"text": "## Cinematography\npainterly"})
        r = self.client.post("/api/specs", json={"specification_id": "TEST_SHEET_V001",
                                                 "subject": "A test"})
        self.assertEqual(r.status_code, 200, r.text)
        # User ruling 2026-08-02: records and prompts carry the ACTIVE
        # production's name, never a hardcoded film's.
        spec = self.client.get("/api/specs/TEST_SHEET_V001").json()["spec"]
        self.assertNotEqual(spec["project"], "The Beltminers")
        self.assertEqual(spec["project"], "Untitled Production")
        # Regression (user-caught 2026-08-02): the validator demanded the
        # hardcoded film and failed every real production's sheets. The
        # rule is presence, not a name.
        v = self.client.post("/api/specs/TEST_SHEET_V001/validate").json()
        joined = " ".join(map(str, v.get("errors", [])))
        self.assertNotIn("must be The Beltminers", joined)
        self.assertNotIn("project must be", joined)

    def test_screenplay_converts_to_efficient_format_at_import(self):
        # User ruling 2026-08-02: $31 of "image gen" was 2.3M input tokens
        # of re-sent PDF. Import extracts once; model calls read the text.
        import io
        content = b"INT. DINER - DAY\n\nA long counter. Twelve stools.\n"
        r = self.client.post("/api/screenplay",
                             files={"file": ("script.txt", io.BytesIO(content))})
        self.assertEqual(r.status_code, 200, r.text)
        rec = r.json()
        self.assertEqual(rec.get("text_file"), "_extracted.txt")
        self.assertGreater(rec.get("text_chars", 0), 10)
        from app import autofill, store
        self.assertIn("Twelve stools", store.screenplay_text_cached())
        doc, mime = autofill._screenplay_bytes()
        self.assertEqual(mime, "text/plain")
        self.assertIn(b"Twelve stools", doc)
        # Legacy backfill: strip the marker and the extraction re-persists.
        state = store.load_app_state()
        state["screenplay"].pop("text_file")
        store.save_app_state(state)
        (paths.SCREENPLAY_DIR / "_extracted.txt").unlink()
        self.assertIn("Twelve stools", store.screenplay_text_cached())
        self.assertTrue((paths.SCREENPLAY_DIR / "_extracted.txt").exists())

    def test_references_store_render_ready_formats(self):
        # Observed live 2026-08-02: an AVIF reference 400'd a generation.
        # Intake transcodes anything outside JPEG/PNG/WEBP; the compose
        # path rescues legacy files that predate the rule.
        import io
        from PIL import Image
        from app import generate, store
        buf = io.BytesIO()
        Image.new("RGB", (64, 40), (120, 90, 60)).save(buf, "TIFF")
        rec = store.add_reference("plate.tiff", buf.getvalue(), "CINEMATOGRAPHY_STYLE — test",
                                  ["contrast"], [], "")
        self.assertTrue(rec["file"].endswith(".jpg"),
                        f"TIFF must transcode at intake, got {rec['file']}")
        # Legacy backstop: plant an unsafe file behind an existing record.
        legacy = paths.REF_ORIGINALS / "REF-9999.tiff"
        buf2 = io.BytesIO()
        Image.new("RGB", (64, 40), (10, 20, 30)).save(buf2, "TIFF")
        legacy.write_bytes(buf2.getvalue())
        ready = generate._render_ready(legacy)
        self.assertTrue(str(ready).endswith(".render.jpg"))
        self.assertTrue(ready.exists())
        safe_path = paths.REF_ORIGINALS / rec["file"]
        self.assertEqual(generate._render_ready(safe_path), safe_path,
                         "safe formats pass through untouched")

    def test_interview_persists_per_production(self):
        # User ruling 2026-08-01: a refresh must never lose the interview.
        r = self.client.get("/api/wizard/interview").json()
        self.assertEqual(r["touchstones"], "")
        put = self.client.put("/api/wizard/interview", json={
            "touchstones": "McQuarrie production paintings",
            "palette": "warm dusk", "never": "glossy key art"})
        self.assertEqual(put.status_code, 200)
        r = self.client.get("/api/wizard/interview").json()
        self.assertEqual(r["touchstones"], "McQuarrie production paintings")
        self.assertEqual(r["medium"], "")
        # The gate chain sees it as real state.
        pd = self.client.get("/api/state").json()["stage_summary"]["production_design"]
        self.assertEqual(pd["interview_answered"], 3)
        # And it survives inside a backup (it lives in data/).
        zip_r = self.client.get("/api/projects/backup?slug=")
        self.assertEqual(zip_r.status_code, 200)
        import io as _io
        import zipfile as _zf
        names = _zf.ZipFile(_io.BytesIO(zip_r.content)).namelist()
        self.assertIn("data/interview.json", names)

    def test_no_template_art_direction(self):
        # Director's ruling 2026-08-01: with no bible, the app never
        # substitutes another film's art direction — the style text is
        # empty, a stated gap, not a Beltminers-flavored default.
        r = self.client.get("/api/style-bible").json()
        self.assertEqual(r["text"], "")
        self.assertNotIn("McQuarrie", r["text"])

    def test_first_run_states_itself_then_clears(self):
        # PRODUCTIONS_PLAN M6: a fresh install reports first_run so the UI
        # opens on "Name the show"; creating a production clears it.
        r = self.client.get("/api/projects").json()
        self.assertTrue(r["first_run"])
        self.client.post("/api/projects", json={"name": "First Show"})
        r = self.client.get("/api/projects").json()
        self.assertFalse(r["first_run"])

    def test_library_summary_reach_and_next(self):
        # PRODUCTIONS_PLAN M3: one row per production, each with reach,
        # counts, and its own next verb — computed without disturbing the
        # active production.
        self.client.post("/api/projects", json={"name": "Empty Film"})
        r = self.client.get("/api/projects/summary")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["active"], "empty-film",
                         "summary must restore the active production")
        row = next(p for p in data["projects"] if p["slug"] == "empty-film")
        self.assertEqual(len(row["reach"]), 5)
        self.assertTrue(all(c["state"] in ("ok", "bad", "never")
                            for c in row["reach"]))
        self.assertEqual(row["counts"], "NO SCREENPLAY YET")
        # LOCKED_STAGE_PLAN L3: the gate chain reads scan state live.
        state = self.client.get("/api/state").json()
        self.assertIn("scan_done", state["stage_summary"]["production_design"])
        self.assertFalse(state["stage_summary"]["production_design"]["scan_done"])
        self.assertEqual(row["next"]["kicker"], "DO THIS NEXT")
        self.assertIn("Upload a screenplay", row["next"]["text"])

    def test_duplicate_and_delete_lifecycle(self):
        self.client.post("/api/projects", json={"name": "Keeper"})
        dup = self.client.post("/api/projects/duplicate", json={"slug": "keeper"})
        self.assertEqual(dup.status_code, 200)
        self.assertEqual(dup.json()["name"], "Keeper copy")
        self.assertEqual(dup.json()["slug"], "keeper-copy")
        # The open production can never be deleted — gate, not surprise.
        active_del = self.client.post("/api/projects/delete",
                                      json={"slug": "keeper",
                                            "confirm_name": "Keeper"})
        self.assertEqual(active_del.status_code, 409)
        # Deleting demands the exact name.
        wrong = self.client.post("/api/projects/delete",
                                 json={"slug": "keeper-copy",
                                       "confirm_name": "nope"})
        self.assertEqual(wrong.status_code, 422)
        gone = self.client.post("/api/projects/delete",
                                json={"slug": "keeper-copy",
                                      "confirm_name": "Keeper copy"})
        self.assertEqual(gone.status_code, 200)
        slugs = [p["slug"] for p in gone.json()["projects"]]
        self.assertNotIn("keeper-copy", slugs)
        self.assertIn("keeper", slugs)

    def test_rename_by_slug_from_the_shelf(self):
        self.client.post("/api/projects", json={"name": "Alpha"})
        self.client.post("/api/projects", json={"name": "Beta"})  # now active
        r = self.client.post("/api/projects/rename",
                             json={"name": "Alpha Prime", "slug": "alpha"})
        self.assertEqual(r.status_code, 200)
        names = {p["slug"]: p["name"]
                 for p in self.client.get("/api/projects").json()["projects"]}
        self.assertEqual(names["alpha"], "Alpha Prime")
        self.assertEqual(names["beta"], "Beta", "only the named card renames")

class RenameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-rename-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)

    def tearDown(self):
        _restore_home()

    def test_rename_active_screenboard(self):
        r = self.client.post("/api/projects/rename", json={"name": "Dune But Cheaper"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "Dune But Cheaper")
        listed = self.client.get("/api/projects").json()["projects"]
        self.assertEqual(listed[0]["name"], "Dune But Cheaper")
        state = self.client.get("/api/state").json()
        self.assertEqual(state["project"], "Dune But Cheaper")
        self.assertEqual(self.client.post("/api/projects/rename",
                                          json={"name": "  "}).status_code, 422)


if __name__ == "__main__":
    unittest.main()


class CountsPluralise(unittest.TestCase):
    """One board is not "1 BOARDS" (user 2026-08-07). Every count on a
    production card can legitimately be 1 — one board, one panel, one
    reference — so each carries its own plural."""

    def _n(self, count, one, many=""):
        # the helper as it is written in api_projects_summary
        return f"{count} {one if count == 1 else (many or one + 'S')}"

    def test_one_is_singular(self):
        self.assertEqual(self._n(1, "BOARD"), "1 BOARD")
        self.assertEqual(self._n(1, "SCENE"), "1 SCENE")
        self.assertEqual(self._n(1, "REF"), "1 REF")

    def test_zero_and_many_are_plural(self):
        self.assertEqual(self._n(0, "BOARD"), "0 BOARDS")
        self.assertEqual(self._n(252, "SCENE"), "252 SCENES")

    def test_the_summary_uses_it_for_every_count(self):
        src = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = src.index("def _n(count: int")
        block = src[i:i + 600]
        for word in ("SCENE", "PANEL", "BOARD", "REF"):
            self.assertIn(f'_n(', block)
            self.assertIn(f'"{word}"', block, word)
        self.assertNotIn("SCENES ·", block, "no hardcoded plural survives")

    def test_the_locations_fact_pluralises_too(self):
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        self.assertIn('LOC${data.locations.length === 1 ? "" : "S"}', js)
