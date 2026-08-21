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

    def test_a_refused_key_offers_the_door_that_fixes_it(self):
        block = self.js.split("const theRead")[1].split("async function startTheRead")[0]
        self.assertIn("data-f=rd-settings", block)
        self.assertIn('showView("settings")', block)

    def test_both_doors_to_the_read_report_the_same_way(self):
        """The read has two doors — the first upload and the Scene Scan —
        and for one commit only the first one reported. The same operation
        must look the same however it was started."""
        doors = re.findall(r'api\("/api/wizard/analyze"', self.js)
        self.assertEqual(len(doors), 2,
                         "a third caller of the read must also report")
        for door in self.js.split('api("/api/wizard/analyze"')[1:]:
            self.assertIn("theRead.finish(", door[:400])
            self.assertIn("theRead.fail(", door[:600])
        # Every other begin() must be the preview, which passes the flag.
        for call in self.js.split("theRead.begin(")[1:]:
            head = call[:80]
            self.assertTrue("true" in head or "engine" in head
                            or "selectedModelLabel" in head,
                            f"unaccounted begin(): {head!r}")

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
