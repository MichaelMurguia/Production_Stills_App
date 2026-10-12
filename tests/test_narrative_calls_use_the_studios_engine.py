"""Every narrative call with no provider named uses the studio's engine.

User-hit 2026-10-04 on an OpenAI-only studio: the three style-anchor cards
on stage 02 sat blank — "These are blank. Fix". The page asks for anchor
proposals on arrival without naming a provider, and the endpoint fell
back to gemini, which that studio holds no key for. The refusal is
deliberately silent on arrival (arriving is not asking for a model call),
so nothing said why.

The screenplay read already resolved the studio's narrative engine
(fixed 2026-08-20). Four other narrative endpoints still hardcoded
gemini. Now all five share `main._narrative_provider`, and this file
holds every one of them to it.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient  # noqa: E402

from app import wizard  # noqa: E402
import app.main as appmain  # noqa: E402
from test_app_api import _redirect_home, _restore_home  # noqa: E402

# endpoint, body, the wizard function it calls
CALLS = [
    ("/api/wizard/suggest-anchors", {}, "suggest_anchors"),
    ("/api/wizard/swatches", {}, "generate_swatches"),
    ("/api/wizard/acts", {}, "name_acts"),
    ("/api/bible/self-check", {"text": "## Palette\nwarm"}, "bible_self_check"),
    ("/api/wizard/analyze", {}, "analyze_screenplay"),
]


class AnOpenAIOnlyStudio(unittest.TestCase):
    def setUp(self):
        _redirect_home(Path(tempfile.mkdtemp(prefix="sb-narrprov-")))
        self.client = TestClient(appmain.app)
        r = self.client.post("/api/settings", json={"openai_api_key": "sk-proj-abc"})
        self.assertEqual(r.status_code, 200)

    def tearDown(self):
        _restore_home()

    def provider_used(self, path, body, fn):
        seen = []

        def fake(*args, **kw):
            seen.extend(a for a in args if a in ("openai", "gemini", "anthropic"))
            seen.extend(v for v in kw.values() if v in ("openai", "gemini", "anthropic"))
            return {}
        with mock.patch.object(wizard, fn, side_effect=fake):
            self.client.post(path, json=body)
        return seen

    def test_no_narrative_call_falls_back_to_an_engine_it_has_no_key_for(self):
        for path, body, fn in CALLS:
            with self.subTest(path):
                used = self.provider_used(path, body, fn)
                self.assertTrue(used, f"{path} never reached wizard.{fn}")
                self.assertEqual(used[0], "openai")

    def test_a_named_provider_still_wins(self):
        used = self.provider_used("/api/wizard/suggest-anchors",
                                  {"provider": "anthropic"}, "suggest_anchors")
        self.assertEqual(used[0], "anthropic")


class OneRuleInTheSource(unittest.TestCase):
    def test_no_narrative_endpoint_hardcodes_gemini_again(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        for fn in ("generate_swatches", "name_acts", "suggest_anchors",
                   "bible_self_check"):
            i = main.index(f".{fn}(" if fn == "name_acts" else f"wizard.{fn}")
            call = main[i:main.index("\n    except", i)]
            self.assertIn("_narrative_provider(body)", call, fn)


if __name__ == "__main__":
    unittest.main()
