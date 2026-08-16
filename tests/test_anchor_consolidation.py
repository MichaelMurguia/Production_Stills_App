"""One question per anchor (user 2026-08-16: "we now have duplicative
entries and we should consolidate").

The look interview and the style anchors were the same four questions
asked in two media. `Medium & finish` and Board Rendering's SETS line were
the same three words; `Palette & light` was one box answering two
different anchors. The fix is not a third list — it is folding the words
INTO the anchor card they duplicate, so each anchor has a picture half and
a words half, and the interview keeps only what no anchor can hold: the
touchstones, the never-list, and notes."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
WIZ = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")

ANCHORS = {
    "WORLD_TEXTURE": "wiz-texture",
    "COLOR_PALETTE": "wiz-palette",
    "CINEMATOGRAPHY_STYLE": "wiz-light",
    "BOARD_RENDERING_STYLE": "wiz-medium",
}


def card(role: str) -> str:
    i = HTML.index(f'<div class="wiz-col" data-role="{role}">')
    return HTML[i:HTML.index('<div class="wiz-col"', i + 10)
                if f'<div class="wiz-col"' in HTML[i + 10:] else len(HTML)]


class TheDuplicationIsGone(unittest.TestCase):
    def test_every_anchor_carries_its_own_words(self):
        for role, fid in ANCHORS.items():
            seg = card(role)
            self.assertIn('class="wiz-words"', seg, f"{role} has no words half")
            self.assertIn(f'id="{fid}"', seg, f"{role} lost {fid}")

    def test_the_interview_no_longer_asks_them_a_second_time(self):
        grid = HTML[HTML.index('<div class="grid-form">'):
                    HTML.index('id="wiz-iv-state"')]
        for fid in ANCHORS.values():
            self.assertNotIn(f'id="{fid}"', grid,
                             f"{fid} is asked in two places again")

    def test_the_interview_keeps_only_what_no_anchor_can_hold(self):
        grid = HTML[HTML.index('<div class="grid-form">'):
                    HTML.index('id="wiz-iv-state"')]
        for fid in ("wiz-touchstones", "wiz-never", "wiz-notes"):
            self.assertIn(f'id="{fid}"', grid)
        i = JS.index("const ivFields =")
        self.assertEqual(
            re.search(r"const ivFields = \[(.*?)\]", JS[i:i + 300], re.S)
              .group(1).count("#wiz-"), 3,
            "step 01 counts three questions, not five")

    def test_a_negative_is_why_the_never_list_stays(self):
        """No anchor can hold it: you cannot photograph "never anime"."""
        self.assertIn("wiz-never", HTML)
        seg = HTML[HTML.index('<div class="grid-form">'):
                   HTML.index('id="wiz-iv-state"')]
        self.assertIn("never look like", seg)


class TheValueStillReachesTheBible(unittest.TestCase):
    def test_the_server_persists_one_key_per_anchor(self):
        i = MAIN.index("_INTERVIEW_FIELDS = (")
        seg = MAIN[i:i + 400]
        for k in ("touchstones", "texture", "palette", "light", "medium",
                  "never", "notes"):
            self.assertIn(f'"{k}"', seg)

    def test_the_two_new_answers_are_not_dropped_on_the_floor(self):
        """A key the drafting prompt never reads is a field that does
        nothing — which is worse than the duplication it replaced."""
        for probe in ("answers.get('texture')", "answers.get('light')",
                      "answers.get('palette')", "answers.get('medium')"):
            self.assertIn(probe, WIZ, probe)

    def test_each_answer_is_fenced_to_its_own_anchor(self):
        i = WIZ.index("WORLD_TEXTURE in words")
        seg = WIZ[i:i + 1400]
        self.assertIn("WORDS half of the anchor it names", seg)
        self.assertIn("feeds only its anchor's sections", seg)
        self.assertIn("the director's words win", seg,
                      "words and photos describe one thing; ties go to the "
                      "person who typed")

    def test_the_draft_payload_carries_all_four(self):
        i = JS.index("const answers = {")
        seg = JS[i:i + 900]
        for k in ("texture:", "palette:", "light:", "medium:"):
            self.assertIn(k, seg)


class AnAnchorIsAnsweredByEither(unittest.TestCase):
    def test_the_step_badge_counts_words_as_an_answer(self):
        i = JS.index("const ANCHOR_WORDS =")
        seg = JS[i:i + 600]
        for role in ANCHORS:
            self.assertIn(role, seg)
        self.assertIn("?.value.trim()).length", seg)

    def test_the_card_badge_never_reads_none_over_its_own_answer(self):
        i = JS.index("const inWords =")
        seg = JS[i - 400:i + 400]
        self.assertIn('"IN WORDS"', seg)
        self.assertIn("mine.length ? `${mine.length}`", seg,
                      "pictures still carry the count")

    def test_the_badge_is_resynced_when_the_words_arrive(self):
        """The interview loads after the cards render, so a badge read at
        render time is read too early."""
        self.assertIn("const syncAnchorBadges =", JS)
        i = JS.index("const syncAnchorBadges =")
        self.assertIn(r"/^\d+$/.test", JS[i:i + 400],
                      "a card with pictures keeps its count")
        self.assertGreaterEqual(JS.count("syncAnchorBadges()"), 3,
                                "called on load, on change, and on a pick")


class OnePickerServesEveryKnownVocabulary(unittest.TestCase):
    def test_there_is_one_picker_not_two(self):
        self.assertEqual(JS.count("function openStylePicker("), 1)
        self.assertNotIn("function openRenderStyleModal", JS)
        self.assertEqual(JS.count("const bindPicker ="), 1)
        self.assertEqual(JS.count("bindPicker(\""), 2,
                         "one helper, bound twice")

    def test_both_catalogues_state_what_they_are_not(self):
        for cat in ("RENDER_STYLES", "CINEMA_STYLES"):
            i = JS.index(f"const {cat} = [")
            seg = JS[i:JS.index("\n];", i)]
            self.assertGreaterEqual(seg.count("name:"), 6,
                                    f"{cat} is thin")
            self.assertEqual(seg.count("name:"), seg.count("not:"),
                             f"every {cat} card states its fence")
            self.assertEqual(seg.count("name:"), seg.count("value:"),
                             f"every {cat} card writes a directive")

    def test_the_definition_leads_and_names_what_it_is_not(self):
        i = JS.index('title: "Rendering style"')
        self.assertIn("not mood, not light, not cinematography", JS[i:i + 500])
        j = JS.index('title: "Cinematography"')
        self.assertIn("not the palette", JS[j:j + 500])
        self.assertIn("single panel's hour", JS[j:j + 500])

    def test_free_text_survived_the_catalogue(self):
        """These were text boxes. A catalogue that cannot say "something
        else" is a smaller field than the one it replaced."""
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index("\n}\n", i)]
        self.assertIn('id="rs-own"', seg)
        self.assertIn("own.value.trim() || picked", seg)

    def test_a_typed_answer_puts_the_cards_out(self):
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index("\n}\n", i)]
        self.assertIn('own.addEventListener("input"', seg)
        self.assertIn("picked = \"\"; mark();", seg,
                      "two answers must never be lit at once")

    def test_the_upload_route_goes_to_the_anchor_it_belongs_to(self):
        i = JS.index("function openStylePicker(")
        seg = JS[i:JS.index("\n}\n", i)]
        self.assertIn('data-role="${uploadRole}"', seg)
        self.assertIn('uploadRole: "BOARD_RENDERING_STYLE"', JS)
        self.assertIn('uploadRole: "CINEMATOGRAPHY_STYLE"', JS)

    def test_selection_is_ink_not_amber(self):
        """§1.3 — a chosen style is STATE; amber stays with the one
        primary action."""
        b = re.search(r"\.rs-card\.on \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertIn("var(--ink)", b.group(1))
        self.assertNotIn("accent", b.group(1))

    def test_the_trigger_reads_as_a_field_not_a_verb(self):
        b = re.search(r"\.pick-btn \{([^}]*)\}", CSS)
        self.assertTrue(b)
        self.assertIn("text-align: left", b.group(1))
        self.assertIn("var(--sans)", b.group(1),
                      "a style NAME is hierarchy, not machine data")


if __name__ == "__main__":
    unittest.main()
