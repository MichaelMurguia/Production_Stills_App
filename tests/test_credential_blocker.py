"""A missing credential is a blocker (user ruling 2026-08-18).

The seam this closes: `blocking()` had no notion of engines, so a keyless
install's Status read "Upload the screenplay" and never said that nothing
could actually run. The header dots were the only signal, and a user who
skipped the walkthrough got only the dots.

The other half is a one-rule consolidation. "Does this install have a
usable credential" was being answered in four places — inline in
`/api/settings`, again in `_role_states` for the header dots, again as
`anyCred` in the client, and it was about to be answered a fifth time
here. `generate.capability()` is now the single answer; these tests pin
it, and `KindsAreFullyWired` stops the next new blocker kind from shipping
half-connected.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, insights, paths, store  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
INSIGHTS = (ROOT / "app/insights.py").read_text(encoding="utf-8")


class Install(unittest.TestCase):
    """A throwaway home AND a cleared environment. Without the second half
    these tests pass or fail depending on whether the developer's shell
    happens to export OPENAI_API_KEY — which it does on this machine."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-cred-"))
        self._saved = {k: paths.HOME for k in ()}
        self._home, self._settings = paths.HOME, paths.SETTINGS
        self._slug = paths.ACTIVE_PROJECT
        paths.HOME = self.tmp
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        self._env = {k: os.environ.pop(k, None)
                     for k in ("OPENAI_API_KEY", "GEMINI_API_KEY",
                               "SCREENBOARD_DEBUG_TOOLS")}

    def tearDown(self):
        paths.HOME, paths.SETTINGS = self._home, self._settings
        paths.set_project(self._slug)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def settings(self, **kw):
        paths.SETTINGS.write_text(json.dumps(kw), encoding="utf-8")


class CapabilityTests(Install):
    def test_a_bare_install_can_run_nothing(self):
        cap = generate.capability()
        self.assertFalse(cap["narrative"]["usable"])
        self.assertFalse(cap["image"]["usable"])
        self.assertFalse(cap["any_credential"])
        self.assertFalse(cap["narrative"]["failed"],
                         "nothing configured is not the same as failing")

    def test_one_openai_key_serves_both_roles(self):
        self.settings(openai_api_key="sk-test")
        cap = generate.capability()
        self.assertTrue(cap["narrative"]["usable"])
        self.assertTrue(cap["image"]["usable"])
        self.assertTrue(cap["any_credential"])

    def test_an_environment_key_counts(self):
        os.environ["GEMINI_API_KEY"] = "g-test"
        cap = generate.capability()
        self.assertTrue(cap["image"]["usable"])
        self.assertIn("gemini", cap["narrative"]["engines"])

    def test_a_key_that_failed_its_own_test_is_not_usable(self):
        """Telling someone to connect an engine when they have one that is
        failing sends them to the wrong fix — hence `failed`, and hence the
        different copy on the blocker."""
        self.settings(openai_api_key="sk-test",
                      engine_tests={"openai": {"ok": False},
                                    "openai-chat": {"ok": False}})
        cap = generate.capability()
        self.assertFalse(cap["narrative"]["usable"])
        self.assertFalse(cap["image"]["usable"])
        self.assertTrue(cap["narrative"]["failed"])
        self.assertTrue(cap["image"]["failed"])
        self.assertTrue(cap["any_credential"],
                        "a failing key is still a credential — the Settings "
                        "page must stay a control panel, not revert to setup")

    def test_an_untested_key_is_usable(self):
        """`warn` on the header dots, but it has never been proven to fail
        and the app will happily call it."""
        self.settings(openai_api_key="sk-test")
        self.assertTrue(generate.capability()["image"]["usable"])

    def test_a_narrative_only_credential_leaves_the_image_role_blocked(self):
        self.settings(anthropic_api_key="ak-test")
        cap = generate.capability()
        self.assertTrue(cap["narrative"]["usable"])
        self.assertFalse(cap["image"]["usable"])

    def test_the_mock_engine_runs_without_configuring_the_install(self):
        """The debug dry-run makes the pipeline runnable without making the
        install configured — so no blocker, but Settings still offers its
        setup form to the owner."""
        os.environ["SCREENBOARD_DEBUG_TOOLS"] = "1"
        self.settings(debug_mock=True)
        cap = generate.capability()
        self.assertTrue(cap["narrative"]["usable"])
        self.assertTrue(cap["image"]["usable"])
        self.assertFalse(cap["any_credential"])


