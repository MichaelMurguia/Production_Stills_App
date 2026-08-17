"""Re-scan the screenplay for one panel, for something the user names.

User 2026-08-16: "For a panel, in the breakdown, I need a 'Scan Screenplay'
button that will rescan for information. A modal will pop up asking for
information to scan for which the AI will use to get better info. In that
modal, a 'Open Screenplay' button will open the screenplay in a new tab."

A breakdown is drafted once, from a brief, and the draft summarises — it
captured "airlock hatch behind Sal" and lost that the hatch irises. Until
now nothing could go back and ask.

Two things carry the weight:

1. VERBATIM QUOTES. Every find must quote the text, and the quote is
   checked against what was actually sent. A find the screenplay does not
   say is worse than no find, because it enters a breakdown looking like
   evidence.
2. THE RIGHT SCENE. Building this exposed a live bug in scene_anchor that
   also affected the composition check: a board set in "TERRA NOVA SECURE
   BAY" anchored to "TERRA NOVA", a different slugline that happens to be
   a prefix, and every reader silently got the wrong scene."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import scan  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
INS = (ROOT / "app/insights.py").read_text(encoding="utf-8")

SRC = ("INT. TERRA NOVA SECURE BAY - NIGHT\n"
       "Behind him - an airlock hatch.\n"
       "Frost tendrils creep along the edges.\n")


class AQuoteMustBeReal(unittest.TestCase):
    def test_a_verbatim_find_survives(self):
        out = scan._coerce({"finds": [
            {"object": "airlock hatch", "detail": "It sits behind Sal.",
             "quote": "Behind him - an airlock hatch."}]}, SRC)
        self.assertEqual([f["object"] for f in out["finds"]], ["airlock hatch"])
        self.assertEqual(out["unverified_dropped"], 0)

    def test_an_invented_quote_is_dropped_and_counted(self):
        """The trust model. Silently dropping would be almost as bad —
        the user has to know the model tried."""
        out = scan._coerce({"finds": [
            {"object": "brass porthole", "detail": "Invented.",
             "quote": "A brass porthole gleams in the dark."}]}, SRC)
        self.assertEqual(out["finds"], [])
        self.assertEqual(out["unverified_dropped"], 1)

    def test_whitespace_differences_do_not_fail_a_real_quote(self):
        """Screenplays wrap; a quote re-flowed across lines is still the
        text. Only the WORDS have to match."""
        out = scan._coerce({"finds": [
            {"object": "hatch", "detail": "d",
             "quote": "Behind   him -  an\n  airlock hatch."}]}, SRC)
        self.assertEqual(len(out["finds"]), 1)

    def test_a_find_with_no_quote_is_dropped(self):
        out = scan._coerce({"finds": [
            {"object": "x", "detail": "asserted with nothing behind it",
             "quote": ""}]}, SRC)
        self.assertEqual(out["finds"], [])

    def test_a_find_with_no_detail_is_not_a_find(self):
        out = scan._coerce({"finds": [
            {"object": "hatch", "detail": "", "quote": "Behind him - an airlock hatch."}]}, SRC)
        self.assertEqual(out["finds"], [])

    def test_context_finds_need_no_object(self):
        """Not everything the screenplay settles is a thing to render."""
        out = scan._coerce({"finds": [
            {"object": "", "detail": "The scene is at night.",
             "quote": "INT. TERRA NOVA SECURE BAY - NIGHT"}]}, SRC)
        self.assertEqual(len(out["finds"]), 1)
        self.assertEqual(out["finds"][0]["object"], "")


class TheInstructionsBindTheModel(unittest.TestCase):
    def test_it_is_told_an_empty_answer_is_valid(self):
        i = scan._instructions({"specification_id": "S"}, {"id": "P01"}, "ask", True)
        self.assertIn("an empty `finds` list is a valid, useful result", i)

    def test_it_is_told_not_to_paraphrase_into_the_quote(self):
        i = scan._instructions({}, {}, "", True)
        self.assertIn("Do not paraphrase\n  into the quote field", i)

    def test_it_asks_for_drawable_facts(self):
        i = " ".join(scan._instructions({}, {}, "", True).split())
        self.assertIn("Prefer PHYSICAL, DRAWABLE facts", i)
        self.assertIn("A production designer cannot draw a mood", i)

    def test_it_says_when_the_scene_was_not_located(self):
        i = scan._instructions({}, {}, "", False)
        self.assertIn("screenplay scene could not be located", i)


class TheAnchorPicksTheRightScene(unittest.TestCase):
    """The live bug this feature exposed. Both directions matter, and the
    first fix overshot in the second one."""

    def test_the_most_specific_containing_location_wins(self):
        self.assertIn("inside = [sc for sc in scenes", INS)
        self.assertIn("best = max(inside, key=lambda sc: (len(norm(sc[\"location\"]).split()),",
                      INS)

    def test_a_broader_subject_takes_the_least_invented_match(self):
        """Asking for "terra nova" must not land on "terra nova hangar
        02" — which the length-only first fix did."""
        self.assertIn("best = min(hits, key=lambda sc: (len(norm(sc[\"location\"]).split()),",
                      INS)

    def test_it_no_longer_stops_at_the_first_overlap(self):
        self.assertNotIn("            best = sc[\"location\"]\n            break", INS)


