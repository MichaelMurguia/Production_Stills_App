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


class TwoLeversNotThree(Grammar):
    """User, 2026-08-22: "there should be no switch on the panels in the
    Production Design tab. That sets the default. It should be
    over-rideable on the panel render tab."

    A third lever stood between the other two — an off-by-default switch
    deciding whether a chosen grammar reached a render at all. It was
    built on 2026-08-16 so the feature could be evaluated and rolled back,
    and it did that job. What it left was a control that silently decided
    whether the production's choice and the panel's override meant
    anything.

    Production Design now sets a default and that default renders. The
    panel is where it is varied or refused.
    """

    def test_a_fresh_production_has_no_grammar(self):
        self.assertEqual(cine.setting()["key"], "")
        self.assertNotIn("CINEMATOGRAPHY GRAMMAR", self.prompt())

    def test_the_setting_carries_a_default_and_nothing_else(self):
        """The retired field must not linger as a vestigial key that some
        later reader treats as meaningful."""
        self.assertEqual(set(cine.setting()), {"key"})
        import inspect
        self.assertEqual(list(inspect.signature(cine.save_setting).parameters),
                         ["key"], "nothing else can be set")

    def test_choosing_a_default_puts_it_in_every_render(self):
        before = self.prompt()
        cine.save_setting(key="cine-classical-adventure")
        after = self.prompt()
        self.assertNotEqual(after, before)
        self.assertIn("CINEMATOGRAPHY GRAMMAR", after)

    def test_choosing_a_default_is_journaled(self):
        cine.save_setting(key="cine-classical-adventure")
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("production default grammar", log)
        self.assertIn("cine-classical-adventure", log)

    def test_clearing_the_default_restores_the_prompt_byte_for_byte(self):
        """Rollback survives the switch's removal — it is now clearing the
        default rather than throwing a toggle. Anything less than
        identical is not a rollback, it is a second variant."""
        none = self.prompt()
        cine.save_setting(key="cine-classical-adventure")
        self.assertNotEqual(self.prompt(), none)
        cine.save_setting(key="")
        self.assertEqual(self.prompt(), none)

    def test_a_panel_can_roll_it_back_for_itself(self):
        """The per-panel equivalent, which is what the switch's removal
        leaves in its place."""
        cine.save_setting(key="cine-classical-adventure")
        panel = {**SPEC["panels"][0], "cinematography": "NONE"}
        self.assertNotIn("CINEMATOGRAPHY GRAMMAR",
                         generate.compile_panel_prompt(SPEC, panel, []))

    def test_a_missing_document_cannot_break_a_render(self):
        cine.save_setting(key="cine-nonexistent-grammar")
        self.assertNotIn("CINEMATOGRAPHY GRAMMAR", self.prompt())

    def test_no_switch_survives_in_the_client(self):
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        self.assertNotIn("cineRideSwitch", js)
        self.assertNotIn("prompt_rides", js)
        self.assertNotIn("Add it to every render", js)


class ItDefersToTheCamera(Grammar):
    def setUp(self):
        super().setUp()
        cine.save_setting(key="cine-classical-adventure")

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
        self.assertEqual(cine.stamp(), {"rides": False, "refused": False})

    def test_a_take_made_with_it_records_which_and_what_text(self):
        cine.save_setting(key="cine-classical-adventure")
        st = cine.stamp()
        self.assertTrue(st["rides"])
        self.assertEqual(st["key"], "cine-classical-adventure")
        self.assertEqual(st["name"], "Classical Adventure")
        self.assertTrue(st["prompt_sha"],
                        "the document can change; a take says which text rode")

    def test_the_record_carries_it(self):
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        self.assertIn('"cinematography": _cine.stamp(panel)', src,
                      "the stamp records the PANEL's grammar, not just "
                      "the production's")
        i = src.index('"cinematography": _cine.stamp(panel)')
        # on the record a render writes, beside the spec hash it pairs with
        self.assertIn('"spec_hash": stable_hash(spec)', src[i - 400:i])
        self.assertIn('"candidate_id": cand_id', src[i - 600:i])


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


