"""The suite checks itself for dead tests.

2026-08-06: two token contracts were appended to a test file AFTER its
`if __name__ == "__main__":` block. They were correctly indented, they
read as methods, they were reported as added — and they never ran once.
A test that cannot fail is worse than no test: it is a false assurance
sitting in the commit that claims to cover the thing it does not.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
MAIN = 'if __name__ == "__main__":'


class SuiteHygiene(unittest.TestCase):
    def files(self):
        return sorted(TESTS.glob("test_*.py"))

    def test_there_are_test_files_to_check(self):
        self.assertGreater(len(self.files()), 5)

    def block_at(self, src: str) -> int | None:
        """The real guard is at column 0 — the same text quoted inside a
        file (as this one quotes it) is not it."""
        hits = list(re.finditer(r"^if __name__ == .__main__.:", src, re.M))
        return hits[-1].end() if hits else None

    def test_nothing_lives_after_the_main_block(self):
        for f in self.files():
            src = f.read_text(encoding="utf-8")
            at = self.block_at(src)
            if at is None:
                continue
            after = src[at:]
            # only the unittest.main() call and blank lines may follow
            leftover = re.sub(r"\s+|unittest\.main\(\)", "", after)
            with self.subTest(file=f.name):
                self.assertEqual(leftover, "",
                                 f"{f.name} has code after its __main__ block — "
                                 "anything defined there never runs")

    def test_every_test_file_defines_at_least_one_reachable_test(self):
        for f in self.files():
            src = f.read_text(encoding="utf-8")
            at = self.block_at(src)
            body = src[:at] if at is not None else src
            with self.subTest(file=f.name):
                self.assertRegex(body, r"\n    def test_",
                                 f"{f.name} defines no test method above its "
                                 "__main__ block")


if __name__ == "__main__":
    unittest.main()
