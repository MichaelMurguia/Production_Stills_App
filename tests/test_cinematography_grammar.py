"""The cinematography grammar that rides a render — and the ability to
take it back (user 2026-08-16: "the doc provides a prompt — shouldn't we
apply the prompt?", then "we need to evaluate the output, so we need to
be able to roll this back").

The anchor's WORDS never reached a render directly: they feed the bible
draft, which writes Lighting Language and Composition Rules, which ride
every prompt. The document's Image-Model Prompt is written for an image
model, not for a prose drafter — so it rides the render itself, as its
own block, and the compact form keeps feeding the bible.

Reversibility is the point of these tests: OFF is the default, and a
render made with the switch off must be byte-identical to one made before
the feature existed."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import bible, cinematography as cine, generate, paths  # noqa: E402

SPEC = {
    "specification_id": "S1", "subject": "A shack", "mode": "CANON_EXTRACTION",
    "scene": "A shack at dusk.", "render_intent": "Grounded.",
    "panels": [{"id": "P01", "title": "Interior", "purpose": "Show it.",
                "camera_lens": "85MM", "scale": "CLOSE"}],
}


class Grammar(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-cine-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR,
                       paths.ACTIVE_PROJECT_FILE, paths.SETTINGS,
                       paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        bible.save_text("# B\n\n## Rendering Language\n### Required\n"
                        "- Painterly.\n\n## Lighting Language\n- Hard sun.\n")

    def tearDown(self):
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def prompt(self):
        return generate.compile_panel_prompt(SPEC, SPEC["panels"][0], [])


class ItIsOffUntilYouSaySo(Grammar):
    def test_a_fresh_production_has_no_grammar_riding(self):
        s = cine.setting()
        self.assertEqual(s["key"], "")
        self.assertFalse(s["prompt_rides"])
        self.assertNotIn("CINEMATOGRAPHY GRAMMAR", self.prompt())

    def test_choosing_a_grammar_does_not_by_itself_change_a_render(self):
        """Picking a style writes the bible-facing words. Whether its page
        of prompt reaches a render is a separate, stated act."""
        before = self.prompt()
        cine.save_setting(key="cine-classical-adventure")
        self.assertEqual(self.prompt(), before)

    def test_the_switch_is_journaled_both_ways(self):
        cine.save_setting(key="cine-classical-adventure", prompt_rides=True)
        cine.save_setting(prompt_rides=False)
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("RIDES", log)
        self.assertIn("does not ride", log)


class ItRollsBackExactly(Grammar):
    def test_turning_it_off_restores_the_previous_prompt_byte_for_byte(self):
        """The whole ask. Anything less than identical is not a rollback,
        it is a second variant."""
        off = self.prompt()
        cine.save_setting(key="cine-classical-adventure", prompt_rides=True)
        on = self.prompt()
        self.assertNotEqual(on, off)
        cine.save_setting(prompt_rides=False)
        self.assertEqual(self.prompt(), off)

    def test_the_chosen_grammar_survives_the_rollback(self):
        """Turning it off is not forgetting which one you picked — you are
        evaluating, and you will turn it back on."""
        cine.save_setting(key="cine-classical-adventure", prompt_rides=True)
        cine.save_setting(prompt_rides=False)
        self.assertEqual(cine.setting()["key"], "cine-classical-adventure")

    def test_a_missing_document_cannot_break_a_render(self):
        cine.save_setting(key="cine-nonexistent-grammar", prompt_rides=True)
        self.assertNotIn("CINEMATOGRAPHY GRAMMAR", self.prompt())


class ItDefersToTheCamera(Grammar):
    def setUp(self):
        super().setUp()
        cine.save_setting(key="cine-classical-adventure", prompt_rides=True)

    def test_the_block_carries_the_documents_prompt_verbatim(self):
        st = cine.by_key("cine-classical-adventure")
        self.assertIn(st["prompt"], self.prompt())

    def test_it_sits_after_the_camera_and_says_the_camera_wins(self):
        p = self.prompt()
        self.assertLess(p.index("CAMERA — the shot"),
                        p.index("CINEMATOGRAPHY GRAMMAR"))
        head = p[p.index("CINEMATOGRAPHY GRAMMAR"):][:400]
        self.assertIn("the CAMERA block wins", head)
        self.assertIn("governs approach, not the shot", head)

    def test_it_names_the_grammar_it_is(self):
        self.assertIn("CLASSICAL ADVENTURE", self.prompt())


class EveryTakeSaysWhetherItRode(Grammar):
    def test_a_take_made_without_it_records_that(self):
        self.assertEqual(cine.stamp(), {"rides": False})

    def test_a_take_made_with_it_records_which_and_what_text(self):
        cine.save_setting(key="cine-classical-adventure", prompt_rides=True)
        st = cine.stamp()
        self.assertTrue(st["rides"])
        self.assertEqual(st["key"], "cine-classical-adventure")
        self.assertEqual(st["name"], "Classical Adventure")
        self.assertTrue(st["prompt_sha"],
                        "the document can change; a take says which text rode")

    def test_the_record_carries_it(self):
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        self.assertIn('"cinematography": _cine.stamp()', src)
        i = src.index('"cinematography": _cine.stamp()')
        # on the record a render writes, beside the spec hash it pairs with
        self.assertIn('"spec_hash": stable_hash(spec)', src[i - 400:i])
        self.assertIn('"candidate_id": cand_id', src[i - 600:i])


class TheSwitchReadsAsStateBeforeItIsHit(unittest.TestCase):
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")

    def test_the_panel_states_which_way_it_is_set(self):
        i = self.JS.index("async function cineRideSwitch")
        seg = self.JS[i:i + 2600]
        self.assertIn("rides every render", seg)
        self.assertIn("does not reach a render", seg)
        self.assertIn("Stop it riding renders", seg)

    def test_turning_it_on_states_the_consequence_first(self):
        i = self.JS.index("async function cineRideSwitch")
        seg = self.JS[i:i + 2600]
        self.assertIn("This WILL change what comes out", seg)
        self.assertIn("Reversible at any time", seg)
        self.assertIn("already approved ", seg)
        self.assertIn("are untouched", seg)

    def test_turning_it_off_asks_nothing(self):
        """A confirm on the way out of an experiment is friction on the
        act that makes the experiment safe."""
        i = self.JS.index("async function cineRideSwitch")
        seg = self.JS[i:i + 2600]
        self.assertIn("if (next && !(await askConfirm(", seg)

    def test_the_routes_exist(self):
        self.assertIn('@app.get("/api/cinematography/setting")', self.MAIN)
        self.assertIn('@app.put("/api/cinematography/setting")', self.MAIN)


class ItSurvivesConcurrentRenders(Grammar):
    """Ten concurrent renders allocate candidate ids while compiling their
    prompts. Reading app_state unlocked while another thread os.replace()s
    it raises PermissionError on Windows — the concurrency suite caught it
    the moment the grammar started reading that file."""

    def test_the_setting_is_read_under_the_counter_lock(self):
        src = (ROOT / "app/cinematography.py").read_text(encoding="utf-8")
        i = src.index("def setting()")
        seg = src[i:src.index("def save_setting", i)]
        self.assertIn("with paths.SWITCH_LOCK:", seg)

    def test_concurrent_reads_and_writes_do_not_raise(self):
        import threading
        errors = []

        def hammer(n):
            try:
                for _ in range(25):
                    cine.setting()
                    generate.store.next_counter("t_counter", "T")
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        ts = [threading.Thread(target=hammer, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertFalse(errors, errors)


if __name__ == "__main__":
    unittest.main()
