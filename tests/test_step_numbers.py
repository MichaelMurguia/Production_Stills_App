"""Copy that names a wizard step names the right one.

Reported 2026-08-22: a gate line read "Draft it in step 5", and step 5 is
the Model Test. The Bible is step 4.

The cause was a renumbering. On 2026-08-16 the separate look interview was
dissolved into the anchor cards — "the anchor cards ARE that statement
now" — which removed a step and shifted every later one down by one. The
panels were renumbered. The prose that pointed at them was not, so every
reference past the removed step has been one too high ever since:

    Color Palette column   said step 2   actually step 1 (Anchors)
    Cast the film          said step 4   actually step 3
    Art Direction Bible    said step 5   actually step 4

Nothing failed. Every one of those sentences reads perfectly and sends the
user to the wrong panel — the exact failure mode a test suite exists to
catch and this one could not, because no test knew where a step was.

So the truth is DERIVED here, from the markup, rather than restated. The
rail's own labels and the panels' own `data-step` attributes are the
authority; copy is checked against them. Renumber again and this file
fails until the prose is brought along.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
WIZ = (ROOT / "app" / "wizard.py").read_text(encoding="utf-8")

# id -> the data-step panel that contains it, read off the markup.
_STEP_OPEN = re.compile(r'<div class="panel step" data-step="(\d+)"')


def step_of(needle: str) -> int:
    """Which numbered step panel contains this markup."""
    i = HTML.index(needle)
    opens = [(m.start(), int(m.group(1))) for m in _STEP_OPEN.finditer(HTML)
             if m.start() < i]
    assert opens, f"{needle!r} is not inside a numbered step"
    return opens[-1][1]


def rail() -> dict[str, int]:
    """The rail's own labels, which are what the user reads on screen."""
    m = re.search(r"const RAIL = \[(.*?)\];", JS, re.S)
    assert m, "the six-step rail must be declared as RAIL"
    return {label.lower(): int(n)
            for n, label in re.findall(r'\[(\d+), "([^"]+)"\]', m.group(1))}


class TheRailAgreesWithThePanels(unittest.TestCase):
    """Two independent statements of the same numbering."""

    def test_the_bible_panel_is_the_rail_s_bible_chip(self):
        self.assertEqual(step_of('id="wiz-draft"'), rail()["bible"])

    def test_the_design_plan_panel_is_the_rails_design_plan_chip(self):
        """Renamed 2026-08-28. "Script scene scan" named a mechanism and
        collided with stage 01, which also calls itself a read."""
        self.assertEqual(step_of("<h2>Build Design Plan"), rail()["design plan"])

    def test_the_model_test_is_last(self):
        self.assertEqual(rail()["test"], max(rail().values()))


class CopyPointsAtTheRightStep(unittest.TestCase):

    def bible(self):
        return step_of('id="wiz-draft"')

    def palette(self):
        return step_of('<div class="wiz-col" data-role="COLOR_PALETTE">')

    def test_the_palette_origin_line_points_at_the_bible(self):
        i = JS.index("const paletteOrigin")
        seg = JS[i:i + 2000]
        for m in re.finditer(r"[Ss]tep (\d+)", seg):
            self.assertEqual(int(m.group(1)), self.bible(),
                             f"palette origin says step {m.group(1)}, "
                             f"the Bible is step {self.bible()}")

    def test_the_empty_bible_toast_points_somewhere_real(self):
        """It names the control rather than a step now — the button is on
        the same panel, and "above" cannot go stale the way a number can.
        If it ever names a step again, that step must be the Bible's."""
        m = re.search(r"The bible is empty — ([^\"]+)", JS)
        self.assertTrue(m, "the empty-bible message must say where to go")
        said = m.group(1)
        step = re.search(r"step (\d+)", said)
        if step:
            self.assertEqual(int(step.group(1)), self.bible())
        else:
            self.assertIn("above", said)

    def test_the_server_refusal_points_at_the_bible(self):
        m = re.search(r"Draft and save the Bible first \(step (\d+)\)", WIZ)
        self.assertTrue(m, "the refusal must name where to go")
        self.assertEqual(int(m.group(1)), self.bible())

    def test_the_swatch_result_names_the_palette_s_own_step(self):
        """The act and its result were two steps apart until 2026-08-29 —
        generation reads the saved Bible in step 4 and the swatches landed
        in step 1. Colour moved to the Bible, so they are one step now and
        the line says "beside this" rather than pointing away."""
        m = re.search(r"LANDS IN STEP (\d+) / COLOUR", JS)
        self.assertTrue(m, "the swatch result must still name where it lands")
        self.assertEqual(int(m.group(1)), self.palette())

    def test_the_cast_pointer_names_the_cast_step(self):
        cast = rail()["cast"]
        for text, where in ((JS, "app.js"), (HTML, "index.html")):
            for m in re.finditer(r"cast (?:the film )?in Production Design "
                                 r"step (\d+)", text):
                self.assertEqual(int(m.group(1)), cast, where)

    def test_the_design_plan_pointers_name_the_design_plan_step(self):
        """Copy elsewhere that sends the user to this step must name the
        step it is actually at. Renamed 2026-08-28 with the step."""
        n = rail()["design plan"]
        for m in re.finditer(r"[Ss]tep (\d+) built the design plan", HTML):
            self.assertEqual(int(m.group(1)), n)
        for m in re.finditer(r"design plan in Step (\d+)", JS):
            self.assertEqual(int(m.group(1)), n)


if __name__ == "__main__":
    unittest.main()
