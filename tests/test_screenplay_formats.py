"""The five formats the app claims, actually read.

`PDF · FDX · FOUNTAIN · TXT · HTML` appears on the Status lead, the stage-01
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


def imsdb_bytes() -> bytes:
    """A script archive page: the script in one <pre>, wrapped in the
    site's menus, scripts and footer — the shape most saved web scripts
    have."""
    menu = "".join(f'<td><a href="/genre/{g}">{g}</a></td>'
                   for g in ("Action", "Drama", "Sci-Fi", "Thriller"))
    body = "\n".join(SCENES).replace("VERA", "<b>VERA</b>")
    return (
        '<html><head><meta http-equiv="Content-Type" '
        'content="text/html; charset=utf-8"><title>The Quiet Shift Script</title>'
        '<style>td{font:12px Arial}</style><script>var ad = "INT. NOWHERE - DAY";</script>'
        f'</head><body><table><tr>{menu}</tr></table><nav>Home &gt; Scripts</nav>'
        f'<table><tr><td class="scrtext"><pre>{body}</pre></td></tr></table>'
        '<footer>&copy; Script Archive. All rights reserved.</footer></body></html>'
    ).encode("utf-8")


FILES = {
    "script.txt": "\n".join(SCENES).encode("utf-8"),
    "script.fountain": ("Title: The Quiet Shift\n\n" + "\n".join(SCENES)).encode("utf-8"),
    "script.fdx": fdx_bytes(),
    "script.pdf": pdf_bytes(),
    "script.html": imsdb_bytes(),
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

    def test_a_web_page_is_read_as_a_script_not_as_a_page(self):
        """The site around the script is billed on every model call if it
        survives import. The <pre> is the script; the rest goes."""
        _, html = self.load("script.html")
        for leftover in ("<pre", "<b>", "Thriller", "Home > Scripts",
                         "All rights reserved", "var ad", "INT. NOWHERE",
                         "font:12px"):
            self.assertNotIn(leftover, html)
        self.assertIn("Cold light. VERA works a panel loose.", html)
        self.setUp()
        _, plain = self.load("script.txt")
        self.assertLess(len(html), len(plain) * 1.2,
                        "a saved web page should cost about what the plain text does")

    def test_pre_keeps_its_indentation(self):
        """In an archive script the indentation IS the structure — a
        character cue is the line indented furthest."""
        page = ("<html><body><pre>INT. GALLEY - DAY\n\n"
                "                         MARCUS\n"
                "               Coffee's cold.\n</pre></body></html>")
        rec = store.set_screenplay("cue.htm", page.encode("utf-8"))
        self.assertTrue(rec.get("text_chars"))
        self.assertIn("\n                         MARCUS\n",
                      store.screenplay_text_cached())

    def test_an_export_without_pre_reads_as_paragraphs(self):
        """Writing tools export one element per block and style the
        heading with CSS. The heading must reach the parser in capitals,
        each element on its own line, with entities decoded."""
        rows = []
        for line in SCENES:
            if not line:
                continue
            if line.startswith(("INT.", "EXT.")):
                rows.append(f'<p class="scene-heading">{line.lower()}</p>')
            else:
                rows.append(f'<p class="action">{line} &amp; more&nbsp;here</p>')
        page = ('<!DOCTYPE html><html><head><style>.scene-heading'
                '{text-transform:uppercase}</style></head><body>'
                + "\n".join(rows) + "</body></html>")
        store.set_screenplay("export.html", page.encode("utf-8"))
        text = store.screenplay_text_cached()
        self.assertIn("\nINT. ORBITAL RELAY - GALLEY - DAY\n", text)
        self.assertIn("MARCUS pours coffee. & more here", text)
        self.assertNotIn("text-transform", text)
        exported = len(insights.locations()["locations"])
        self.setUp()
        self.load("script.txt")
        self.assertEqual(exported, len(insights.locations()["locations"]))

    def test_a_speech_sits_on_consecutive_lines(self):
        """The shape of a real styled export (DESCENDANT, 2026-10-04): the
        cue is CSS-capitalised, and a dialogue block's cue, parenthetical
        and line read as one speech, not three paragraphs."""
        page = ('<section class="scene"><div class="slug">int. galley — day</div>'
                '<div class="action">Steam.</div>'
                '<div class="dialogue-block"><div class="cue">Marcus '
                '<span class="cue-ext">(radio)</span></div>'
                '<div class="paren">(flat)</div>'
                '<div class="line">Coffee\'s cold.</div></div>'
                '<div class="action">He drinks it.</div></section>')
        store.set_screenplay("styled.html", page.encode("utf-8"))
        self.assertEqual(store.screenplay_text_cached(),
                         "INT. GALLEY — DAY\n\nSteam.\n\n"
                         "MARCUS (RADIO)\n(flat)\nCoffee's cold.\n\n"
                         "He drinks it.")

    def test_a_page_in_its_declared_charset(self):
        """Old archive pages are windows-1252. Decoded as UTF-8, every
        curly quote and dash in the script becomes U+FFFD."""
        page = ('<html><head><meta charset="windows-1252"></head><body><pre>'
                "INT. GALLEY — DAY\n\nMARCUS: “Cold.”</pre></body></html>")
        store.set_screenplay("old.html", page.encode("cp1252"))
        text = store.screenplay_text_cached()
        self.assertIn("“Cold.”", text)
        self.assertNotIn("�", text)

    def test_an_unreadable_file_extracts_nothing_rather_than_guessing(self):
        """An image-only scan has no text layer. Empty is the documented
        signal — callers fall back to sending the original file."""
        rec = store.set_screenplay("scan.pdf", b"%PDF-1.4\nnot really a pdf\n")
        self.assertFalse(rec.get("text_chars"))


if __name__ == "__main__":
    unittest.main()
