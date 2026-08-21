"""The read, as it happens.

The model's read is a single opaque call. This surface reports it with the
LOCAL parse, and the whole reason it is allowed to exist is that every
number on it is measured from the file. These tests hold that line: the
parse is real, the observations are arithmetic, and the model's phase
never claims progress it cannot have.
"""
import os
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

STATIC = pathlib.Path(__file__).resolve().parents[1] / "app" / "static"

SCRIPT = """\
FADE IN:

INT. RELAY STATION - MAINTENANCE BAY - NIGHT

Cold light. Racks of dead servers breathe frost. VERA OKONJO (40s) works
a panel loose with a screwdriver.

VERA
Third one this week.

EXT. STATION HULL - CONTINUOUS

The GT40 hangs in the cradle, unlovely and enormous.

INT. RELAY STATION - GALLEY - DAY

MARCUS pours something that is not coffee.

MARCUS
You slept out there again.

VERA
I slept fine.

INT. RELAY STATION - MAINTENANCE BAY - LATER

The GT40 chassis, opened. VERA reads a fault code.

VERA
That is not a fault. That is a signature.

CUT TO:

EXT. DUST FLATS - DAY

The GT40 races across the pan, throwing a rooster tail of rust.

FADE OUT.
"""


def _home():
    d = tempfile.mkdtemp(prefix="read-")
    from app import paths
    paths.HOME = pathlib.Path(d)
    paths.set_project("")
    paths.ensure_dirs()
    return pathlib.Path(d)


def _load(text=SCRIPT):
    _home()
    from app import store
    store.set_screenplay("draft.txt", text.encode("utf-8"))


class TheParseIsReal(unittest.TestCase):
    """Sluglines, cue lines and snapshots come off the page, not out of a
    model — that is the only reason this surface may run live."""

    def setUp(self):
        _load()
        from app import insights
        self.d = insights.screenplay_digest()

    def test_every_slugline_becomes_a_scene(self):
        self.assertTrue(self.d["available"])
        self.assertEqual(self.d["total"], 5)
        self.assertEqual(
            [s["heading"] for s in self.d["scenes"]][:2],
            ["INT. RELAY STATION - MAINTENANCE BAY - NIGHT",
             "EXT. STATION HULL - CONTINUOUS"])

    def test_scenes_are_numbered_from_one_in_page_order(self):
        self.assertEqual([s["n"] for s in self.d["scenes"]], [1, 2, 3, 4, 5])

    def test_speakers_are_cue_lines_from_the_scene_they_are_in(self):
        by_n = {s["n"]: s["speakers"] for s in self.d["scenes"]}
        self.assertEqual(by_n[1], ["VERA"])
        self.assertEqual(by_n[2], [])            # action only
        self.assertEqual(sorted(by_n[3]), ["MARCUS", "VERA"])

    def test_a_transition_is_not_a_person(self):
        """`FADE OUT.` and `CUT TO:` read as all-caps short lines, which is
        also what a character cue looks like. The first version of this
        parse reported FADE OUT. as a speaker with a line count."""
        everyone = {p for s in self.d["scenes"] for p in s["speakers"]}
        for word in ("FADE OUT.", "FADE IN:", "CUT TO:", "FADE OUT", "CUT TO"):
            self.assertNotIn(word, everyone)
        for obs in self.d["observations"]:
            self.assertNotRegex(obs, r"^(FADE|CUT|DISSOLVE|SMASH)\b")

    def test_the_snapshot_is_the_scripts_own_words(self):
        snap = self.d["scenes"][0]["snapshot"]
        self.assertTrue(snap)
        for line in snap:
            self.assertIn(line.strip(), SCRIPT)

    def test_no_screenplay_is_stated_not_faked(self):
        _home()
        from app import insights
        d = insights.screenplay_digest()
        self.assertFalse(d["available"])
        self.assertEqual(d["scenes"], [])
        self.assertEqual(d["observations"], [])


