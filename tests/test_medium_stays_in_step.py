"""Regression, user-hit 2026-08-22 and reproduced from the install.

The Board Rendering Style anchor said **Photo Real**. The Model Test came
back an oil painting.

The evidence, off disk:

  16:17  the Art Direction Bible is written. Its Rendering Language reads
         "Production Painting rendering style — the brush left visible…
         Avoid: photographic detail. Lens effects."
  18:04  PUT /api/wizard/interview sets medium to "Photo Real rendering
         style — no mark of the hand… Everything must be explicable as
         optics."
  18:06  POST /api/wizard/samples/openai. `sample_probe` builds its ENTIRE
         brief from `bible.render_context("")`, so the only thing it said
         about medium was the 16:17 transcription. The engine painted what
         it was told to paint.

One question — "what medium do the panels render in?" — with two answers,
which is the failure this repo keeps meeting. The section is not an
independent statement: it is a transcription of the anchor's document
entry, so it is derived here and kept derived.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import bible, paths, store, style_docs  # noqa: E402

# The reporting user's own bible, trimmed to the sections that matter and
# carrying their Rendering Language section verbatim.
BIBLE = """# Project Oxcart — Locked Art Direction Bible

## Status
authoritative visual context

## Overall Visual Identity
- machined optimism, bare metal and desert light

## Rendering Language
### Required
- Production Painting rendering style — the brush left visible.
- Describe form with masses and edges, not with line.
- Visible directional brushwork follows the form and movement of the subject.
- Maintain a matte finish with no photographic specular sheen.

### Avoid
- Photographic detail.
- Cel outlines.
- Lens effects.

## Design Languages

## Skunkworks Engineering
Keywords: hangar, titanium
**Design language:** machined, bare, unsentimental
**Color identity:** unpainted titanium greys against desert ochre
- panel lines left visible

## Lighting Language
- hard desert sun, long shadows

