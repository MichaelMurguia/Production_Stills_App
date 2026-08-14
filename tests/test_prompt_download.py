"""The compiled-prompt download (user 2026-08-06).

A 16,000-character prompt is a file, not a clipboard payload. The header
must carry what the prompt body does not — engine, size, and WHICH
references were attached, because "the render ignored my reference" is
answered by that list and nothing else.

These assert the source, since the download itself is a browser Blob:
the button exists, the handler builds the header from the candidate
record, and the record actually carries what the header claims."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def _dl_handler() -> str:
    """The download handler, wherever it lives. STEP_SEQUENCE_SPEC moved the
    compiled prompt off the provenance rail and into step 05, and its acts
    travelled with it — a verb belongs with its object."""
    h = JS[JS.index('$("[data-f=dl]", report).onclick'):]
    return h[:h.index("toast(")]


class PromptDownloadTests(unittest.TestCase):
    def test_the_button_sits_with_the_other_prompt_acts(self):
        self.assertIn('data-f="dl"', JS)
        self.assertIn(">Download</button>", JS)
        # Copy and Download are peers in the prompt's reading view. Expand
        # and Full retired with the rail block: the reading view IS the
        # expansion, and a height toggle on a full-height pre said nothing.
        row = JS[JS.index('data-f="copy"'):JS.index('data-f="dl"') + 260]
        for act in ("copy", "dl"):
            self.assertIn(f'data-f="{act}"', row)
        self.assertIn("close-report", row, "the reading view still closes")

    def test_the_header_states_the_render_conditions(self):
        h = _dl_handler()
        for fact in ("p.id", "specId", "c?.model", "c?.image_size",
                     "c?.created_at", "c?.status"):
            self.assertIn(fact, h, f"the header must record {fact}")

    def test_it_names_the_attached_references_or_says_there_were_none(self):
        h = _dl_handler()
        self.assertIn("c?.references", h)
        self.assertIn("Attached references — none", h)
        self.assertIn("style", h.lower(),
                      "the empty case must say what it DID render from")

    def test_it_downloads_markdown_named_for_the_take(self):
        h = _dl_handler()
        self.assertIn("text/markdown", h)
        self.assertIn("c?.candidate_id", h)
        self.assertIn(".md", h)
        self.assertIn("revokeObjectURL", h, "the blob url must be released")


class CandidateRecordTests(unittest.TestCase):
    """The header can only be honest if the record carries these."""

    def test_a_candidate_records_what_anchored_it(self):
        gen = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        m = re.search(r'"references":\s*\[', gen)
        self.assertIsNotNone(
            m, "candidates must persist the references attached to them — "
               "without it the download's header would be a guess")


if __name__ == "__main__":
    unittest.main()
