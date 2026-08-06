"""Programmatic file pickers must be attached to the document.

Regression, 2026-08-06: "I selected import backup and got no feedback."
The Import handler built its `<input type="file">` with createElement and
called .click() on it without ever putting it in the page. A DETACHED file
input's click() is silently ignored by the browser — no picker, no error,
no console warning. Reproduced with a trusted mouse event over CDP: a
detached input produced zero Page.fileChooserOpened events, an attached
one produced exactly one.

Every other file field in this app is markup that already lives in the
page, which is why this was the first place it bit — and why nothing in
the suite would have caught it. These assertions are on the SOURCE,
because the failure is in the browser's response to a method call.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


class FilePickerTests(unittest.TestCase):
    def created_file_inputs(self) -> list[str]:
        """Each block from a `type = "file"` assignment to the click that
        opens its picker — the window in which it must be appended."""
        out = []
        for m in re.finditer(r'\.type\s*=\s*"file"', JS):
            tail = JS[m.start():m.start() + 1200]
            click = re.search(r"\w+\.click\(\)", tail)
            out.append(tail[:click.end()] if click else tail)
        return out

    def test_there_is_at_least_one_to_check(self):
        self.assertTrue(self.created_file_inputs(),
                        "no dynamically created file input found — if the "
                        "pattern moved, move this contract with it")

    def test_every_created_file_input_is_in_the_document_before_it_is_clicked(self):
        for block in self.created_file_inputs():
            with self.subTest(block=block[:80]):
                self.assertRegex(
                    block, r"append(Child)?\(\s*inp\s*\)|body\.append\(",
                    "a detached file input's click() opens nothing at all")

    def test_the_import_picker_cleans_itself_up(self):
        """It is display:none in the page, so it must not accumulate — one
        orphan per cancelled import would be invisible and unbounded."""
        block = next(b for b in self.created_file_inputs() if ".zip" in b)
        self.assertIn("inp.oncancel", block,
                      "cancelling the picker fires cancel, not change")
        after = JS[JS.index(block):JS.index(block) + 2000]
        self.assertIn("inp.remove()", after)

    def test_blob_downloads_attach_their_anchor_too(self):
        """Same class of bug for <a download>: a detached anchor's click is
        ignored in some browsers. Both download paths append first."""
        anchors = re.findall(r'createElement\("a"\)(.{0,700}?)\.click\(\)', JS, re.S)
        self.assertGreaterEqual(len(anchors), 2, "expected the backup and prompt downloads")
        for a in anchors:
            self.assertIn("append(a)", a)


if __name__ == "__main__":
    unittest.main()