## Drift Prevention Rule
stop and check
"""

PHOTO_REAL = style_docs.styles("rendering")[0]
for _e in style_docs.styles("rendering"):
    if _e.get("name") == "Photo Real":
        PHOTO_REAL = _e
        break
ANSWER = PHOTO_REAL["value"]


class TheBibleFollowsTheRenderingAnchor(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-medium-"))
        self._bible, self._data = paths.BIBLE, paths.DATA
        paths.BIBLE = self.tmp / "bible.md"
        paths.DATA = self.tmp / "data"
        paths.DATA.mkdir(parents=True, exist_ok=True)
        paths.BIBLE.write_text(BIBLE, encoding="utf-8")

    def tearDown(self):
        paths.BIBLE, paths.DATA = self._bible, self._data

    def answer(self, medium):
        store._atomic_write_json(paths.DATA / "interview.json",
                                 {"medium": medium})

    # ------------------------------------------------ the reported failure
    def test_the_reported_state_is_a_contradiction_the_app_can_see(self):
        self.answer(ANSWER)
        self.assertEqual(bible.stated_style(), "Production Painting")
        self.assertEqual(bible.medium_entry().get("name"), "Photo Real")
        self.assertIn("Production Painting", bible.medium_conflict())
        self.assertIn("Photo Real", bible.medium_conflict())

    def test_what_the_probe_would_have_sent(self):
        """The exact defect: the only medium instruction in the sample's
        brief was the wrong one, and it explicitly forbade the right one."""
        self.answer(ANSWER)
        brief = bible.render_context("")
        self.assertIn("the brush left visible", brief)
        self.assertIn("Photographic detail", brief)   # under Avoid
        self.assertNotIn("Photo Real", brief)

    def test_the_sync_puts_the_anchor_back_in_the_bible(self):
        self.answer(ANSWER)
        r = bible.sync_rendering_language()
        self.assertTrue(r["changed"])
        self.assertEqual(r["from"], "Production Painting")
        self.assertEqual(r["to"], "Photo Real")
        self.assertEqual(bible.stated_style(), "Photo Real")
        self.assertEqual(bible.medium_conflict(), "")

    def test_the_rebuilt_brief_asks_for_the_medium_that_was_chosen(self):
        self.answer(ANSWER)
        bible.sync_rendering_language()
        brief = bible.render_context("")
        self.assertIn("Photo Real rendering style", brief)
        self.assertIn("Lens-accurate detail falloff", brief)
        self.assertNotIn("brush left visible", brief)

    # ------------------------------------------------------ what it spares
    def test_it_touches_nothing_but_that_section(self):
        """The bible is a document the director edits. A whole-file rewrite
        would reflow the parts this has no business owning."""
        self.answer(ANSWER)
        bible.sync_rendering_language()
        after = bible.parse_sections(paths.BIBLE.read_text(encoding="utf-8"))
        before = bible.parse_sections(BIBLE)
        for name, body in before.items():
            if name == "Rendering Language":
                continue
            self.assertEqual(after.get(name), body, f"{name} was disturbed")

    def test_a_section_hand_tuned_within_the_right_style_is_left_alone(self):
        """Only a genuine contradiction fires. A director who added a
        bullet under Photo Real still has a section naming Photo Real."""
        text = BIBLE.replace(
            "- Production Painting rendering style — the brush left visible.",
            "- Photo Real rendering style — no mark of the hand.\n"
            "- Shoot it as if on a 40mm.")
        paths.BIBLE.write_text(text, encoding="utf-8")
        self.answer(ANSWER)
        r = bible.sync_rendering_language()
        self.assertFalse(r["changed"])
        self.assertIn("Shoot it as if on a 40mm.",
                      paths.BIBLE.read_text(encoding="utf-8"))

    def test_an_anchor_naming_no_known_style_changes_nothing(self):
        """Free text is a legitimate answer and the app cannot rebuild
        from it, so it neither rewrites nor blocks."""
        self.answer("something the library has never heard of")
        self.assertFalse(bible.sync_rendering_language()["changed"])
        self.assertEqual(bible.medium_conflict(), "")

    def test_no_bible_is_not_an_error(self):
        paths.BIBLE.unlink()
        self.answer(ANSWER)
        self.assertFalse(bible.sync_rendering_language()["changed"])

    def test_the_section_is_the_document_entry_not_a_summary(self):
        """The drafter saw a 600-character anchor answer capped at six
        mechanics. The rebuild reads the entry, so nothing is lost."""
        body = bible.rendering_section(PHOTO_REAL)
        for m in PHOTO_REAL["mechanics"]:
            self.assertIn(m.rstrip("."), body)
        for a in PHOTO_REAL["avoid"]:
            self.assertIn(a.lstrip().rstrip(".").lower(), body.lower())


class TheProbeRefusesAContradiction(unittest.TestCase):
    """The sync runs on the interview save and at boot, so a clash should
    not reach a render. It refuses anyway: an anchor naming a style the
    library does not carry cannot be rebuilt from, and that is exactly the
    case where a silent contradiction would ride."""

    def test_the_guard_is_on_the_path_that_spends_money(self):
        src = (ROOT / "app" / "generate.py").read_text(encoding="utf-8")
        i = src.index("def sample_probe(")
        seg = src[i:i + 4000]
        self.assertIn("bible.medium_conflict()", seg)
        # before the render is dispatched, not after
        self.assertLess(seg.index("medium_conflict"), seg.index("_samples_dir"))


class TheReconciliationRunsRatherThanAsks(unittest.TestCase):
    """"Migrations run, not offered" — and the installs carrying this bug
    are by definition the ones that already have a stale section."""

    SRC = (ROOT / "app" / "main.py").read_text(encoding="utf-8")

    def test_the_interview_save_reconciles(self):
        i = self.SRC.index("async def api_save_interview")
        self.assertIn("bible.sync_rendering_language(", self.SRC[i:i + 900])

    def test_boot_reconciles_every_production(self):
        i = self.SRC.index("def _resync_rendering_language")
        seg = self.SRC[i:i + 1200]
        self.assertIn("paths.list_projects()", seg)
        self.assertIn("bible.sync_rendering_language()", seg)
        self.assertIn("paths.set_project(prev)", seg)

    def test_there_is_no_button(self):
        self.assertNotIn("sync-rendering", self.SRC)
        self.assertNotIn("/api/bible/resync", self.SRC)

    def test_the_state_is_readable_before_a_render_is_paid_for(self):
        i = self.SRC.index("def api_get_style_bible")
        self.assertIn("medium_conflict", self.SRC[i:i + 700])


if __name__ == "__main__":
    unittest.main()
