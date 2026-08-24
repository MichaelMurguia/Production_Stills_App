"""Stop 4: the app fills it in, and says so.

The "I didn't know what to do" half of the first user test — none of it a
bug, all of it a user standing in front of a field the app could have
answered itself.

Two of these were already built and invisible, which is the finding: a
control nobody can find is indistinguishable from a control that does not
exist, and the remedy is not more machinery.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def fn(name: str) -> str:
    """A whole function, bounded by the next top-level one. Fixed windows
    have stopped covering their subject four times in two days as these
    functions grew."""
    i = JS.index(f"function {name}")
    j = JS.index(chr(10) + "function ", i + 10)
    return JS[i:j]


class TheLocationsAreOffered(unittest.TestCase):
    """S2.2 — "if this is going to be a drop down like give me all my
    locations because you have the screenplay."

    It WAS a list: a `datalist`, which shows nothing until you type into
    it. So a user whose screenplay the app had just read saw an empty box
    with no sign that his own locations were behind it. A datalist is a
    convenience for a field you already know how to fill; this is a field
    whose entire value is that the app knows the answers."""

    def test_it_is_a_real_picker(self):
        self.assertIn('<select id="wiz-sample-pick">', HTML)

    def test_the_datalist_is_gone(self):
        self.assertNotIn('list="wiz-sample-locs"', HTML)
        self.assertNotIn('<datalist id="wiz-sample-locs">', HTML)

    def test_free_text_survives(self):
        """A location the scan missed must still be reachable — the picker
        is the default, not a cage."""
        self.assertIn("Somewhere else — type it…", JS)
        self.assertIn('locPick.value === OTHER', JS)

    def test_an_unscanned_production_says_what_to_do(self):
        self.assertIn("run the Step 2 Scene Scan to list your locations", JS)

    def test_a_typed_location_is_remembered_as_typed(self):
        """Reopening on a free-text choice must restore the text, not
        silently snap back to the first scanned location."""
        i = JS.index("if (saved && sampleLocs.includes(saved))")
        seg = JS[i:i + 400]
        self.assertIn("locPick.value = OTHER; locInput.value = saved", seg)


class TheModelTestSaysWhatItIs(unittest.TestCase):
    """S2.5 — agreed on the call: "I would make that super clear like test
    your model"."""

    def test_the_heading_is_the_agreed_words(self):
        self.assertIn("<h2>Test your model", HTML)

    def test_the_old_label_is_gone(self):
        self.assertNotIn("<h2>Model Test:", HTML)


class TheSpecIdNamesItself(unittest.TestCase):
    """S2.3 — "I don't have the vocabulary to understand what this should
    actually be."

    It already filled itself from a picked scene and from a pasted
    section's location. What it SAID was `A NAME ONLY` beside a placeholder
    that looked like an example to copy — so on the call it was dictated by
    hand, one word at a time, by the person who wrote the auto-fill."""

    def test_the_field_says_it_fills_itself(self):
        self.assertIn("NAMED FROM YOUR SCENE", HTML)
        self.assertIn("fills itself when you pick or paste a scene", HTML)

    def test_it_no_longer_reads_as_a_blank_to_invent(self):
        i = HTML.index('id="spec-auto-id"')
        seg = HTML[i - 400:i + 200]
        self.assertNotIn("A NAME ONLY", seg)
        self.assertNotIn("GENETICS_FACTION_V001", seg)

    def test_the_manual_door_keeps_its_example(self):
        """The OTHER Spec ID field is the hand-built door, where there is
        no scene to name the board after and the user genuinely is
        inventing one. An example belongs there."""
        i = HTML.index('id="spec-new-id"')
        seg = HTML[i - 400:i + 200]
        self.assertIn("GENETICS_FACTION_V001", seg)
        self.assertIn("A NAME ONLY", seg)

    def test_the_autofill_still_exists_and_still_yields(self):
        """Filling itself must never overwrite what the user typed."""
        self.assertIn("if (idEl && !idEl.value.trim())", JS)
        self.assertIn("if (id && !id.value.trim())", JS)


class TheCinematographyAxisIsFindable(unittest.TestCase):
    """User, 2026-08-24: "I want to be able to change the cinematography
    style when rendering the panel. How? If thats not possible now, add the
    feature."

    It was possible, and had been since 2026-08-22 — added at the same
    user's request, in the panel's camera editor, with the same three
    states as every camera axis. It was labelled `Grammar`, which is not a
    word anyone reaches for. The control was there; the name was not."""

    def test_the_field_answers_to_the_name_people_use(self):
        self.assertIn("<span>Cinematography</span>", fn("grammarSelect"))

    def test_the_three_states_are_intact(self):
        seg = fn("grammarSelect")
        self.assertIn('<option value="">', seg)          # inherit
        self.assertIn('value="NONE"', seg)               # refuse
        self.assertIn("CINEMA_STYLES", seg)              # name one

    def test_the_render_workbench_draws_it(self):
        """The one surface the request was about. `cameraRow` only draws
        the axis when it has a blank option, so this asserts the call the
        panel makes, not merely that the function exists."""
        i = JS.index('cameraRow("cam", p, "— production default —", false)')
        self.assertGreater(i, 0)
        self.assertIn("blank ? grammarSelect(prefix, obj?.cinematography", JS)

    def test_a_surface_without_the_control_cannot_clear_the_choice(self):
        """Pre-existing guard, pinned because relabelling touched this
        code: an editor that never drew the axis must not send a blank and
        silently delete a panel's grammar."""
        self.assertIn('if ($(`[data-f=${prefix}-grammar]`, root)) '
                      'out.cinematography = val("grammar");', JS)


class AFrozenStepSaysWhyOnScreen(unittest.TestCase):
    """User-caught 2026-08-24: "it says I cant change camera. I rendered a
    take and on that panel, I get the 'no' icon when i hover over change
    camera."

    The panel had an approved take, which settles what the panel ASKS FOR —
    correct behaviour. But the step showed a green "✓ SETTLED" chip, which
    reads as good and complete, beside a disabled verb whose only
    explanation was a hover title. Third instance of the same defect in one
    week (Repair Region, the board lock, this), so the fix is in seqStep and
    covers every frozen step rather than the camera alone."""

    def test_the_reason_renders_not_only_on_hover(self):
        i = JS.index("function seqStep")
        seg = JS[i:JS.index("function modal(", i)]
        self.assertIn('class="step-frozen mono"', seg)
        self.assertIn("frozenWhy", seg)

    def test_it_names_the_take_that_froze_it(self):
        self.assertIn("FROZEN BY ${approvedTakes.join", JS)

    def test_it_names_the_door_out(self):
        """Knowing you are blocked is half an answer."""
        self.assertIn("USE WITHDRAW APPROVAL ON THAT", JS)

    def test_it_says_what_is_still_allowed(self):
        """An approval freezes the SHEET, not the experiment — the same
        rule the prompt editor already states. A user who reads only
        "frozen" reasonably concludes the panel is finished with them."""
        self.assertIn("GENERATING A NEW TAKE IS", JS)

    def test_a_settled_step_is_not_painted_as_an_error(self):
        css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
        i = css.index(".step-frozen")
        self.assertNotIn("--bad", css[i:i + 200])


if __name__ == "__main__":
    unittest.main()
