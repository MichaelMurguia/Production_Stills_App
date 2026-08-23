"""A hand-edited prompt can be SAVED onto the panel (user 2026-08-16: "I
need to be able to Save the prompt once I edit it — explicit button").

An edit that rides one take is a test; a correction the compile cannot
express is a standing fact about the panel. But a saved prompt is the
sharpest override in the app: while one exists, steps 01–04 no longer write
that panel's render text, so editing the camera or the required objects
changes nothing visible. That is precisely the silent gate the product
rules forbid, so most of what is pinned here is the STATE being readable
before it is hit, not the storage."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def preview_block() -> str:
    """The whole preview handler, bounded by the next handler rather than by
    a character count — a fixed window silently stops covering the code it
    was written to pin as the block grows."""
    i = JS.index('$("[data-f=preview]", card).onclick')
    j = JS.index("// Composition check (2026-08-13)", i)
    return JS[i:j]


class TheEditorCanSave(unittest.TestCase):
    def test_there_is_an_explicit_save_button(self):
        b = preview_block()
        self.assertIn('data-f="save-prompt"', b)
        self.assertIn("Save prompt to this panel", b)

    def test_saving_posts_to_the_panel(self):
        b = preview_block()
        self.assertIn("/panels/${p.id}/prompt`", b)
        self.assertIn('method: "POST"', b)

    def test_clearing_is_a_separate_act_from_reverting(self):
        """Revert restores the COMPILE in the box — it is how you see what
        steps 01–04 would make of the panel while an override sits on it.
        Clearing deletes the saved text. Merging them would mean a user who
        wanted to look lost their save."""
        b = preview_block()
        self.assertIn('data-f="clear-saved"', b)
        self.assertIn("promptBox.value = r.compiled", b)

    def test_the_editor_loads_what_a_render_would_send(self):
        self.assertIn('return {"prompt": saved or compiled,', MAIN)
        self.assertIn('"compiled": compiled,', MAIN)
        self.assertIn('"saved": bool(saved),', MAIN)

    def test_an_approved_take_freezes_the_prompt_and_says_why(self):
        b = preview_block()
        self.assertIn("${r.frozen ?", b)
        self.assertIn('"frozen": bool(store.approved_takes_by_panel', MAIN)

    def test_the_refusal_is_on_screen_not_only_in_a_tooltip(self):
        """User-caught 2026-08-16: "I cant save prompt to panel once I open
        and edit". The panel had an approved take, Save was greyed, and the
        ONLY statement of why was a hover title — while the help text below
        told them to press it. A disabled control has to state its unmet
        condition beside it and say where it is resolved."""
        b = preview_block()
        self.assertIn("AN APPROVED TAKE FREEZES THIS PANEL · NO PROMPT CAN BE SAVED TO IT", b)
        self.assertIn("Withdraw the approval on", b)
        self.assertIn("Settled by ${esc(approvedTakes.join", b,
                      "name the take that did it, not just the fact")

    def test_the_frozen_help_does_not_advertise_the_dead_button(self):
        """The unfrozen copy says "Save prompt to this panel to make them
        stick". Showing that beside a Save that cannot be pressed is worse
        than showing nothing."""
        b = preview_block()
        i = b.index("editHelp.innerHTML = r.frozen")
        frozen_arm = b[i:b.index(": saved", i)]
        self.assertNotIn("Save prompt to this panel</b> to make", frozen_arm)

    def test_the_one_take_path_stays_open_and_says_so(self):
        """An approval freezes the SAVE, not the render — a panel with an
        approved take is exactly where you iterate. Blocking the experiment
        too would be a gate nobody asked for."""
        b = preview_block()
        self.assertIn("You can still test:", b)
        self.assertIn('data-f="generate-edited"', b)
        i = b.index('data-f="generate-edited"')
        self.assertNotIn("r.frozen", b[i:i + 200],
                         "Generate is never disabled by the freeze")

    def test_frozen_is_settled_green_not_amber(self):
        """Amber is the live signal — the text a render is about to use.
        Canon already paints a settled step with --ok (.step-confirmed);
        spending the accent on a refusal would dilute it."""
        b = preview_block()
        self.assertIn('editState.classList.toggle("settled", !!r.frozen)', b)
        self.assertIn('.report [data-f="edit-state"].settled { color: var(--ok); }', CSS)

    def test_a_missing_compiled_field_cannot_kill_the_editor(self):
        """`(saved || r.compiled).trim()` threw on a server that answered
        without `compiled`, and the throw took Save, Clear and Revert with
        it while the editor still looked usable."""
        self.assertIn('const base = (saved || r.compiled || r.prompt || "").trim();',
                      preview_block())


class TheOverrideIsReadableAsState(unittest.TestCase):
    def test_the_step_head_says_the_panel_is_off_the_compile(self):
        self.assertIn("SAVED PROMPT — STEPS 01–04 DO NOT WRITE THIS PANEL", JS)

    def test_the_generate_step_says_it_too(self):
        """Step 05's head sits above step 06 but a user who edits the camera
        and hits Generate never has to read it. The warning belongs where
        the spend happens as well."""
        self.assertIn("THIS TAKE RENDERS FROM THE SAVED PROMPT", JS)

    def test_the_state_line_distinguishes_saved_from_unsaved(self):
        b = preview_block()
        for s in ("SAVED PROMPT · EVERY TAKE OF THIS PANEL RENDERS FROM THIS",
                  "UNSAVED CHANGES OVER THE SAVED PROMPT · SAVE OR THEY RIDE ONE TAKE",
                  "EDITED · UNSAVED · THIS TAKE ONLY",
                  "UNEDITED · STEPS 01–04 COMPILE THIS"):
            self.assertIn(s, b, s)

    def test_the_alert_is_amber(self):
        self.assertIn(".step-meta-alert { color: var(--accent); }", CSS)

    def test_saving_moves_the_cards_state_without_closing_the_editor(self):
        """The card's step head is the standing warning, so it has to move
        with the save. Redrawing the card would do that — and would close
        the editor you just saved from, which is its own small betrayal.
        The two surfaces are patched in place instead."""
        b = preview_block()
        self.assertNotIn("renderBoardPanels(specId);", b,
                         "a full redraw closes the report host")
        self.assertIn('$("[data-step=prompt] .step-meta", card)', b)
        self.assertIn("genStep.insertAdjacentHTML", b)
        self.assertIn("note.remove()", b)

    def test_the_cards_own_copy_moves_too(self):
        """A later redraw for some unrelated reason must not resurrect the
        pre-save head."""
        self.assertIn("p.prompt_override = text;", preview_block())


class TheStoreHoldsIt(unittest.TestCase):
    def setUp(self):
        import tempfile
        from app import paths
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        for n in ("SPECS_DIR", "DATA", "PROJECT_STATE_DIR"):
            pass
        self._old = {k: getattr(paths, k) for k in ("SPECS_DIR", "SPEC_LOCKS", "APPROVAL_LOG")}
        (home / "specs").mkdir(parents=True)
        (home / "state").mkdir(parents=True)
        paths.SPECS_DIR = home / "specs"
        paths.SPEC_LOCKS = home / "specs" / "locks.json"
        paths.APPROVAL_LOG = home / "state" / "approval_log.md"
        self.spec = {
            "specification_id": "TEST_V001", "subject": "t", "mode": "CANON_EXTRACTION",
            "board_type": "SCENE", "panels": [
                {"id": "P01", "title": "t", "purpose": "p", "required_objects": ["x"]}],
            "evidence_ledger": [],
        }
        (paths.SPECS_DIR / "TEST_V001.json").write_text(
            json.dumps(self.spec), encoding="utf-8")

    def tearDown(self):
        from app import paths
        for k, v in self._old.items():
            setattr(paths, k, v)
        self.tmp.cleanup()

    def test_a_long_prompt_saves_and_clears(self):
        from app import store
        body = "X" * 400
        r = store.amend_panel_prompt("TEST_V001", "P01", body)
        self.assertTrue(r["saved"])
        self.assertEqual(store.panel_prompt_override("TEST_V001", "P01"), body)
        r2 = store.amend_panel_prompt("TEST_V001", "P01", "")
        self.assertFalse(r2["saved"])
        self.assertTrue(r2["was_saved"])
        self.assertEqual(store.panel_prompt_override("TEST_V001", "P01"), "")

    def test_a_prompt_too_short_to_be_one_is_refused(self):
        """A saved prompt REPLACES the compile — canon rules, camera,
        reference scopes and all. A stray one-line paste would silently
        strip the panel of everything that governs it."""
        from app import store
        with self.assertRaises(ValueError) as cm:
            store.amend_panel_prompt("TEST_V001", "P01", "make it cooler")
        self.assertIn("too short", str(cm.exception))

    def test_saving_is_journaled(self):
        from app import store, paths
        store.amend_panel_prompt("TEST_V001", "P01", "Y" * 400)
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("prompt SAVED by hand", log)
        self.assertIn("steps 01–04 no longer compile", log)


class TheRenderUsesIt(unittest.TestCase):
    def test_a_saved_prompt_rides_every_take(self):
        self.assertIn(
            'override = asked or str(panel.get("prompt_override", "")).strip()',
            GEN)

    def test_but_it_does_not_freeze_the_art_direction(self):
        """User-hit 2026-08-22. The editor opens on the COMPILED prompt,
        so saving after any edit froze the VISUAL STYLE block too and the
        panel could never see a Bible change. The panel's own words stay;
        the production's art direction is re-applied at render time."""
        i = GEN.index('asked = (render_prompt or "").strip()')
        self.assertIn("refresh_art_direction(override, spec, panel)",
                      GEN[i:i + 700])

    def test_a_per_call_override_still_wins(self):
        """The one-take test path has to be able to try something OTHER
        than what is saved, or a saved prompt could never be experimented
        against."""
        i = GEN.index('asked = (render_prompt or "").strip()')
        self.assertIn("render_prompt or", GEN[i:i + 120])
        self.assertLess(GEN[i:i + 200].index("render_prompt"),
                        GEN[i:i + 200].index("prompt_override"))

    def test_the_take_records_which_kind_of_override_it_was(self):
        self.assertIn('record["prompt_override_scope"]', GEN)
        self.assertIn('"panel" if override ==', GEN)


if __name__ == "__main__":
    unittest.main()
