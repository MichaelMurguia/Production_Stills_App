"""NON_CANON_REVIEW_2026-08-07 — the seven rulings, held.

The principle behind R3–R5, in the reviewer's words:

    A verb sits with the thing it acts on, and never in the row of verbs
    that judge it. Making, reading and judging are three different acts;
    a bar that mixes them makes the user read every button before
    pressing any.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
DS = (ROOT / "app/static/DESIGN_SYSTEM.md").read_text(encoding="utf-8")
# The design system is hard-wrapped prose, so a canon phrase can straddle
# a line break. Assertions read the flattened text.
DS_FLAT = re.sub(r"\s+", " ", DS).lower()


def between(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i)]


class R1_TwoFactsTwoVoices(unittest.TestCase):
    def test_the_strip_has_a_separate_progress_line(self):
        self.assertIn('<span class="busy-prog mono"></span>', JS)
        self.assertIn("progress(msg)", JS)

    def test_the_phase_is_a_sentence_and_the_measure_is_courier(self):
        i = JS.index('startBusy($("[data-busy]", card)')
        body = JS[i:i + 1400]
        self.assertIn('"Packing the production…"', body)
        self.assertIn('busy.label("Downloading the backup…")', body)
        self.assertIn("busy.progress(", body)
        self.assertNotIn("Downloading — ${mbs", body,
                         "one sentence must not carry both facts")

    def test_the_progress_line_is_faint_courier(self):
        b = between(CSS, ".busy .busy-prog", "}")
        self.assertIn("var(--ink-faint)", b)
        self.assertIn("letter-spacing", b)


class R2_AReportHasNoAmber(unittest.TestCase):
    def test_the_questions_verb_is_a_text_act(self):
        i = JS.index('data-f="answer-qs"')
        self.assertIn("text-act", JS[i - 60:i])

    def test_the_count_reads_as_a_fact(self):
        i = JS.index("ANSWERED${")
        window = JS[i - 200:i + 80]
        self.assertIn("mini mono", window)
        self.assertNotIn("accent", window)
        self.assertNotIn("--bad", window)


class R3_GenerationLeavesTheVerdictBar(unittest.TestCase):
    def viewer(self) -> str:
        return between(JS, "const openSwatchViewer", "\n    const renderSwatchStrip")

    def test_rescan_is_in_the_header_not_the_footer(self):
        head = between(self.viewer(), '<div class="sv-head">', "</div>")
        self.assertIn('data-f="rescan"', head)
        foot = between(self.viewer(), '<div class="sv-foot">', "</div>")
        self.assertNotIn('data-f="rescan"', foot,
                         "a generation act may not sit in the verdict row")

    def test_deep_scan_stayed_beside_generate(self):
        self.assertIn('data-f="sw-deep"', JS)
        i = JS.index('data-f="sw-go"')
        self.assertLess(abs(JS.index('data-f="sw-deep"') - i), 400,
                        "Deep scan belongs beside Generate at step 5")

    def test_the_brief_is_free_text_with_recall_not_chips(self):
        i = JS.index('name: "note"')
        block = JS[i:i + 500]
        self.assertIn("textarea: true", block)
        self.assertIn("recall:", block)
        self.assertIn('uiSet("swatchBriefs"', JS)
        self.assertIn(".slice(0, 3)", JS, "the last three, no more")

    def test_a_recalled_brief_fills_the_field(self):
        self.assertIn("[data-mfr]", JS)
        self.assertIn("mf-recall", CSS)


class R4_DestructionWhereItsObjectReads(unittest.TestCase):
    def test_the_ramp_row_has_no_delete(self):
        body = between(JS, "const renderPaletteRows", "\n  const refreshRefs")
        self.assertNotIn('data-f="del"', body)
        self.assertNotIn("&times;", body)

    def test_remove_group_is_in_the_viewer_footer(self):
        viewer = between(JS, "const openSwatchViewer", "\n    const renderSwatchStrip")
        foot = between(viewer, '<div class="sv-foot">', "</div>")
        self.assertIn('data-f="rm-group"', foot)
        self.assertIn("Remove group", foot)

    def test_it_confirms_with_the_count(self):
        self.assertIn("Remove ${ids.length} reference", JS)

    def test_it_is_offered_only_where_the_group_is_readable(self):
        """approved && !many — one language, fully on screen."""
        self.assertIn("${approved && !many ?", JS)


class R5_ABulkVerdictIsWithheld(unittest.TestCase):
    def test_approve_all_is_disabled_while_anything_is_unopened(self):
        i = JS.index('data-f="ap-all"${unopened(r)')
        self.assertIn('" disabled" : ""', JS[i:i + 80])

    def test_discard_the_rest_is_not_withheld(self):
        i = JS.index('data-f="discard"')
        self.assertNotIn("disabled", JS[i:i + 60],
                         "rejecting unread proposals is legitimate and logged")

    def test_the_condition_stays_a_fact(self):
        b = between(CSS, ".sw-bar-note", "}")
        self.assertIn("var(--ink-faint)", b)
        self.assertNotIn("--accent", b)
        self.assertNotIn("--bad", b)


class R6_TheColourSwatchIsSquare(unittest.TestCase):
    def test_square_at_the_fields_height(self):
        b = between(CSS, ".mf-color input[type=color] {", "}")
        self.assertIn("aspect-ratio: 1", b)
        self.assertNotIn("width: 46px", b)

    def test_the_hex_is_still_the_value_of_record(self):
        self.assertIn('fields.map((f, i) => [f.name, $(`[data-mf="${i}"]`, ov).value.trim()])', JS)


class R7_AMenuReadsIntoConsequence(unittest.TestCase):
    def test_import_sits_above_delete(self):
        menu = between(JS, 'data-act="dup"', 'data-act="del"')
        self.assertIn('data-act="imp"', menu)

    def test_delete_is_separated_by_the_menus_rule(self):
        self.assertIn("border-top: 1px solid var(--line-soft)",
                      between(CSS, ".card-menu .danger-act {", "}"))


class TheTableIsEmpty(unittest.TestCase):
    def test_every_row_was_ruled(self):
        table = between(DS, "| Date | Pattern | Used in |", "## Changelog")
        rows = [l for l in table.splitlines() if l.startswith("| 2026-")]
        self.assertEqual(rows, [], f"{len(rows)} rows still awaiting review")

    def test_the_principle_is_canon(self):
        for phrase in ("a verb sits with the thing it acts on",
                       "a bulk verdict is withheld until everything it judges has been seen",
                       "only offered where its object can be read in full",
                       "amber marks what blocks. a report has no amber",
                       "an in-card wait states its phase in sentence case",
                       "a resolved item fades its label and keeps its answer",
                       "card menus read top to bottom in increasing consequence"):
            self.assertIn(phrase, DS_FLAT, phrase)


if __name__ == "__main__":
    unittest.main()
