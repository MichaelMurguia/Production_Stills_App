"""Eight defects found reviewing the 2026.08.05.90 batch, and their fixes.

Every one of these shipped. They are grouped here rather than scattered
because they share a cause worth naming: each was a correct-looking line
whose *runtime* behaviour nobody measured. A predicate returning "" on
the branch it exists to fill; a body-level flag with no teardown; a
snapshot read long after it went stale; a sidecar trusted on existence;
a fixed temp path under new concurrency; a flag set and then deleted two
lines later; a disposer in `catch` instead of `finally`; a guard skipped
by the exact input it was written for.

The regressions below each reproduce the failure, not the fix.
"""
from __future__ import annotations

import re
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


class AppearsInFillsTheCellItReserves(unittest.TestCase):
    """FINDING 1. It read:

        (s.ref_ids || []).length && acts ? "" : <the blocker>

    which returns EMPTY exactly when the condition holds — and
    `renderCastAccepted`, its only caller, is reached only when the
    subject HAS an approved picture. So on the cast state, as soon as the
    read had produced acts, APPEARS IN rendered blank: the one thing B3
    forbids, in the cell written to satisfy B3."""

    def seg(self):
        """The CODE, not the comment above it. The comment quotes the old
        predicate verbatim so the next reader knows what was wrong, and a
        test that searched the raw text would match that quotation — the
        same way a test forbidding a removed button's label matched the
        comment recording its removal (2026-09-14)."""
        i = JS.index("const appearsIn = ")
        body = JS[i:JS.index(NL + "  };", i)]
        return re.sub(r"/\*.*?\*/", "", body, flags=re.S)

    def test_it_always_states_the_blocker(self):
        seg = self.seg()
        self.assertIn("NOT UNTIL THIS SUBJECT IS ON A BREAKDOWN", seg)
        self.assertNotIn('? ""', seg, "a branch that can blank the cell")

    def test_it_no_longer_asks_about_reference_images(self):
        """Whether a subject has PICTURES has nothing to do with which
        acts it appears in. The edge does not exist, so there is no
        condition to write."""
        seg = self.seg()
        self.assertNotIn("ref_ids", seg)
        self.assertNotIn("getAnalysis", seg)

    def test_the_cell_is_still_on_the_card(self):
        self.assertIn("<b>APPEARS IN</b>", JS)


class TheCastFlagIsTornDownByTheRouter(unittest.TestCase):
    """FINDING 2. `body[data-cast="1"]` hides `.panel.step`,
    `.wiz-logline` and `.wiz-head`. Nothing cleared it on navigation, so:
    open the cast, go to stage 01, come back to stage 02 — and stage 02
    rendered as the cast roster with the whole stage hidden behind it.

    Its sibling `data-reading` has always had an explicit clear."""

    def test_showview_clears_it(self):
        i = JS.index("async function showView(")
        seg = JS[i:JS.index("try { await views[name]", i)]
        self.assertIn("delete document.body.dataset.cast;", seg)

    def test_it_is_cleared_before_the_view_renders(self):
        """After the render would be a flash of the wrong stage."""
        i = JS.index("async function showView(")
        seg = JS[i:JS.index("try { await views[name]", i)]
        self.assertLess(seg.index("delete document.body.dataset.cast"),
                        seg.index("activeView = name"))

    def test_arriving_at_a_subject_still_sets_it(self):
        """renderWizard runs after the router and re-sets the flag when it
        is arriving AT a cast screen — the clear must not break that."""
        self.assertIn('if (castOpen) document.body.dataset.cast = "1";', JS)

    def test_the_css_that_made_it_matter_is_unchanged(self):
        self.assertIn('body[data-cast="1"] .panel.step', CSS)


