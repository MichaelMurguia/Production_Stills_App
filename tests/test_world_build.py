"""Process World Visualization: Production Design fills itself in.

User, 2026-10-04: "Once the screenplay is read, I want the Production
Design to fill out automatically ... make the art direction bible first,
then render the thumbnails." Rulings from the same conversation, each
held here:

- the upload's click is the consent; arriving at the stage is not;
- unset anchors take the script's proposal, set ones are never touched;
- proposed design languages and environments are confirmed;
- the Bible is written before any thumbnail, so thumbnails come FROM it;
- characters (only) get a small portrait awaiting a verdict;
- thumbnails are small, and rendered several at a time;
- a draft is built once.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient  # noqa: E402

from app import (bible, generate, language_previews as lp, paths, store,  # noqa: E402
                 wizard, world_build as wb)
import app.main as appmain  # noqa: E402
from test_app_api import _redirect_home, _restore_home  # noqa: E402

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
       b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
       b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")

ANALYSIS = {
    "design_worlds": [
        {"name": "Terran Concord", "description": "Imperial stone and brass."},
        {"name": "Oruna", "description": "Reed towns on stilts.", "status": "PROPOSED"},
    ],
    "environments": [
        {"name": "NORTHERN COAST", "notes": "Storm light on salt.", "status": "PROPOSED",
         "locations": ["EXT. HEADLAND - NIGHT"]},
    ],
    "subjects": [
        {"name": "Maren", "kind": "CHARACTER", "description": "Weathered pilot, forties."},
        {"name": "The Kestrel", "kind": "VEHICLE", "description": "Twin-engine fighter."},
    ],
}

BIBLE = """# Bible

## Rendering Language
Production painting.

## Terran Concord
Brass and white marble, tiered galleries.

## Oruna
Woven reed, tidal flats.

## Environments

