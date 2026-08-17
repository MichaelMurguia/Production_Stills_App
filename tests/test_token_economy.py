"""What a model call costs, and what happens when it runs out.

Adversarial review F17, F20, F11.

- `INTENT.md` claims prompt caching is "engaged by keeping the screenplay
  as the stable prompt prefix". True for OpenAI and Gemini, whose caching
  is automatic. False for Anthropic, whose caching is opt-in per block and
  where no breakpoint was ever set — so every pass billed the ~131 KB
  screenplay (~33k tokens) at full input rate, on every scene scan,
  breakdown draft, re-draft and bible draft.
- `MAX_OUTPUT_TOKENS = 8192` capped the path that produces the app's
  largest structured output. On overflow the whole input was paid for and
  nothing came back — and the retry re-sent the screenplay, on the one
  provider where that input was uncached.
- The truncated reply surfaced as `Expecting ',' delimiter: line 1 column
  91`, because the recovery `json.loads` sat outside any try.

The inverse case matters as much as the waste: under-spending output
tokens to save pennies costs a full input pass."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TheScreenplayIsCached(unittest.TestCase):
    def _send(self, doc=b"SCREENPLAY BODY", mime="text/plain", refs=()):
        from app import narrative
        sent = {}

        def fake_http(url, method=None, headers=None, body=None, timeout=None):
            sent.update(body or {})
            return {"content": [{"type": "text", "text": '{"ok":1}'}],
                    "stop_reason": "end_turn"}

        real = narrative.anthropic_key
        narrative.anthropic_key = lambda: "k"
        try:
            narrative.anthropic_complete(doc, mime, "INSTRUCTIONS", refs, fake_http)
        finally:
            narrative.anthropic_key = real
        return sent["messages"][0]["content"]

    def test_the_screenplay_block_carries_a_breakpoint(self):
        blocks = self._send()
        self.assertEqual(blocks[0].get("cache_control"), {"type": "ephemeral"})

    def test_the_instructions_stay_outside_the_cached_prefix(self):
        """They vary per call; caching them would make every call a miss."""
        blocks = self._send()
        self.assertIsNone(blocks[-1].get("cache_control"))
        self.assertEqual(blocks[-1]["text"], "INSTRUCTIONS")

    def test_a_pdf_document_is_cached_too(self):
        blocks = self._send(doc=b"%PDF-1.4", mime="application/pdf")
        self.assertEqual(blocks[0]["type"], "document")
        self.assertEqual(blocks[0].get("cache_control"), {"type": "ephemeral"})

    def test_the_breakpoint_is_the_last_stable_block(self):
        """With reference images the prefix runs screenplay → images →
        breakpoint → instructions, so the images are cached as well."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.png"
            p.write_bytes(b"\x89PNG\r\n\x1a\n")
            blocks = self._send(refs=(p,))
        self.assertEqual(blocks[-2]["type"], "image")
        self.assertEqual(blocks[-2].get("cache_control"), {"type": "ephemeral"})
        self.assertIsNone(blocks[0].get("cache_control"),
                          "only ONE breakpoint — it covers everything before it")


class TheOutputCeilingIsNotTheCheapPlace(unittest.TestCase):
    def test_the_ceiling_is_raised_off_8192(self):
        from app import narrative
        self.assertGreaterEqual(narrative.MAX_OUTPUT_TOKENS, 16000)

    def test_the_other_providers_still_set_none(self):
        """The cap was unique to Anthropic, which is what made it a
        surprise rather than a policy."""
        auto = (ROOT / "app/autofill.py").read_text(encoding="utf-8")
        i = auto.index("def _draft_gemini")
        self.assertNotIn("max_output_tokens", auto[i:i + 700])

    def test_a_cut_off_reply_is_named_not_guessed(self):
        from app import narrative
        real = narrative.anthropic_key
        narrative.anthropic_key = lambda: "k"

        def fake_http(url, method=None, headers=None, body=None, timeout=None):
            return {"content": [{"type": "text", "text": '{"partial":'}],
                    "stop_reason": "max_tokens"}
        try:
            with self.assertRaises(narrative.NarrativeError) as cm:
                narrative.anthropic_complete(b"x", "text/plain", "i", (), fake_http)
        finally:
            narrative.anthropic_key = real
        msg = str(cm.exception)
        self.assertIn("cut off", msg)
        self.assertIn("re-sends the whole screenplay", msg,
                      "the retry cost is the actionable half")

    def test_an_empty_reply_at_the_ceiling_says_which_failure_it_was(self):
        from app import narrative
        real = narrative.anthropic_key
        narrative.anthropic_key = lambda: "k"

        def fake_http(url, method=None, headers=None, body=None, timeout=None):
            return {"content": [], "stop_reason": "max_tokens"}
        try:
            with self.assertRaises(narrative.NarrativeError) as cm:
                narrative.anthropic_complete(b"x", "text/plain", "i", (), fake_http)
        finally:
            narrative.anthropic_key = real
        self.assertIn("output", str(cm.exception).lower())


class ATruncatedReplySaysSo(unittest.TestCase):
    def test_a_reply_with_no_closing_brace(self):
        from app.autofill import AutofillError, _parse_json
        with self.assertRaises(AutofillError) as cm:
            _parse_json('{"subject": "x", "panels": [{"id": "P01", "title": "The over')
        self.assertIn("cut off", str(cm.exception))

    def test_a_reply_that_closes_a_nested_object_but_not_the_whole(self):
        """The shape that used to escape the guard entirely, because the
        recovery json.loads sat outside any try."""
        from app.autofill import AutofillError, _parse_json
        with self.assertRaises(AutofillError) as cm:
            _parse_json('{"a": {"b": 1}, "panels": [{"id": "P01", "title": "The over')
        self.assertIn("cut off", str(cm.exception))

    def test_it_says_a_retry_will_not_help(self):
        from app.autofill import AutofillError, _parse_json
        with self.assertRaises(AutofillError) as cm:
            _parse_json('{"a": 1')
        self.assertIn("will stop at the same place", str(cm.exception))

    def test_a_genuinely_non_json_reply_still_says_that(self):
        """A refusal is a different failure and must not be mislabelled."""
        from app.autofill import AutofillError, _parse_json
        with self.assertRaises(AutofillError) as cm:
            _parse_json("I cannot help with that request.")
        self.assertIn("did not return valid JSON", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
