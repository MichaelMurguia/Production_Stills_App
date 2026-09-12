"""A character's own screen, and the verdict it asks for.

CAST_CHARACTER_SCREEN_2026-09-12, §1 and §2.

WHAT CHANGED. Generating a subject reference used to approve it on
arrival — the 2026-08-18 reading that asking for a picture IS the review.
That was true of a supplied plate, where the user had already seen the
picture, and false of a render, which nobody has seen when the call
returns. The plan puts **Accept / Reject** under the frame, so a render
lands PROVISIONAL and the screen asks.

THE EMPTY SCREEN is the one the user meets first and the plan specifies
hardest: a dashed 9:16 frame with `FULL BODY` on it, **Generate** (the
single amber primary) over **Attach**, and on the right the description
with a LARGE edit button — large because editing the words is the only
way to change a result; there is no adjust field — then the verbatim
lines the screenplay described this subject in, each with its page.

"Nothing else. No traits list, no scene table, no design-language row, no
'where this lives' line." Those were words the picture and the quotes
already carry.

WHAT IT COSTS. Nothing. The scenes tally and the quotes are derived from
the stored extraction and the page sidecar — one local walk, no model
call — so opening a card is free and the roster's counts come from a
single pass rather than one per card.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, insights, paths, store  # noqa: E402

CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
NL = chr(10)


def block(sel):
    return CSS.split(NL + sel)[1].split("}")[0]


def empty_screen():
    i = JS.index("const renderCastEmpty = (s, pending, refs, ev) => {")
    return JS[i:JS.index(NL + "  const renderCastAccepted", i)]


# --------------------------------------------------------------- §2 markup

class TheEmptyScreenIsTheFrameAndTheWords(unittest.TestCase):
    def test_the_header_names_the_kind_and_the_scene_count(self):
        i = JS.index("const castHead = (s, ev, mark, extra) => `")
        seg = JS[i:JS.index(NL + NL, i)]
        self.assertIn("&larr; Cast", seg)
        self.assertIn("${esc(s.kind)} &middot; ${ev.scenes} SCENE", seg)

    def test_the_name_is_24px(self):
        self.assertIn("font-size: 24px", block(".cd-name {"))

    def test_no_picture_is_the_one_amber_thing_on_it(self):
        """Amber marks the one thing asking for attention. §3 drops the
        mark entirely, because by then nothing is asking."""
        self.assertIn("var(--accent)", block(".cd-mark {"))
        self.assertIn('pending ? "AWAITING YOUR VERDICT" : "NO PICTURE"',
                      empty_screen())
        i = JS.index("const renderCastAccepted = (s, ok, refs, ev) => {")
        self.assertIn('castHead(s, ev, "", role.replaceAll("_", " "))',
                      JS[i:i + 900])

    def test_the_columns_are_280_and_the_rest(self):
        self.assertIn("grid-template-columns: 280px minmax(0, 1fr)",
                      block('.cast-detail[data-state="empty"] {'))

    def test_the_frame_is_one_dashed_nine_by_sixteen_slot(self):
        b = block(".cd-frame {")
        self.assertIn("aspect-ratio: .5625", b)     # 9:16
        self.assertIn("1px dashed", b)
        self.assertEqual(empty_screen().count('<div class="cd-frame${'), 1)

    def test_the_frame_is_kicked_and_expandable(self):
        seg = empty_screen()
        self.assertIn('class="cd-kick cd-frame-kick">FULL BODY<', seg)
        self.assertIn('class="cd-expand" data-f="expand"', seg)
        self.assertIn("&#10530;", seg)              # the expand glyph
        self.assertIn("cursor: zoom-in", block(".cd-frame.has {"))

    def test_generate_is_the_only_primary_and_attach_is_a_ghost(self):
        seg = empty_screen()
        self.assertEqual(seg.count('class="primary"'), 1)
        self.assertIn('class="primary" data-f="gen">Generate<', seg)
        self.assertIn('class="ghost" data-f="attach">Attach<', seg)

    def test_expand_states_that_there_is_nothing_to_expand(self):
        """B3: a control that cannot act says why, rather than acting on
        nothing."""
        self.assertIn('disabled title="Nothing to expand yet"', empty_screen())

    def test_the_edit_button_is_large_because_it_is_the_only_adjustment(self):
        """"There is no 'adjust' field — if the user wants a different
        result they edit the description and generate again, which is why
        the edit button is large.\""""
        b = block(".cd-edit {")
        self.assertIn("font-size: 15px", b)
        self.assertIn("border-color: var(--line-strong)", b)   # the plan's #6b7278
        self.assertIn('class="ghost cd-edit" data-f="edit">Edit description<', JS)

    def test_the_description_is_16px_over_1_6(self):
        b = block(".cd-desc {")
        self.assertIn("font-size: 16px", b)
        self.assertIn("line-height: 1.6", b)

    def test_the_quotes_carry_their_page_in_courier_beside_italic_prose(self):
        i = JS.index('${ev.quotes.length ? `<p class="cd-kick cd-kick2">SCREENPLAY</p>')
        seg = JS[i:i + 900]
        self.assertIn('P ${String(q.page).padStart(2, "0")}', seg)
        self.assertIn("<i>&ldquo;${esc(q.line)}&rdquo;</i>", seg)
        self.assertIn("var(--mono)", block(".cd-quote > .cd-page {"))
        self.assertIn("font-style: italic", block(".cd-quote > i {"))
        self.assertIn("border-left: 1px solid", block(".cd-quote {"))

    def test_a_text_draft_is_located_by_scene_rather_than_page_zero(self):
        """The page sidecar only exists for a PDF. `P 00` would read as a
        broken citation, and the scene ordinal is provenance the walk
        already has."""
        i = JS.index("const castWords = (s, ev) => `")
        seg = JS[i:i + 2200]
        self.assertIn('`SC ${String(q.scene || 0).padStart(2, "0")}`', seg)

    def test_a_draft_that_never_describes_them_says_so(self):
        """B3 again: an empty SCREENPLAY block would read as a bug."""
        i = JS.index("const castWords = (s, ev) => `")
        self.assertIn("there is nothing to quote", JS[i:i + 1800])

    def test_nothing_else_is_on_it(self):
        """The plan's list of cuts, asserted as cuts."""
        seg = empty_screen()
        for cut in ("WHAT RIDES EVERY PROMPT", "cd-trait", "APPEARS IN",
                    "LIVES ON", "RIDES AS", "cd-facts", "lang-card"):
            self.assertNotIn(cut, seg, cut)