class ObservationsAreArithmetic(unittest.TestCase):
    """The commentary is the fun part and therefore the dangerous part. A
    line like "CHARLIE is probably the lead" is only allowed to appear
    because it is a scene count with a threshold on it — never a guess."""

    def setUp(self):
        _load()
        from app import insights
        self.d = insights.screenplay_digest()

    def test_every_speaker_claim_matches_a_real_count(self):
        counts = {}
        for sc in self.d["scenes"]:
            for p in sc["speakers"]:
                counts[p] = counts.get(p, 0) + 1
        found = 0
        for obs in self.d["observations"]:
            m = re.match(r"^(.+?) speaks in (\d+) of (\d+) scenes", obs)
            if not m:
                continue
            found += 1
            self.assertEqual(int(m.group(2)), counts[m.group(1)])
            self.assertEqual(int(m.group(3)), self.d["total"])
        self.assertGreater(found, 0, "no speaker observation was produced")

    def test_lead_and_recurring_are_a_stated_threshold(self):
        obs = " | ".join(self.d["observations"])
        self.assertRegex(obs, r"VERA speaks in 3 of 5 scenes — probably a lead")
        self.assertRegex(obs, r"MARCUS speaks in 1 of 5 scenes — recurring")

    def test_a_location_seen_once_is_not_a_place_it_keeps_returning_to(self):
        for obs in self.d["observations"]:
            m = re.match(r"^(.+?) carries (\d+) scenes — the script keeps", obs)
            if m:
                self.assertGreater(int(m.group(2)), 1, obs)

    def test_the_interior_exterior_split_adds_up(self):
        line = [o for o in self.d["observations"] if "exterior," in o]
        self.assertTrue(line)
        m = re.match(r"^(\d+) exterior, (\d+) interior$", line[0])
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)) + int(m.group(2)), self.d["total"])

    def test_a_character_is_never_also_reported_as_a_prop(self):
        """Action lines name people in caps too. Without excluding known
        speakers, VERA came back twice — once as a lead and again as "a
        thing the draft shouts", which reads as a parse that does not know
        what a person is."""
        speakers = {p for sc in self.d["scenes"] for p in sc["speakers"]}
        self.assertIn("VERA", speakers)
        for obs in self.d["observations"]:
            m = re.match(r"^([A-Z0-9'-]+) appears in \d+ scenes", obs)
            if m:
                self.assertNotIn(m.group(1), speakers, obs)

    def test_a_shouted_prop_claim_matches_the_page(self):
        for obs in self.d["observations"]:
            m = re.match(r"^([A-Z0-9'-]+) appears in (\d+) scenes", obs)
            if m:
                self.assertGreaterEqual(SCRIPT.count(m.group(1)), int(m.group(2)))


class TheRouteAnswers(unittest.TestCase):
    def test_digest_is_served_and_shaped(self):
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)
        _load()
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            r = c.get("/api/screenplay/digest")
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertTrue(body["available"])
            self.assertEqual(len(body["scenes"]), 5)
            for sc in body["scenes"]:
                self.assertEqual(
                    sorted(sc), sorted(["n", "heading", "location", "int_ext",
                                        "lines", "speakers", "snapshot"]))


