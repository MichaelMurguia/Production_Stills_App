"""The four formats the app claims, actually read.

`PDF · FDX · FOUNTAIN · TXT` appears on the Status lead, the stage-01
empty state, the Replace card and the file picker's `accept`. Nothing
proved the app could read all four until 2026-08-20, and it could not
read one of them WELL: Final Draft is XML, and every non-PDF file was
decoded as raw text — so an .fdx reached the models as markup, three
times the characters for the same script, against this module's own rule
that import converts once to the efficient format.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import insights, paths, store  # noqa: E402

SCENES = [
    "INT. ORBITAL RELAY - MAINTENANCE BAY - NIGHT", "",
    "Cold light. VERA works a panel loose.", "",
    "EXT. RELAY HULL - CONTINUOUS", "",
    "The station turns against a dead planet.", "",
    "INT. ORBITAL RELAY - GALLEY - DAY", "",
    "MARCUS pours coffee.", "",
]


def fdx_bytes() -> bytes:
    rows = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            '<FinalDraft DocumentType="Script" Template="No" Version="5">',
            "<Content>"]
    for line in SCENES:
        if not line:
            continue
        kind = "Scene Heading" if line.startswith(("INT.", "EXT.")) else "Action"
        rows.append(f'<Paragraph Type="{kind}"><Text>{line}</Text></Paragraph>')
    rows += ["</Content>", "</FinalDraft>"]
    return "\n".join(rows).encode("utf-8")


def pdf_bytes() -> bytes:
    """A minimal text PDF — not an image scan, which is the other case."""
    body = "".join(f"({l}) Tj 0 -16 Td\n" for l in SCENES if l)
    stream = f"BT /F1 11 Tf 40 740 Td\n{body}ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
            + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offs:
        out += f"{o:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n"
            f"{xref}\n%%EOF\n").encode()
    return bytes(out)


FILES = {
    "script.txt": "\n".join(SCENES).encode("utf-8"),
    "script.fountain": ("Title: The Quiet Shift\n\n" + "\n".join(SCENES)).encode("utf-8"),
    "script.fdx": fdx_bytes(),
    "script.pdf": pdf_bytes(),
}


class EveryClaimedFormatReads(unittest.TestCase):
    def setUp(self):
        self._home, self._slug = paths.HOME, paths.ACTIVE_PROJECT
        paths.HOME = pathlib.Path(tempfile.mkdtemp(prefix="sb-fmt-"))
        paths.set_project("")
        paths.ensure_dirs()

    def tearDown(self):
        paths.HOME = self._home
        paths.set_project(self._slug)

    def load(self, name):
        rec = store.set_screenplay(name, FILES[name])
        return rec, store.screenplay_text_cached()

    def test_each_format_extracts_text(self):
        for name in FILES:
            with self.subTest(name):
                rec, text = self.load(name)
                self.assertTrue(rec.get("text_chars"),
                                f"{name}: nothing extracted at import")
                self.assertIn("ORBITAL RELAY", text)

    def test_each_format_yields_the_same_scenes_to_the_parser(self):
        counts = {}
        for name in FILES:
            self.setUp()
            self.load(name)
            counts[name] = len(insights.locations())
        self.assertEqual(len(set(counts.values())), 1,
                         f"the formats disagree about the script: {counts}")
        self.assertGreaterEqual(min(counts.values()), 3, counts)

    def test_final_draft_is_read_as_a_script_not_as_markup(self):
        """The defect this file was written for. An .fdx that reaches a
        model as XML costs the customer three times the tokens for the
        same script, and every model call pays it again."""
        _, fdx = self.load("script.fdx")
        self.assertNotIn("<Paragraph", fdx)
        self.assertNotIn("<?xml", fdx)
        self.setUp()
        _, plain = self.load("script.txt")
        self.assertLess(len(fdx), len(plain) * 1.2,
                        "Final Draft should cost about what the plain text does")

    def test_an_unreadable_file_extracts_nothing_rather_than_guessing(self):
        """An image-only scan has no text layer. Empty is the documented
        signal — callers fall back to sending the original file."""
        rec = store.set_screenplay("scan.pdf", b"%PDF-1.4\nnot really a pdf\n")
        self.assertFalse(rec.get("text_chars"))


if __name__ == "__main__":
    unittest.main()