class BlockerTests(Install):
    def kinds(self):
        return [b["kind"] for b in insights.blocking()]

    def keyrows(self):
        return [b for b in insights.blocking() if b["kind"] == "KEY"]

    def test_a_keyless_install_says_so(self):
        """TRIAGE §2 (2026-08-18): ONE row per missing credential, never
        one per stage — there is one thing to fix. The text names the
        SHAPE of the loss; four named downstream things is a manifest."""
        rows = self.keyrows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["text"],
            "No AI engine connected — nothing can be read, drafted or rendered")
        self.assertEqual(rows[0]["action"], "settings")
        self.assertEqual(rows[0]["scope"], "install",
                         "the only blocker that survives a production switch")
        self.assertEqual(rows[0]["sub"], "BLOCKS STAGE 02 AND STAGE 04")
        self.assertEqual(rows[0]["stages"], ["wizard", "boards"])

    def test_the_stage_line_carries_what_the_text_drops(self):
        """How "the two roles fail separately" reads without a second row."""
        self.settings(anthropic_api_key="ak-test")
        row = self.keyrows()[0]
        self.assertIn("BLOCKS STAGE 04", row["sub"])
        self.assertIn("RESEARCH STILL RUNS", row["sub"])
        self.assertEqual(row["stages"], ["boards"])

    def test_a_configured_install_has_no_key_row(self):
        self.settings(openai_api_key="sk-test")
        self.assertEqual(self.keyrows(), [])

    def test_each_role_states_its_own_consequence(self):
        self.settings(anthropic_api_key="ak-test")
        rows = self.keyrows()
        self.assertEqual(len(rows), 1)
        self.assertIn("No image engine", rows[0]["text"])
        self.assertEqual(rows[0]["stages"], ["boards"],
                         "an image credential blocks stage 04, not stage 03")

    def test_failing_keys_read_differently_from_missing_ones(self):
        self.settings(openai_api_key="sk-test",
                      engine_tests={"openai": {"ok": False},
                                    "openai-chat": {"ok": False}})
        row = self.keyrows()[0]
        self.assertIn("failed its last test", row["text"])
        self.assertNotIn("No AI engine connected", row["text"])

    def test_the_credential_leads_because_it_locks_the_upload(self):
        """User ruling 2026-08-18: the screenplay is locked until an AI
        model is connected. It used to sort after the upload, on the
        reasoning that the upload needs no engine — void now that it
        does."""
        self.assertEqual(self.kinds()[0], "KEY")

    def test_once_the_screenplay_is_in_the_key_becomes_the_next_action(self):
        from app import store
        store.save_app_state({"screenplay": {"filename": "s.pdf"}})
        blockers = insights.blocking()
        verb = insights.next_verb(insights.stage_summary(blockers), blockers)
        self.assertIn("No AI engine connected", verb["text"])
        self.assertEqual(verb["action"], "settings")

    def test_a_key_row_never_marks_a_stage_it_does_not_block(self):
        """Its action is "settings", which no stage maps to. Without the
        server-sent `stage` the client's `|| "specs"` fallback would paint
        stage 03 red for a missing credential."""
        for row in self.keyrows():
            self.assertIn(row["stage"], ("wizard", "boards"))