class NothingForcesThePanelWider(unittest.TestCase):
    """A regression shipped 2026-08-16: replacing a neighbouring CSS block
    deleted `.cine-ride`, so the strip fell back to `.lock-strip`'s
    `flex-direction: row` and `gate-text { flex: none }` — right for one
    short fact, and it blew a paragraph out to twice the panel's width.
    The symptom was a horizontal scrollbar on the whole modal."""

    CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")

    def test_the_strip_wraps_and_its_text_can_shrink(self):
        import re
        b = re.search(r"\.cine-ride \{([^}]*)\}", self.CSS)
        self.assertTrue(b, ".cine-ride was deleted again")
        self.assertIn("flex-wrap: wrap", b.group(1))
        t = re.search(r"\.cine-ride \.gate-text \{([^}]*)\}", self.CSS)
        self.assertTrue(t)
        self.assertIn("flex: 1 1", t.group(1))
        self.assertIn("min-width: 0", t.group(1))

    def test_the_panel_refuses_to_be_widened_by_its_contents(self):
        """The backstop, so the next deleted block is a layout nit rather
        than a scrollbar across the whole surface."""
        import re
        b = re.search(r"\.rs-modal > \* \{([^}]*)\}", self.CSS)
        self.assertTrue(b)
        self.assertIn("min-width: 0", b.group(1))
        self.assertIn("max-width: 100%", b.group(1))


class AFailedLoadIsStatedNotSwallowed(unittest.TestCase):
    """Reported 2026-08-21: "on the Production Design board — failed to
    fetch cinematography styles."

    The cause that time was a dead port, not the app. But the report
    exposed a real one: `loadCinemaStyles()` caught every failure and
    returned the empty list, so a picker that could not reach its grammars
    rendered as a picker with none.

    That is not a cosmetic distinction here. The grammars are READ from
    docs/CINEMATOGRAPHY_STYLES.md rather than hardcoded, so "this document
    defines no styles" is a genuinely possible answer — and a silently
    empty list is indistinguishable from it. The one case the user can act
    on (the app cannot reach the server) looked exactly like the one they
    cannot.
    """

    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def body(self):
        i = self.JS.index("async function loadStyleLibrary(")
        return self.JS[i:i + 1400]

    def test_the_failure_reaches_the_user(self):
        b = self.body()
        self.assertIn("catch (err)", b)
        self.assertIn("toast(", b)
        self.assertNotIn("catch { return into; }", b)

    def test_it_names_where_the_grammars_come_from(self):
        """So the user can tell a missing document from a broken fetch."""
        self.assertIn("STYLE_DOCS[library]", self.body())
        self.assertIn("docs/CINEMATOGRAPHY_STYLES.md", self.JS)

    def test_the_failure_is_recorded_on_the_cache(self):
        """An empty list that failed must be distinguishable from an empty
        list that is genuinely empty, for any later caller."""
        self.assertIn("into.failed = true", self.body())


