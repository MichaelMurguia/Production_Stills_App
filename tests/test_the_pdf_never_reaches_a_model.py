"""The raw upload is for the user to read. Models get extracted text.

User ruling 2026-08-02, restated 2026-08-28: "we have explicitly
converted PDFs to text, and I want to make sure we are still doing that,
period. Processing a PDF with AI is extremely expensive."

The cost is not marginal. PDFs bill per PAGE on every pass, and this app
sends the screenplay on five of them — the design plan, the faction
self-check, the Bible draft, naming the acts, and every breakdown draft.
A 207 KB PDF against 54,316 characters of extracted text, re-sent on
every run and every redraft, is the difference between a caching text
prompt and a per-page bill each time.

The guard is at the SOURCE and it refuses rather than falling back. That
matters more than the branch counting: a silent fallback to the upload is
what used to happen, and it was invisible at the moment it happened.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import autofill  # noqa: E402


class TheSourceReturnsTextOrRefuses(unittest.TestCase):
    def bytes_for(self, extracted):
        from app import store
        was_state, was_text = store.load_app_state, store.screenplay_text_cached
        try:
            store.load_app_state = lambda: {"screenplay": {"file": "s.pdf"}}
            store.screenplay_text_cached = lambda: extracted
            return autofill._screenplay_bytes()
        finally:
            store.load_app_state, store.screenplay_text_cached = was_state, was_text

    def test_extracted_text_is_what_goes_out(self):
        doc, mime = self.bytes_for("INT. SALT PANS - NIGHT\n\nAvrel waits.\n")
        self.assertEqual(mime, "text/plain")
        self.assertIn(b"SALT PANS", doc)

    def test_no_text_REFUSES_rather_than_sending_the_upload(self):
        """A silent fallback billed a PDF per page on every scan, draft
        and redraft — the exact cost the extracted text exists to avoid,
        and invisible at the moment it happened."""
        for empty in ("", "   ", "\n\n"):
            with self.assertRaises(autofill.AutofillError) as e:
                self.bytes_for(empty)
            msg = str(e.exception)
            self.assertIn("never sent to a model", msg)
            self.assertIn("image-only PDF", msg)

    def test_the_refusal_names_the_fix(self):
        with self.assertRaises(autofill.AutofillError) as e:
            self.bytes_for("")
        self.assertIn("re-export the screenplay", str(e.exception))

    def test_no_screenplay_is_its_own_refusal(self):
        from app import store
        was = store.load_app_state
        try:
            store.load_app_state = lambda: {}
            with self.assertRaises(autofill.AutofillError):
                autofill._screenplay_bytes()
        finally:
            store.load_app_state = was


class EveryPassSourcesItsDocumentFromThere(unittest.TestCase):
    """Five passes carry the screenplay. Each must get its bytes from the
    one guarded function — a sixth that read the file itself would bypass
    every protection above."""

    WIZ = (ROOT / "app/wizard.py").read_text(encoding="utf-8")
    AF = (ROOT / "app/autofill.py").read_text(encoding="utf-8")

    def test_the_wizard_passes_use_it(self):
        # design plan, faction self-check, bible draft, name the acts
        self.assertEqual(self.WIZ.count("_screenplay_bytes()"), 4)

    def test_the_breakdown_draft_uses_it(self):
        self.assertIn("doc, mime = _screenplay_bytes()", self.AF)

    def test_a_pasted_section_is_text_too(self):
        """The other document source: a section the user pasted."""
        self.assertIn('source_text.strip().encode("utf-8"), "text/plain"', self.AF)

    def test_nothing_else_opens_the_upload_for_a_model(self):
        """`/api/screenplay/file` serves the original for the USER to
        read, and its docstring says the pipeline never consumes it."""
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = main.index("def api_screenplay_file()")
        self.assertIn("models get the extracted text", main[i:i + 400])


class ProbedAgainstARealPdf(unittest.TestCase):
    """Read-the-code is how the old fallback survived. This runs the
    passes with the transport blocked and inspects what would have gone
    out."""

    def sent_by(self, run):
        seen = []

        def spy(provider, doc, mime, instructions):
            seen.append({"mime": mime, "doc": doc})
            raise RuntimeError("STOP — transport blocked")

        was = autofill._draft
        autofill._draft = spy
        try:
            run()
        except RuntimeError as e:
            if "STOP" not in str(e):
                raise
        finally:
            autofill._draft = was
        return seen

    def setUp(self):
        from app import store
        self._state, self._text = store.load_app_state, store.screenplay_text_cached
        store.load_app_state = lambda: {"screenplay": {"file": "ANCESTOR.pdf"}}
        store.screenplay_text_cached = lambda: "INT. SALT PANS - NIGHT\n\nAvrel waits.\n"

    def tearDown(self):
        from app import store
        store.load_app_state, store.screenplay_text_cached = self._state, self._text

    def test_the_design_plan_sends_text(self):
        from app import wizard
        sent = self.sent_by(lambda: wizard.analyze_screenplay("gemini"))
        self.assertTrue(sent)
        self.assertEqual(sent[0]["mime"], "text/plain")
        self.assertNotEqual(sent[0]["doc"][:5], b"%PDF-")

    def test_naming_the_acts_sends_text(self):
        from app import wizard
        sent = self.sent_by(lambda: wizard.name_acts("gemini"))
        self.assertTrue(sent)
        self.assertEqual(sent[0]["mime"], "text/plain")

    def test_the_faction_check_sends_text(self):
        from app import wizard
        sent = self.sent_by(lambda: wizard.faction_self_check(
            {"design_worlds": [{"name": "X"}]}, "gemini"))
        self.assertTrue(sent)
        self.assertEqual(sent[0]["mime"], "text/plain")

    def test_a_pdf_mime_is_never_produced_by_any_screenplay_path(self):
        """The transports still carry `application/pdf` branches. Nothing
        in this app can reach them, and this is the assertion that says
        so — if a future caller starts producing that mime, this fails."""
        import re
        for f in ("app/wizard.py", "app/autofill.py"):
            src = (ROOT / f).read_text(encoding="utf-8")
            produced = re.findall(r'mime\s*=\s*"([^"]+)"', src)
            self.assertNotIn("application/pdf", produced, f)


if __name__ == "__main__":
    unittest.main()
