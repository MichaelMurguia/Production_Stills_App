"""The stylesheet must actually parse.

A CSS syntax error does not fail loudly — the browser discards from the
error to the end of the enclosing block and keeps going, so a stray `*/`
two-thirds of the way up silently drops everything below it. On 2026-08-16
an edit left comment prose outside its `/* */` and the parsed sheet went
from 1519 rules to 482: two-thirds of the design system stopped existing
in the browser while the file on disk looked fine, the server served it
with a 200, and every existing test still passed because they all read the
TEXT of the file rather than what a parser makes of it.

Caught only because a computed style was being measured over CDP at the
time. These assertions are the cheap standing version of that."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CSS_FILES = [ROOT / "app/static/styles.css",
             ROOT / "storefront/static/store.css"]


def comment_problems(s: str):
    """Every /* closed, no */ without an opener. CSS comments do not nest,
    so a second /* inside one is also a smell worth reporting."""
    out, depth, i = [], 0, 0
    while i < len(s):
        a, b = s.find("/*", i), s.find("*/", i)
        if a == -1 and b == -1:
            break
        if a != -1 and (b == -1 or a < b):
            if depth:
                out.append(("nested /*", s[:a].count("\n") + 1))
            depth += 1
            i = a + 2
        else:
            if not depth:
                out.append(("stray */", s[:b].count("\n") + 1))
            depth = max(0, depth - 1)
            i = b + 2
    if depth:
        out.append(("unclosed /*", s.count("\n") + 1))
    return out


def strip_comments(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


class EveryStylesheetParses(unittest.TestCase):
    def test_comments_are_balanced(self):
        for f in CSS_FILES:
            if not f.exists():
                continue
            self.assertEqual(comment_problems(f.read_text(encoding="utf-8")), [],
                             f"{f.name}: a comment fault silently drops the rest")

    def test_braces_are_balanced(self):
        for f in CSS_FILES:
            if not f.exists():
                continue
            body = strip_comments(f.read_text(encoding="utf-8"))
            self.assertEqual(body.count("{"), body.count("}"),
                             f"{f.name}: unbalanced braces")

    def test_nothing_stray_sits_between_rules(self):
        """The actual 2026-08-16 fault: prose left outside a comment. Once
        comments are stripped, anything at top level that is not a rule, an
        at-rule or whitespace is text the parser will choke on."""
        for f in CSS_FILES:
            if not f.exists():
                continue
            body = strip_comments(f.read_text(encoding="utf-8"))
            depth, buf, line = 0, "", 1
            for ch in body:
                if ch == "\n":
                    line += 1
                if ch == "{":
                    depth += 1
                    buf = ""
                elif ch == "}":
                    depth -= 1
                    buf = ""
                elif depth == 0:
                    buf += ch
                    # A top-level run with a sentence-ender and no selector
                    # punctuation is prose, not a selector.
                    if any(p in buf for p in (". ", "! ", "? ")) and "{" not in buf:
                        self.fail(f"{f.name}: prose outside a comment near line {line}: "
                                  f"{buf.strip()[:60]!r}")

    def test_the_app_sheet_is_not_mysteriously_small(self):
        """A blunt backstop on the failure mode itself. The count only ever
        grows; if it collapses, something is eating rules."""
        body = strip_comments((ROOT / "app/static/styles.css").read_text(encoding="utf-8"))
        self.assertGreater(body.count("{"), 1200,
                           "the stylesheet lost a large number of rules")


if __name__ == "__main__":
    unittest.main()