# -------------------------------------------------------------- the verdict

class AcceptAndReject(unittest.TestCase):
    def test_both_are_inactive_until_a_picture_exists(self):
        seg = empty_screen()
        i = seg.index('<div class="cd-verdict">')
        row = seg[i:i + 400]
        self.assertIn('data-f="accept"', row)
        self.assertIn('data-f="reject"', row)
        self.assertEqual(row.count('${pending ? "" : "disabled"}'), 2)

    def test_they_are_only_wired_when_there_is_something_to_rule_on(self):
        seg = empty_screen()
        self.assertIn('if (pending) {', seg)
        self.assertIn('castRule(pending, "APPROVED")', seg)
        self.assertIn('castRule(pending, "REJECTED")', seg)

    def test_the_verdict_goes_to_the_reference_status_route(self):
        i = JS.index("const castRule = async (ref, status) => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn("/api/references/${ref.id}/status", seg)
        self.assertIn('json: { status, reason:', seg)

    def test_reject_says_what_to_do_next(self):
        """Rejecting without a next step leaves the user at an empty
        frame wondering what changed."""
        self.assertIn("Edit the description and generate again.", JS)

    def test_a_pending_picture_outranks_an_accepted_one(self):
        """A question left behind a filmstrip is a question nobody
        answers."""
        i = JS.index("const renderCastDetail = async (s, refs) => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertIn('const pending = all.find(r => r.status === "PROVISIONAL");', seg)
        self.assertIn("if (!pending && ok.length) return renderCastAccepted", seg)


class _Home(unittest.TestCase):
    """Never the real install."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._was = dict(HOME=paths.HOME, PROJECTS_DIR=paths.PROJECTS_DIR,
                         ACTIVE=paths.ACTIVE_PROJECT_FILE,
                         SETTINGS=paths.SETTINGS, slug=paths.ACTIVE_PROJECT)
        t = Path(self._tmp.name)
        paths.HOME = t
        paths.PROJECTS_DIR = t / "projects"
        paths.ACTIVE_PROJECT_FILE = t / "active_project.json"
        paths.SETTINGS = t / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        self._mock = generate.mock_enabled
        generate.mock_enabled = lambda: True

    def tearDown(self):
        generate.mock_enabled = self._mock
        paths.HOME = self._was["HOME"]
        paths.PROJECTS_DIR = self._was["PROJECTS_DIR"]
        paths.ACTIVE_PROJECT_FILE = self._was["ACTIVE"]
        paths.SETTINGS = self._was["SETTINGS"]
        paths.set_project(self._was["slug"])
        self._tmp.cleanup()


class TheRenderWaitsForTheVerdict(_Home):
    def _subject(self):
        generate.save_style_bible(
            "## Rendering Language" + NL + "Production painting.")
        return store.add_subject("Ryna Sokol", "CHARACTER", "Fugitive pilot",
                                 ["Flight jacket"])

    def test_it_arrives_provisional(self):
        out = generate.subject_portrait(self._subject()["id"], "mock")
        ref = next(r for r in store.list_references() if r["id"] == out["reference"])
        self.assertEqual(ref["status"], "PROVISIONAL")

    def test_accepting_it_approves_it(self):
        out = generate.subject_portrait(self._subject()["id"], "mock")
        self.assertEqual(
            store.set_reference_status(out["reference"], "APPROVED",
                                       "RULED ON THE CAST SCREEN")["status"],
            "APPROVED")

    def test_rejecting_it_quarantines_it(self):
        """A rejected picture must be unreachable by any later stage, not
        merely hidden on this screen."""
        out = generate.subject_portrait(self._subject()["id"], "mock")
        ref = store.set_reference_status(out["reference"], "REJECTED", "no")
        self.assertEqual(ref["status"], "REJECTED")
        self.assertFalse((paths.REF_ORIGINALS / ref["file"]).exists())
        self.assertTrue((paths.REF_QUARANTINE / ref["file"]).exists())

    def test_a_pending_render_is_not_a_style_reference_yet(self):
        """Only approved references ride into other prompts — which is
        the whole point of withholding the approval."""
        out = generate.subject_portrait(self._subject()["id"], "mock")
        self.assertNotIn(out["reference"],
                         [r["id"] for r in store.auto_style_references()])


# ------------------------------------------------------- what the read knows

class TheScreenplayIsTheSource(_Home):
    DRAFT = NL.join([
        "INT. VALLEY CLINIC - DAY",
        "",
        "DR. ADAEZE OYELARAN, fifties, in a Descent field coat that was white",
        "once. She does not look up from the wound.",
        "",
        "EXT. RIDGE - NIGHT",
        "",
        "OYELARAN",
        "Hold still.",
        "",
        "INT. CORRIDOR - LATER",
        "",
        "Reading glasses she does not need, pushed up into grey hair. OYELARAN",
        "has the steadiest hands in the corridor.",
    ])

    def setUp(self):
        super().setUp()
        self._draft(self.DRAFT)

    def _draft(self, text):
        """The stored extraction IS what every reader sees — the raw file
        never reaches one (see `screenplay_two_copies`)."""
        store.set_screenplay("draft.txt", text.encode("utf-8"))
        insights._text_cache.clear()

    def test_it_quotes_the_action_lines_not_the_dialogue_cue(self):
        """A cue is the character about to speak. It is not a description
        of anything, so it counts for the scene and is never quoted."""
        ev = insights.subject_evidence("Dr. Adaeze Oyelaran")
        self.assertTrue(ev["quotes"])
        for q in ev["quotes"]:
            self.assertNotEqual(q["line"].strip(), "OYELARAN")

    def test_the_introduction_leads(self):
        """A screenplay introduces a character in CAPS, and the
        introduction is the description."""
        ev = insights.subject_evidence("Dr. Adaeze Oyelaran")
        self.assertIn("Descent field coat", ev["quotes"][0]["line"])

    def test_every_quote_carries_a_page(self):
        for q in insights.subject_evidence("Dr. Adaeze Oyelaran")["quotes"]:
            self.assertIn("page", q)

    def test_the_roster_walk_and_the_detail_walk_agree(self):
        """The roster prints `n SCENES` from one bulk pass and the header
        prints it from the single-subject call. Two numbers for one fact
        is how a screen loses its credibility."""
        name = "Dr. Adaeze Oyelaran"
        self.assertEqual(insights.subject_scene_counts([name])[name],
                         insights.subject_evidence(name)["scenes"])

    def test_it_finds_them_by_surname_too(self):
        """A draft writes the full name once and the surname thereafter."""
        self.assertGreater(insights.subject_evidence("Dr. Adaeze Oyelaran")["scenes"], 1)

    def test_an_unread_project_answers_zero_rather_than_failing(self):
        self._draft("   ")
        self.assertEqual(insights.subject_evidence("Anybody")["scenes"], 0)
        self.assertEqual(insights.subject_scene_counts(["Anybody"]), {"Anybody": 0})


class TheseCostNothing(unittest.TestCase):
    def test_neither_route_calls_a_model(self):
        i = MAIN.index('@app.get("/api/subjects/{sid}/evidence")')
        seg = MAIN[i:MAIN.index('@app.post("/api/subjects/{sid}/generate")', i)]
        for spend in ("generate.", "await ", "provider"):
            self.assertNotIn(spend, seg, spend)

    def test_the_bulk_route_is_declared_before_the_id_routes(self):
        """`/api/subjects/scenes` would otherwise be read as a subject
        id — the failure would be a 404 on a name, which reads as a bug
        in the roster rather than in the routing table."""
        self.assertLess(MAIN.index('@app.get("/api/subjects/scenes")'),
                        MAIN.index('@app.put("/api/subjects/{sid}")'))

    def test_the_roster_asks_once_not_once_per_card(self):
        i = JS.index("const renderCastScreen = async () => {")
        seg = JS[i:JS.index(NL + "  };", i)]
        self.assertEqual(seg.count('api("/api/subjects/scenes")'), 1)
        self.assertIn("if (open) return renderCastDetail(open, refs);", seg)

    def test_the_roster_card_prints_scenes_not_photographs(self):
        i = JS.index('<span class="cast-scenes">')
        seg = JS[i:i + 200]
        self.assertIn("${scenes[s.id] ?? 0} SCENE", seg)
        self.assertNotIn("PHOTO", seg)


class ThePicturesActuallyReachTheMarkup(unittest.TestCase):
    """No picture had EVER rendered on the cast row, the roster or the
    detail — found 2026-09-12 by reading `getComputedStyle(...)
    .backgroundImage` off the running page, which answered `url("")`.

    `castShot()` returned `background-image:url("...")` and every caller
    interpolated it into `style="${...}"`. The attribute ends at the
    first inner double quote, so the browser parsed
    `style="background-image:url("` and discarded the URL as stray
    markup. It failed everywhere at once and looked like "the pictures
    do not work" rather than like one wrong character."""

    def test_the_helper_quotes_the_url_so_the_attribute_survives(self):
        i = JS.index("const castShot = r => r")
        seg = JS[i:i + 220]
        self.assertIn("url('/api/references/", seg)
        self.assertNotIn('url("', seg)

    def test_no_inline_style_anywhere_nests_double_quotes(self):
        """The two survivors assign `.style.backgroundImage` directly —
        a property, not an attribute, where quoting is free."""
        import re
        # Comments talk ABOUT the bug; strip them, keeping the line
        # count so a failure still names a real line.
        code = re.sub(r"/\*.*?\*/", lambda m: NL * m.group(0).count(NL),
                      JS, flags=re.S)
        lines = code.split(NL)
        for n, line in enumerate(lines, 1):
            if 'url("' not in line or line.lstrip().startswith("//"):
                continue
            # An assignment may wrap, so read the statement, not the line.
            stmt = NL.join(lines[max(0, n - 2):n])
            self.assertIn("style.backgroundImage", stmt, "line " + str(n))

    def test_the_frame_builds_its_own_the_same_way(self):
        self.assertIn("background-image:url('${shot}')", empty_screen())


class NothingOnEitherScreenIsUnderTwelvePixels(unittest.TestCase):
    """The plan's floor, and it was the user's complaint before the plan
    existed: "the font is 7 pixels high - a person cant read that"."""

    SELECTORS = [".cast-name {", ".cast-sub {", ".cast-scenes {",
                 ".cast-kick b {", ".cast-kick span {", ".cast-unrow > b {",
                 ".cast-chip {", ".cd-name {", ".cd-meta {", ".cd-mark {",
                 ".cd-kick {", ".cd-desc {", ".cd-nodesc {", ".cd-edit {",
                 ".cd-quote > .cd-page {", ".cd-quote > i {", ".cd-trait {",
                 ".cd-more {", ".cd-spend {", ".cd-none {",
                 ".cd-fact > b {", ".cd-fact > span {"]

    def test_every_size_on_the_cast_screens(self):
        import re
        for sel in self.SELECTORS:
            m = re.search(r"font-size:\s*([\d.]+)px", block(sel))
            self.assertIsNotNone(m, sel)
            self.assertGreaterEqual(float(m.group(1)), 12, sel)

    def test_the_shared_courier_labels_clear_the_floor_everywhere(self):
        """These three were 9.5-10.5px app-wide and this screen patched
        them for itself, because raising them everywhere was not this
        plan's to authorize. LEGIBILITY_FLOOR authorized it on the same
        day, so the patch is gone and the rule is at the source.

        `.text-act` is why the floor is measured from the DOM and not
        from the markup: `<-- Cast` and the gate's link both render
        through it, and neither screen's own CSS mentions it."""
        import re
        self.assertNotIn("#cast-screen .wiz-group-label", CSS)
        for sel in (".wiz-group-label", ".cost", ".text-act"):
            b = CSS.split(NL + sel + " {")[1].split("}")[0]
            m = re.search(r"font-size:\s*([\d.]+)px", b)
            self.assertIsNotNone(m, sel)
            self.assertGreaterEqual(float(m.group(1)), 13, sel)


if __name__ == "__main__":
    unittest.main()
