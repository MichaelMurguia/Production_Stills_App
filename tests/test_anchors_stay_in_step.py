"""Regression, user-hit 2026-08-22 and reproduced from the install.

The Board Rendering Style anchor said **Photo Real**. The Model Test came
back an oil painting.

The evidence, off disk:

  16:17  the Art Direction Bible is written. Its Rendering Language reads
         "Production Painting rendering style — the brush left visible…
         Avoid: photographic detail. Lens effects."
  18:04  PUT /api/wizard/interview sets medium to "Photo Real rendering
         style — no mark of the hand… Everything must be explicable as
         optics."
  18:06  POST /api/wizard/samples/openai. `sample_probe` builds its ENTIRE
         brief from `bible.render_context("")`, so the only thing it said
         about medium was the 16:17 transcription. The engine painted what
         it was told to paint.

One question — "what medium do the panels render in?" — with two answers,
which is the failure this repo keeps meeting. The section is not an
independent statement: it is a transcription of the anchor's document
entry, so it is derived here and kept derived.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import bible, paths, store, style_docs  # noqa: E402

# The reporting user's own bible, trimmed to the sections that matter and
# carrying their Rendering Language section verbatim.
BIBLE = """# Project Oxcart — Locked Art Direction Bible

## Status
authoritative visual context

## Overall Visual Identity
- Lived-In world texture — wear where hands go.
- machined optimism, bare metal and desert light

## Rendering Language
### Required
- Production Painting rendering style — the brush left visible.
- Describe form with masses and edges, not with line.
- Visible directional brushwork follows the form and movement of the subject.
- Maintain a matte finish with no photographic specular sheen.

### Avoid
- Photographic detail.
- Cel outlines.
- Lens effects.

## Design Languages

## Skunkworks Engineering
Keywords: hangar, titanium
**Design language:** machined, bare, unsentimental
**Color identity:** unpainted titanium greys against desert ochre
- panel lines left visible

## Lighting Language
- Classical Adventure cinematography — camera as storyteller.
- hard desert sun, long shadows
- Approved atmosphere studies include:
  - Hard White Desert Test Day
  - Dust-Hazed Area 51 Dawn

