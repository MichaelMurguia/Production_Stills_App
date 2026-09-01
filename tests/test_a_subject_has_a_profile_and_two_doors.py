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
        self.assertEqual(JS.count("/api/subjects/${s.id}/generate"), 1)
        for slot in ('$("[data-f=gen]", host).onclick', '$("[data-f=gen2]", host).onclick'):
            self.assertIn(slot, JS, slot)

    def test_a_failure_is_stated_and_the_button_comes_back(self):
        i = JS.index("const generate = async (btn) => {")
        seg = JS[i:JS.index(NL + "    };", i)]
        self.assertIn("toast(err.message, true)", seg)
        self.assertIn("finally { stop?.(); }", seg)


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


if __name__ == "__main__":
    unittest.main()