### NORTHERN COAST
Salt-bleached timber, storm light.
"""

PROPOSALS = {"proposals": {
    "texture": {"name": "Lived-In", "value": "Lived-In world texture — wear where hands go"},
    "cinematography": {"name": "Formalist", "value": "Formalist / Architectural cinematography"},
    "rendering": {"name": "Production Painting", "value": "Production Painting rendering style"},
}}


class Build(unittest.TestCase):
    def setUp(self):
        _redirect_home(Path(tempfile.mkdtemp(prefix="sb-world-")))
        self.addCleanup(_restore_home)
        paths.ensure_dirs()
        store.set_screenplay("s.txt", b"INT. HALL - DAY\n\nBrass.\n")
        store.save_wizard_analysis(json.loads(json.dumps(ANALYSIS)))
        self.order, self.renders, self.portraits = [], [], []

        def fake_render(provider, prompt, refs, size, aspect, out, **kw):
            self.renders.append({"prompt": prompt, "size": size,
                                 "quality": kw.get("quality", "")})
            self.order.append("render")
            Path(out).write_bytes(PNG)

        def fake_draft(answers, provider):
            self.order.append("bible")
            self.answers = answers
            return {"markdown": BIBLE, "model": "fake"}

        def fake_suggest(provider, force=False):
            self.order.append("anchors")
            return PROPOSALS

        def fake_portrait(sid, provider="", size="1K", quality=""):
            self.order.append("portrait")
            self.portraits.append({"sid": sid, "size": size, "quality": quality})
            return {}

        patches = [
            mock.patch.object(generate, "render_to", side_effect=fake_render),
            mock.patch.object(generate, "image_engine", return_value="openai"),
            mock.patch.object(generate, "narrative_default", return_value="openai"),
            mock.patch.object(wizard, "draft_bible", side_effect=fake_draft),
            mock.patch.object(wizard, "suggest_anchors", side_effect=fake_suggest),
            mock.patch.object(wizard, "generate_swatches",
                              return_value={"groups": [{"swatches": [{}, {}]}]}),
            mock.patch.object(generate, "subject_portrait", side_effect=fake_portrait),
        ]
        for p in patches:
            p.start()
        self.addCleanup(mock.patch.stopall)

    def build(self):
        wb._run(paths.ACTIVE_PROJECT, wb._sha())
        return wb.status()

    def test_the_whole_stage_fills_in_order(self):
        st = self.build()
        self.assertEqual(st["state"], "done")
        self.assertEqual([s["state"] for s in st["steps"]], ["done"] * 7)
        self.assertEqual(self.order.index("anchors"), 0)
        first_render = self.order.index("render")
        self.assertLess(self.order.index("bible"), first_render,
                        "the Bible is written before any thumbnail")

    def test_proposals_are_confirmed_and_reach_the_bible(self):
        self.build()
        a = store.load_wizard_analysis()
        self.assertFalse(any(w.get("status") for w in a["design_worlds"]))
        self.assertFalse(any(e.get("status") for e in a["environments"]))
        self.assertIn("Oruna", [w["name"] for w in self.answers["worlds"]])

    def test_unset_anchors_take_the_proposal_and_set_ones_are_kept(self):
        (paths.DATA / "interview.json").write_text(json.dumps(
            {"medium": "Ink & Wash rendering style"}), encoding="utf-8")
        self.build()
        iv = store.interview_answers()
        self.assertEqual(iv["medium"], "Ink & Wash rendering style", "the director's pick stands")
        self.assertTrue(iv["texture"].startswith("Lived-In"))
        self.assertTrue(iv["light"].startswith("Formalist"))

    def test_the_bible_is_saved_like_the_editor_saves_it(self):
        self.build()
        self.assertIn("Terran Concord", bible.load_text())
        # At least the save itself; the anchor sync bumps it again when it
        # rewrites Rendering Language to the chosen style, as the editor's
        # Save does.
        self.assertGreaterEqual(store.load_app_state().get("bible_rev", 0), 1)

    def test_thumbnails_come_from_the_bible_small_and_medium(self):
        self.build()
        langs = {l["name"]: l for l in lp.status()["languages"]}
        envs = {e["name"]: e for e in lp.status()["environments"]}
        self.assertEqual(langs["Terran Concord"]["basis"], "bible")
        self.assertEqual(langs["Oruna"]["basis"], "bible")
        self.assertEqual(envs["NORTHERN COAST"]["basis"], "bible")
        self.assertTrue(all(r["size"] == "512" and r["quality"] == "medium"
                            for r in self.renders))
        self.assertTrue(any("Salt-bleached timber" in r["prompt"] for r in self.renders))

    def test_characters_only_get_a_small_portrait(self):
        self.build()
        names = {s["id"]: s["name"] for s in store.list_subjects()}
        self.assertEqual(sorted(names.values()), ["Maren"], "vehicles stay on demand")
        self.assertEqual([names[p["sid"]] for p in self.portraits], ["Maren"])
        self.assertEqual((self.portraits[0]["size"], self.portraits[0]["quality"]),
                         ("512", "medium"))

    def test_a_draft_is_built_once(self):
        self.build()
        self.assertFalse(wb.needed())
        n = len(self.order)
        self.assertEqual(wb.start()["state"], "done")
        time.sleep(0.05)
        self.assertEqual(len(self.order), n, "asking again spends nothing")

    def test_a_new_draft_is_due_again(self):
        self.build()
        store.set_screenplay("s2.txt", b"INT. HALL - NIGHT\n\nBrass.\n")
        self.assertTrue(wb.needed())

    def test_a_failed_bible_still_leaves_best_guess_thumbnails(self):
        wizard.draft_bible.side_effect = RuntimeError("model refused")
        st = self.build()
        steps = {s["key"]: s for s in st["steps"]}
        self.assertEqual(steps["bible"]["state"], "failed")
        self.assertEqual(steps["languages"]["state"], "done")
        self.assertEqual(lp.status()["languages"][0]["basis"], "guess")
        self.assertEqual(self.portraits, [], "portraits wait for a Bible")
        self.assertTrue(st["errors"])

    def test_a_switched_production_stops_the_build_before_it_writes(self):
        real = wb._step_anchors

        def switch_then(run):
            paths.ACTIVE_PROJECT = "someone-else"
            return real(run)
        with mock.patch.object(wb, "_step_anchors", side_effect=switch_then):
            wb._run("", wb._sha())
        paths.ACTIVE_PROJECT = ""
        self.assertNotIn("bible", self.order)
        self.assertNotEqual(wb._read().get("state"), "done")

    def test_a_moved_home_stops_the_build_too(self):
        """A test's temporary home being torn down, or another install,
        must never receive this build's writes."""
        real = wb._step_anchors
        other = Path(tempfile.mkdtemp(prefix="sb-world-other-"))

        def move_then(run):
            paths.HOME = other
            paths.set_project("")
            return real(run)
        with mock.patch.object(wb, "_step_anchors", side_effect=move_then):
            wb._run("", wb._sha())
        self.assertNotIn("bible", self.order)
        self.assertFalse((other / "data" / "world_build.json").exists())

    def test_images_render_several_at_a_time(self):
        self.assertGreaterEqual(wb.WORKERS, 2)


