"""C4 — a take can say what it was actually rendered from.

The record keeps two prompts and they are not the same thing. `prompt` is
the steps 01-04 compile at render time, kept as the governance record.
`render_prompt` is the text the image model received, present only when an
override rode — a saved panel prompt, or a one-take edit.

No screen showed either. "Preview prompt" reads the panel's CURRENT
compile, which for any take older than the last edit describes a render
that never happened.

Two days of the 2026-08-25 cinematography investigation were spent reading
`prompt` and reasoning about renders it had never described. Four
conclusions drawn from it were wrong, and the tests below exist so nobody
repeats that from the UI.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")


def handler() -> str:
    i = JS.index('const readSent = $("[data-f=read-sent]", card);')
    return JS[i:JS.index('const readCine = $(', i)]


class TheTakeSaysWhatItRenderedFrom(unittest.TestCase):
    def test_there_is_a_control_on_the_take(self):
        self.assertIn('data-f="read-sent"', JS)
        self.assertIn("shot-tag-prompt", JS)

    def test_the_tag_says_which_of_the_two_it_holds(self):
        """A hand-edited take and a compiled one must not look identical
        before you open them — that is the whole failure."""
        self.assertIn('staged.render_prompt ? "SENT \u2014 HAND-EDITED" '
                      ': "SENT \u2014 THE COMPILE"', JS)

    def test_the_sent_text_leads_when_one_exists(self):
        b = handler()
        self.assertIn("THE IMAGE MODEL RECEIVED THIS, VERBATIM:", b)
        self.assertLess(b.index("sent"), b.index("governance record"))

    def test_the_compile_is_shown_but_named_as_not_sent(self):
        """Keeping it matters — it is the governance record — but showing
        it without saying so is exactly how this went wrong."""
        b = handler()
        self.assertIn("It is NOT what was sent", b)

    def test_it_states_both_lengths(self):
        """1,782 against 19,094 is the single fact that would have ended
        the investigation two days earlier."""
        b = handler()
        self.assertIn("${sent.length} CHARACTERS SENT", b)
        self.assertIn("${compiled.length} COMPILED", b)

    def test_it_names_the_override_scope(self):
        """A take made from the panel's saved prompt is reproducible from
        the panel; a one-take edit is not."""
        self.assertIn("prompt_override_scope", handler())

    def test_a_take_with_no_prompt_says_so(self):
        self.assertIn("This take recorded no prompt.", handler())

    def test_the_record_still_keeps_both(self):
        """The UI change must not tempt anyone into storing only one."""
        self.assertIn('"prompt": prompt,', GEN)
        self.assertIn('record["render_prompt"] = override', GEN)
        self.assertIn('"prompt_source": "edited" if override else "spec"', GEN)

    def test_the_tag_is_not_amber(self):
        i = CSS.index(".shot-tag-prompt")
        self.assertNotIn("--accent", CSS[i:i + 220])


if __name__ == "__main__":
    unittest.main()