class ThePaletteIsGatedOnTheBible(unittest.TestCase):
    """User, 2026-08-22, in three passes.

    First: "no color swatches" after a screenplay upload. The dependency
    was working — the scan finds design LANGUAGES; colour is proposed by a
    model reading the SAVED Bible, each swatch cited to a line of it.

    Then: "it does not show that" — I had put the explanation in step 4,
    under a control that is deliberately silent before a save, rather than
    in the column where the absence is felt.

    Then: "it's not disabled, totally unclear, I can add swatches —
    disable this section with an obvious callout on why." The faint 9.5px
    line I moved into the column was a stated gate in principle and
    invisible in practice, beside a control that still worked. A gate you
    can act through is not a gate.

    So the manual adder is genuinely disabled — inputs and verb — while no
    Bible exists, and the reason is said at a size that competes with the
    control it governs.
    """

    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")

    def body(self):
        i = self.JS.index("const paletteOrigin")
        return self.JS[i:i + 2400]

    def test_the_condition_is_the_bible_and_nothing_else(self):
        """An earlier attempt also unlocked once the column held any
        colour — "you may add more by hand once you have added one by
        hand" is not a rule, and the check was broken anyway: a swatch
        thumb is a coloured block, not an <img>."""
        b = self.body()
        self.assertIn("const locked = !b.text.trim();", b)
        self.assertNotIn("hasColour", b)

    def test_the_control_is_really_disabled_not_merely_dimmed(self):
        b = self.body()
        self.assertIn('$$("input, button", add).forEach', b)
        self.assertIn("el.disabled = locked", b)

    def test_the_callout_carries_the_users_own_copy(self):
        """Verbatim, 2026-08-22. Not a paraphrase — the user wrote this
        sentence and the step is bold."""
        b = self.body()
        self.assertIn("LOCKED — NO ART DIRECTION BIBLE", b)
        self.assertIn("Color swatches reference the Art Direction Bible "
                      "once created.", b)
        self.assertIn("<b>Step 4</b>", b)

    def test_the_callout_carries_no_verb(self):
        """Removed on instruction: the step it names is on the same page,
        and a button that only scrolls is not worth a primary's weight."""
        b = self.body()
        self.assertNotIn("pal-go", b)
        self.assertNotIn("<button", b)

    def test_everything_that_states_a_palette_is_locked_together(self):
        """Three passes, one per control left behind — the hand-added
        colour, then the words, then Add images. Each survivor read as the
        gate not meaning it."""
        b = self.body()
        self.assertIn('$$("input, button", add).forEach', b)   # the adder
        self.assertIn("words.disabled = locked", b)            # the words
        self.assertIn("addImgs.disabled = locked", b)          # the images
        self.assertIn('$("[data-f=files]", col)', b)           # and its input

    def test_the_callout_precedes_what_it_disables(self):
        """A gate under half its own controls explains them too late."""
        self.assertIn("col.insertBefore(gate, addImgs || add);", self.body())

    def test_the_gate_goes_when_the_bible_arrives(self):
        b = self.body()
        self.assertIn("if (!locked) { if (gate) gate.remove(); return; }", b)

    def test_the_callout_is_visible_not_a_faint_line(self):
        """The 9.5px --ink-faint `.up-gate` was technically compliant and
        practically unreadable next to a live control."""
        block = self.CSS.split(".pal-gate {")[1].split(".wiz-thumb-note")[0]
        self.assertIn("var(--accent-line)", block)
        self.assertIn("var(--accent-soft)", block)
        self.assertIn("font-size: 12px", block)
        self.assertNotIn("up-gate", self.body())

    def test_the_gate_invents_no_colours(self):
        block = self.CSS.split(".pal-gate {")[1].split(".wiz-thumb-note")[0]
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}", block), [])

    def test_the_server_still_refuses_without_a_bible(self):
        """The gate is the courtesy; the refusal is the contract."""
        self.assertIn("No saved Art Direction Bible yet",
                      (ROOT / "app/wizard.py").read_text(encoding="utf-8"))


class AChainLinkWithoutANumberSaysItsName(unittest.TestCase):
    """Seen on screen 2026-08-22: the gate chain read "Connect a model ·
    STAGE undefined · DONE".

    STAGE_NUM maps the five pipeline stages; the credential link points at
    Settings, which is not one of them. It has read `STAGE undefined`
    since that link was added on 2026-08-18 — four days of a template
    printing a JavaScript failure mode at the user, in the first row of
    the first thing a locked stage shows them."""

    def test_a_numbered_stage_still_says_stage_n(self):
        i = JS.index("const cur = chain.findIndex")
        seg = JS[i:i + 900]
        self.assertIn("STAGE_NUM[s.stage] ? `STAGE ${STAGE_NUM[s.stage]}`", seg)

    def test_an_unnumbered_one_says_its_own_name(self):
        i = JS.index("const cur = chain.findIndex")
        seg = JS[i:i + 900]
        self.assertIn('String(s.stage || "").toUpperCase()', seg)

    def test_settings_is_the_link_that_has_no_number(self):
        self.assertNotIn('settings:', JS[JS.index("const STAGE_NUM"):
                                         JS.index("const STAGE_NUM") + 200])
        i = JS.index("CONNECT AN AI MODEL")
        self.assertIn('stage: "settings"', JS[i:i + 400])


