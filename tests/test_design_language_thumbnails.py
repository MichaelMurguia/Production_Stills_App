"""Every design-language card gets a thumbnail before any panel exists.

User, 2026-10-04, looking at seven cards that each said "Examples will
appear here from your panels": "This section needs to auto generate images
once an art direction bible is created. Before that, it should make
thumbnail renderings based on 'Best Guess'."

What these tests hold, because the feature spends without being asked:
- a thumbnail is DUE only when missing, or once when the Bible now exists
  and the thumbnail is still a guess — never on a Bible edit;
- nothing renders from a name alone;
- a failed render leaves the last good thumbnail standing;
- one language never renders twice at once;
- a thumbnail is never a reference, so it can never ride into a panel.
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient  # noqa: E402

from app import bible, generate, language_previews as lp, paths, store  # noqa: E402
import app.main as appmain  # noqa: E402
from test_app_api import _redirect_home, _restore_home  # noqa: E402

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
       b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
       b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")

WORLDS = [
    {"name": "Terran Concord", "description": "Polished imperial stone and brass, "
     "tiered galleries, ceremonial order.", "keywords": ["concord", "imperial"]},
    {"name": "Northern Coast", "description": "Salt-bleached timber and iron, "
     "storm light.", "status": "PROPOSED"},
    {"name": "Nameless", "description": ""},
]

BIBLE = """# Production Bible

## Rendering Language
Production painting, readable form over surface.

