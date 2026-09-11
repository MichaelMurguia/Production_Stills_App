"""A subject carries a profile, and two ways to get a picture.

User, 2026-08-31, on the cast screen built earlier the same day: "you need
to include the character profile description and the option to upload or
generate an image."

THE PROFILE. A subject had one text field, `subtitle`, and the mocks show
two different sentences: "Fugitive pilot" on the roster card, and on the
detail "Dark hair, mid-thirties, weather on the face. Reads the same at
wide as at close." One is the role, the other is who they are. The profile
had nowhere to live, so `description` is now its own field.

THE SECOND DOOR. Uploading a photograph existed. Generating one did not,
and §3.4's filmstrip ends in a dashed GENERATE ANOTHER slot. It renders
from the subject's OWN words under the Bible and the approved anchors —
the same conditions a panel renders under — and lands exactly where the
upload lands: an approved reference carrying the subject's role, linked
to its card. Nothing downstream can tell the two apart, and Reject in
Reference is the recourse for both.

It refuses rather than inventing. No Bible means no rendering language;
no description and no traits means a reference rendered from a name, which
would be the engine's invention rather than this production's.
"""
from __future__ import annotations

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

    def tearDown(self):
        generate.mock_enabled = self._mock
        paths.HOME = self._was["HOME"]
        paths.PROJECTS_DIR = self._was["PROJECTS_DIR"]
        paths.ACTIVE_PROJECT_FILE = self._was["ACTIVE"]
        paths.SETTINGS = self._was["SETTINGS"]
        paths.set_project(self._was["slug"])
        self._tmp.cleanup()

    def subject(self, **kw):
        s = store.add_subject(kw.pop("name", "Ryna Sokol"), kw.pop("kind", "CHARACTER"),
                              kw.pop("subtitle", "Fugitive pilot"),
                              kw.pop("traits", ["Flight jacket, valley-repaired"]))
        if kw:
            s = store.update_subject(s["id"], kw)
        return s

    def bible(self):
        generate.save_style_bible(
            "## Rendering Language" + NL + "Production painting; value groups carry form.")


class TheProfileIsItsOwnField(_Home):
    def test_a_new_subject_has_one(self):
        self.assertIn("description", self.subject())

    def test_it_is_not_the_role_line(self):
        s = self.subject(description="Dark hair, mid-thirties.")
        self.assertEqual(s["subtitle"], "Fugitive pilot")
        self.assertEqual(s["description"], "Dark hair, mid-thirties.")

    def test_it_can_be_edited(self):
        s = self.subject()
        self.assertEqual(
            store.update_subject(s["id"], {"description": "Weather on the face."})
            ["description"], "Weather on the face.")

    def test_the_add_endpoint_accepts_one(self):
        i = MAIN.index("async def api_add_subject(")
        seg = MAIN[i:MAIN.index("@app.put", i)]
        self.assertIn('body.get("description", "")', seg)

    def test_the_detail_shows_the_profile_and_falls_back_to_the_role(self):
        i = JS.index('<p class="cd-lab">WHO THIS IS</p>')
        seg = JS[i:i + 700]
        self.assertIn("s.description ? esc(s.description)", seg)
        self.assertIn("s.subtitle ? esc(s.subtitle)", seg)

    def test_editing_writes_the_profile_not_the_role(self):
        i = JS.index('await askText("The profile"')
        seg = JS[i:i + 700]
        self.assertIn('json: { description: v.trim() }', seg)
        self.assertNotIn("subtitle: v.trim()", seg)


class GeneratingLandsWhereUploadingLands(_Home):
    def test_it_makes_an_approved_reference_with_the_subjects_role(self):
        self.bible()
        s = self.subject(description="Dark hair, mid-thirties.")
        out = generate.subject_portrait(s["id"], "mock")
        ref = next(r for r in store.list_references() if r["id"] == out["reference"])
        self.assertEqual(ref["role"], "CHARACTER_LIKENESS — RYNA SOKOL")
        self.assertEqual(ref["status"], "APPROVED")

    def test_it_links_the_reference_to_the_card(self):
        self.bible()
        s = self.subject(description="Dark hair, mid-thirties.")
        out = generate.subject_portrait(s["id"], "mock")
        self.assertIn(out["reference"], store.get_subject(s["id"])["ref_ids"])

    def test_it_renders_in_the_shape_the_subject_is_shown_in(self):
        """§3.4: "at the subject's own ratio — 1:1.25 for a character,
        1.85:1 for a vehicle or a prop, and never letterboxed into the
        other shape." Rendering 16:9 into a 1:1.25 frame is letterboxing
        by another route."""
        self.bible()
        c = self.subject(name="A", description="x")
        v = self.subject(name="B", kind="VEHICLE", description="x")
        self.assertEqual(generate.subject_portrait(c["id"], "mock")["aspect_ratio"], "4:5")
        self.assertEqual(generate.subject_portrait(v["id"], "mock")["aspect_ratio"], "16:9")

    def test_the_ratios_match_what_the_screen_draws(self):
        self.assertEqual(generate.SUBJECT_ASPECT["CHARACTER"], "4:5")
        b = CSS.split(NL + ".cd-hero {")[1].split("}")[0] if NL + ".cd-hero {" in CSS else ""
        self.assertTrue(b or ".cast-shot" in CSS)


