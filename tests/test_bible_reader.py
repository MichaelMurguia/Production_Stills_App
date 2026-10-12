"""The Bible is written as markdown and read as a document.

PRODUCTION_DESIGN_UI_PLAN §3.5, revised 2026-08-29, which calls this
"the ruling that matters most in this section":

    Storage and display are two different things.

The file stays exactly what it is — `context/01_ART_DIRECTION_BIBLE.md`,
written by `draft_bible`, parsed by heading, read by `generate.py` and
`bible.infer_selection`. Nothing here moves it into a database, stores
rendered HTML, or touches the heading vocabulary. What changes is that a
document about how a film looks stops being shown as a monospace
textarea by default.

Three views over ONE file. READING renders it. MARKDOWN is the literal
bytes, because that view exists to verify what the model will actually be
given and a re-render would defeat its only purpose. Edit writes back
verbatim.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def block(sel):
    return CSS.split(chr(10) + sel)[1].split("}")[0]


class ThreeViewsOverOneFile(unittest.TestCase):
    def test_reading_is_the_default(self):
        self.assertIn('data-v="reading"', HTML)
        i = JS.index("const syncBibleView =")
        self.assertIn('uiGet(BIBLE_VIEW_KEY, "reading")', JS[i:i + 600])

    def test_markdown_shows_the_literal_file(self):
        """Its only purpose is verifying what the model is given, so a
        re-render would defeat it. The textarea holds the file."""
        i = JS.index("const syncBibleView =")
        seg = JS[i:i + 700]
        self.assertIn('$("#style-bible")?.classList.toggle("hidden", v === "reading")', seg)
        self.assertIn('$("#bible-doc")?.classList.toggle("hidden", v !== "reading")', seg)

    def test_the_markdown_view_carries_the_parse_warning(self):
        # RULED 2026-10-07 (user): no on-page explanations or instructions. "SECTION HEADINGS
        # ARE PARSED — DO NOT RENAME" was an instruction; it and its toggle
        # are gone. The three views themselves are unchanged.
        self.assertNotIn('id="bible-md-note"', HTML)
        self.assertNotIn("DO NOT RENAME", HTML)
        i = JS.index("const syncBibleView =")
        self.assertNotIn("bible-md-note", JS[i:i + 700])
        self.assertIn('$("#bible-doc")?.classList.toggle("hidden", v !== "reading")',
                      JS[i:i + 700])

    def test_editing_forces_the_source_view(self):
        """You cannot edit a render. While editing there is one view."""
        i = JS.index("const syncBibleView =")
        seg = JS[i:i + 700]
        self.assertIn('const v = editing ? "edit"', seg)
        self.assertIn('$("#bible-views")?.classList.toggle("hidden", editing)', seg)

    def test_the_file_path_is_stated(self):
        self.assertIn("context/01_ART_DIRECTION_BIBLE.md", HTML)


def reader():
    """The reader, start to end: the section model, the body renderer and
    renderBibleDoc (2026-10-04 split it into three)."""
    i = JS.index("const BIBLE_LOOK =")
    return JS[i:JS.index("const slugify =", i)]


class TheRendererNeverMutatesTheFile(unittest.TestCase):
    """The plan's hard constraint. A renderer that writes is a second
    author of a document the whole pipeline parses."""

    def seg(self):
        return reader()

    def test_it_only_reads(self):
        s = self.seg()
        for write in ("putPrompt", "api(", "fetch(", ".value =", "PUT"):
            self.assertNotIn(write, s, write)

    def test_it_renders_into_its_own_host(self):
        self.assertIn('const host = $("#bible-doc")', self.seg())

    def test_the_source_textarea_is_untouched_by_it(self):
        self.assertNotIn("#style-bible", self.seg())


class ItSupportsOnlyWhatTheDrafterEmits(unittest.TestCase):
    """"No markdown feature beyond #/##/###, paragraphs, `**bold**` leads
    and `-` lists is used or supported." Every feature added here is one
    the drafter may then be tempted to use, and the file has to stay
    parseable by a heading walk."""

    def seg(self):
        return reader()

    def test_the_four_shapes_and_no_others(self):
        s = self.seg()
        for pattern in (r"^#\s+(.+)$", r"^##\s+(.+)$", r"^###\s+(.+)$", r"^[-*]\s+(.+)$"):
            self.assertIn(pattern, s, pattern)

    def test_no_table_or_code_fence_syntax(self):
        s = self.seg()
        for gone in ("```", "<table", "<code", "<pre"):
            self.assertNotIn(gone, s, gone)

    def test_a_bold_lead_is_a_label_not_emphasis(self):
        """`**Design language:**` names a field; the sentence after it is
        the answer. Grey lead, not bold ink."""
        i = JS.index("const bibleInline =")
        seg = JS[i:i + 700]
        self.assertIn('<span class="bd-lead">$1 —</span>', seg)

    def test_everything_is_escaped_before_it_is_rendered(self):
        """The file is user-editable and model-written. It is data."""
        i = JS.index("const bibleInline =")
        self.assertIn("let out = esc(t);", JS[i:i + 400])


class AnAvoidListIsASet(unittest.TestCase):
    def test_it_renders_as_chips(self):
        s = reader()
        self.assertIn('class="bd-chips"', s)
        self.assertIn("inAvoid", s)

    def test_only_under_an_avoid_heading(self):
        self.assertIn("inAvoid = /^avoid/i.test(", reader())


class ThePictureComesFromWhatTheProductionHas(unittest.TestCase):
    def test_a_language_shows_a_reference_scoped_to_it(self):
        i = JS.index("const bibleArt =")
        seg = JS[i:i + 900]
        self.assertIn("r.language", seg)

    def test_a_language_with_no_art_renders_as_prose_alone(self):
        """B3 — never a placeholder. A reserved shape that states nothing
        is worse than no shape."""
        self.assertIn("if (shot || swatches.length)", reader())

    def test_the_language_rule_lives_in_one_place(self):
        """A JS twin of `store.reference_language` would be free to drift
        from the one the renders actually use, so the server decides and
        the client reads."""
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        self.assertIn('r["language"] = store.reference_language(r)', main)
        self.assertNotIn("function refLanguage", JS)


class TheRailSaysWhereYouAreAndWhatWroteIt(unittest.TestCase):
    def test_the_index_is_built_from_the_same_headings_the_server_parses(self):
        i = JS.index("const renderBibleRail =")
        seg = JS[i:i + 1200]
        self.assertIn(r"/^##\s+(.+)$/", seg)

    def test_what_wrote_it_shows_the_anchors(self):
        i = JS.index("const renderBibleRail =")
        self.assertIn("AUTO_ATTACH_HEADS.map", JS[i:i + 1200])

    def test_an_empty_rail_states_the_gap(self):
        # RULED 2026-10-07 (user): no on-page explanations or instructions. Empty states are
        # short Courier labels.
        i = JS.index("const renderBibleRail =")
        seg = JS[i:i + 1600]
        self.assertIn("NO PICTURES YET", seg)
        self.assertNotIn("no anchor has a picture yet", seg)

    def test_the_rail_no_longer_lists_sections(self):
        """The index moved into the reader, where choosing a section shows
        it (2026-10-04). Two indexes would be two answers to one question."""
        i = JS.index("const renderBibleRail =")
        self.assertIn("idx.hidden = true", JS[i:i + 1600])


class TheDocumentKeepsItsOwnVoice(unittest.TestCase):
    def test_headings_are_archivo_and_not_the_chrome_s_caps(self):
        """`.panel h2` uppercases and letterspaces every heading in the
        app — right for a step label, wrong for a section of a document
        the drafter titled itself."""
        b = block(".bible-doc .bd-h2 {")
        self.assertIn("var(--sans)", b)
        self.assertIn("text-transform: none", b)
        self.assertIn("letter-spacing: normal", b)

    def test_prose_has_a_measure(self):
        """15.5px across a full workbench is a line nobody finishes."""
        self.assertIn("max-width: 68ch", block(".bible-doc {"))

    def test_a_kicker_is_courier(self):
        """Rule 2 — `###` is the machine's own sub-label."""
        self.assertIn("var(--mono)", block(".bible-doc .bd-kick {"))