## Terran Concord
Mirrored aisles, gold leaf, nine-hundred-seat tiers. Brass and white marble.
"""


class Thumbnails(unittest.TestCase):
    def setUp(self):
        _redirect_home(Path(tempfile.mkdtemp(prefix="sb-langprev-")))
        self.addCleanup(_restore_home)
        paths.ensure_dirs()
        store.save_wizard_analysis({"design_worlds": WORLDS})
        (paths.DATA / "interview.json").write_text(json.dumps(
            {"medium": "Production Painting rendering style"}), encoding="utf-8")
        self.calls = []

        def fake_render(provider, prompt, ref_paths, size, aspect, out, verbatim=False):
            self.calls.append({"provider": provider, "prompt": prompt,
                               "size": size, "aspect": aspect})
            Path(out).write_bytes(PNG)
        p1 = mock.patch.object(generate, "render_to", side_effect=fake_render)
        p2 = mock.patch.object(lp, "engine", return_value="openai")
        self.render_to = p1.start()
        p2.start()
        self.addCleanup(mock.patch.stopall)

    def by_name(self):
        return {l["name"]: l for l in lp.status()["languages"]}

    # -- before the Bible: best guess ---------------------------------------

    def test_before_the_bible_every_described_language_is_due_as_a_guess(self):
        s = self.by_name()
        self.assertTrue(s["Terran Concord"]["due"])
        self.assertEqual(s["Terran Concord"]["next_basis"], "guess")
        self.assertTrue(s["Northern Coast"]["due"], "proposed languages get one too")

    def test_a_name_alone_is_never_rendered(self):
        self.assertFalse(self.by_name()["Nameless"]["due"])
        with self.assertRaises(lp.PreviewError):
            lp.render("Nameless")
        self.assertEqual(self.calls, [])

    def test_a_guess_renders_from_the_read_and_the_anchors_at_thumbnail_size(self):
        st = lp.render("Terran Concord")
        self.assertEqual((st["state"], st["basis"], st["due"]), ("current", "guess", False))
        call = self.calls[-1]
        self.assertEqual((call["size"], call["aspect"]), ("1K", "3:2"))
        self.assertIn("Polished imperial stone and brass", call["prompt"])
        self.assertIn("RENDERING STYLE: Production Painting", call["prompt"])
        self.assertIn("No text, lettering", call["prompt"])
        self.assertTrue(lp.image_path(st["slug"]).exists())

    # -- once the Bible exists ---------------------------------------------

    def test_the_bible_upgrades_a_guess_once(self):
        lp.render("Terran Concord")
        bible.save_text(BIBLE)
        s = self.by_name()["Terran Concord"]
        self.assertTrue(s["due"], "a guess is re-rendered once the Bible exists")
        self.assertEqual(s["next_basis"], "bible")
        st = lp.render("Terran Concord")
        self.assertEqual((st["basis"], st["due"]), ("bible", False))
        self.assertIn("Mirrored aisles, gold leaf", self.calls[-1]["prompt"])

    def test_a_bible_edit_is_stated_never_spent(self):
        bible.save_text(BIBLE)
        lp.render("Terran Concord")
        n = len(self.calls)
        bible.save_text(BIBLE.replace("gold leaf", "silver leaf"))
        s = self.by_name()["Terran Concord"]
        self.assertEqual(s["state"], "outdated")
        self.assertFalse(s["due"], "editing the Bible must not bill a render by itself")
        self.assertEqual(len(self.calls), n)

    def test_a_language_the_bible_does_not_cover_stays_a_guess(self):
        bible.save_text(BIBLE)
        lp.render("Northern Coast")
        s = self.by_name()["Northern Coast"]
        self.assertEqual((s["basis"], s["next_basis"], s["due"]), ("guess", "guess", False))

    # -- failure, concurrency, isolation ------------------------------------

    def test_a_failed_render_keeps_the_last_good_thumbnail(self):
        lp.render("Terran Concord")
        img = lp.image_path("terran-concord")
        before = img.read_bytes()
        self.render_to.side_effect = generate.GenerationError("engine refused")
        with self.assertRaises(generate.GenerationError):
            lp.render("Terran Concord")
        self.assertEqual(img.read_bytes(), before)
        leftovers = [p for p in img.parent.iterdir() if p.name.startswith(".")]
        self.assertEqual(leftovers, [], "the private temp file is cleaned up")

    def test_one_language_never_renders_twice_at_once(self):
        gate, release = threading.Event(), threading.Event()

        def slow(provider, prompt, refs, size, aspect, out, verbatim=False):
            gate.set()
            release.wait(5)
            Path(out).write_bytes(PNG)
        self.render_to.side_effect = slow
        t = threading.Thread(target=lp.render, args=("Terran Concord",))
        t.start()
        gate.wait(5)
        self.assertTrue(self.by_name()["Terran Concord"]["rendering"])
        self.assertFalse(self.by_name()["Terran Concord"]["due"])
        with self.assertRaises(lp.PreviewError):
            lp.render("Terran Concord")
        release.set()
        t.join(5)

    def test_without_an_image_engine_nothing_renders(self):
        with mock.patch.object(lp, "engine", return_value=""):
            with self.assertRaises(lp.PreviewError):
                lp.render("Terran Concord")
        self.assertEqual(self.calls, [])

    def test_a_thumbnail_is_never_a_reference(self):
        lp.render("Terran Concord")
        self.assertEqual(store.list_references(), [],
                         "a reference could ride into a panel; a thumbnail must not")


class TheRoutes(unittest.TestCase):
    def setUp(self):
        _redirect_home(Path(tempfile.mkdtemp(prefix="sb-langprev-api-")))
        self.addCleanup(_restore_home)
        paths.ensure_dirs()
        store.save_wizard_analysis({"design_worlds": WORLDS[:1]})
        self.client = TestClient(appmain.app)

    def test_status_render_and_image(self):
        def fake(provider, prompt, refs, size, aspect, out, verbatim=False):
            Path(out).write_bytes(PNG)
        with mock.patch.object(generate, "render_to", side_effect=fake), \
                mock.patch.object(lp, "engine", return_value="openai"):
            s = self.client.get("/api/design-languages/previews").json()
            self.assertEqual(s["engine"], "openai")
            self.assertTrue(s["languages"][0]["due"])
            r = self.client.post("/api/design-languages/previews/render",
                                 json={"name": "Terran Concord"})
            self.assertEqual(r.status_code, 200, r.text)
            url = r.json()["url"]
        img = self.client.get(url)
        self.assertEqual(img.status_code, 200)
        self.assertEqual(img.headers["content-type"], "image/png")

    def test_unknown_language_and_traversal_are_404(self):
        r = self.client.post("/api/design-languages/previews/render", json={"name": "Nobody"})
        self.assertEqual(r.status_code, 404)
        for bad in ("..%2Fsettings", ".hidden", "missing"):
            self.assertEqual(self.client.get(
                f"/api/design-languages/previews/{bad}.png").status_code, 404, bad)

    def test_no_engine_is_a_stated_422(self):
        with mock.patch.object(lp, "engine", return_value=""):
            r = self.client.post("/api/design-languages/previews/render",
                                 json={"name": "Terran Concord"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("Connect an image model", r.json()["detail"])


class TheCards(unittest.TestCase):
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def test_one_queue_one_render_at_a_time(self):
        i = self.JS.index("async function runLangPreviewQueue(")
        body = self.JS[i:self.JS.index("async function renderWizard()", i)]
        self.assertIn("if (langPreviews.running || !list?.engine) return;", body)
        self.assertIn("!langPreviews.failed[l.slug]", body,
                      "a failed render is not retried by itself")
        self.assertIn("if (rendered) langPreviews.repaint?.(true);", body,
                      "the closing re-read must not restart an idle queue")

    def test_a_real_panel_wins_over_a_thumbnail(self):
        i = self.JS.index("const pic = shot || prev?.url")
        self.assertGreater(i, 0)

    def test_what_it_spends_is_stated_where_it_spends(self):
        """It renders without a click, so the cost is on screen: one image
        per language on the named engine, one more when the Bible covers
        it (/spend)."""
        self.assertIn('id="wiz-lang-cost"', self.JS)
        self.assertIn("1 IMAGE PER LANGUAGE ON ${eng.toUpperCase()}", self.JS)
        self.assertIn("1 MORE WHEN THE BIBLE FIRST COVERS IT", self.JS)

    def test_the_card_says_what_it_was_rendered_from(self):
        self.assertIn('prev.basis === "bible" ? "FROM THE BIBLE" : "BEST GUESS"', self.JS)


class OneDispatch(unittest.TestCase):
    def test_panels_and_thumbnails_share_the_engine_dispatch(self):
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        i = src.index("def generate_panel(")
        self.assertIn("notes = render_to(provider,", src[i:])
        lp_src = (ROOT / "app/language_previews.py").read_text(encoding="utf-8")
        self.assertIn("generate.render_to(provider,", lp_src)


if __name__ == "__main__":
    unittest.main()
