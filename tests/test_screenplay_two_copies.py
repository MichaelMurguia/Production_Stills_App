"""Two copies of the screenplay, and only one of them costs money
(user rule, 2026-08-16).

A production keeps the original upload — a PDF, usually — and the text
extracted from it. **The extracted text is the only one a model ever
sees.** The original exists so the user can open and read it, and that is
its whole job. Sending a PDF instead bills a page at a time on every
scan, every draft and every redraft, and the extracted text of a feature
is a fraction of it: 131 KB against 339 KB on the draft this rule was
written against.

The rule is absolute because the failure was silent. A screenplay that
extracted badly would quietly switch every future call to the expensive
format with nothing on screen to say so."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import autofill, paths, store  # noqa: E402


class TheModelOnlyEverSeesTheText(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-scr-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR,
                       paths.ACTIVE_PROJECT_FILE, paths.SETTINGS,
                       paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        paths.SCREENPLAY_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plant(self, *, text: str) -> Path:
        pdf = paths.SCREENPLAY_DIR / "draft.pdf"
        pdf.write_bytes(b"%PDF-1.4 not really a pdf")
        if text:
            (paths.SCREENPLAY_DIR / "_extracted.txt").write_text(
                text, encoding="utf-8")
        state = store.load_app_state()
        rec = {"file": "draft.pdf", "sha256": "abc123"}
        if text:
            # what store.set_screenplay records once the extraction runs
            rec["text_file"] = "_extracted.txt"
            rec["text_chars"] = len(text)
        state["screenplay"] = rec
        store.save_app_state(state)
        return pdf

    def test_the_extracted_text_is_what_goes_out(self):
        self.plant(text="INT. SHACK - DAY\nA stove.\n")
        doc, mime = autofill._screenplay_bytes()
        self.assertEqual(mime, "text/plain")
        self.assertIn(b"INT. SHACK", doc)
        self.assertNotIn(b"%PDF", doc)

    def test_the_original_is_never_sent_even_when_the_text_is_missing(self):
        """The silent fallback this replaces switched every future call to
        the expensive format with nothing on screen to say so."""
        self.plant(text="")
        with self.assertRaises(autofill.AutofillError) as e:
            autofill._screenplay_bytes()
        msg = str(e.exception)
        self.assertIn("image-only", msg)
        self.assertIn("never sent to a model", msg)

    def test_the_refusal_names_the_way_through(self):
        self.plant(text="")
        with self.assertRaises(autofill.AutofillError) as e:
            autofill._screenplay_bytes()
        msg = str(e.exception)
        self.assertIn("re-export", msg)
        self.assertIn(".txt", msg)

    def test_no_model_facing_path_reads_the_raw_file(self):
        """One reader is allowed: the route that hands the file to the
        USER. Anything else that opens it is a cost leak."""
        for mod in ("autofill.py", "wizard.py", "generate.py", "insights.py"):
            src = (ROOT / "app" / mod).read_text(encoding="utf-8")
            self.assertNotIn("SCREENPLAY_DIR / rec[", src, mod)

    def test_the_user_facing_route_still_serves_it(self):
        src = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = src.index("def api_screenplay_file()")
        seg = src[i:i + 700]
        self.assertIn("SCREENPLAY_DIR / rec[", seg)
        self.assertIn("inline", seg, "so it opens rather than downloads")
        self.assertIn("never consumes this", src[i - 300:i + 300],
                      "and says why it exists")


class BothCopiesSurviveABackup(unittest.TestCase):
    def test_the_backup_carries_the_readable_original_too(self):
        """A restore that lost the PDF would leave the user unable to read
        their own screenplay, even though the pipeline would still run.
        The backup takes whole directories, and both copies live under
        data/screenplay/ — so neither can be dropped by accident."""
        src = (ROOT / "app/backup.py").read_text(encoding="utf-8")
        self.assertIn('BACKUP_DIRS = ("data", "project_state", "context")', src)
        self.assertIn("data/settings.json", src,
                      "the one thing a backup deliberately excludes")


if __name__ == "__main__":
    unittest.main()
