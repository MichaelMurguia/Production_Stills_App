"""The take action bar — one verdict, two lists, no wrap (mock 17a,
2026-08-08; supersedes the 14a comparison contract in this file's own
history).

The plan's rule, canonized: the code is not the authority on hierarchy —
the decision is. Seven verbs were not peers; one is the verdict the whole
screen exists to collect. A shared constructor (`mk(…, "ghost")`) is an
implementation fact, never a design argument.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def staged_block() -> str:
    i = JS.index('<div class="act-bar">')
    j = JS.index('if (c.status === "REJECTED") actDanger.append(mk("Delete forever"', i)
    return JS[i:j + 300]


class OneVerdict(unittest.TestCase):
    def test_approve_is_the_only_primary(self):
        body = staged_block()
        self.assertIn('mk("Approve panel", "primary act-approve-btn"', body)
        # count VERBS, not the slice — the Full-size dialog's own modal
        # buttons live inside this range and are not bar chrome
        import re
        prim = [m for m in re.findall(r'mk\("[^"]+", "([^"]+)"', body)
                if m.startswith("primary")]
        self.assertEqual(len(prim), 1,
                         "exactly one boxed amber verdict in the bar")

    def test_the_six_verbs_are_text_acts(self):
        body = staged_block()
        for verb in ('mk("Full-size take", "text-act"',
                     'mk("Repair region", "text-act"',
                     'mk("Reference", "text-act act-dim"',
                     'mk("Crop to reference", "text-act act-dim"',
                     'mk("Light study", "text-act act-dim"',
                     'mk("Reject", "text-act act-reject"'):
            self.assertIn(verb, body, verb)
        self.assertNotIn('mk("→', body, "arrows came off every label")
        import re
        ghosts = [m for m in re.findall(r'mk\("[^"]+", "([^"]+)"', body)
                  if "ghost" in m]
        self.assertEqual(ghosts, [], "no ghost verbs remain in the bar")

    def test_the_groups_carry_their_kickers(self):
        i = JS.index('<div class="act-bar">')
        markup = JS[i:i + 1400]
        self.assertIn('class="act-kicker">USE<', markup)
        self.assertIn('class="act-kicker">DERIVE<', markup)
        self.assertIn('class="act-spacer"', markup)

    def test_derive_holds_three(self):
        body = staged_block()
        self.assertEqual(body.count('actDerive.append('), 3)

    def test_the_gates_are_unchanged(self):
        """Reference stays disabled until approval, title as explanation;
        Delete forever appears only on a REJECTED take and keeps danger."""
        body = staged_block()
        self.assertIn('c.status !== "APPROVED"', body)
        self.assertIn("Approve this take first", body)
        self.assertIn('mk("Delete forever", "danger"', body)


class TheFold(unittest.TestCase):
    def test_derive_collapses_before_the_row_wraps(self):
        """Wrapped content is not overflow — flex-wrap absorbs the row and
        scrollWidth never exceeds clientWidth (the first live check found
        the fold never firing). The real test is whether any zone left the
        first line."""
        i = JS.index("// 17a — a group folds before the row breaks")
        block = JS[i:i + 2400]
        self.assertIn("new ResizeObserver(fit).observe(bar)", block)
        self.assertIn('bar.classList.add("derive-collapsed")', block)
        self.assertIn("z.offsetTop", block, "fold on wrap, not only overflow")
        self.assertIn("requestAnimationFrame", block,
                      "mutation leaves the observer's frame")

    def test_the_menu_reuses_the_card_menu_and_returns_its_buttons(self):
        i = JS.index("// 17a — a group folds before the row breaks")
        block = JS[i:i + 1800]
        self.assertIn('menu.className = "card-menu act-derive-menu"', block)
        self.assertIn("deriveItems.append(...menu.querySelectorAll", block,
                      "closing the menu must give the zone its buttons back")

    def test_an_empty_group_hides_kicker_and_all(self):
        i = JS.index("// 17a — a group folds before the row breaks")
        self.assertIn('zone.classList.add("hidden")', JS[i:i + 1800])


class TheSelectionIsRemembered(unittest.TestCase):
    """Reference selection carries generation to generation (user
    2026-08-08). The memory is the take record itself — every take stores
    which references it attached — so it survives reloads and devices
    with no new storage, and an emptied selection is remembered too."""

    def block(self) -> str:
        i = JS.index("buildWorkbench.isChecked")
        return JS[i - 900:i + 900]

    def test_the_newest_take_is_the_memory(self):
        b = self.block()
        self.assertIn("const lastTake = panelCands[0]", b)
        self.assertIn("(lastTake?.references || []).map(r => r.id)", b)
        self.assertIn("g.ids.some(id => lastIds.has(id))", b)

    def test_the_matcher_is_only_the_first_take_default(self):
        b = self.block()
        self.assertIn("lastTake", b)
        self.assertIn("reqObjs.some(o => matches(o, g.name))", b)

    def test_the_hint_says_which_rule_is_in_force(self):
        self.assertIn("rode the previous take and stay selected", JS)
        self.assertIn("match this panel's required objects and are pre-checked", JS)

    def test_no_match_warning_never_second_guesses_a_remembered_choice(self):
        i = JS.index("P5: four unchecked boxes")
        self.assertIn("panelCands.length", JS[i:i + 700],
                      "an empty remembered selection is a decision, not a gap")


if __name__ == "__main__":
    unittest.main()
