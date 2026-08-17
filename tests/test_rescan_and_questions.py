"""Rescanning swatches, answered design questions, and the hour that wasn't.

Three user reports, 2026-08-07:

  * "For GRM it did not pick up Onyx black, or any red… I want to rescan
    for that swatch" — and a deep pass for whatever a first read missed.
    A rescan must be told what the palette already holds and already
    refused, or it proposes the same colours again.
  * The breakdown told the user to "run a DESIGN_EXPLORATION board" while
    they were reading one. Answers now exist, and they must reach the
    image prompt or answering is theatre.
  * A slugline reading SAME became the board's time of day. SAME is a
    continuity marker, not an hour.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import autofill, generate, paths, store, wizard  # noqa: E402


class ContinuityIsNotAnHour(unittest.TestCase):
    def test_continuity_markers_do_not_become_a_time(self):
        for marker in ("SAME", "same", "CONTINUOUS", "LATER", "MOMENTS LATER",
                       "CONT'D", "PRESENT"):
            self.assertEqual(autofill._real_hour(marker), "", marker)

    def test_real_hours_survive(self):
        for hour in ("DAY", "night", "DUSK", "MAGIC HOUR"):
            self.assertEqual(autofill._real_hour(hour), hour.upper())

    def test_empty_stays_empty(self):
        self.assertEqual(autofill._real_hour(""), "")
        self.assertEqual(autofill._real_hour(None), "")

    def test_the_dropdown_always_offers_the_hours(self):
        """It was an <input list=…>; a datalist filters itself away against
        a value like SAME, leaving the user nothing to pick."""
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        i = js.index('data-setf="tod"')
        block = js[i:i + 900]
        self.assertIn('<select id="sp-tod"', block)
        self.assertIn("TIMES_OF_DAY", block)
        self.assertNotIn('list="tod-list"', js,
                         "the filtering datalist must be gone")
        self.assertIn("spec.setting?.time_of_day ? [spec.setting.time_of_day]", block,
                      "an unrecognised stored value must still be offered, "
                      "or opening the sheet would silently change it")


class _IsolatedStyleContext(unittest.TestCase):
    """compile_panel_prompt requires a rendering language, and these tests
    are not about it — they must never read the real install's Art
    Direction Bible (it emptied with a production switch and took nine
    tests down). A canned language keeps the real prompt pipeline running
    deterministically. The home redirect (2026-08-12 review) closes the
    residual leak: rejection_feedback and project_name otherwise read the
    real install's boards/ and project files, so a real production holding
    a SPEC_X rejection would bleed into these assertions."""

    def setUp(self):
        from unittest import mock
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-style-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
                       paths.SETTINGS, paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        self._style_patches = [
            mock.patch.object(generate.bible, "render_context",
                              return_value=""),
            mock.patch.object(generate, "load_style_bible",
                              return_value="Analog sci-fi. Real materials."),
        ]
        for p in self._style_patches:
            p.start()

    def tearDown(self):
        for p in self._style_patches:
            p.stop()
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)


class AnsweredQuestionsReachThePrompt(_IsolatedStyleContext):
    def spec(self, **extra):
        return {"specification_id": "SPEC_X", "subject": "GRM BRIDGE",
                "board_type": "LOCATION", "mode": "CANON_EXTRACTION",
                "setting": {"int_ext": "INT", "location": "GRM BRIDGE"},
                "panels": [], "evidence_ledger": [], **extra}

    def panel(self):
        return {"id": "P1", "panel_id": "P1", "purpose": "establish",
                "required_objects": [], "scale": "wide"}

    def test_an_answered_question_is_stated_as_canon(self):
        out = generate.compile_panel_prompt(
            self.spec(unresolved_questions=["What colour is the Onyx Unit hull?"],
                      question_answers={"What colour is the Onyx Unit hull?":
                                        "matte black, no reflection"}),
            self.panel(), [])
        self.assertIn("DESIGN DECISIONS", out)
        self.assertIn("What colour is the Onyx Unit hull? → matte black, no reflection", out)

    def test_an_unanswered_question_never_reaches_the_prompt(self):
        """An open question in a prompt is an invitation to invent."""
        out = generate.compile_panel_prompt(
            self.spec(unresolved_questions=["What colour is the hull?"]),
            self.panel(), [])
        self.assertNotIn("DESIGN DECISIONS", out)
        self.assertNotIn("What colour is the hull?", out)

    def test_a_blank_answer_counts_as_unanswered(self):
        out = generate.compile_panel_prompt(
            self.spec(unresolved_questions=["Q?"], question_answers={"Q?": "   "}),
            self.panel(), [])
        self.assertNotIn("DESIGN DECISIONS", out)

    def test_only_answered_ones_are_sent(self):
        out = generate.compile_panel_prompt(
            self.spec(unresolved_questions=["A?", "B?"],
                      question_answers={"A?": "yes", "B?": ""}),
            self.panel(), [])
        self.assertIn("A? → yes", out)
        self.assertNotIn("B?", out)

    def test_the_copy_no_longer_contradicts_itself(self):
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        self.assertNotIn("decide them yourself or run a DESIGN_EXPLORATION board", js)
        # The mode-aware copy survives; STEP_SEQUENCE_SPEC §3.2 made the
        # step's own note Courier, so it states the same thing in caps.
        self.assertIn("EXPLORING IS HOW YOU DECIDE THEM", js)
        self.assertIn("ANSWER ONE AND IT BECOMES CANON", js)
        self.assertIn('data-f="answer-qs"', js)

    def test_the_answer_verb_does_not_spend_amber(self):
        """.block-act is canonically the amber verb on a BLOCKING row; the
        questions STEP is a report, so its verb is a plain verb — ink and
        underlined since §1.4 (2026-08-14), never amber."""
        js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
        i = js.index('data-f="answer-qs"')
        self.assertIn('class="verb"', js[i - 60:i])


class RescanKnowsWhatItHas(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-rescan-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
                       paths.SETTINGS, paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()

    def tearDown(self):
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sw(self, lang, name, hexv, status="APPROVED"):
        ref = store.add_reference(f"{name}.png", wizard.render_swatch_png(hexv),
                                  "COLOR_PALETTE", [], [],
                                  f"{lang} · {name} · {hexv} · a label",
                                  source="swatch-proposal")
        store.set_reference_status(ref["id"], status,
                                   "not wanted" if status == "REJECTED" else "")
        return ref["id"]

    def test_it_names_what_the_palette_already_holds(self):
        self.sw("GRM", "LEDGER GREEN", "#1D6E63")
        note = wizard.rescan_note(["GRM"])
        self.assertIn("ALREADY HOLDS", note)
        self.assertIn("#1D6E63 (LEDGER GREEN)", note)

    def test_it_names_what_was_rejected_so_it_is_not_asked_twice(self):
        self.sw("GRM", "BAD BROWN", "#704838", status="REJECTED")
        note = wizard.rescan_note(["GRM"])
        self.assertIn("already REJECTED", note)
        self.assertIn("#704838 (BAD BROWN)", note)

    def test_it_scopes_to_the_named_language(self):
        self.sw("GRM", "GREEN", "#1D6E63")
        self.sw("RESISTANCE", "RUST", "#8A4B2E")
        note = wizard.rescan_note(["GRM"])
        self.assertIn("ONLY for these design languages, and nothing else: GRM", note)
        self.assertIn("#1D6E63", note)
        self.assertNotIn("#8A4B2E", note, "another language's colours are not this pass's business")

    def test_the_designers_brief_rides_the_pass(self):
        note = wizard.rescan_note(["GRM"], note="no Onyx Unit black, and no reds")
        self.assertIn("no Onyx Unit black, and no reds", note)
        self.assertIn("production designer says", note)

    def test_a_deep_pass_says_what_deep_means(self):
        note = wizard.rescan_note(None, deep=True)
        self.assertIn("DEEP pass", note)
        for hint in ("uniforms", "signage", "corrosion", "light sources"):
            self.assertIn(hint, note)

    def test_a_first_pass_adds_nothing(self):
        """No languages, no note, no deep, nothing in the library — the
        instruction must be exactly what it always was."""
        self.assertEqual(wizard.rescan_note(None), "")

    def test_swatches_in_play_splits_live_from_rejected(self):
        self.sw("GRM", "GREEN", "#1D6E63")
        self.sw("GRM", "BAD", "#704838", status="REJECTED")
        live, dead = wizard.swatches_in_play(["GRM"])
        self.assertEqual([p["hex"] for p in live["GRM"]], ["#1D6E63"])
        self.assertEqual([p["hex"] for p in dead["GRM"]], ["#704838"])

    def test_non_palette_references_are_ignored(self):
        store.add_reference("car.png", wizard.render_swatch_png("#111111"),
                            "VEHICLE_GEOMETRY", [], [], "GRM · CAR · #111111 · x")
        live, _ = wizard.swatches_in_play()
        self.assertFalse(live)


class RejectionReasonsArePrimaryRules(_IsolatedStyleContext):
    """A rejection reason is a PRIMARY rule for the next take (user
    2026-08-08). The mechanism already carried reasons into the next
    prompt — verified live before changing anything — but as a bullet ~80%
    of the way in, after the forbidden list. In a 16,000-character prompt
    that is a footnote. It leads now, and the tail re-binds it."""

    def spec(self, **extra):
        return {"specification_id": "SPEC_X", "subject": "DINER",
                "board_type": "LOCATION", "mode": "CANON_EXTRACTION",
                "setting": {"int_ext": "INT", "location": "DINER"},
                "panels": [], "evidence_ledger": [], **extra}

    def panel(self):
        return {"id": "P1", "panel_id": "P1", "purpose": "establish",
                "required_objects": [], "scale": "wide"}

    def compiled(self, monkey_reasons):
        from unittest import mock
        with mock.patch.object(generate, "rejection_feedback",
                               return_value=monkey_reasons):
            return generate.compile_panel_prompt(self.spec(), self.panel(), [])

    def test_corrections_lead_the_prompt(self):
        out = self.compiled(["the jukebox must be chrome and red, never wood"])
        i = out.index("DIRECTOR'S CORRECTIONS — PRIMARY RULES")
        self.assertLess(i / len(out), 0.25,
                        "corrections belong at the head, not 80% deep")
        self.assertIn("- the jukebox must be chrome and red, never wood", out)
        self.assertIn("overrides ANY conflicting instruction", out)

    def test_the_tail_carries_the_full_text(self):
        """A lossy rewrite can drop a pointer's target — the tail repeats
        every correction verbatim (2026-08-13), not a reference to it."""
        out = self.compiled(["no neon signage"])
        self.assertGreater(out.rindex("- no neon signage"),
                           out.index("FINAL INSTRUCTION"))
        self.assertIn("They are, again, in full:", out)
        self.assertNotIn("Re-read", out, "the pointer form is retired")

    def test_no_rejections_means_no_section_anywhere(self):
        out = self.compiled([])
        self.assertNotIn("DIRECTOR'S CORRECTIONS", out)
        self.assertNotIn("again, in full", out)

    def test_the_old_buried_section_is_gone(self):
        out = self.compiled(["a reason"])
        self.assertNotIn("REJECTION FEEDBACK", out,
                         "the legacy mid-prompt section stays dead")

    def test_a_correction_still_suppresses_its_matching_lesson(self):
        """The dedupe against project negatives survives the move: the
        correction rides the head and the tail echo, but never the
        PROJECT RULES section. (Renamed 2026-08-17 — the block carried the
        name of a mechanism that never wrote to it; see review F2.)"""
        from unittest import mock
        with mock.patch.object(generate, "rejection_feedback",
                               return_value=["never photoreal"]), \
             mock.patch.object(generate, "project_negatives",
                               return_value=["never photoreal", "no anime"]):
            out = generate.compile_panel_prompt(self.spec(), self.panel(), [])
        lessons = out[out.index("PROJECT RULES"):
                      out.index("FINAL INSTRUCTION")]
        self.assertNotIn("never photoreal", lessons)
        self.assertEqual(out.count("never photoreal"), 2,
                         "head and tail echo, nowhere else")
        self.assertIn("no anime", out)

    def test_the_rewriter_is_told_to_preserve_corrections_and_camera(self):
        """The openai-chat pipeline rewrites the whole compiled prompt; its
        rules must NAME the corrections and camera blocks or the rewrite
        can legally drop them (found 2026-08-13, CANYON_GRM_GT40_GETAWAY:
        1 of 5 corrections survived a re-render)."""
        rules = generate._rewriter_rules()
        self.assertIn("DIRECTOR'S CORRECTIONS", rules)
        self.assertIn("Never\n  drop, soften, or average".replace("\n  ", " "),
                      rules.replace("\n  ", " "))
        self.assertIn("CAMERA block is binding framing", rules)

    def test_plates_of_one_subject_are_declared_as_one_subject(self):
        """User-hit 2026-08-14: five GT40 plates each got their own
        "this EXACT vehicle" line and NOTHING said they were one car from
        five angles — a model can read that as five different vehicles."""
        plates = [{"id": f"REF-002{n}", "role": "VEHICLE_GEOMETRY — GT40"}
                  for n in range(5)]
        out = "\n".join(generate._reference_role_lines(plates))
        self.assertIn("Attached images 1–5", out)
        self.assertIn("REF-0020, REF-0021, REF-0022, REF-0023, REF-0024", out)
        self.assertIn("5 IMAGES OF THE SAME SUBJECT", out)
        self.assertIn("never 5 different things", out)
        self.assertIn("They do NOT control", out)
        self.assertEqual(out.count("Attached image"), 1,
                         "one declaration for the set, not five")

    def test_a_lone_plate_reads_exactly_as_before(self):
        out = "\n".join(generate._reference_role_lines(
            [{"id": "REF-0040", "role": "VEHICLE_GEOMETRY — GRM JET"}]))
        self.assertIn("- Attached image 1 (REF-0040, "
                      "role VEHICLE_GEOMETRY — GRM JET): controls", out)
        self.assertIn("It does NOT control", out)
        self.assertNotIn("SAME SUBJECT", out)

    def test_different_subjects_keep_their_own_declarations(self):
        out = "\n".join(generate._reference_role_lines([
            {"id": "REF-0001", "role": "VEHICLE_GEOMETRY — GT40"},
            {"id": "REF-0002", "role": "CHARACTER_LIKENESS — KYRA"},
            {"id": "REF-0003", "role": "VEHICLE_GEOMETRY — GT40"},
        ]))
        self.assertIn("Attached images 1, 3 (REF-0001, REF-0003", out)
        self.assertIn("Attached image 2 (REF-0002", out)

    def test_vehicle_geometry_no_longer_argues_for_the_reference_angle(self):
        """The role line used to say 'match that image closely' about the
        angle — directly opposing a corrected angle. Camera and
        corrections outrank the reference's own angle now."""
        ref = {"id": "REF-0040", "role": "VEHICLE_GEOMETRY"}
        out = generate.compile_panel_prompt(self.spec(), self.panel(), [ref])
        self.assertNotIn("match that image closely", out)
        self.assertIn("render THIS vehicle from that angle even if no "
                      "attached image shows it", out)
