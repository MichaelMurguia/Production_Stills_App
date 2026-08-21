"""No control bytes in source. A standing contract, not a style rule.

Twice now a regex written as `\\b` has reached a source file as byte 0x08 —
a real backspace — because it was authored through a shell heredoc that
ate the backslash. The result is a pattern that compiles, runs, raises
nothing, and silently never matches:

  app/insights.py       `\\b[A-Z][A-Z0-9'-]{2,}\\b`  — the digest never
                        reported a shouted prop, and the absence looked
                        exactly like a screenplay that had none.
  app/static/
    tutorial-admin.js   `/^id\\b/i` — the editor's Save-error classifier
                        stopped labelling ID problems.

Neither failed a test, because both failures are *silence*. This file
makes the byte itself the failure.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

TREES = ("app", "tests", "storefront", "docs")
SUFFIXES = {".py", ".js", ".json", ".css", ".html", ".md"}
# Tab, newline and carriage return are the only C0 codes source may hold.
ALLOWED = {0x09, 0x0A, 0x0D}


def _sources():
    for tree in TREES:
        base = ROOT / tree
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.suffix.lower() in SUFFIXES and f.is_file():
                yield f


class SourceHoldsNoControlBytes(unittest.TestCase):
    def test_no_c0_control_characters_anywhere(self):
        found = []
        for f in _sources():
            try:
                text = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for i, ch in enumerate(text):
                if ord(ch) < 32 and ord(ch) not in ALLOWED:
                    line = text.count("\n", 0, i) + 1
                    found.append(
                        f"{f.relative_to(ROOT)}:{line} holds {hex(ord(ch))} — "
                        f"{text.splitlines()[line - 1].strip()[:70]!r}")
        self.assertEqual(
            found, [],
            "control bytes in source (a `\\b` regex written through a shell "
            "heredoc becomes a real backspace and the pattern silently stops "
            "matching):\n  " + "\n  ".join(found))

    def test_the_two_regexes_that_were_eaten_are_word_boundaries(self):
        """Named explicitly, so a revert reads as a revert."""
        ins = (ROOT / "app" / "insights.py").read_text(encoding="utf-8")
        self.assertIn(r"""re.findall(r"\b[A-Z][A-Z0-9'-]{2,}\b", t)""", ins)
        adm = (ROOT / "app" / "static" / "tutorial-admin.js").read_text(
            encoding="utf-8")
        self.assertIn(r"/^id\b/i.test(l)", adm)


if __name__ == "__main__":
    unittest.main()