class TheBibleGateAsksALiveQuestion(unittest.TestCase):
    """FINDING 3. `renderWizard` fetches `state` ONCE. Two gates asked
    that snapshot whether the Bible was saved, and `saveBible` never
    refreshed it — so after saving in step 04, a cast screen opened
    without leaving the stage still refused to Generate, saying the Bible
    was not saved, with the saved document above it."""

    def test_there_is_one_live_answer(self):
        self.assertIn("const bibleIsSaved = () => bibleSaved;", JS)

    def test_every_gate_asks_it_rather_than_the_snapshot(self):
        for site in ("return !bibleIsSaved()",          # castGenBlock
                     "gate: bibleIsSaved() ? \"\" :",    # the locations banner
                     ": bibleIsSaved()"):                # the per-row verb
            self.assertIn(site, JS, site)

    def test_no_gate_still_reads_the_snapshot(self):
        """The wizard's own gates, not the unrelated readers elsewhere in
        the file — `renderWizard` is the long-lived surface."""
        i = JS.index("async function renderWizard()")
        seg = JS[i:]
        # Everything AFTER the one declaration that seeds the live answer.
        # That declaration is the only legitimate reader of the snapshot.
        decl = "let bibleSaved = !!state?.stage_summary?.production_design?.bible_saved;"
        self.assertIn(decl, seg)
        after = seg.split(decl, 1)[1]
        for snapshot in ("state.stage_summary?.production_design?.bible_saved",
                         "state?.stage_summary?.production_design?.bible_saved"):
            self.assertNotIn(snapshot, after, "a gate still reads the snapshot")

    def test_saving_moves_it_at_the_moment_the_server_confirms(self):
        i = JS.index("const saveBible = async (")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("bibleSaved = true;", seg)
        self.assertLess(seg.index('api("/api/style-bible"'), seg.index("bibleSaved = true;"))


class TheReadFlagSurvivesUntilTheReadBegins(unittest.TestCase):
    """FINDING 6. `document.body.dataset.reading = "1"` was set, then
    `showView("screenplay")` rendered the stage, which calls
    `syncScreenplayStage()`, which DELETED the flag because `theRead.on`
    was still false — `startTheRead` makes two round trips before
    `begin()` sets it, and the render needs one. The stage flashed fully
    visible: the exact thing the line above it claims to prevent."""

    def test_the_stage_honours_an_arming_read(self):
        i = JS.index("function syncScreenplayStage()")
        seg = JS[i:JS.index(NL + "}", i)]
        self.assertIn("theRead.arming", seg)

    def test_the_upload_path_arms_before_it_navigates(self):
        i = JS.index("theRead.arming = true;")
        seg = JS[i:i + 200]
        self.assertLess(seg.index("theRead.arming = true;"),
                        seg.index('showView("screenplay")'))

    def test_arming_is_released_on_every_exit(self):
        """Including the two early returns ABOVE begin() — an analysis
        already exists, or no model is usable. Nothing cleared it there,
        and the stage would have stayed hidden for the life of the page:
        worse than the flash it was added to stop."""
        i = JS.index("async function startTheRead()")
        seg = JS[i:JS.index(NL + "}", i)]
        self.assertIn("} finally {", seg)
        self.assertIn("theRead.arming = false;", seg)
        self.assertIn("if (!began) syncScreenplayStage();", seg)

    def test_the_read_itself_clears_it_at_each_end(self):
        for fn in ("async begin(engine, preview = false) {",
                   "finish(analysis) {"):
            i = JS.index(fn)
            self.assertIn("this.arming = false;", JS[i:i + 320], fn)


