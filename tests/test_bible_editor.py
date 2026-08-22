"""The Art Direction Bible panel: one gold verb, one reactive grey one.

User, 2026-08-22:

    "The big gold button should say Create Art Direction Bible. It should
    also save it so it unlocks breakdown tab. The bottom grey button that
    says Save Art Direction Bible should be reactive. It should say Edit,
    then it unlocks the bible for edit and will change to Save."

Before this, the gold button DRAFTED into an editor and stopped. Nothing
downstream opened until you found a second, differently-worded grey button
underneath — so the one primary action on the step produced a result that
changed nothing, and the gate it was supposed to clear stayed shut.

The bible is a saved document, not a scratch pad. Create writes it and
saves it; the editor below then holds a saved thing, and a saved thing is
read-only until you say otherwise.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")


class TheGoldButtonFinishesTheJob(unittest.TestCase):

    def test_it_says_create(self):
        self.assertIn('id="wiz-draft" class="primary">Create Art Direction Bible',
                      HTML)
        self.assertNotIn("Draft Art Direction Bible</button>", HTML)

    def test_it_saves_what_it_creates(self):
        i = JS.index('$("#wiz-draft").onclick')
        seg = JS[i:i + 4200]
        self.assertIn("await saveBible()", seg,
                      "creating must save, or the step's one primary action "
                      "leaves the gate shut")

    def test_it_says_breakdowns_are_open(self):
        i = JS.index('$("#wiz-draft").onclick')
        seg = JS[i:i + 4200]
        self.assertIn("BREAKDOWNS ARE OPEN", seg)

    def test_the_step_condition_promises_what_now_happens(self):
        """It said the draft appears below for review. It now writes,
        saves and opens Breakdowns, and the line says so."""
        self.assertIn("WRITTEN, SAVED, AND BREAKDOWNS OPEN", HTML)
        self.assertNotIn("THE DRAFT APPEARS BELOW FOR REVIEW", HTML)

    def test_replacing_existing_text_no_longer_claims_nothing_is_saved(self):
        """That confirm said "Nothing is saved until you press Save",
        which stopped being true the moment Create began saving."""
        self.assertNotIn("Nothing is saved until you press Save", JS)


class TheGreyButtonIsTheMode(unittest.TestCase):

    def sync(self):
        i = JS.index("const syncBibleSave =")
        return JS[i:i + 1400]

    def test_it_starts_as_edit(self):
        self.assertIn('id="style-save" disabled>Edit</button>', HTML)

    def test_it_becomes_save_while_editing(self):
        self.assertIn('btn.textContent = bibleEditing ? "Save Art Direction Bible" : "Edit";',
                      self.sync())

    def test_the_editor_is_read_only_until_edit_is_pressed(self):
        s = self.sync()
        self.assertIn("editor.readOnly = !bibleEditing;", s)
        self.assertIn('editor.classList.toggle("is-locked", !bibleEditing && !empty)', s)
        self.assertIn("#style-bible.is-locked", CSS)

    def test_pressing_edit_hands_over_the_caret(self):
        i = JS.index('$("#style-save").onclick')
        seg = JS[i:i + 900]
        self.assertIn("bibleEditing = true", seg)
        self.assertIn("editor.focus()", seg)
        self.assertIn("setSelectionRange", seg)

    def test_saving_locks_it_again(self):
        i = JS.index('$("#style-save").onclick')
        seg = JS[i:i + 900]
        self.assertIn("bibleEditing = false", seg)

    def test_the_gate_tag_matches_the_verb(self):
        """It said NOTHING TO SAVE UNTIL A DRAFT EXISTS beside a button
        that now reads Edit."""
        self.assertIn("NOTHING TO EDIT UNTIL A BIBLE EXISTS", HTML)
        self.assertNotIn("NOTHING TO SAVE UNTIL A DRAFT EXISTS", HTML)


class ThereIsOneWriter(unittest.TestCase):
    """Create and Save both persist the bible. Two copies of that would
    drift on what "saved" means — the band, the swatch gate and the status
    line all hang off it."""

    def test_only_saveBible_puts_the_bible(self):
        puts = re.findall(r'api\("/api/style-bible", \{ method: "PUT"', JS)
        self.assertEqual(len(puts), 1, "one writer, not two")

    def test_it_reopens_the_band_and_the_swatch_gate(self):
        i = JS.index("const saveBible = async ()")
        seg = JS[i:i + 1200]
        self.assertIn("updateBand()", seg)
        self.assertIn("syncSwatchGen()", seg)

    def test_exactly_two_callers_use_it(self):
        """Create and Save, and nothing else. Both sit above the
        declaration in the file and reach it at click time, which is the
        same pattern syncBibleSave already uses in this function — proven
        live, not assumed: the grey Save button was exercised in a browser
        and wrote REV 2."""
        self.assertIn("const saveBible = async ()", JS)
        self.assertEqual(JS.count("saveBible()"), 2,
                         "exactly two callers: Create and Save")


if __name__ == "__main__":
    unittest.main()