class AnAnchorCanBeWordsOrAPicture(Install):
    """User, 2026-08-22, looking at stage 03's gate: "the breakdown sheet
    is broken because — what is style reference?"

    Two faults in one line. It was jargon, and its sub-line was wrong
    twice: it named "board layout", which is not one of these anchors, and
    said "three" where there are four.

    The one that actually blocked them: it counted approved reference
    IMAGES only. The 2026-08-16 ruling that dissolved the look interview
    says the opposite in this codebase's own words — "the anchor cards ARE
    that statement now: a picture, words, or both" — and the style pickers
    write WORDS. So a production with texture, cinematography and
    rendering style all stated was told to add a style reference, and
    stage 03 stayed locked over a look that was fully described.
    """

    def words(self, **kw):
        (paths.DATA / "interview.json").write_text(json.dumps(kw),
                                                   encoding="utf-8")

    def test_words_alone_state_an_anchor(self):
        self.assertEqual(insights.anchors_stated(), 0)
        self.words(texture="weathered, repairs visible")
        self.assertEqual(insights.anchors_stated(), 1)

    def test_every_anchor_has_a_words_field(self):
        """If one were missing, that anchor could only ever be stated with
        a picture — the exact asymmetry this fixes."""
        self.assertEqual(set(insights.ANCHOR_WORDS), insights.STYLE_ANCHOR_ROLES)

    def test_all_four_count_and_they_do_not_double_count(self):
        self.words(texture="a", palette="b", light="c", medium="d")
        self.assertEqual(insights.anchors_stated(), 4)
        # a picture for an anchor already stated in words is still ONE
        self.picture(approve=True)
        self.assertEqual(insights.anchors_stated(), 4)

    def picture(self, approve=False):
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (8, 8), (40, 40, 40)).save(buf, "PNG")
        r = store.add_reference("t.png", buf.getvalue(), role="WORLD_TEXTURE",
                                controls=["texture"], does_not_control=[])
        if approve:
            store.set_reference_status(r["id"], "APPROVED", "test")
        return r

    def test_a_picture_alone_still_states_one(self):
        self.picture(approve=True)
        self.assertEqual(insights.anchors_stated(), 1)

    def test_an_unapproved_picture_states_nothing(self):
        self.picture()
        self.assertEqual(insights.anchors_stated(), 0)

    def test_the_summary_carries_both_counts(self):
        """`style_anchors` is pictures, which the reference library
        reports. `anchors_stated` is what the GATE reads."""
        self.words(texture="a")
        pd = insights.stage_summary()["production_design"]
        self.assertEqual(pd["style_anchors"], 0)
        self.assertEqual(pd["anchors_stated"], 1)

    def test_the_gate_reads_the_right_one_and_says_what_it_means(self):
        i = JS.index("gateChain(state)")
        seg = JS[i:i + 2600]
        self.assertIn("done: (pd.anchors_stated || 0) > 0", seg)
        self.assertNotIn("ADD STYLE REFERENCE", seg)
        self.assertIn("DESCRIBE THE LOOK", seg)
        self.assertIn("in words or a picture", seg)
        self.assertIn("four anchors", seg)
        self.assertNotIn("the three anchors", seg)