## Drift Prevention Rule
stop and check
"""

def entry(library, name):
    for e in style_docs.styles(library):
        if e.get("name") == name:
            return e
    raise AssertionError(f"{library} has no {name}")


PHOTO_REAL = entry("rendering", "Photo Real")
ANSWER = PHOTO_REAL["value"]
NATURALISTIC = entry("cinematography", "Naturalistic / Observational")


class TheBibleFollowsTheRenderingAnchor(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-medium-"))
        self._bible, self._data = paths.BIBLE, paths.DATA
        paths.BIBLE = self.tmp / "bible.md"
        paths.DATA = self.tmp / "data"
        paths.DATA.mkdir(parents=True, exist_ok=True)
        paths.BIBLE.write_text(BIBLE, encoding="utf-8")

    def tearDown(self):
        paths.BIBLE, paths.DATA = self._bible, self._data

    def answer(self, medium):
        store._atomic_write_json(paths.DATA / "interview.json",
                                 {"medium": medium})

    # ------------------------------------------------ the reported failure
    def test_the_reported_state_is_a_contradiction_the_app_can_see(self):
        self.answer(ANSWER)
        self.assertEqual(bible.stated_style("medium"), "Production Painting")
        self.assertEqual(bible.anchor_entry("medium").get("name"), "Photo Real")
        [d] = bible.anchor_drift()
        self.assertEqual(d["anchor"], "medium")
        self.assertEqual(d["stated"], "Production Painting")
        self.assertEqual(d["chosen"], "Photo Real")

    def test_but_it_is_never_REPORTED_as_a_conflict(self):
        """User ruling 2026-08-22: "the rendering style chosen in the
        style anchors is the style, period." A medium disagreement is a
        thing to FIX, not to refuse over — and refusing produced "the
        Bible's Rendering Language says Rendered Illustration, and the
        board rendering style is Rendered Illustration", the same name on
        both sides, blocking a render over wording the app was about to
        rewrite itself."""
        self.answer(ANSWER)
        self.assertEqual(bible.anchor_conflicts(), [])
        # and asking cleaned it up on the way past
        self.assertEqual(bible.stated_style("medium"), "Photo Real")

    def test_what_the_probe_would_have_sent(self):
        """The exact defect: the only medium instruction in the sample's
        brief was the wrong one, and it explicitly forbade the right one."""
        self.answer(ANSWER)
        brief = bible.render_context("")
        self.assertIn("the brush left visible", brief)
        self.assertIn("Photographic detail", brief)   # under Avoid
        self.assertNotIn("Photo Real", brief)

    def test_the_sync_puts_the_anchor_back_in_the_bible(self):
        self.answer(ANSWER)
        [r] = bible.sync_from_anchors()
        self.assertEqual(r["anchor"], "medium")
        self.assertEqual(r["stated"], "Production Painting")
        self.assertEqual(r["chosen"], "Photo Real")
        self.assertEqual(bible.stated_style("medium"), "Photo Real")
        self.assertEqual(bible.anchor_conflicts(), [])

    def test_the_rebuilt_brief_asks_for_the_medium_that_was_chosen(self):
        self.answer(ANSWER)
        bible.sync_from_anchors()
        brief = bible.render_context("")
        self.assertIn("Photo Real rendering style", brief)
        self.assertIn("Lens-accurate detail falloff", brief)
        self.assertNotIn("brush left visible", brief)

    # ------------------------------------------------------ what it spares
    def test_it_touches_nothing_but_that_section(self):
        """The bible is a document the director edits. A whole-file rewrite
        would reflow the parts this has no business owning."""
        self.answer(ANSWER)
        bible.sync_from_anchors()
        after = bible.parse_sections(paths.BIBLE.read_text(encoding="utf-8"))
        before = bible.parse_sections(BIBLE)
        for name, body in before.items():
            if name == "Rendering Language":
                continue
            self.assertEqual(after.get(name), body, f"{name} was disturbed")

    def test_rendering_language_is_derived_all_the_way_down(self):
        """Two kinds of drift, and the SECOND is why hand edits to this
        section are not a supported concept.

        The director edits `docs/RENDERING_STYLES.md` to change what
        Production Painting IS (2026-08-22), and that change has to reach
        the productions using it. A name-only check would never see it —
        the bible still says Production Painting, just the old definition
        of it. So the section is rewritten whenever it differs from the
        entry, and the place to change what a style MEANS is the style
        document, which is the same canon the picker reads."""
        text = BIBLE.replace(
            "- Production Painting rendering style — the brush left visible.",
            "- Photo Real rendering style — no mark of the hand." + chr(10)
            + "- Shoot it as if on a 40mm.")
        paths.BIBLE.write_text(text, encoding="utf-8")
        self.answer(ANSWER)
        [d] = bible.anchor_drift()
        self.assertEqual(d["kind"], "wording")
        [r] = bible.sync_from_anchors()
        self.assertEqual(r["anchor"], "medium")
        after = paths.BIBLE.read_text(encoding="utf-8")
        self.assertNotIn("Shoot it as if on a 40mm.", after)
        self.assertIn("Lens-accurate detail falloff", after)

    def test_a_section_that_already_matches_is_not_rewritten(self):
        """Otherwise every boot bumps the revision on every production."""
        self.answer(ANSWER)
        bible.sync_from_anchors()
        self.assertEqual(bible.sync_from_anchors(), [])
        self.assertEqual(bible.anchor_drift(), [])

    def test_an_edited_style_document_reaches_the_bible(self):
        """The reported workflow end to end: the canon changes, and the
        production's bible follows without anyone re-drafting it."""
        self.answer(ANSWER)
        bible.sync_from_anchors()
        moved = dict(PHOTO_REAL, mechanics=["Shot on a long lens"],
                     avoid=["illustration"])
        real = bible.anchor_entry
        bible.anchor_entry = (
            lambda a, answer=None: moved if a == "medium" else real(a, answer))
        try:
            [r] = bible.sync_from_anchors()
            self.assertEqual(r["anchor"], "medium")
            self.assertIn("Shot on a long lens",
                          paths.BIBLE.read_text(encoding="utf-8"))
        finally:
            bible.anchor_entry = real

    def test_an_anchor_naming_no_known_style_changes_nothing(self):
        """Free text is a legitimate answer and the app cannot rebuild
        from it, so it neither rewrites nor blocks."""
        self.answer("something the library has never heard of")
        self.assertEqual(bible.sync_from_anchors(), [])
        self.assertEqual(bible.anchor_conflicts(), [])

    def test_no_bible_is_not_an_error(self):
        paths.BIBLE.unlink()
        self.answer(ANSWER)
        self.assertEqual(bible.sync_from_anchors(), [])

    def test_the_section_is_the_document_entry_not_a_summary(self):
        """The drafter saw a 600-character anchor answer capped at six
        mechanics. The rebuild reads the entry, so nothing is lost."""
        body = bible.rendering_section(PHOTO_REAL)
        for m in PHOTO_REAL["mechanics"]:
            self.assertIn(m.rstrip("."), body)
        for a in PHOTO_REAL["avoid"]:
            self.assertIn(a.lstrip().rstrip(".").lower(), body.lower())


