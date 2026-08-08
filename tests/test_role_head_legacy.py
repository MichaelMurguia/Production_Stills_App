"""A titled reference still belongs to its family (user 2026-08-07).

The Panels screen enumerated the kinds of reference in the library and
listed a person among them:

    Every group in the library is a board layout style, character likeness
    john, cast likeness, vehicle reference, …

`role_head` split on the em-dash, which handles "CHARACTER_LIKENESS_—_JOHN".
It does not handle "CHARACTER_LIKENESS_JOHN", the fully sanitized legacy
form where the dash itself was replaced — so JOHN became a role FAMILY.

Same defect, two consequences: a person's name enumerated as a kind of
reference in the UI, and — worse — no recognisable family in a render
prompt, so a titled reference fell through to the generic jurisdiction
line instead of the one written for its role.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, store  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
# Prose assertions read a comment-stripped view: the phrases these
# tests forbid also appear in the comments explaining why they went,
# and a plain substring search cannot tell the two apart.
JS_CODE = "\n".join(l for l in JS.splitlines()
                    if not l.lstrip().startswith("//"))


class LegacyTitledRoles(unittest.TestCase):
    def test_the_fully_sanitized_form_resolves_to_its_family(self):
        self.assertEqual(store.role_head("CHARACTER_LIKENESS_JOHN"),
                         "CHARACTER_LIKENESS")

    def test_the_em_dash_forms_still_resolve(self):
        for r in ("CHARACTER_LIKENESS_—_JOHN", "CHARACTER_LIKENESS — JOHN",
                  "CHARACTER_LIKENESS—JOHN"):
            self.assertEqual(store.role_head(r), "CHARACTER_LIKENESS", r)

    def test_a_bare_family_is_unchanged(self):
        for r in ("CHARACTER_LIKENESS", "VEHICLE_GEOMETRY", "COLOR_PALETTE"):
            self.assertEqual(store.role_head(r), r)

    def test_the_two_board_families_do_not_swallow_each_other(self):
        self.assertEqual(store.role_head("BOARD_LAYOUT_STYLE"), "BOARD_LAYOUT_STYLE")
        self.assertEqual(store.role_head("BOARD_RENDERING_STYLE"), "BOARD_RENDERING_STYLE")

    def test_a_free_form_role_is_left_alone(self):
        """Roles are free-form by design; an unknown one is its own head."""
        self.assertEqual(store.role_head("P-38 COCKPIT"), "P-38 COCKPIT")
        self.assertEqual(store.role_head("MADE_UP_ROLE"), "MADE_UP_ROLE")

    def test_a_titled_reference_now_gets_its_familys_jurisdiction(self):
        """The consequence that reached a render: it used to fall through
        to the generic line."""
        out = "\n".join(generate._reference_role_lines(
            [{"id": "REF-001", "role": "CHARACTER_LIKENESS_JOHN"}]))
        self.assertIn("this character's facial likeness", out)
        self.assertNotIn("controls its assigned role", out)

    def test_the_js_twin_uses_the_same_rule(self):
        m = re.search(r"function roleHead\(role\) \{.*?\n\}", JS, re.S)
        self.assertIsNotNone(m)
        body = m.group(0)
        self.assertIn("ROLE_FAMILIES", body)
        self.assertIn('raw.startsWith(h + "_")', body)


class TheNoMatchNoticeNamesWhatFailed(unittest.TestCase):
    def test_it_lists_the_required_objects(self):
        i = JS.index("NO MATCHES")
        block = JS[i - 700:i + 700]
        self.assertIn("Nothing in the library matches what this panel requires",
                      block)
        self.assertIn("reqObjs.slice(0, 4)", block)

    def test_the_hardcoded_claim_is_gone(self):
        """The sentence that enumerated role kinds and then asserted what
        the panel needed. (The phrase survives in a comment explaining why
        it went — assert the rendered string, not the file.)"""
        self.assertNotIn("Every group in the library is", JS_CODE)

    def test_it_says_what_to_do_next(self):
        i = JS.index("NO MATCHES")
        self.assertIn("tick a group below", JS[i:i + 700])

    def test_no_required_objects_is_its_own_sentence(self):
        i = JS.index("NO MATCHES")
        self.assertIn("lists no required objects", JS[i:i + 700])


class TheSettingsPointerIsGone(unittest.TestCase):
    def test_nothing_references_it_anywhere(self):
        for rel in ("app/static/app.js", "app/static/index.html",
                    "app/static/styles.css"):
            src = (ROOT / rel).read_text(encoding="utf-8")
            for dead in ("PRODUCTIONS MOVED", "goto-productions", "subnav-end"):
                self.assertNotIn(dead, src, f"{dead} still in {rel}")


if __name__ == "__main__":
    unittest.main()