class TheLeadNeverJumpsAheadOfTheWork(Install):
    """User, 2026-08-22: "the DO THIS NEXT in the current state is wrong —
    production design should be completed. You would not go to Board
    layout master before you complete the production design panel because
    that panel creates it."

    next_verb() took blockers[0] in APPEND order, and the board-layout gap
    is appended third. So a keyed install with a screenplay and no Bible
    led with a stage 05 need — pointing the user at a thing stage 02
    produces, from a user standing at stage 02.

    A blocker for a stage beyond the frontier stays in the BLOCKING list,
    where it is true and useful. It just is not the one verb on screen.
    """

    DRAFT = b"INT. ROOM - DAY\n\nA room.\n"

    def a_read_install(self):
        """Key connected, screenplay uploaded, no Bible — the reported
        state exactly."""
        self.settings(openai_api_key="sk-test")
        store.set_screenplay("d.txt", self.DRAFT)

    def test_the_lead_is_the_stage_the_user_is_actually_on(self):
        self.a_read_install()
        b = insights.blocking()
        sm = insights.stage_summary(b)
        self.assertEqual(insights.frontier_rank(sm), 2, "standing at stage 02")
        verb = insights.next_verb(sm, b)
        self.assertIn("Bible", verb["text"])
        self.assertEqual(verb["action"], "wizard")
        self.assertNotIn("board layout", verb["text"].lower())

    def test_the_later_blocker_is_still_reported(self):
        """Demoting it from the lead must not hide it."""
        self.a_read_install()
        texts = [r["text"].lower() for r in insights.blocking()]
        self.assertTrue(any("board layout master" in t for t in texts),
                        "the gap is still true and must still be listed")

    def test_blockers_read_in_pipeline_order(self):
        self.a_read_install()
        ranks = [insights.stage_rank(r) for r in insights.blocking()
                 if r["kind"] != "CARE"]
        self.assertEqual(ranks, sorted(ranks))

    def test_a_credential_still_leads_everything(self):
        """Install-scope: it blocks every stage, so it outranks them."""
        store.set_screenplay("d.txt", self.DRAFT)
        b = insights.blocking()
        self.assertEqual(b[0]["kind"], "KEY")
        self.assertEqual(insights.stage_rank(b[0]), 0)

    def test_an_unranked_blocker_sorts_last_not_first(self):
        """A row nobody has ranked must never outrank a real one."""
        self.assertEqual(insights.stage_rank({"action": "who-knows"}), 9)
        self.assertEqual(insights.stage_rank({}), 9)


class BlockersSpeakEnglish(Install):
    """User, 2026-08-22: "that underscore in the parentheses is not for end
    users, it has no meaning, remove it." The row read "Board layout master
    (BOARD_LAYOUT_STYLE) not approved". The role is a key the app matches
    on, not a word anyone says."""

    ROLES = ("BOARD_LAYOUT_STYLE", "CINEMATOGRAPHY_STYLE",
             "BOARD_RENDERING_STYLE", "WORLD_TEXTURE", "COLOR_PALETTE")

    def rows(self):
        self.settings(openai_api_key="sk-test")
        store.set_screenplay("d.txt", b"INT. ROOM - DAY")
        return insights.blocking()

    def test_no_blocker_shows_an_internal_role_name(self):
        for row in self.rows():
            for field in ("text", "sub", "detail"):
                v = str(row.get(field) or "")
                for role in self.ROLES:
                    self.assertNotIn(role, v, f"{field}: {v}")

    def test_the_role_is_still_carried_as_data(self):
        """Removing it from the prose must not lose it — a consumer that
        needs to know WHICH role is missing still can."""
        row = next(r for r in self.rows()
                   if "board layout master" in r["text"].lower())
        self.assertEqual(row.get("role"), "BOARD_LAYOUT_STYLE")


