"""Regression, user-hit 2026-08-22 and reproduced end to end.

  "I can change the rendering style on the production design page, go to
   the panel page and render — I don't get the rendering style."

The fresh path was never broken: `generate._style_context` calls
`bible.render_context()` on every render and that reads the Bible file
each time, so `compile_panel_prompt` follows the anchor immediately.

What broke it is a prompt SAVED onto the panel. That rides every take by
design (ruled 2026-08-16, and it is right — it is the panel's own words
about its own subject). But the editor opens on the COMPILED prompt, so
saving after any edit freezes a copy of the whole thing, VISUAL STYLE
block included. From then on the panel could never see a Bible change,
and nothing said so.

The art direction is the PRODUCTION's, not the panel's to freeze. The
authored half stays exactly as written; the derived half is re-applied at
render time.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BIBLE_PAINT = """# Oxcart

## Rendering Language
### Required
- Production Painting rendering style - the brush left visible.
- Massed tone rather than outline.

### Avoid
- Photographic detail.

## Lighting Language
- hard desert sun
"""


class TheArtDirectionIsNotThePanelsToFreeze(unittest.TestCase):
    def setUp(self):
        from app import paths, store
        # Restore it: a home left pointing at a temp dir followed this
        # class into every test that ran after it.
        self._home, self._slug = paths.HOME, paths.ACTIVE_PROJECT
        self.addCleanup(self._restore)
        paths.HOME = Path(tempfile.mkdtemp(prefix="sb-ovr-"))
        paths.set_project("")
        paths.ensure_dirs()
        paths.BIBLE.parent.mkdir(parents=True, exist_ok=True)
        paths.BIBLE.write_text(BIBLE_PAINT, encoding="utf-8")
        self.spec = store.new_spec("S1", "the hangar", "CANON_EXTRACTION")
        self.spec["panels"] = [{"id": "P01", "title": "Hero",
                                "purpose": "the hangar floor"}]
        self.spec["setting"] = {"int_ext": "INT", "location": "HANGAR",
                                "time_of_day": "DAY"}
        store.save_spec("S1", self.spec)
        self.panel = self.spec["panels"][0]

    def _restore(self):
        from app import paths
        paths.HOME = self._home
        paths.set_project(self._slug)

    def edited_prompt(self):
        """What the workbench saves: the compiled prompt with an edit in
        it. The editor opens on `saved or compiled`, so this is the shape
        every saved prompt actually has."""
        from app import generate
        p = generate.compile_panel_prompt(self.spec, self.panel, [])
        return p.replace("the hangar floor",
                         "the hangar floor, wet, seen from the door")

    def change_the_style_to(self, name):
        from app import bible, paths, store, style_docs
        e = next(x for x in style_docs.styles("rendering") if x["name"] == name)
        store._atomic_write_json(paths.DATA / "interview.json",
                                 {"medium": e["value"]})
        return bible.sync_from_anchors()

    # ------------------------------------------------ the fresh path is fine
    def test_a_panel_with_no_saved_prompt_follows_the_anchor(self):
        from app import generate
        self.assertIn("brush left visible",
                      generate.compile_panel_prompt(self.spec, self.panel, []))
        self.change_the_style_to("Photo Real")
        after = generate.compile_panel_prompt(self.spec, self.panel, [])
        self.assertIn("Photo Real rendering style", after)
        self.assertNotIn("brush left visible", after)

    # ------------------------------------------------------ the reported bug
    def test_a_saved_prompt_carried_the_old_medium(self):
        """The state before the fix, kept as the reproduction."""
        saved = self.edited_prompt()
        self.change_the_style_to("Photo Real")
        self.assertIn("brush left visible", saved)
        self.assertNotIn("Photo Real", saved)

    def test_the_render_re_applies_the_current_art_direction(self):
        from app import generate
        saved = self.edited_prompt()
        self.change_the_style_to("Photo Real")
        out, note = generate.refresh_art_direction(saved, self.spec, self.panel)
        self.assertIn("Photo Real rendering style", out)
        self.assertNotIn("brush left visible", out)
        self.assertIn("re-applied", note)

    def test_the_users_own_words_survive_it(self):
        """The whole point of the split. Their edit is the panel's; the
        VISUAL STYLE block is the production's."""
        from app import generate
        saved = self.edited_prompt()
        self.change_the_style_to("Photo Real")
        out, _ = generate.refresh_art_direction(saved, self.spec, self.panel)
        self.assertIn("wet, seen from the door", out)
        self.assertIn("PANEL: P01", out)
        self.assertIn("BOARD-SPECIFIC TREATMENT", out)

    def test_nothing_changes_when_nothing_changed(self):
        """No note, no rewrite — otherwise every take would claim one."""
        from app import generate
        saved = self.edited_prompt()
        out, note = generate.refresh_art_direction(saved, self.spec, self.panel)
        self.assertEqual(out, saved)
        self.assertEqual(note, "")

    def test_a_hand_written_prompt_is_left_exactly_as_written(self):
        """One with no recognisable block. There is nothing to replace,
        and inventing a place to put it would be worse than leaving it."""
        from app import generate
        mine = "Render the hangar at dawn. Nothing else."
        out, note = generate.refresh_art_direction(mine, self.spec, self.panel)
        self.assertEqual(out, mine)
        self.assertIn("left as written", note)

    # ------------------------------------------------------------ the wiring
    def test_a_per_call_prompt_still_renders_verbatim(self):
        """The one-take test path. A test has to be able to try something
        other than what is saved, art direction included."""
        src = (ROOT / "app" / "generate.py").read_text(encoding="utf-8")
        i = src.index('asked = (render_prompt or "").strip()')
        seg = src[i:i + 700]
        self.assertIn("if override and not asked:", seg)
        self.assertIn("refresh_art_direction(override, spec, panel)", seg)

    def test_the_take_records_that_it_happened(self):
        src = (ROOT / "app" / "generate.py").read_text(encoding="utf-8")
        self.assertIn('record["prompt_art_direction"] = ad_note', src)


if __name__ == "__main__":
    unittest.main()