class TheOtherTwoAnchorsAreCheckedTheSameWay(unittest.TestCase):
    """User, 2026-08-22: "do the same check for World Texture and
    Cinematography — make sure it is updated correctly and used."

    Cinematography carried the identical fault, unreported, in the same
    install: Lighting Language said "Classical Adventure cinematography"
    while the anchor said Naturalistic / Observational. It is WORSE than
    the medium case, because cinematography has a live second path —
    `cinematography.prompt_block()` puts the current grammar verbatim
    into every render — so one prompt carried both grammars.

    The three are not repaired the same way, because the sections are not
    the same kind of thing."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-anchors-"))
        self._bible, self._data = paths.BIBLE, paths.DATA
        paths.BIBLE = self.tmp / "bible.md"
        paths.DATA = self.tmp / "data"
        paths.DATA.mkdir(parents=True, exist_ok=True)
        paths.BIBLE.write_text(BIBLE, encoding="utf-8")

    def tearDown(self):
        paths.BIBLE, paths.DATA = self._bible, self._data

    def answers(self, **kw):
        store._atomic_write_json(paths.DATA / "interview.json", kw)

    # ------------------------------------------------------------ used?
    def test_all_three_destinations_actually_reach_a_render(self):
        """The first half of the question. Rendering Language, Lighting
        Language and Overall Visual Identity are all GLOBAL_SECTIONS, so
        every panel prompt carries them."""
        for name in ("Rendering Language", "Lighting Language",
                     "Overall Visual Identity"):
            self.assertIn(name, bible.GLOBAL_SECTIONS)
        self.answers()
        brief = bible.render_context("")
        self.assertIn("wear where hands go", brief)          # texture
        self.assertIn("hard desert sun", brief)              # light
        self.assertIn("brush left visible", brief)           # medium

    def test_the_two_sections_that_are_written_and_never_read(self):
        """The other halves of the texture and cinematography fences.
        `Composition Rules` and `Production Board Presentation` are drafted,
        the anchors are fenced into them, and `render_context` never sends
        either — the app draws board architecture itself. Pinned so the
        next reader finds it stated rather than assuming they ride."""
        for name in ("Composition Rules", "Production Board Presentation"):
            self.assertNotIn(name, bible.GLOBAL_SECTIONS)
            self.assertIn(name, bible.SYSTEM_SECTIONS)

    # --------------------------------------------------------- updated?
    def test_a_changed_cinematography_anchor_is_caught(self):
        self.answers(light=NATURALISTIC["value"])
        d = bible.anchor_drift()
        self.assertEqual([x["anchor"] for x in d], ["light"])
        self.assertEqual(d[0]["stated"], "Classical Adventure")
        self.assertEqual(d[0]["chosen"], "Naturalistic / Observational")

    def test_the_stale_grammar_bullet_is_deleted_not_corrected(self):
        """`cinematography.prompt_block()` is the live authority and sends
        the grammar's name, subtitle and full prompt into every render.
        Writing the name into the bible as well is a SECOND answer, so
        correcting it would only re-create the duplicate one version
        later."""
        self.answers(light=NATURALISTIC["value"])
        done = bible.sync_from_anchors()
        self.assertEqual([d["anchor"] for d in done], ["light"])
        text = paths.BIBLE.read_text(encoding="utf-8")
        self.assertNotIn("Classical Adventure", text)
        self.assertNotIn("Naturalistic", text)
        self.assertEqual(bible.anchor_drift(), [])

    def test_the_productions_own_lighting_survives_the_repair(self):
        """Lighting Language is not a transcription — it holds contrast
        rules and the approved atmosphere studies. Only the one stamped
        bullet goes."""
        self.answers(light=NATURALISTIC["value"])
        bible.sync_from_anchors()
        text = paths.BIBLE.read_text(encoding="utf-8")
        self.assertIn("hard desert sun, long shadows", text)
        self.assertIn("Hard White Desert Test Day", text)
        self.assertIn("Dust-Hazed Area 51 Dawn", text)

    def test_a_changed_texture_anchor_is_caught_but_not_rewritten(self):
        """Overall Visual Identity is a SYNTHESIS of the anchor and the
        screenplay — how this world weathers, where water tracks, what the
        repairs look like. Nothing can rebuild that from a style entry, so
        it is reported and the re-draft is the director's call."""
        other = next(e for e in style_docs.styles("texture")
                     if e["name"] != "Lived-In")
        self.answers(texture=other["value"])
        d = bible.anchor_drift()
        self.assertEqual([x["anchor"] for x in d], ["texture"])
        self.assertEqual(bible.sync_from_anchors(), [])
        self.assertIn("Lived-In", paths.BIBLE.read_text(encoding="utf-8"))
        self.assertEqual(len(bible.anchor_conflicts()), 1)
        self.assertIn("world texture", bible.anchor_conflicts()[0])

    def test_the_drafter_stamps_the_texture_so_this_is_detectable_at_all(self):
        """Rendering Language and Lighting Language named their style
        because the drafter is told to carry the director's vocabulary in
        verbatim. Overall Visual Identity did not, so a drifted texture
        was invisible — the section is now required to open with one."""
        src = (ROOT / "app" / "wizard.py").read_text(encoding="utf-8")
        i = src.index("## Overall Visual Identity")
        self.assertIn("<Name> world texture", src[i:i + 700])

    def test_all_three_drift_at_once_and_two_of_them_repair(self):
        other = next(e for e in style_docs.styles("texture")
                     if e["name"] != "Lived-In")
        self.answers(medium=ANSWER, light=NATURALISTIC["value"],
                     texture=other["value"])
        self.assertEqual(len(bible.anchor_drift()), 3)
        done = bible.sync_from_anchors()
        self.assertEqual(sorted(d["anchor"] for d in done), ["light", "medium"])
        self.assertEqual([d["anchor"] for d in bible.anchor_drift()], ["texture"])

    def test_one_repair_pass_bumps_the_revision_once(self):
        """Two sections rewritten is one edit to one document."""
        self.answers(medium=ANSWER, light=NATURALISTIC["value"])
        done = bible.sync_from_anchors()
        self.assertEqual(len({d["rev"] for d in done}), 1)

    def test_silence_is_never_a_contradiction(self):
        """A section naming no style, or an answer naming no known style,
        is not a disagreement — it is an absence, and the app does not
        invent a side for it."""
        text = BIBLE.replace(
            "- Classical Adventure cinematography — camera as storyteller.\n", "")
        paths.BIBLE.write_text(text, encoding="utf-8")
        self.answers(light=NATURALISTIC["value"], texture="my own words")
        self.assertEqual(bible.anchor_drift(), [])
        self.assertEqual(bible.anchor_conflicts(), [])