class ItRefusesRatherThanInventing(_Home):
    def test_no_bible_means_no_rendering_language(self):
        s = self.subject(description="x")
        with self.assertRaises(generate.GenerationError) as e:
            generate.subject_portrait(s["id"], "mock")
        self.assertIn("Art Direction Bible", str(e.exception))

    def test_a_name_alone_is_not_a_reference(self):
        """The engine would be inventing the production, not rendering
        it."""
        self.bible()
        s = self.subject(name="Nobody", subtitle="", traits=[])
        with self.assertRaises(generate.GenerationError) as e:
            generate.subject_portrait(s["id"], "mock")
        self.assertIn("write who this is first", str(e.exception))

    def test_an_unknown_subject_is_named(self):
        self.bible()
        with self.assertRaises(generate.GenerationError) as e:
            generate.subject_portrait("SUBJ-9999", "mock")
        self.assertIn("SUBJ-9999", str(e.exception))

    def test_the_prompt_carries_the_traits_as_requirements(self):
        """Assert the PROMPT, not the source that builds it — a source
        search passes on a line that never reaches an engine, and fails on
        a sentence merely wrapped across two literals."""
        self.bible()
        s = self.subject(description="Dark hair, mid-thirties.",
                         traits=["Burn scar, left forearm"])
        seen = {}
        was = generate.mockflow.render
        try:
            def spy(prompt, refs, size, aspect, out):
                seen["prompt"], seen["aspect"] = prompt, aspect
                return was(prompt, refs, size, aspect, out)
            generate.mockflow.render = spy
            generate.subject_portrait(s["id"], "mock")
        finally:
            generate.mockflow.render = was
        p = seen["prompt"]
        self.assertIn("EVERY ONE OF THESE MUST BE TRUE AND VISIBLE:", p)
        self.assertIn("- Burn scar, left forearm", p)
        self.assertIn("Dark hair, mid-thirties.", p)
        self.assertIn("Invent no clothing, marking, era or equipment they do "
                      "not state.", p)
        self.assertEqual(seen["aspect"], "4:5")

    def test_the_prompt_renders_under_the_bible_not_beside_it(self):
        """A portrait made outside the art direction is a picture of a
        person, not a reference for this production."""
        generate.save_style_bible(
            "## Rendering Language" + NL + "PRODUCTION PAINTING, values carry form.")
        s = self.subject(description="Dark hair.")
        seen = {}
        was = generate.mockflow.render
        try:
            generate.mockflow.render = lambda p, r, sz, a, o: (
                seen.setdefault("p", p), was(p, r, sz, a, o))[1]
            generate.subject_portrait(s["id"], "mock")
        finally:
            generate.mockflow.render = was
        self.assertIn("PRODUCTION PAINTING", seen["p"])