class TheUploadIsLocked(Install):
    """User ruling 2026-08-18: the screenplay is locked until an AI model
    is connected. The read starts the moment the draft lands and the read
    needs an engine, so accepting the file would be taking work the studio
    cannot begin.

    This REVERSES two things Claude Design ruled the same day — TRIAGE
    §3.1 removed the walkthrough's credential step, and §2 kept the upload
    unblocked and the screenplay leading. A user instruction outranks a
    design ruling; the reversal is logged in DESIGN_SYSTEM.md rather than
    left for the next pass to rediscover."""

    def test_the_server_refuses_the_upload(self):
        from fastapi.testclient import TestClient
        import app.main as appmain
        c = TestClient(appmain.app)
        r = c.post("/api/screenplay",
                   files={"file": ("s.txt", b"INT. ROOM - DAY", "text/plain")})
        self.assertEqual(r.status_code, 423, "the app's gate status")
        self.assertIn("Connect an AI model first", r.json()["detail"])

    def test_it_opens_once_a_model_is_connected(self):
        from fastapi.testclient import TestClient
        import app.main as appmain
        self.settings(openai_api_key="sk-test")
        c = TestClient(appmain.app)
        r = c.post("/api/screenplay",
                   files={"file": ("s.txt", b"INT. ROOM - DAY", "text/plain")})
        self.assertEqual(r.status_code, 200, r.text)

    def test_the_gate_is_readable_before_it_is_hit(self):
        """A gate surfaced only as an error after the user acts is the
        thing the product rule forbids."""
        self.assertIn("NO AI MODEL CONNECTED", JS)
        self.assertIn("Connect an AI model first — Settings → AI & engines", JS)
        # every upload form is told what the server declared
        self.assertEqual(JS.count("bindScreenplayUpload($("), 3)
        for call in re.findall(r"bindScreenplayUpload\(\$\([^)]*\)([^;]*)", JS):
            self.assertIn("state.capability", call,
                          "an ungated upload form would 423 in the user's face")

    def test_the_lead_never_names_an_act_the_studio_refuses(self):
        self.assertIn("const canUpload = state.capability", JS)
        self.assertIn("if (!state.screenplay && canUpload)", JS)

    def test_the_state_endpoint_declares_what_can_run(self):
        from fastapi.testclient import TestClient
        import app.main as appmain
        cap = TestClient(appmain.app).get("/api/state").json()["capability"]
        self.assertFalse(cap["any_credential"])


class TheWalkthroughStartsOnSettings(unittest.TestCase):
    """Same ruling: if the upload is locked until a model is connected,
    the tour cannot open by pointing at the upload."""

    def doc(self):
        import json as _j
        from app import tutorials
        return _j.loads((tutorials.PACKAGED / "first-board.json")
                        .read_text(encoding="utf-8"))

    def test_the_first_step_is_the_credential_and_it_is_held(self):
        first = self.doc()["steps"][0]
        self.assertEqual(first["goto"], "/settings")
        self.assertEqual(first["advance"], {"state": "capability.any_credential"})
        self.assertIn("CONNECT A MODEL", first["wait"])

    def test_it_leaves_the_page_usable(self):
        """User 2026-08-18: any model will do, so a spotlight on one of
        them would be pointing at the wrong thing. The `page` surface has
        no scrim and no cutout."""
        first = self.doc()["steps"][0]
        self.assertEqual(first["surface"], "page")
        self.assertNotIn("anchor", first)

    def test_a_page_step_may_not_point_or_block(self):
        from app import tutorials
        doc = {"id": "x", "kind": "flow", "title": "X", "rev": 1,
               "steps": [{"surface": "page", "title": "t", "anchor": "band"}]}
        self.assertTrue(any("takes no anchor" in e
                            for e in tutorials.validate(doc)))
        doc["steps"][0] = {"surface": "page", "title": "t", "block": True}
        self.assertTrue(any("cannot block" in e
                            for e in tutorials.validate(doc)))

    def test_it_skips_itself_for_a_studio_that_already_has_one(self):
        self.assertEqual(self.doc()["steps"][0]["skip_if"],
                         {"state": "capability.any_credential"})

    def test_the_upload_step_comes_after_it(self):
        ids = [s["id"] for s in self.doc()["steps"]]
        self.assertLess(ids.index("connect"), ids.index("upload"))


