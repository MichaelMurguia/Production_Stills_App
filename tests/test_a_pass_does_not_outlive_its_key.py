"""A stored test result must not outlive the credential it tested.

User-caught 2026-08-26: "It is not connecting to GPT auth — even though
tests ok before."

Both halves were true. `engine_tests` lives in settings.json and
persists, and the credential can stop being visible to a process without
that file changing at all: the dev loop blanks stored keys unless
`--keys` is passed, and it does so by making the process unable to SEE
them rather than by editing anything (which is the right design — a dev
guard that rewrote your keys would be worse than one that spends money).

So the Settings row read `SYNCED` from a test on 2026-08-16, beside an
engine this process held no key for, and every call failed. The screen
was read correctly. The screen was wrong.

Same fault as a take badge naming a framing that was not in its prompt:
a record describing an intention rather than the present fact.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

PASSED = {"ok": True, "at": "2026-08-16T16:19:26+00:00"}


class APassIsMarkedStaleWithoutAKey(unittest.TestCase):
    def creds(self, settings, env=None):
        import os
        was_load, was_env = generate.load_settings, dict(os.environ)
        generate.load_settings = lambda: settings
        for k in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
            os.environ[k] = (env or {}).get(k, "")
        try:
            return generate.engine_credentials()
        finally:
            generate.load_settings = was_load
            os.environ.clear()
            os.environ.update(was_env)

    def test_a_visible_key_keeps_its_pass_untouched(self):
        e = self.creds({"openai_api_key": "sk-real",
                        "engine_tests": {"openai": PASSED}})["openai"]
        self.assertTrue(e["configured"])
        self.assertEqual(e["last_test"], PASSED)

    def test_no_visible_key_marks_the_pass_stale(self):
        e = self.creds({"engine_tests": {"openai": PASSED}})["openai"]
        self.assertFalse(e["configured"])
        self.assertTrue(e["last_test"]["stale"])

    def test_the_result_is_kept_not_dropped(self):
        """When it ran and what it said is still worth reading. Only the
        claim that it describes now is removed."""
        e = self.creds({"engine_tests": {"openai": PASSED}})["openai"]
        self.assertTrue(e["last_test"]["ok"])
        self.assertEqual(e["last_test"]["at"], PASSED["at"])
        self.assertIn("the key was there when this ran", e["last_test"]["stale_why"])

    def test_it_applies_to_every_engine_that_shares_the_key(self):
        eng = self.creds({"engine_tests": {"openai": PASSED,
                                           "openai-chat": PASSED,
                                           "gemini": PASSED}})
        for pid in ("openai", "openai-chat", "gemini"):
            self.assertTrue(eng[pid]["last_test"]["stale"], pid)

    def test_an_env_key_is_still_a_key(self):
        """Blanking only the environment was never the whole guard, and a
        key from the environment is as real as one from settings."""
        e = self.creds({"engine_tests": {"openai": PASSED}},
                       env={"OPENAI_API_KEY": "sk-from-env"})["openai"]
        self.assertTrue(e["configured"])
        self.assertNotIn("stale", e["last_test"])

    def test_no_test_at_all_is_still_no_test(self):
        e = self.creds({"engine_tests": {}})["openai"]
        self.assertIsNone(e["last_test"])

    def test_a_failure_is_not_relabelled(self):
        """A key that failed its own test says so; losing that behind
        "no key here" would send someone to the wrong fix."""
        bad = {"ok": False, "at": PASSED["at"], "error": "401"}
        e = self.creds({"openai_api_key": "sk-real",
                        "engine_tests": {"openai": bad}})["openai"]
        self.assertEqual(e["last_test"], bad)


class TheRowSaysSo(unittest.TestCase):
    def test_stale_reads_as_no_key_not_as_synced(self):
        i = JS.index("const keyState = pid => {")
        seg = " ".join(JS[i:i + 1400].split())
        self.assertIn("if (e.last_test?.stale) return", seg)
        self.assertIn("NO KEY HERE — LAST TEST", seg)

    def test_it_is_checked_before_the_pass(self):
        """Order is the whole fix: `ok` is true on a stale record."""
        i = JS.index("const keyState = pid => {")
        seg = JS[i:i + 1400]
        self.assertLess(seg.index("e.last_test?.stale"),
                        seg.index('if (e.last_test?.ok) return ["ok", "SYNCED"]'))


if __name__ == "__main__":
    unittest.main()