class APanelCanSetItsOwnGrammar(unittest.TestCase):
    """User, 2026-08-22: "check that we can actually set it when rendering
    a panel, including None. and if not - make it so." It could not — the
    grammar was production-wide, `prompt_block()` took no panel, and there
    was no way to refuse it for one render.

    Three states, the shape every camera axis already uses: unset inherits
    the production's choice, a key overrides it, NONE refuses it for this
    panel alone.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-cine-"))
        self._home, self._slug = paths.HOME, paths.ACTIVE_PROJECT
        paths.HOME = self.tmp
        paths.set_project("")
        paths.ensure_dirs()
        from app import store
        store._atomic_write_json(store._spec_path("SPEC-0001"), {
            "specification_id": "SPEC-0001", "locked": False, "status": "DRAFT",
            "panels": [{"id": "P1", "required_objects": [], "brief": "x"}]})

    def tearDown(self):
        paths.HOME = self._home
        paths.set_project(self._slug)

    def key(self):
        from app import cinematography as cine
        return cine.styles()[2]["key"]

    def panel(self):
        from app import store
        return store.get_spec("SPEC-0001")["panels"][0]

    def test_a_panel_can_name_a_grammar(self):
        from app import store, cinematography as cine
        store.amend_panel_camera("SPEC-0001", "P1", {"cinematography": self.key()})
        self.assertEqual(cine.resolve(self.panel())["key"], self.key())

    def test_a_panel_can_refuse_one(self):
        from app import store, cinematography as cine
        cine.save_setting(key=self.key())
        self.assertIsNotNone(cine.resolve({}), "the production default rides")
        store.amend_panel_camera("SPEC-0001", "P1", {"cinematography": "NONE"})
        self.assertIsNone(cine.resolve(self.panel()),
                          "NONE wins over the production default")
        self.assertTrue(cine.stamp(self.panel())["refused"],
                        "a take made under NONE says so")

    def test_a_panel_grammar_works_with_no_production_default(self):
        """A panel may name a grammar for a production that has chosen
        none — the panel is a full statement, not a modifier on one."""
        from app import store, cinematography as cine
        self.assertEqual(cine.setting()["key"], "")
        store.amend_panel_camera("SPEC-0001", "P1", {"cinematography": self.key()})
        block = cine.prompt_block(self.panel())
        self.assertTrue(block)
        self.assertIn("This panel names this grammar itself", block[0])

    def test_clearing_returns_it_to_the_production(self):
        from app import store
        store.amend_panel_camera("SPEC-0001", "P1", {"cinematography": self.key()})
        store.amend_panel_camera("SPEC-0001", "P1", {"cinematography": ""})
        self.assertNotIn("cinematography", self.panel())

    def test_a_camera_only_amend_does_not_clear_it(self):
        """The route touches a field only if the caller names it, and the
        client only sends the grammar when the row actually drew it."""
        from app import store
        store.amend_panel_camera("SPEC-0001", "P1", {"cinematography": self.key()})
        store.amend_panel_camera("SPEC-0001", "P1", {"camera_angle": "LOW"})
        self.assertEqual(self.panel().get("cinematography"), self.key())

    def test_an_unknown_grammar_is_refused_not_dropped(self):
        """A silent drop would read on screen as "inherit" and render
        something the user did not ask for."""
        from app import store
        with self.assertRaises(ValueError):
            store.amend_panel_camera("SPEC-0001", "P1",
                                     {"cinematography": "cine-nonsense"})

    def test_the_stamp_says_where_the_grammar_came_from(self):
        from app import store, cinematography as cine
        store.amend_panel_camera("SPEC-0001", "P1", {"cinematography": self.key()})
        self.assertEqual(cine.stamp(self.panel())["from"], "panel")
        cine.save_setting(key=self.key())
        self.assertEqual(cine.stamp({})["from"], "production")

    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def test_the_control_offers_inherit_none_and_every_grammar(self):
        JS = self.JS
        self.assertIn("function grammarSelect", JS)
        self.assertIn('None — no grammar', JS)
        self.assertIn('data-f="${prefix}-grammar"', JS)
        # only where a blank exists — the defaults card would point at itself
        self.assertIn("${blank ? grammarSelect(prefix, obj?.cinematography, blank, disabled) : \"\"}", JS)

    def test_the_picker_says_it_is_only_a_default(self):
        JS = self.JS
        i = JS.index('title: "Cinematography"')
        seg = JS[i:i + 900]
        self.assertIn("sets the production default", seg)
        self.assertIn("changed", seg)


class TheGrammarOutranksTheBibleOnColour(unittest.TestCase):
    """User-hit 2026-08-22: set Chromatic / Operatic, got a desaturated
    frame back.

    Both blocks were in the prompt. The bible's Lighting Language is a
    SYNTHESIS written when the bible was drafted — under whatever grammar
    was chosen then — and it survives a change of anchor because the
    production's own contrast rules and atmosphere studies live in it.
    That bible carried "maintain generally restrained saturation" and
    "avoid unmotivated colored light" from its Classical Adventure draft,
    and the art-direction block closes with "non-negotiable; it overrides
    model defaults". The model obeyed the last and strongest thing it was
    told.

    So precedence is stated, and stated LAST."""

    def setUp(self):
        import tempfile
        from pathlib import Path as _P
        from app import paths, store
        self._home, self._slug = paths.HOME, paths.ACTIVE_PROJECT
        self.addCleanup(self._restore)
        paths.HOME = _P(tempfile.mkdtemp(prefix="prec-"))
        paths.set_project("")
        paths.ensure_dirs()
        paths.BIBLE.parent.mkdir(parents=True, exist_ok=True)
        paths.BIBLE.write_text(
            "# P" + chr(10) * 2
            + "## Rendering Language" + chr(10) + "### Required" + chr(10)
            + "- Production Painting rendering style - x." + chr(10) * 2
            + "## Lighting Language" + chr(10)
            + "- Maintain generally restrained saturation." + chr(10),
            encoding="utf-8")
        self.spec = store.new_spec("S1", "cockpit", "CANON_EXTRACTION")
        self.spec["panels"] = [{"id": "P01", "title": "H", "purpose": "the cockpit"}]
        store.save_spec("S1", self.spec)
        self.panel = self.spec["panels"][0]

    def _restore(self):
        from app import paths
        paths.HOME = self._home
        paths.set_project(self._slug)

    def compiled(self):
        from app import generate
        return generate.compile_panel_prompt(self.spec, self.panel, [])

    def test_no_grammar_means_no_precedence_line(self):
        """A production without one renders byte-identically to before,
        which is what makes this reversible."""
        self.assertNotIn("WHERE THEY DISAGREE", self.compiled())

    def test_it_is_stated_AFTER_the_bible_not_before(self):
        """Position is the whole point: the bible's own closing line
        claims to override defaults, so anything meant to outrank it has
        to come later."""
        from app import cinematography
        cinematography.save_setting(cinematography.styles()[0]["key"])
        lines = self.compiled().splitlines()
        i = next(n for n, l in enumerate(lines) if l.startswith("VISUAL STYLE"))
        j = next(n for n, l in enumerate(lines) if "restrained saturation" in l)
        k = next(n for n, l in enumerate(lines) if l.startswith("WHERE THEY DISAGREE"))
        self.assertLess(i, k)
        self.assertLess(j, k)

    def test_it_names_the_grammar_that_is_actually_riding(self):
        from app import cinematography
        st = cinematography.styles()[0]
        cinematography.save_setting(st["key"])
        self.assertIn(st["name"].upper(), self.compiled())

    def test_it_claims_light_and_colour_only(self):
        """Narrow on purpose. The bible keeps medium, finish, materials,
        world condition and what may appear — a grammar that could
        overrule the rendering style would undo the anchor split."""
        from app import cinematography
        cinematography.save_setting(cinematography.styles()[0]["key"])
        i = self.compiled().index("WHERE THEY DISAGREE")
        seg = self.compiled()[i:i + 700]
        for owns in ("saturation", "hue", "contrast", "value key"):
            self.assertIn(owns, seg)
        for keeps in ("medium", "brushwork", "finish", "materials"):
            self.assertIn(keeps, seg)

    def test_a_panel_that_refused_a_grammar_gets_no_line(self):
        """NONE means no grammar, so there is nothing to give precedence
        to and nothing to say."""
        from app import cinematography
        cinematography.save_setting(cinematography.styles()[0]["key"])
        self.panel["cinematography"] = "NONE"
        self.assertNotIn("WHERE THEY DISAGREE", self.compiled())


if __name__ == "__main__":
    unittest.main()