class Consent(unittest.TestCase):
    def setUp(self):
        _redirect_home(Path(tempfile.mkdtemp(prefix="sb-world-api-")))
        self.addCleanup(_restore_home)
        paths.ensure_dirs()
        self.client = TestClient(appmain.app)

    def test_a_read_draft_never_built_is_needed_but_not_consented(self):
        store.set_screenplay("s.txt", b"INT. HALL - DAY\n")
        store.save_wizard_analysis({"design_worlds": [{"name": "A", "description": "b"}]})
        st = self.client.get("/api/world/status").json()
        self.assertTrue(st["needed"])
        self.assertFalse(st["consented"], "arriving at the stage is not a click")

    def test_the_read_starts_the_build(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = main.index('@app.post("/api/wizard/analyze")')
        seg = main[i:main.index('@app.get("/api/world/status")', i)]
        self.assertIn("world_build.start()", seg)

    def test_an_upload_that_skips_the_read_still_starts_the_build(self):
        """User 2026-10-04, "my build is not working like that": a draft
        uploaded to a production that already had a read skipped the read
        (no re-scan of curated work), and the build only started when a
        read finished. The click is the consent either way."""
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        i = js.index("async function startTheRead()")
        early = js[i:js.index("const s = await api(\"/api/settings\")", i)]
        self.assertIn('api("/api/world/build", { method: "POST" })', early)

    def test_the_button_names_the_cost_of_the_click(self):
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        self.assertEqual(js.count(">Process World Visualization</button>"), 3)
        self.assertIn("This could take up to an hour.", js)
        self.assertEqual(js.count("${WORLD_CONSENT}"), 3,
                         "the line stands beside every button that starts it")


class TheScreen(unittest.TestCase):
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")

    def test_production_design_shows_visualizing_world_while_it_runs(self):
        i = self.JS.index("async function renderWizard() {")
        head = self.JS[i:i + 900]
        self.assertIn('if (ws && ws.state === "running")', head)
        self.assertIn("paintWorldBuild(ws)", head)
        self.assertIn('<h1 class="wp-title">Visualizing world</h1>', self.JS)

    def test_only_a_consented_build_resumes_on_arrival(self):
        self.assertIn('ws.state === "interrupted" && ws.consented', self.JS)

    def test_the_ground_drifts_slowly_and_stops_for_reduced_motion(self):
        b = self.CSS.split("\n.world-proc {")[1].split("}")[0]
        self.assertIn("animation: world-hue 240s", b)
        self.assertIn("@keyframes world-hue", self.CSS)
        i = self.CSS.index("@keyframes world-hue")
        self.assertIn(".world-proc { animation: none; }", self.CSS[i:i + 2500])


if __name__ == "__main__":
    unittest.main()
