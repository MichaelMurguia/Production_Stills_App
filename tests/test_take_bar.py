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


if __name__ == "__main__":
    unittest.main()