class TheProbeRefusesAContradiction(unittest.TestCase):
    """The sync runs on the interview save and at boot, so a clash should
    not reach a render. It refuses anyway: an anchor naming a style the
    library does not carry cannot be rebuilt from, and that is exactly the
    case where a silent contradiction would ride."""

    def test_the_guard_is_on_the_path_that_spends_money(self):
        src = (ROOT / "app" / "generate.py").read_text(encoding="utf-8")
        i = src.index("def sample_probe(")
        seg = src[i:i + 4000]
        self.assertIn("bible.anchor_conflicts()", seg)
        # before the render is dispatched, not after
        self.assertLess(seg.index("anchor_conflicts"), seg.index("_samples_dir"))


class TheReconciliationRunsRatherThanAsks(unittest.TestCase):
    """"Migrations run, not offered" — and the installs carrying this bug
    are by definition the ones that already have a stale section."""

    SRC = (ROOT / "app" / "main.py").read_text(encoding="utf-8")

    def test_the_interview_save_reconciles(self):
        i = self.SRC.index("async def api_save_interview")
        self.assertIn("bible.sync_from_anchors()", self.SRC[i:i + 900])

    def test_boot_reconciles_every_production(self):
        i = self.SRC.index("def _resync_bible_anchors")
        seg = self.SRC[i:i + 2200]
        self.assertIn("paths.list_projects()", seg)
        self.assertIn("bible.sync_from_anchors()", seg)
        self.assertIn("bible.anchor_conflicts()", seg)
        self.assertIn("paths.set_project(prev)", seg)

    def test_there_is_no_button(self):
        self.assertNotIn("sync-rendering", self.SRC)
        self.assertNotIn("/api/bible/resync", self.SRC)

    def test_the_state_is_readable_before_a_render_is_paid_for(self):
        i = self.SRC.index("def api_get_style_bible")
        self.assertIn("anchor_conflicts", self.SRC[i:i + 700])



