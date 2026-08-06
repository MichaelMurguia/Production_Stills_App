"""Reference role jurisdiction — what each role tells the model it controls.

These lock a user ruling (2026-08-06) made after a first attempt got it
wrong. The tempting "fix" — give every role a jurisdiction so none renders
the bare "controls its assigned role" line — is WRONG and must not be
re-applied:

  * SCENE_REFERENCE is for the scene. It does NOT control composition,
    camera or content, and deliberately has no entry in the jurisdiction
    table. The generic line is the correct output for it.
  * VEHICLE_GEOMETRY covers interior and exterior alike, but it is a
    geometry reference — what the vehicle looks like. Nothing about it
    binds layout.
"""
import unittest

from app.generate import _reference_role_lines

GENERIC = "controls its assigned role."


def line_for(role: str, **extra) -> str:
    return "\n".join(_reference_role_lines([{"id": "REF-001", "role": role, **extra}]))


class RoleJurisdiction(unittest.TestCase):
    def test_scene_reference_has_no_jurisdiction(self):
        """Ruled: a scene reference does not control composition or camera."""
        text = line_for("SCENE_REFERENCE")
        self.assertTrue(text.endswith(GENERIC), text)
        self.assertNotIn("It does NOT control:", text)
        for word in ("composition", "camera", "match"):
            self.assertNotIn(word, text.lower())

    def test_free_form_role_falls_through_to_the_generic_line(self):
        text = line_for("P-38 COCKPIT")
        self.assertTrue(text.endswith(GENERIC), text)

    def test_vehicle_geometry_covers_interiors(self):
        text = line_for("VEHICLE_GEOMETRY").lower()
        self.assertIn("inside and out", text)
        self.assertIn("interior", text)
        self.assertIn("instruments", text)

    def test_vehicle_geometry_binds_nothing_about_layout(self):
        text = line_for("VEHICLE_GEOMETRY").lower()
        self.assertNotIn("binding", text)
        self.assertNotIn("layout", text)
        self.assertIn("it does not control: the vehicle's placement, "
                      "viewing angle, lighting, or the scene.", text)

    def test_location_geometry_is_the_role_that_carries_layout(self):
        """The distinction the vehicle role must not blur."""
        text = line_for("LOCATION_GEOMETRY").lower()
        self.assertIn("layout", text)
        self.assertIn("composition", text)

    def test_per_reference_text_still_overrides_the_default(self):
        text = line_for("VEHICLE_GEOMETRY", controls=["the exact gauge layout"],
                        does_not_control=["weather"])
        self.assertIn("controls the exact gauge layout.", text)
        self.assertIn("It does NOT control: weather.", text)
        self.assertNotIn("intakes", text)


if __name__ == "__main__":
    unittest.main()
