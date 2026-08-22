"""Documentation that can go stale is derived, not restated.

TEST_MATRIX.md was a review written 2026-08-02 with updates bolted on. By
2026-08-22 its header said "116 tests, 14 files" over a suite of 1605
tests in 86 files, and it named 15 of them. Nothing failed — a stale
document never does, which is exactly why it had drifted that far.

The same rule the wizard's step numbers got: derive the fact, assert the
document matches. A doc that cannot rot silently is worth more than one
that is accurate today.
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TheTestMatrixIsGenerated(unittest.TestCase):

    def test_the_committed_file_matches_the_generator(self):
        from scripts import test_matrix
        committed = (ROOT / "docs" / "TEST_MATRIX.md").read_text(encoding="utf-8")
        self.assertEqual(
            test_matrix.build(), committed,
            "docs/TEST_MATRIX.md is stale — run "
            "`python -m scripts.test_matrix`")

    def test_the_count_is_stable_wherever_it_runs(self):
        """Two earlier attempts failed here. `def test_` undercounts by 8
        (a base class's tests run once per subclass); unittest discovery
        is exact but context-sensitive, so the same generator produced
        different totals inside and outside a test run — which makes a
        self-asserting document impossible to keep green. The AST count
        is the same everywhere, which is what this file needs."""
        from scripts import test_matrix
        a = test_matrix.counts(ROOT / "tests")
        b = test_matrix.counts(ROOT / "tests")
        self.assertEqual(a, b)
        self.assertGreater(sum(a.values()), 1000, "the sweep still sees the suite")

    def test_every_suite_file_says_what_it_holds(self):
        """A row reading "—" is a suite nobody can find by purpose."""
        from scripts import test_matrix
        blank = [r["file"] for folder in (ROOT / "tests",
                                          ROOT / "storefront" / "tests")
                 for r in test_matrix.scan(folder) if r["purpose"] == "—"]
        self.assertEqual(blank, [], "these test files have no docstring")


class TheArchitectureNamesEveryModule(unittest.TestCase):
    """A module absent from the map is a module the next reader does not
    know exists — nine of them were, including the one that decides which
    cinematography grammar rides a render."""

    def test_no_app_module_is_undocumented(self):
        arch = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        missing = [f.name for f in sorted((ROOT / "app").glob("*.py"))
                   if f.name not in ("__init__.py", "__main__.py")
                   and f"`{f.name}`" not in arch]
        self.assertEqual(missing, [], "modules missing from ARCHITECTURE.md")


if __name__ == "__main__":
    unittest.main()