class TheModelPhaseClaimsNothing(unittest.TestCase):
    """The reason a live progress surface over an opaque call is honest at
    all: the phase where nothing is knowable says so, in the interface, in
    words — and has no bar to lie with."""

    def setUp(self):
        self.js = (STATIC / "app.js").read_text(encoding="utf-8")
        self.css = (STATIC / "styles.css").read_text(encoding="utf-8")

    def test_the_model_phase_states_it_has_no_per_scene_progress(self):
        self.assertIn("NO ", self.js)
        self.assertIn("PER-SCENE PROGRESS TO REPORT", self.js)

    def test_the_parse_phase_says_nothing_has_been_sent(self):
        self.assertIn("NOTHING SENT ANYWHERE YET", self.js)

    def test_the_ladder_is_fed_by_the_digest_route(self):
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        self.assertIn('api("/api/screenplay/digest")', block)
        # …and by nothing else. A second source here is a second answer to
        # "what is in this screenplay", which is how the four-parser
        # problem started.
        self.assertEqual(len(re.findall(r'api\("/api/', block)), 1)

    def test_a_refused_key_is_named_as_a_refused_key(self):
        """The panel's first real failure was a 401, and it uppercased the
        whole 200-character provider body — URL and masked key included —
        which made the one sentence that mattered the hardest to find."""
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        self.assertIn("REFUSED THE KEY IT WAS GIVEN", block)
        self.assertIn("refused()", block)
        # the provider's own words, unshouted, in their own element
        self.assertIn('rd-raw', block)
        self.assertNotIn('(this.error || "").toUpperCase()', block)

    def test_a_spent_account_is_named_as_a_spent_account(self):
        """User, 2026-08-21: the read died on 429/insufficient_quota and
        the panel said only "THE READ DID NOT FINISH". The key was fine,
        the balance was not, and the app was holding a message that said
        so. A billing failure and an auth failure have different fixes, so
        they get different sentences."""
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        self.assertIn("insufficient_quota", block)
        self.assertIn("HAS NO CREDIT LEFT", block)
        self.assertIn('kind: "quota"', block)

    def test_rate_limiting_is_not_confused_with_being_out_of_credit(self):
        """Both arrive as 429. One is fixed by waiting, the other by
        paying — telling a user to wait for a balance that will never
        refill on its own is worse than saying nothing."""
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        q = block.index('kind: "quota"')
        r = block.index('kind: "rate"')
        self.assertLess(q, r, "quota must be tested before the bare 429 "
                              "catch-all, or every spent account reads as "
                              "a rate limit")

    def test_the_key_test_does_not_claim_more_than_it_measured(self):
        """`/api/settings/test` is deliberately a models call that spends
        nothing — so it passes on an account with no credit. It said "the
        key works" three seconds before a read failed on billing."""
        i = self.js.index('api("/api/settings/test"')
        # the success line only — a comment may quote the old copy
        j = self.js.index('say(', i)
        line = self.js[j:self.js.index('"ok");', j)]
        self.assertNotIn("the key works", line)
        self.assertIn("does not", line)
        self.assertIn("credit", line)

    def test_a_refused_key_offers_the_door_that_fixes_it(self):
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        self.assertIn("data-f=rd-settings", block)
        self.assertIn('showView("settings")', block)

    def test_the_panel_belongs_to_stage_01_and_stays_there(self):
        """User, 2026-08-21: "Reading the Draft panel was copied to the
        Prod Design tab — remove." It had been mounted into whichever view
        was open, so finishing a read and walking to stage 02 carried it
        along. Reading the draft is a stage 01 fact; on the next stage the
        same panel is not progress, it is a leftover."""
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        i = block.index("mount() {")
        seg = block[i:i + 700]
        self.assertIn('$(".dash-main")', seg)
        self.assertNotIn("wiz-v3", seg)
        # …and no other view re-mounts it
        self.assertEqual(self.js.count("theRead.mount()"), 1)

    def test_the_scene_scan_reports_through_its_own_busy_line(self):
        """Removing the panel from stage 02 must not leave that door
        silent — it reports the way it always did."""
        i = self.js.index('#wiz-analyze").onclick')
        seg = self.js[i:i + 1400]
        self.assertIn("startBusy(", seg)
        self.assertIn("design language(s)", seg)
        self.assertNotIn("theRead.", seg)

    def test_the_finish_state_does_not_outstay_the_work(self):
        """"At the end of reading and processing, the read-is-in section
        should go away." The panel is an account of something happening;
        once nothing is happening it is a spent receipt on the stage. The
        toast carries the result, so the finding survives the panel."""
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        i = block.index("finish(analysis) {")
        seg = block[i:i + 1200]
        self.assertIn("this.dismiss()", seg)
        self.assertIn("toast(", seg)
        self.assertIn('if (this.phase === "found")', seg)
        j = block.index("dismiss() {")
        self.assertIn("clearTimeout(this.bye)", block[j:j + 200])
    def test_a_preview_never_claims_a_model_ran(self):
        """The preview exists so the animation and the copy can be checked
        without spending anything. It walks the SAME parse — so it must
        stop where the model would take over, and say why. A preview that
        invented the model's half would be a lie told by the one surface
        built to avoid telling them."""
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        self.assertIn('this.phase = this.preview ? "previewed" : "model";', block)
        self.assertIn("NO MODEL WAS CALLED", block)
        # and it must not fall into the model phase's copy
        i = block.index('"previewed"')
        self.assertNotIn("IS READING", block[i:i + 400])

    def test_the_preview_is_owner_only(self):
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        i = html.index('id="dbg-read-preview"')
        # it lives inside the debug subview, which the client hides unless
        # settings.debug_tools is true
        self.assertLess(html.index('data-subview="debug"'), i)
        self.assertIn('_debugTools = !!settings.debug_tools;', self.js)

    def test_the_preview_reads_the_same_digest_as_the_real_read(self):
        """Two parses would be two answers to "what is in this screenplay"
        — the failure mode this codebase has hit four times."""
        i = self.js.index("dbg-read-preview")
        self.assertIn('api("/api/screenplay/digest")', self.js[i:i + 900])
        self.assertIn("theRead.begin(", self.js[i:i + 900])

    def test_the_preview_can_be_closed(self):
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        i = block.rindex('this.phase === "previewed"')
        self.assertIn("rd-dismiss", block[i:i + 400])

    def test_the_panel_cannot_change_height_while_it_is_watched(self):
        """User, 2026-08-21: "that section should not change height, it
        causes popping during the read." Two things moved — the snapshot
        column re-flowed per scene, and the ticker grew as findings
        landed. Both are reserved now."""
        css = self.css
        body = css.split(".rd-body {")[1].split("}")[0]
        self.assertIn("height: 268px", body)
        ticker = css.split(".rd-ticker {")[1].split("}")[0]
        self.assertIn("min-height:", ticker)
        obs = css.split(".rd-obs, .rd-found {")[1].split("}")[0]
        self.assertIn("white-space: nowrap", obs)
        # and the page's lines must refuse to shrink inside the fixed box,
        # or a line of action breaks one word per row
        self.assertIn(".rd-page > * { flex: 0 0 auto; }", css)

    def test_the_findings_are_not_set_as_a_footnote(self):
        """They are the point of the surface."""
        ticker = self.css.split(".rd-ticker {")[1].split("}")[0]
        self.assertIn("background: var(--field)", ticker)
        self.assertIn("var(--ok)", ticker)
        obs = self.css.split(".rd-obs, .rd-found {")[1].split("}")[0]
        self.assertIn("font-size: 13px", obs)

    def test_the_model_phase_spins_and_says_what_it_is_doing(self):
        """A surface whose whole job is to look alive went static at the
        one point the user had least idea what was happening."""
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        self.assertIn("Scoping production needs", block)
        self.assertIn('class="spinner"', block)
        # `wrap` is load-bearing: .busy-bar is flex-basis 100% and without
        # it the label renders one word per line.
        self.assertIn('class="busy wrap"', block)

    def test_nothing_else_offers_to_start_work_during_a_read(self):
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        self.assertIn('document.body.dataset.readBusy', block)
        self.assertIn('body[data-read-busy="1"]', self.css)
        # the read's own controls stay live
        self.assertIn('body[data-read-busy="1"] #read-live button', self.css)

    def test_the_lock_never_outlives_the_read(self):
        """A lock that survives its reason is how an app becomes
        unusable."""
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        for fn in ("stopTimers() {", "dismiss() {"):
            i = block.index(fn)          # the definition, not a call site
            self.assertIn('readBusy = "0"', block[i:i + 400], fn)
        # …and the nav is never locked, so nobody is trapped
        self.assertNotIn('body[data-read-busy="1"] #nav', self.css)

    def test_screenplay_grammar_is_never_a_finding(self):
        """"INT appears in 20 scenes" is true of every script ever
        written. It was topping the ticker and crowding out GT40."""
        from app import insights
        self.assertIn("INT", insights.SCREENPLAY_GRAMMAR)
        self.assertIn("EXT", insights.SCREENPLAY_GRAMMAR)
        self.assertIn("CONTINUOUS", insights.SCREENPLAY_GRAMMAR)
        _load()
        for obs in insights.screenplay_digest()["observations"]:
            m = re.match(r"^([A-Z0-9'-]+) appears in", obs)
            if m:
                self.assertNotIn(m.group(1), insights.SCREENPLAY_GRAMMAR, obs)

    def test_the_read_survives_leaving_the_view(self):
        self.assertIn("if (theRead.on) theRead.mount();", self.js)

    def test_exactly_one_amber_in_the_panel(self):
        block = self.css.split(".rd {")[1]
        accents = [ln for ln in block.splitlines()
                   if "--accent" in ln and not ln.strip().startswith(("*", "/*"))]
        self.assertEqual(
            len(accents), 1,
            f"the read panel must carry exactly one amber, found: {accents}")
        self.assertIn(".rd-row.now .rd-bar i", accents[0])

    def test_the_panel_invents_no_colours(self):
        block = self.css.split(".rd {")[1]
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b", block), [])


if __name__ == "__main__":
    unittest.main()