class TheUploadStartsTheRead(unittest.TestCase):
    """User 2026-08-20: the button said `Upload & start the read` and only
    uploaded. The read is the Scene Scan, and the verb now performs it."""

    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")

    def body(self):
        i = self.JS.index("async function startTheRead()")
        return self.JS[i:i + 1400]

    def test_the_upload_fires_it(self):
        i = self.JS.index('const rec = await api("/api/screenplay"')
        self.assertIn("startTheRead();", self.JS[i:i + 700])

    def test_it_never_re_scans_a_curated_production(self):
        """A re-run overwrites curated design languages, environments and
        subjects — the same reason `Name the acts` is not a re-scan."""
        b = self.body()
        self.assertIn('api("/api/wizard/analysis")', b)
        self.assertIn("have.design_worlds || have.subjects || have.analyzed_at", b)
        self.assertIn("return", b)

    def test_it_does_not_call_a_model_the_studio_does_not_have(self):
        """The narrative capability is read from /api/settings and the
        function returns before anything is spent or shown. Asserted as
        order, not as a literal — the guard was split across two lines
        adding the live read (2026-08-20) and this test failed over a
        rename while the behaviour it names never moved."""
        b = self.body()
        self.assertRegex(b, r"capability\?\.narrative")
        self.assertRegex(b, r"if \(!cap\?\.usable\) return;")
        # …and that guard precedes both the spend and the surface.
        self.assertLess(b.index("usable) return;"), b.index("/api/wizard/analyze"))
        self.assertLess(b.index("usable) return;"), b.index("theRead.begin"))

    def test_a_failure_points_at_the_manual_door(self):
        self.assertIn("run the Scene Scan on", self.body())

    def test_the_scan_defaults_to_an_engine_this_studio_has(self):
        """Hardcoding gemini handed an OpenAI-only install a stated-
        unavailable engine for any caller that did not pass one."""
        i = self.MAIN.index('@app.post("/api/wizard/analyze")')
        seg = self.MAIN[i:i + 900]
        self.assertNotIn('body.get("provider", "gemini")', seg)
        self.assertIn('generate.capability()["narrative"]', seg)


class AHeldStepOffersNoNext(unittest.TestCase):
    """User 2026-08-20: a disabled `Next` beside the app's own live button
    read as two competing actions. The step's condition is the only way
    forward, so a second control was the confusion."""

    TUT = (ROOT / "app/static/tutorial.js").read_text(encoding="utf-8")

    def test_a_held_step_hides_next_rather_than_disabling_it(self):
        i = self.TUT.index("if (step.advance && !running.resumedInto)")
        seg = self.TUT[i:i + 700]
        self.assertIn('next.classList.add("hidden")', seg)

    def test_leaving_is_still_possible(self):
        """Skip and Back stay: a held step must never be a trap."""
        self.assertIn('.tut-skip', self.TUT)
        i = self.TUT.index("if (step.advance && !running.resumedInto)")
        seg = self.TUT[i:i + 700]
        self.assertNotIn('skip.classList.add("hidden")', seg)


class KindsAreFullyWired(unittest.TestCase):
    """Every kind the server can emit must be renderable. A kind with no
    verb silently reads "Open"; a kind with no CSS renders unstyled; a kind
    with no support line loses its explanation."""

    def kinds_the_server_emits(self):
        return set(re.findall(r'"kind": "([A-Z]+)"', INSIGHTS))

    def test_every_kind_has_a_verb(self):
        verbs = re.search(r"const BLOCK_VERBS = \{(.*?)\};", JS, re.S).group(1)
        for kind in self.kinds_the_server_emits():
            self.assertIn(f"{kind}:", verbs, f"{kind} has no act-button verb")

    def test_every_kind_has_a_badge_rule(self):
        for kind in self.kinds_the_server_emits():
            self.assertIn(f".block-kind.{kind}", CSS,
                          f"{kind} would render as an unstyled badge")

    def test_every_blocking_kind_has_a_support_line(self):
        support = re.search(r"const BLOCK_SUPPORT = \{(.*?)\n\};", JS, re.S).group(1)
        for kind in self.kinds_the_server_emits() - {"CARE"}:
            self.assertIn(f"{kind}:", support, f"{kind} explains nothing")


class OneAuthority(unittest.TestCase):
    def test_the_client_no_longer_recomputes_whether_a_key_exists(self):
        """The fourth copy. It read the engine fields directly; it now
        reads the server's answer."""
        self.assertNotIn("engAll.openai?.configured || engAll.gemini?.configured", JS)
        self.assertIn("settings.capability?.any_credential", JS)

    def test_the_settings_route_does_not_rebuild_the_engine_block(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        self.assertIn("engines = generate.engine_credentials()", main)
        self.assertNotIn('"openai-chat": {"configured": bool(openai_src)', main,
                         "the settings route is building engines a second time")


if __name__ == "__main__":
    unittest.main()
