"""The Art Direction Bible panel: one button, at the top, four verbs.

User, 2026-08-22:

    "I should not have to detail out how creating, editing, and saving
    should work. Make it all one button." — and then: "It should be at the
    top of the Art Direction Bible section. Have a regenerate button only
    once created."

The panel had a gold DRAFT that wrote into an editor and stopped, and a
grey SAVE underneath that was the only thing which actually opened
Breakdowns — so the step's one primary action produced a result that
changed nothing, and deciding how those decomposed was left to the user.

Now the primary control is a single button whose verb is always the next
true thing, and Regenerate joins it only once a bible exists.

    no bible, editor empty   Create Art Direction Bible
    no bible, text pasted    Save Art Direction Bible
    saved                    Edit          + Regenerate
    editing                  Save          (Regenerate hidden)
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")


def panel() -> str:
    i = HTML.index('<div class="panel step" data-step="4">')
    return HTML[i:HTML.index('<div class="panel step" data-step="5">', i)]


class ThereIsOneButton(unittest.TestCase):

    def test_the_act_row_carries_one_primary_and_one_regenerate(self):
        """The 2026-08-04 ruling ("it should all work — make it all one
        button") collapsed Create / Edit / Save into one verb that states
        the next true thing. Its subject is the DOCUMENT'S VERB, and the
        row that carries it.

        Scoped to that row from 2026-08-25, when R2 added a read-the-bible
        -against-itself act. That act belongs to the document, not to the
        stage, so it sits under the editor beside the report it produces —
        which is the distinction the ruling was making, not a count of
        buttons in a panel."""
        p = panel()
        row = p[p.index('<div class="row" style="margin-top:0">'):p.index("</div>")]
        buttons = re.findall(r"<button[^>]*id=\"([^\"]+)\"", row)
        self.assertEqual(buttons, ["wiz-draft", "bible-regen"])

    def test_the_self_check_sits_under_the_document_it_reads(self):
        p = panel()
        self.assertLess(p.index('id="style-bible"'), p.index('id="bible-check"'))
        self.assertLess(p.index('id="bible-check"'), p.index('id="bible-conflicts"'))

    def test_both_sit_at_the_top_above_the_editor(self):
        p = panel()
        self.assertLess(p.index('id="wiz-draft"'), p.index('id="style-bible"'))
        self.assertLess(p.index('id="bible-regen"'), p.index('id="style-bible"'))

    def test_the_old_second_button_is_gone(self):
        for gone in ('id="style-save"', "style-save-gate",
                     "NOTHING TO EDIT UNTIL A BIBLE EXISTS"):
            self.assertNotIn(gone, HTML, f"{gone} outlived the one-button pass")

    def test_the_verb_is_a_function_of_state(self):
        i = JS.index("const VERB = {")
        seg = JS[i:i + 400]
        for state, verb in (("empty", "Build Art Direction Bible"),
                            ("unsaved", "Save Art Direction Bible"),
                            ("saved", "Edit"),
                            ("editing", "Save Art Direction Bible")):
            self.assertIn(f'{state}: "{verb}"', seg)

    def test_the_one_button_dispatches_rather_than_asking(self):
        i = JS.index('$("#wiz-draft").onclick')
        seg = JS[i:i + 900]
        self.assertIn("const st = bibleState();", seg)
        self.assertIn('if (st === "saved")', seg)      # Edit
        self.assertIn('st === "editing" || st === "unsaved"', seg)  # Save
        self.assertIn("return writeBible();", seg)      # Create


class RegenerateAppearsOnlyOnceCreated(unittest.TestCase):

    def test_it_ships_hidden(self):
        self.assertIn('id="bible-regen" class="ghost hidden"', HTML)

    def test_it_shows_only_in_the_saved_state(self):
        i = JS.index("const syncBibleSave =")
        self.assertIn('regen.classList.toggle("hidden", st !== "saved");',
                      JS[i:i + 1800])

    def test_it_confirms_and_says_the_text_cannot_be_recovered(self):
        """bible.save_text() overwrites and revisions.py is for specs — a
        replaced bible is genuinely gone, so the confirm may not imply
        otherwise."""
        i = JS.index('$("#bible-regen").onclick')
        seg = JS[i:i + 900]
        self.assertIn("askConfirm", seg)
        self.assertIn("CANNOT BE RECOVERED", seg)
        self.assertIn("Approved work already made under it is untouched", seg)

    def test_creating_and_regenerating_are_one_act(self):
        """Both write from the anchors and save. Two copies would drift on
        what a written bible is."""
        self.assertIn("return writeBible({ replacing: true });", JS)
        self.assertEqual(JS.count("const writeBible = async"), 1)


class TheEditorIsADocumentNotAScratchPad(unittest.TestCase):

    def sync(self):
        i = JS.index("const syncBibleSave =")
        return JS[i:i + 1800]

    def test_a_saved_bible_is_read_only(self):
        s = self.sync()
        self.assertIn('editor.readOnly = st === "saved";', s)
        self.assertIn("#style-bible.is-locked", CSS)

    def test_an_unsaved_one_is_yours_to_paste_into(self):
        """Editable while nothing is saved, so pasting your own bible is
        still possible — the button becomes Save when you do."""
        self.assertIn('if (!bibleSavedText) return text ? "unsaved" : "empty";',
                      JS)

    def test_pressing_edit_hands_over_the_caret(self):
        i = JS.index('$("#wiz-draft").onclick')
        seg = JS[i:i + 900]
        self.assertIn("bibleEditing = true", seg)
        self.assertIn("editor.focus()", seg)
        self.assertIn("setSelectionRange", seg)

    def test_escape_discards_so_edit_is_never_a_trap(self):
        i = JS.index('$("#style-bible").addEventListener("keydown"')
        seg = JS[i:i + 400]
        self.assertIn('e.key !== "Escape"', seg)
        self.assertIn("value = bibleSavedText", seg)
        self.assertIn("bibleEditing = false", seg)

    def test_saving_nothing_is_not_a_save(self):
        """No revision bump, no journal line, no toast claiming something
        happened. Verified live: rev 5 stayed rev 5."""
        self.assertIn("quietIfUnchanged: true", JS)
        i = JS.index("const saveBible = async")
        self.assertIn("if (quietIfUnchanged && text === bibleSavedText) return true;",
                      JS[i:i + 900])


class ThereIsOneWriter(unittest.TestCase):

    def test_only_saveBible_puts_the_bible(self):
        self.assertEqual(
            len(re.findall(r'api\("/api/style-bible", \{ method: "PUT"', JS)), 1)

    def test_it_reopens_the_band_and_the_swatch_gate(self):
        i = JS.index("const saveBible = async")
        seg = JS[i:i + 1400]
        self.assertIn("updateBand()", seg)
        self.assertIn("syncSwatchGen()", seg)

    def test_it_records_what_is_on_disk(self):
        """Every state question — is there a bible, has anything changed —
        is answered against this, so it must be set wherever the file
        changes: on load and on save."""
        i = JS.index("const saveBible = async")
        self.assertIn("bibleSavedText = text;", JS[i:i + 1400])
        j = JS.index("const loadBibleEditor = async")
        self.assertIn("bibleSavedText =", JS[j:j + 600])

    def test_the_fact_is_stated_once_on_the_row(self):
        """The heading, the condition line and the status line all said
        "every future prompt uses this"."""
        i = JS.index("const syncBibleSave =")
        self.assertIn('saved: "",', JS[i:i + 1800])
        self.assertNotIn("saved — every future prompt uses this", JS)


class TheActIsWatched(unittest.TestCase):
    """User, 2026-08-22: "generating the art direction bible and swatches
    should happen in a single step ... same razzle-dazzle feedback during
    generation as the screenplay read."

    Two passes became one, and the surface reuses the read panel's own
    `.rd-*` vocabulary rather than inventing a second one. Same honesty
    rule: the two phases that are single opaque model calls say so, and
    the two around them are real local work carrying the feedback.
    """

    def body(self):
        i = JS.index("const theBible = {")
        return JS[i:JS.index("\n};", i)]

    def test_one_press_writes_saves_and_colours(self):
        i = JS.index("const writeBible = async")
        seg = JS[i:i + 4600]
        self.assertIn("theBible.begin(", seg)
        self.assertIn("await saveBible()", seg)
        self.assertIn('api("/api/wizard/swatches"', seg)
        self.assertIn("theBible.coloured(", seg)

    def test_the_colour_pass_cannot_lose_a_saved_bible(self):
        """Colour runs after the save, and its failure says the bible
        survived — otherwise a swatch error reads as having lost the
        thing that took two minutes to write."""
        i = JS.index("const writeBible = async")
        seg = JS[i:i + 4600]
        self.assertIn("the bible is saved, but colour failed", seg)
        self.assertLess(seg.index("await saveBible()"),
                        seg.index('api("/api/wizard/swatches"'))

    def test_the_spinner_says_what_is_happening_and_stops(self):
        """The label carried "One call — it reports nothing until it is
        done" until the user cut it (2026-08-22). The spinner and the
        phase strip already say the same thing without a sentence, and
        the read panel keeps the fuller statement where it is the only
        thing on screen."""
        b = self.body()
        self.assertIn("Writing the Art Direction Bible from the anchors", b)
        self.assertNotIn("it reports nothing", b)

    def test_the_local_phases_carry_real_work(self):
        """The ladder is the production's actual design languages and the
        page is the director's actual answers — nothing invented."""
        b = self.body()
        self.assertIn("ASSEMBLED HERE — NOTHING SENT ANYWHERE YET", b)
        self.assertIn("THE DIRECTOR'S ANSWERS", b)
        self.assertIn("SECTIONS WRITTEN", b)

    def test_it_reuses_the_read_panel_rather_than_a_second_one(self):
        b = self.body()
        for cls in ("rd-head", "rd-phase", "rd-ladder", "rd-page", "rd-ticker"):
            self.assertIn(cls, b, f"{cls} — one pattern, two operations")

    def test_a_language_with_no_colour_of_its_own_is_named(self):
        """The diagnosis surfaced where it happens, not only afterwards."""
        b = self.body()
        self.assertIn("NO COLOUR OF ITS OWN", b)
        self.assertIn("OWNS ITS COLOUR", b)

    def test_the_timers_stop_however_it_ends(self):
        b = self.body()
        for fn in ("coloured(res)", "fail(msg)"):
            i = b.index(fn)
            self.assertIn("stopTimers()", b[i:i + 300], fn)


if __name__ == "__main__":
    unittest.main()
