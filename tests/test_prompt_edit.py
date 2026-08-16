"""Step 05's verb says "Read & edit" and both halves have to be true
(user-caught 2026-08-16: "there is a 'Read and Edit' button on the prompt,
but I cannot edit and save it").

The override existed end-to-end the whole time — `generate_panel` takes a
`render_prompt`, files the take as `prompt_source: "edited"`, and the take
card reads it back under "Edited render prompt". The only producer was
`Draft prose`. So the ONE text an image model actually receives, the
compiled prompt, was the one text in the app you could not correct.

What this pins: the body is a textarea, generating sends what is in it,
and unedited text is NOT sent as an override — otherwise a take made from
an untouched prompt files as hand-edited and freezes a copy of something
the panel still compiles."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def preview_block() -> str:
    """The whole preview handler, bounded by the next handler rather than by
    a character count — a fixed window silently stops covering the code it
    was written to pin as the block grows."""
    i = JS.index('$("[data-f=preview]", card).onclick')
    j = JS.index("// Composition check (2026-08-13)", i)
    return JS[i:j]


class TheCompiledPromptIsEditable(unittest.TestCase):
    def test_the_body_is_a_textarea_not_a_pre(self):
        b = preview_block()
        self.assertIn('data-f="prompt-edit"', b)
        self.assertIn("<textarea", b)
        self.assertNotIn('<pre style="white-space:pre-wrap;margin:0">', b,
                         "the read-only body the verb was lying about")

    def test_it_can_render_from_the_edited_text(self):
        b = preview_block()
        self.assertIn('data-f="generate-edited"', b)
        self.assertIn("runGenerate(e2.target", b)

    def test_unedited_text_is_not_sent_as_an_override(self):
        """`render_prompt` is an override with consequences: it is archived
        verbatim and the take is filed `edited`. Passing the untouched
        compile through it would claim a hand edit that never happened."""
        b = preview_block()
        self.assertIn("const inForce = (saved || r.compiled).trim();", b)
        self.assertIn('text === inForce ? "" : text', b)

    def test_reverting_is_offered(self):
        self.assertIn('data-f="revert"', preview_block())

    def test_copy_and_download_take_what_is_on_screen(self):
        """Both used to read the compiled `r.prompt`. With the box editable
        that is a file that lies about the take it names."""
        b = preview_block()
        self.assertIn('copyText(promptBox.value', b)
        self.assertIn("const shown = promptBox.value", JS,
                      "the download handler sits past the editor block")
        self.assertNotIn('copyText(r.prompt', b)


class TheStateIsReadableBeforeItIsHit(unittest.TestCase):
    def test_the_line_states_which_text_will_be_sent(self):
        b = preview_block()
        self.assertIn("UNEDITED · STEPS 01–04 COMPILE THIS", b)
        self.assertIn("EDITED · UNSAVED · THIS TAKE ONLY", b)

    def test_it_updates_while_you_type(self):
        b = preview_block()
        self.assertIn('promptBox.addEventListener("input", sayState)', b)
        self.assertIn("        sayState();", b, "and once on open, before any typing")

    def test_the_edited_state_is_amber_and_is_a_stage_not_a_decoration(self):
        """§ amber is a signal: while this reads EDITED, the compiled panel
        below is not what gets rendered. It is the state of the render."""
        self.assertIn('.report [data-f="edit-state"].edited { color: var(--accent); }',
                      CSS)

    def test_the_one_take_scope_is_stated_not_discovered(self):
        self.assertIn("Unsaved edits ride ONE take", preview_block())


class TheOverridePathIsUnchanged(unittest.TestCase):
    def test_the_backend_still_files_an_edited_take_as_edited(self):
        py = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        self.assertIn('"prompt_source": "edited" if override else "spec"', py)
        self.assertIn('record["render_prompt"] = override', py)

    def test_the_take_card_reads_an_edited_prompt_back(self):
        self.assertIn('c.prompt_source === "edited" ? "edited render prompt"', JS)


if __name__ == "__main__":
    unittest.main()