class CorrectionsCanRetire(unittest.TestCase):
    """A correction that was satisfied or superseded stops carrying (user
    2026-08-08): CAND-0072 followed "shoot into a corner" but kept the
    person at the window, because an OLDER carried note — "closer
    adherence to the reference provided" — stood as a counter-order.
    Corrections were permanent; every stale note fought every new one."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-retire-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
                       paths.SETTINGS, paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()

    def tearDown(self):
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cand(self, cid, reason, retired=False):
        import json as _json
        d = paths.BOARDS_DIR / "SPEC_X"
        d.mkdir(parents=True, exist_ok=True)
        rec = {"candidate_id": cid, "panel_id": "P1", "status": "REJECTED",
               "status_reason": reason}
        if retired:
            rec["feedback_retired"] = True
        (d / f"{cid}.json").write_text(_json.dumps(rec), encoding="utf-8")

    def test_a_retired_correction_stops_carrying(self):
        self.cand("CAND-0068", "closer adherence to the reference")
        self.cand("CAND-0071", "get rid of the person at the window")
        generate.retire_feedback("SPEC_X", "CAND-0068")
        out = generate.rejection_feedback("SPEC_X", "P1")
        self.assertEqual(out, ["get rid of the person at the window"])

    def test_reinstating_brings_it_back(self):
        self.cand("CAND-0068", "closer adherence", retired=True)
        generate.retire_feedback("SPEC_X", "CAND-0068", retired=False)
        self.assertEqual(generate.rejection_feedback("SPEC_X", "P1"),
                         ["closer adherence"])

    def test_the_rejection_itself_is_untouched(self):
        self.cand("CAND-0068", "a reason")
        generate.retire_feedback("SPEC_X", "CAND-0068")
        rec = generate.get_candidate("SPEC_X", "CAND-0068")
        self.assertEqual(rec["status"], "REJECTED")
        self.assertEqual(rec["status_reason"], "a reason")

    def test_newest_correction_leads_the_list(self):
        """The latest note is the director's current mind."""
        self.cand("CAND-0068", "older note")
        self.cand("CAND-0071", "newest note")
        self.assertEqual(generate.rejection_feedback("SPEC_X", "P1"),
                         ["newest note", "older note"])

    def test_retiring_an_unknown_candidate_raises(self):
        with self.assertRaises(KeyError):
            generate.retire_feedback("SPEC_X", "CAND-9999")

    def test_a_deleted_takes_archived_reason_retires_too(self):
        self.cand("CAND-0068", "archived note")
        generate.archive_feedback("SPEC_X", "P1", "archived note", "CAND-0068")
        (paths.BOARDS_DIR / "SPEC_X" / "CAND-0068.json").unlink()
        self.assertEqual(generate.rejection_feedback("SPEC_X", "P1"),
                         ["archived note"])
        generate.retire_feedback("SPEC_X", "CAND-0068")
        self.assertEqual(generate.rejection_feedback("SPEC_X", "P1"), [])


if __name__ == "__main__":
    unittest.main()