class OneSectionAtATime(unittest.TestCase):
    """User 2026-10-04: "For humans looking at the interface, it should be
    a well-formatted, sectioned document." Ruled: an index, one section at
    a time, and each section editable on its own. The file is unchanged."""

    def test_the_index_groups_the_file_s_own_headings(self):
        r = reader()
        for label in ('"THE LOOK"', '"DESIGN LANGUAGES"', '"ENVIRONMENTS"', '"REFERENCE"'):
            self.assertIn(label, r)
        self.assertIn('h.title.toLowerCase() === "environments"', r)

    def test_selection_is_ink_never_amber(self):
        b = block(".bd-nav-item.on {")
        self.assertIn("var(--ink)", b)
        self.assertNotIn("accent", b)

    def test_a_section_save_goes_through_the_one_bible_save(self):
        i = JS.index("const bibleSaveSection =")
        seg = JS[i:i + 900]
        self.assertIn("await saveBible()", seg)
        self.assertIn("await loadBibleEditor()", seg)
        self.assertNotIn('api("/api/style-bible"', seg)

    def test_the_model_and_the_splice_on_a_real_bible(self):
        """Run the section model and the splice in Node against a Bible
        with globals, two languages, materials and environments."""
        import shutil
        import subprocess
        import textwrap
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        a = JS.index("  const BIBLE_LOOK =")
        model = JS[a:JS.index("  // A section's body as the drafter wrote it", a)]
        b = JS.index("  const bibleSaveSection =")
        splice = JS[b:JS.index("btn.disabled = true;", b)]
        prog = textwrap.dedent(r"""
          const slugify = t => String(t).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
          const getAnalysis = () => ({ design_worlds: [{ name: "Terran Concord" }, { name: "Oruna" }] });
          %MODEL%
          const TEXT = [
            "# Io — Art Direction Bible", "", "## Status", "Locked.", "",
            "## Overall Visual Identity", "- Lived-In.", "",
            "## Terran Concord", "Brass and marble.", "",
            "## Oruna", "Woven reed.", "",
            "## Core Material Language", "### Terran Concord", "- brass", "",
            "## Environments", "### NORTHERN COAST", "Storm light.", "", "### CITADEL", "Gold leaf.", ""
          ].join("\n");
          const m = bibleModel(TEXT);
          const groups = {};
          m.secs.forEach(x => (groups[x.group] = groups[x.group] || []).push(x.title));
          const oruna = m.secs.find(x => x.title === "Oruna");
          %SPLICE% return next; };
          const next = bibleSaveSection(m, oruna, "Woven reed on tidal flats.\n- stilts");
          console.log(JSON.stringify({ title: m.title, groups, next }));
        """)
        prog = prog.replace("%MODEL%", model).replace(
            "%SPLICE%", splice.replace("async (model, sec, body, btn)", "(model, sec, body, btn)"))
        out = subprocess.run([node, "-e", prog], capture_output=True, text=True,
                             encoding="utf-8", timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        import json as _json
        r = _json.loads(out.stdout)
        self.assertEqual(r["title"], "Io — Art Direction Bible")
        self.assertEqual(r["groups"]["look"], ["Overall Visual Identity"])
        self.assertEqual(r["groups"]["languages"], ["Terran Concord", "Oruna"])
        self.assertEqual(r["groups"]["environments"], ["NORTHERN COAST", "CITADEL"])
        self.assertEqual(r["groups"]["reference"], ["Status", "Core Material Language"])
        nxt = r["next"]
        self.assertIn("## Oruna\n\nWoven reed on tidal flats.\n- stilts\n\n## Core Material Language", nxt)
        self.assertNotIn("Woven reed.\n", nxt)
        self.assertIn("## Terran Concord\nBrass and marble.", nxt, "other sections untouched")
        self.assertIn("### CITADEL\nGold leaf.", nxt)


if __name__ == "__main__":
    unittest.main()
