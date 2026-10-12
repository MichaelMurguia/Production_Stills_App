"""Every storefront test file imports _offline, so no test reaches the
network. See tests/_offline.py for the hang this prevents."""
import _offline  # noqa: F401 — no real network in tests
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent


class EveryTestFileIsOffline(unittest.TestCase):
    def test_each_file_imports_the_guard(self):
        missing = [p.name for p in sorted(HERE.glob("test_*.py"))
                   if "import _offline" not in p.read_text(encoding="utf-8")]
        self.assertEqual(missing, [])

    def test_the_probe_is_stubbed(self):
        from app import provisioner
        self.assertFalse(provisioner._domain_serves("example.invalid"))


if __name__ == "__main__":
    unittest.main()