class BothDoorsAreOnTheScreen(unittest.TestCase):
    def test_the_filmstrip_ends_in_generate_another(self):
        i = JS.index('<div class="cd-strip">')
        seg = JS[i:i + 900]
        self.assertIn("GENERATE<br>ANOTHER", seg)
        self.assertNotIn("ADD<br>ANOTHER", seg)

    def test_that_slot_is_dashed_because_it_holds_no_picture(self):
        b = CSS.split(NL + ".cd-more {")[1].split("}")[0]
        self.assertIn("dashed", b)

    def test_both_acts_are_offered_side_by_side(self):
        i = JS.index('<div class="cd-acts">')
        seg = JS[i:i + 600]
        self.assertIn("Attach a photograph", seg)
        self.assertIn("Generate one", seg)
        self.assertIn("Edit the description", seg)

    def test_the_spend_is_stated_before_it_is_pressed(self):
        """A render is money, and canon says a gate reads as state before
        it is hit."""
        self.assertIn("it spends a render", JS)
        i = JS.index('data-f="gen"')
        self.assertIn("Spends a render", JS[i:i + 400])

    def test_both_slots_go_through_one_call(self):
        """Both are bound in one place now (2026-09-10) — and only when
        the act is available, since a disabled button with a handler is a
        gate you can still trip."""
        self.assertEqual(JS.count("/api/subjects/${s.id}/generate"), 1)
        self.assertIn('const genBtns = [$("[data-f=gen]", host), '
                      '$("[data-f=gen2]", host)].filter(Boolean);', JS)
        self.assertIn("genBtns.forEach(b => { b.onclick = e => generate(e.currentTarget); });",
                      JS)

    def test_a_failure_is_stated_and_the_spinner_actually_stops(self):
        """`startBusy` returns an OBJECT with .done(), not a stop
        function. This called `stop?.()`, which throws inside the
        `finally` — so the real error was swallowed, the spinner never
        cleared, and its elapsed clock kept counting on a request that had
        already failed. The user read that as a three-minute render; the
        server had answered 422 in milliseconds (2026-09-10)."""
        i = JS.index("const generate = async (btn) => {")
        seg = JS[i:JS.index(NL + "    };", i)]
        self.assertIn("toast(err.message, true)", seg)
        self.assertIn("finally { stop.done(); }", seg)
        self.assertNotIn("stop?.()", seg)

    def test_every_startBusy_caller_disposes_of_it(self):
        """The same mistake anywhere else leaves a stopwatch running on a
        finished request."""
        import re
        for m in re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*startBusy\(", JS):
            name = m.group(1)
            seg = JS[m.end():m.end() + 4000]
            self.assertTrue(f"{name}.done()" in seg or f"{name}?.done()" in seg,
                            f"{name} at line {JS[:m.start()].count(NL) + 1}")


class AppearsInSaysWhatItCannotKnow(unittest.TestCase):
    """§3.4 asks for APPEARS IN. Nothing in this app maps a subject to an
    act — the read returns both and no edge between them — so it states
    what would produce the answer rather than guessing from a name."""

    def test_it_states_the_blocker(self):
        i = JS.index("const appearsIn = (s) => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("NOT UNTIL THIS SUBJECT IS ON A BREAKDOWN", seg)

    def test_it_does_not_guess_from_a_name(self):
        i = JS.index("const appearsIn = (s) => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        for guess in ("indexOf", "includes(", "match("):
            self.assertNotIn(guess, seg, guess)

    def test_the_row_is_on_the_card(self):
        self.assertIn("<b>APPEARS IN</b>", JS)




class TheCastingModalAsksForBoth(unittest.TestCase):
    """User, 2026-09-01, looking at the casting modal: "None of your
    changes seem to be in."

    They were in — on the cast DETAIL, which is the surface you reach
    AFTER casting. The modal is where a subject's words are written for
    the first time, and it had neither the profile field nor the second
    door. Both were built one screen too late."""

    def body(self):
        i = JS.index("function castModal(rec, onDone) {")
        return JS[i:JS.index(NL + "}" + NL, i)]

    def test_the_profile_is_asked_for_where_the_words_are_first_written(self):
        b = self.body()
        self.assertIn('data-f="description"', b)
        self.assertIn("Who this is", b)

    def test_it_is_a_separate_question_from_the_role(self):
        b = self.body()
        self.assertIn('data-f="subtitle"', b)
        self.assertLess(b.index('data-f="subtitle"'), b.index('data-f="description"'))

    def test_casting_saves_it(self):
        b = self.body()
        self.assertIn('description: $("[data-f=description]", ov).value.trim()', b)

    def test_the_second_door_is_offered_beside_the_first(self):
        b = self.body()
        i = b.index('class="cast-photos"')
        seg = b[i:i + 1200]
        self.assertIn("Reference photos", seg)
        self.assertIn('data-f="gen"', seg)

    def test_the_render_runs_after_the_card_exists(self):
        """There is nothing to render from until the words are saved."""
        b = self.body()
        self.assertLess(b.index('api("/api/subjects", { method: "POST"'),
                        b.index("/generate"))

    def test_the_spend_rides_with_the_option(self):
        b = self.body()
        self.assertIn("SPENDS A RENDER", b)

    def test_a_failed_render_does_not_claim_the_casting_failed(self):
        """The card exists and the photos landed — that is the larger half
        and it says so."""
        b = self.body()
        self.assertIn("is cast, but the render did not run", b)


class TheModalIsReadable(unittest.TestCase):
    """User, same sitting: "the font is 7 pixels high — a person can't
    read that — is that a design decision?"

    It was not a decision, it was drift. §1.3 allows THREE sizes per
    surface and its smallest is 11.5px; this modal had four — 9, 10, 10.5
    and 12.5 — three of them under the floor. The rule exists for exactly
    this: "the measured fault this replaced was nine sizes between 9.5px
    and 15px."
    """

    def test_nothing_in_this_modal_is_under_the_floor(self):
        import re
        i = CSS.index(".cast-kind {")
        seg = CSS[i:CSS.index(".photos-modal", i)]
        for m in re.finditer(r"font-size:\s*([\d.]+)px", seg):
            self.assertGreaterEqual(float(m.group(1)), 11.5, m.group(0))

    def test_the_read_mark_came_up_with_it(self):
        b = CSS.split(NL + ".read-mark {")[1].split("}")[0]
        self.assertIn("font-size: 11.5px", b)

    def test_the_surface_keeps_three_sizes_and_the_largest_anchors(self):
        for rule in (".cast-modal .modal-title { font-size: 15px; }",
                     ".cast-modal .modal-actions button { font-size: 15px; }",
                     ".cast-modal .f-label { font-size: 11.5px;"):
            self.assertIn(rule, CSS, rule)

    def test_the_fix_did_not_raise_those_classes_app_wide(self):
        """The same drift is everywhere and deserves one deliberate pass,
        not a side effect of a casting fix."""
        b = CSS.split(NL + ".f-label {")[1].split("}")[0]
        self.assertIn("font-size: 10.5px", b)




class TheGenerateGateReadsBeforeItIsHit(unittest.TestCase):
    """User, 2026-09-10: "Im trying to render a character and its taking
    over 3 minutes?" then, having found it in the activity log himself:
    "it should not just spin forever. Need a meaningful warning prompt."

    The server had refused in milliseconds — no saved Art Direction Bible,
    so there is no rendering language and a reference would invent one.
    Canon: a gate reads as state BEFORE it is hit, never as an error
    after. Both conditions the server refuses on are knowable on the card,
    so refusing after a press was the app declining to say what it already
    knew."""

    def seg(self):
        i = JS.index("const hasWords = !!(String(s.description")
        return JS[i:JS.index("host.innerHTML = `", i)]

    def test_it_knows_whether_there_is_anything_to_render_from(self):
        s = self.seg()
        self.assertIn("String(s.description", s)
        self.assertIn("String(s.subtitle", s)
        self.assertIn("(s.traits || []).length", s)

    def test_it_knows_whether_the_bible_is_saved(self):
        self.assertIn(
            "const bibleSaved = !!state?.stage_summary?.production_design?.bible_saved;",
            self.seg())

    def test_the_bible_is_the_first_thing_it_names(self):
        """Words with no Bible still cannot render, so naming the words
        first would send someone to fix the wrong thing."""
        s = self.seg()
        self.assertLess(s.index("!bibleSaved ?"), s.index(": !hasWords ?"))

    def test_the_buttons_are_disabled_rather_than_left_to_fail(self):
        i = JS.index("if (genBlock) {")
        seg = JS[i:i + 500]
        self.assertIn("b.disabled = true", seg)
        self.assertIn("b.title = genBlock.why", seg)

    def test_the_reason_is_on_the_card_not_only_in_a_tooltip(self):
        self.assertIn("cd-blocked", JS)
        self.assertIn("esc(genBlock.why)", JS)

    def test_it_links_to_where_the_condition_is_resolved(self):
        """Canon: state the unmet condition beside the control AND link to
        where it gets resolved."""
        self.assertIn('data-f="gen-go"', JS)
        i = JS.index('const goFix = $("[data-f=gen-go]", host);')
        seg = JS[i:i + 400]
        self.assertIn("closeCast()", seg)
        self.assertIn('data-step="4"', seg)

    def test_a_blocked_card_does_not_advertise_a_spend(self):
        """The cost line is replaced by the reason, not shown beside it —
        a price for something you cannot buy is noise."""
        i = JS.index("${genBlock")
        seg = JS[i:i + 700]
        self.assertLess(seg.index("cd-blocked"), seg.index("it spends a render"))

    def test_the_gate_is_hold_not_bad(self):
        b = CSS.split(NL + ".cd-blocked {")[1].split("}")[0]
        self.assertIn("var(--hold)", b)
        self.assertNotIn("--bad", b)

    def test_the_server_still_refuses_on_its_own(self):
        """The client gate is a courtesy; the server is the rule. A third
        condition — a Bible contradicting the rendering anchor — needs the
        server and stays a refusal."""
        gen = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        i = gen.index("def subject_portrait(")
        seg = gen[i:i + 3000]
        self.assertIn("no rendering language", seg)
        self.assertIn("write who this is first", seg)
        self.assertIn("bible.anchor_conflicts()", seg)


if __name__ == "__main__":
    unittest.main()