class TheUiOffersIt(unittest.TestCase):
    def test_the_panel_row_carries_the_button(self):
        self.assertIn('data-f="scan-scene"', JS)
        self.assertIn(">Scan screenplay</button>", JS)

    def test_a_frozen_panel_does_not_offer_it(self):
        """It proposes edits to required content, which an approved take
        freezes."""
        i = JS.index('data-f="scan-scene"')
        self.assertIn('${ro ? "" : `', JS[max(0, i - 200):i])

    def test_the_modal_asks_before_it_scans(self):
        self.assertIn('data-f="ask"', JS)
        self.assertIn("What should I look for?", JS)

    def test_the_modal_opens_the_screenplay_in_a_new_tab(self):
        i = JS.index("function scanScreenplayDialog")
        seg = JS[i:i + 4000]
        self.assertIn("Open screenplay ↗", seg)
        self.assertIn('window.open("/api/screenplay/file", "_blank", "noopener")', seg)

    def test_a_find_shows_its_quote(self):
        """Accepting a find has to be reading evidence, not trusting a
        model — so the screenplay's own words are on screen."""
        self.assertIn('<blockquote class="scan-quote">', JS)

    def test_nothing_changes_until_a_find_is_accepted(self):
        i = JS.index("function scanScreenplayDialog")
        seg = JS[i:i + 6200]
        self.assertIn("const added = await accept(b.dataset.add, b.dataset.quote", seg)
        self.assertIn("nothing changes until you accept", seg)

    def test_the_quote_travels_with_the_object(self):
        """A scan-sourced object is SCRIPT_EXPLICIT evidence against that
        line, not USER_DIRECTED — the app HAS the citation, so filing it as
        user direction would throw away the best evidence it will ever
        have for that object."""
        self.assertIn('data-quote="${esc(f.quote)}"', JS)
        self.assertIn('json: { add: [{ object: obj, quote: quote || "" }] }', JS)
        st = (ROOT / "app/store.py").read_text(encoding="utf-8")
        self.assertIn('"evidence_class": "SCRIPT_EXPLICIT" if quote else "USER_DIRECTED"', st)

    def test_the_workbench_offers_it_too(self):
        """It shipped only on the breakdown editor, three screens down.
        The user was on the Panels page: "Dont see it"."""
        i = JS.index('${step({ n: "02", id: "objects", label: "REQUIRED"')
        self.assertIn('data-f="scan-scene"', JS[i:i + 700])
        self.assertIn('const scanHere = $("[data-f=scan-scene]", card);', JS)

    def test_an_accept_failure_does_not_look_like_a_success(self):
        i = JS.index("function scanScreenplayDialog")
        seg = JS[i:i + 6200]
        self.assertIn("b.textContent = prev;", seg)
        self.assertIn("b.disabled = false;", seg)

    def test_dropped_finds_are_reported_not_hidden(self):
        self.assertIn("DROPPED — NOT LITERALLY IN THE TEXT", JS)

    def test_an_object_already_required_is_marked_before_it_is_clicked(self):
        self.assertIn("already required", JS)

    def test_the_endpoint_exists(self):
        self.assertIn('@app.post("/api/specs/{spec_id}/panels/{panel_id}/scan")', MAIN)
        self.assertIn("/scan`", JS)


if __name__ == "__main__":
    unittest.main()
