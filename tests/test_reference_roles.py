"""Every role the picker offers must carry real jurisdiction text.

Regression, 2026-08-06: a P-38 cockpit photo was attached to a panel and
rendered with invented instrumentation. The images WERE sent — the prompt
line for them read, in full, "controls its assigned role." SCENE_REFERENCE
is the role picker's first option and had no entry in the prompt builder's
jurisdiction table, so the model was handed a photograph and told nothing
about it. These tests hold the two lists together.
"""
import re
import unittest
from pathlib import Path

from app.generate import _reference_role_lines

APP_JS = Path(__file__).resolve().parents[1] / "app" / "static" / "app.js"

# BOARD_LAYOUT_STYLE is assembly grammar — it gates board assembly and never
# enters a panel render, so it needs no render-time jurisdiction.
NOT_IN_RENDERS = {"BOARD_LAYOUT_STYLE"}

EMPTY = "controls its assigned role"


def picker_roles() -> list[str]:
    """The heads ROLE_FAMILIES offers in the UI — parsed from the source so
    adding a role to the picker without jurisdiction text fails here."""
    src = APP_JS.read_text(encoding="utf-8")
    block = src.split("const ROLE_FAMILIES = [", 1)[1].split("\n];", 1)[0]
    return re.findall(r'head:\s*"([A-Z_]+)"', block)


def line_for(role: str, **extra) -> str:
    return "\n".join(_reference_role_lines([{"id": "REF-001", "role": role, **extra}]))


class RoleJurisdiction(unittest.TestCase):
    def test_picker_offers_roles(self):
        roles = picker_roles()
        self.assertIn("SCENE_REFERENCE", roles)
        self.assertGreaterEqual(len(roles), 10)

    def test_every_offered_role_has_jurisdiction(self):
        for role in picker_roles():
            if role in NOT_IN_RENDERS:
                continue
            with self.subTest(role=role):
                text = line_for(role)
                self.assertNotIn(EMPTY, text)
                self.assertIn("It does NOT control:", text)

    def test_scene_reference_binds_composition(self):
        text = line_for("SCENE_REFERENCE").lower()
        self.assertIn("composition", text)
        self.assertIn("match the image closely", text)

    def test_vehicle_geometry_covers_interiors(self):
        """The cockpit case: an interior render must be told the instrument
        layout is binding, not that the reference has no say in the angle."""
        text = line_for("VEHICLE_GEOMETRY").lower()
        self.assertIn("interior", text)
        self.assertIn("gauge", text)
        self.assertIn("binding", text)

    def test_free_form_role_still_instructs(self):
        """Roles are free-form by design; an unknown one must still say
        something the model can act on."""
        text = line_for("P-38 COCKPIT")
        self.assertNotIn(EMPTY, text)
        self.assertIn("Match them closely", text)
        self.assertIn("It does NOT control:", text)

    def test_no_role_anywhere_renders_the_empty_instruction(self):
        for role in picker_roles() + ["", "SOMETHING_INVENTED", "scene_reference"]:
            with self.subTest(role=role):
                self.assertNotIn(EMPTY, line_for(role))

    def test_per_reference_text_still_overrides_the_default(self):
        text = line_for("VEHICLE_GEOMETRY", controls=["the exact gauge layout"],
                        does_not_control=["weather"])
        self.assertIn("controls the exact gauge layout.", text)
        self.assertIn("It does NOT control: weather.", text)
        self.assertNotIn("intakes", text)


if __name__ == "__main__":
    unittest.main()
