"""A take's framing badge must describe the text that was SENT.

User-caught 2026-08-26, on CAND-0035. The badge read

    FRAMING — SUBJECTIVE / POETIC CHARACTER · 50-100mm, f/1.4-2.8, SELECTIVE

over a deep-focus wide of a ship on a salt pan: everything sharp from the
foreground figure to the hull behind her. Nothing about that image is
50–100mm at f/1.4–2.8.

The panel really did resolve that framing. But the take was rendered from
a SAVED prompt — the badge beside it said `SENT — HAND-EDITED` — and a
saved prompt carries its own CAMERA block, because the camera is the
panel's own wording and is deliberately not among the blocks refreshed
into a saved prompt. That rule is right. The prompt was saved before
framings existed, so it still said 24mm, wide, deep, and the image is
exactly what it asked for.

The record was the only thing that was wrong.

This is C4 one level up. C4 was reading `prompt` where `render_prompt`
was the truth; this was building a stamp from the panel's CURRENT fields
and calling it what the take rode. Both report intent as if it were fact,
and both cost a day of reading images against a record that was lying.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import camera_recipes as rec  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
POETIC = "cine-subjective-poetic"
PANEL = {"cinematography": POETIC}

RODE = "CAMERA — the shot's framing.\n- FRAMING — Subjective / poetic character — 50–100mm."
DIDNT = "CAMERA — the shot's framing.\n- WIDE SHOT.\n- 24mm LENS — a wide field of view."


class TheStampReadsTheSentText(unittest.TestCase):
    def test_a_framing_in_the_prompt_rides(self):
        s = rec.stamp(PANEL, RODE)
        self.assertTrue(s["rides"])
        self.assertEqual(s["key"], "subjective-poetic-character")

    def test_a_framing_absent_from_the_prompt_does_not(self):
        s = rec.stamp(PANEL, DIDNT)
        self.assertFalse(s["rides"])
        self.assertIs(s["in_prompt"], False)

    def test_it_still_names_what_would_have_ridden(self):
        """Both facts. "No framing" alone would read as a panel that never
        chose one, which is a different and equally wrong story."""
        s = rec.stamp(PANEL, DIDNT)
        self.assertEqual(s["would_be"], "subjective-poetic-character")
        self.assertEqual(s["would_be_name"], "Subjective / poetic character")
        self.assertIn("carries its own CAMERA block", s["why"])

    def test_it_is_not_reported_as_a_refusal(self):
        """NONE is a director's choice. This is a saved prompt predating
        the field, and calling it a refusal would blame the user."""
        self.assertFalse(rec.stamp(PANEL, DIDNT)["refused"])

    def test_a_panel_that_refused_still_reads_as_a_refusal(self):
        self.assertEqual(rec.stamp({"camera_recipe": "NONE"}, DIDNT),
                         {"rides": False, "refused": True})

    def test_no_sent_text_falls_back_to_the_panel(self):
        """Callers that have no prompt to check — the panel preview, a
        test — get the old answer rather than a false negative."""
        self.assertTrue(rec.stamp(PANEL)["rides"])
        self.assertTrue(rec.stamp(PANEL, "")["rides"])

    def test_the_render_path_passes_what_it_sent(self):
        g = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        self.assertIn('"camera_recipe": _rec_stamp(panel, override or prompt),', g)

    def test_the_head_it_looks_for_is_the_one_the_compiler_writes(self):
        """A head this checks for and the compiler does not write would
        mark every take as not-ridden, silently."""
        from app import generate
        block = generate._camera_block(PANEL)
        self.assertTrue(any(ln.startswith(rec.LINE_HEAD) for ln in block))


class TheBadgeSaysSo(unittest.TestCase):
    def test_it_states_the_framing_was_not_in_this_prompt(self):
        i = JS.index("shot-tag-didnt")
        seg = " ".join(JS[i:i + 500].split())
        self.assertIn("FRAMING — NOT IN THIS PROMPT", seg)
        self.assertIn("WOULD RIDE A RECOMPILE", seg)

    def test_it_is_not_painted_as_an_error(self):
        """A saved prompt carrying its own camera is the correct rule.
        What was wrong was the badge claiming otherwise."""
        block = CSS.split(".shot-tag-didnt {")[1].split("}")[0]
        self.assertIn("--ink-faint", block)
        self.assertNotIn("--bad", block)
        self.assertNotIn("--accent", block)

    def test_the_two_states_cannot_both_render(self):
        i = JS.index("staged.camera_recipe?.in_prompt === false")
        seg = JS[i:i + 900]
        self.assertIn(": staged.camera_recipe?.rides", seg)


if __name__ == "__main__":
    unittest.main()