class TheSpinnerStopsOnSuccessToo(unittest.TestCase):
    """FINDING 7. `stop.done()` was in the `catch` only, so every
    SUCCESSFUL render left a 1s interval ticking against a node
    `refreshCast()` had already replaced. One leaked timer per generate,
    for the life of the page."""

    def test_it_is_disposed_in_a_finally(self):
        i = JS.index("const castGenerate = async (s, host) => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("} finally {", seg)
        self.assertIn("stop.done();", seg.split("} finally {")[1])

    def test_it_is_not_the_old_throwing_disposer(self):
        """A previous fix here called `stop?.()` — startBusy returns an
        OBJECT — which threw inside the finally and swallowed the error."""
        i = JS.index("const castGenerate = async (s, host) => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertNotIn("stop?.()", seg)

    def test_every_startbusy_caller_still_disposes(self):
        for m in re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*startBusy\(", JS):
            name = m.group(1)
            seg = JS[m.end():m.end() + 4000]
            self.assertTrue(f"{name}.done()" in seg or f"{name}?.done()" in seg,
                            f"{name} at line {JS[:m.start()].count(NL) + 1}")


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

    def tearDown(self):
        paths.HOME = self._was["HOME"]
        paths.PROJECTS_DIR = self._was["PROJECTS_DIR"]
        paths.ACTIVE_PROJECT_FILE = self._was["ACTIVE"]
        paths.SETTINGS = self._was["SETTINGS"]
        paths.set_project(self._was["slug"])
        self._tmp.cleanup()


class ThePageSidecarNamesItsDraft(_Home):
    """FINDING 4. `page_offsets()` returned `_pages.json` on EXISTENCE
    alone, and `set_screenplay` never removed it. Upload a PDF, then a
    second draft: the cast screen printed page refs computed from the
    first one's pagination. A `.txt` draft — which has no pages at all —
    inherited them instead of falling back to scene ordinals."""

    def test_a_new_draft_invalidates_it(self):
        store.set_screenplay("a.txt", ("INT. ONE - DAY" + NL * 2 + "x" * 400).encode())
        (paths.SCREENPLAY_DIR / "_pages.json").write_text(
            '{"offsets": [0, 100, 200]}', encoding="utf-8")
        store.set_screenplay("b.txt", ("INT. TWO - DAY" + NL * 2 + "y" * 400).encode())
        self.assertEqual(store.page_offsets(), [],
                         "the previous draft's pagination survived the upload")

    def test_an_unstamped_sidecar_is_not_believed(self):
        """One written before the stamp existed cannot prove what it
        describes, so it is discarded rather than trusted."""
        store.set_screenplay("a.txt", ("INT. ONE - DAY" + NL * 2 + "z" * 400).encode())
        sc = paths.SCREENPLAY_DIR / "_pages.json"
        sc.write_text('{"offsets": [0, 50]}', encoding="utf-8")
        self.assertEqual(store.page_offsets(), [])
        self.assertFalse(sc.exists(), "a sidecar it refused to trust was left behind")

    def test_a_text_draft_reports_no_pages(self):
        store.set_screenplay("draft.txt", ("INT. ONE - DAY" + NL * 2 + "q" * 900).encode())
        self.assertEqual(store.page_offsets(), [])
        self.assertEqual(store.page_of(500), 0, "page_of must say 'cannot know'")


class EachRenderWritesItsOwnFile(unittest.TestCase):
    """FINDING 5. `subject_portrait` rendered to the single fixed path
    `data/subject_render.png` and unlinked it in `finally`. The cast
    ribbon now offers Generate from twelve tiles, so two in flight either
    handed one subject the other's picture, or raced the unlink and died
    on FileNotFoundError — which is not a GenerationError, so it escaped
    main.py's handler as a 500 instead of a stated refusal."""

    SRC = (ROOT / "app/generate.py").read_text(encoding="utf-8")

    def test_the_path_is_unique_per_call(self):
        i = self.SRC.index("def subject_portrait(")
        seg = self.SRC[i:self.SRC.index(NL + "def ", i + 10)]
        self.assertIn("uuid.uuid4().hex", seg)
        self.assertNotIn('paths.DATA / "subject_render.png"', seg)

    def test_it_is_still_cleaned_up(self):
        i = self.SRC.index("def subject_portrait(")
        seg = self.SRC[i:self.SRC.index(NL + "def ", i + 10)]
        self.assertIn("out.unlink(missing_ok=True)", seg)
        self.assertIn("finally:", seg)

    def test_uuid_is_imported(self):
        self.assertIn(NL + "import uuid" + NL, self.SRC)


class TheRestoreGuardCannotBeSkipped(unittest.TestCase):
    """FINDING 8. The draft-identity guard ran only `if said:` — so a
    body with no `screenplay_sha256` skipped it entirely. That is exactly
    the shape of the reads it was written to stop: the field postdates
    them, so a browser's cached copy has none.

    It could not simply be made mandatory. An analysis read before the
    stamping also has no sha, and EDITING one comes back through this
    route — a blanket refusal would 409 every edit on every project read
    before that release. The two separate by what the studio holds: a
    restore arrives when there is nothing here, an edit when there is."""

    def seg(self):
        i = MAIN.index('@app.put("/api/wizard/analysis")')
        return MAIN[i:MAIN.index(NL + "@app.", i + 10)]

    def test_an_unnamed_restore_is_refused(self):
        seg = self.seg()
        self.assertIn("restoring = store.load_wizard_analysis() is None", seg)
        self.assertIn("if restoring and not said:", seg)

    def test_an_edit_of_a_pre_stamp_read_still_saves(self):
        """The regression this fix had to avoid: projects read before the
        stamping hold an analysis with no sha, and confirming a language
        or answering a question saves through here."""
        seg = self.seg()
        i = seg.index("if restoring and not said:")
        j = seg.index("store.save_wizard_analysis(body)")
        self.assertLess(i, j)
        self.assertIn("if not said and here:", seg)
        self.assertIn('body["screenplay_sha256"] = here', seg)

    def test_a_foreign_draft_is_still_refused(self):
        seg = self.seg()
        self.assertIn("names screenplay", seg)
        self.assertIn("if said != here:", seg)


if __name__ == "__main__":
    unittest.main()