class ABibleThatNamesNoStyleStillFollowsTheAnchor(unittest.TestCase):
    """User-hit on the LIVE tenant, 2026-08-22: "I changed the rendering
    style on my oxcart screenplay, went to the panel tab and rendered
    another take. It did not pick up the rendering style change."

    The panel prompt reads `bible.render_context()` fresh on every render,
    so nothing is cached — the break was upstream. `anchor_drift` began
    with `if not stated: continue`, which needed the section to NAME a
    style before it would look at it. A bible whose Rendering Language is
    prose, or an older draft that never stamped a name, matched nothing:
    no drift, so no rewrite and no conflict. The change landed nowhere and
    said so nowhere.

    Rendering Language is DERIVED, so the comparison is the body."""

    NAMELESS = ("# Oxcart" + chr(10) * 2
                + "## Rendering Language" + chr(10)
                + "### Required" + chr(10)
                + "- Painted concept art with the brush left visible." + chr(10)
                + "- Massed tone rather than outline." + chr(10) * 2
                + "### Avoid" + chr(10)
                + "- Photographic detail." + chr(10) * 2
                + "## Lighting Language" + chr(10)
                + "- hard sun" + chr(10))

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-live-"))
        self._bible, self._data = paths.BIBLE, paths.DATA
        paths.BIBLE = self.tmp / "bible.md"
        paths.DATA = self.tmp / "data"
        paths.DATA.mkdir(parents=True, exist_ok=True)
        paths.BIBLE.write_text(self.NAMELESS, encoding="utf-8")
        store._atomic_write_json(paths.DATA / "interview.json",
                                 {"medium": ANSWER})

    def tearDown(self):
        paths.BIBLE, paths.DATA = self._bible, self._data

    def test_the_section_names_nothing_which_is_the_whole_problem(self):
        self.assertEqual(bible.stated_style("medium"), "")

    def test_it_is_caught_anyway(self):
        [d] = bible.anchor_drift()
        self.assertEqual(d["anchor"], "medium")
        self.assertEqual(d["stated"], "(unstated)")
        self.assertEqual(d["chosen"], "Photo Real")

    def test_the_rewrite_reaches_the_panel_prompt(self):
        """`render_context` is what `generate._style_context` calls for
        every panel, and it reads the file fresh — so proving it here
        proves the render."""
        bible.sync_from_anchors()
        brief = bible.render_context("")
        self.assertIn("Photo Real rendering style", brief)
        self.assertIn("Lens-accurate detail falloff", brief)
        self.assertNotIn("brush left visible", brief)

    def test_a_bible_with_no_such_section_is_not_drift(self):
        """There is nothing to rebuild, and reporting one would refuse
        renders over a section the document never had."""
        paths.BIBLE.write_text("# Oxcart" + chr(10) * 2
                               + "## Lighting Language" + chr(10)
                               + "- hard sun" + chr(10), encoding="utf-8")
        self.assertEqual(bible.anchor_drift(), [])
        self.assertEqual(bible.anchor_conflicts(), [])
        self.assertEqual(bible.sync_from_anchors(), [])

    def test_the_other_two_anchors_still_need_a_name(self):
        """Overall Visual Identity and Lighting Language are SYNTHESES of
        the anchor and the screenplay, not transcriptions of an entry, so
        there is no body to compare — only the style they name."""
        i = (ROOT / "app" / "bible.py").read_text(encoding="utf-8")
        j = i.index("# The other two sections are SYNTHESES")
        self.assertIn("if stated and stated.lower() != want.lower():",
                      i[j:j + 400])

if __name__ == "__main__":
    unittest.main()
