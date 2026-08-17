"""Tell the app anything about a panel; it re-reads the screenplay.

Asked 2026-08-16 as a "Scan Screenplay" button, reframed by the user on
2026-08-17: "I want to be able to say just about anything and have it
considered. Paste the screenplay. Describe a feel. Explain in my own
words. It re-reads the screenplay and updates the panel info. It is not an
object scan."

So the text is DIRECTION, not a search query, and what comes back is a
proposed BRIEF plus proposed REQUIRED CONTENT.

The line that must never blur is whose fact a proposal is:

- `screenplay` — the scene says it, and the find carries the VERBATIM
  line, checked against the text actually sent. Files as SCRIPT_EXPLICIT.
- `direction` — the designer said it. No quote, and any offered is
  stripped, because a citation here would file as SCRIPT_EXPLICIT and put
  their words in the screenplay's mouth. Files as USER_DIRECTED, and is
  never withheld for lacking a citation.

Building this also exposed a live bug in scene_anchor that affected the
composition check: a board set in "TERRA NOVA SECURE BAY" anchored to
"TERRA NOVA", a different slugline that happens to be a prefix, and every
reader silently got the wrong scene."""
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
STORE = (ROOT / "app/store.py").read_text(encoding="utf-8")

SRC = ("INT. TERRA NOVA SECURE BAY - NIGHT\n"
       "Behind him - an airlock hatch.\n"
       "Frost tendrils creep along the edges.\n")


def flat(s: str) -> str:
    return " ".join(str(s).split())


class ProvenanceIsTheTrustModel(unittest.TestCase):
    def test_a_screenplay_find_with_a_real_quote_survives(self):
        out = scan._coerce({"finds": [
            {"from": "screenplay", "object": "airlock hatch",
             "detail": "It sits behind Sal.",
             "quote": "Behind him - an airlock hatch."}]}, SRC)
        self.assertEqual([f["object"] for f in out["finds"]], ["airlock hatch"])
        self.assertEqual(out["finds"][0]["from"], "screenplay")
        self.assertEqual(out["unverified_dropped"], 0)

    def test_a_screenplay_find_with_an_invented_quote_is_dropped(self):
        """Dropped, NOT demoted to direction — the designer never said it
        either, so it is nobody's fact. And counted, because swallowing it
        silently hides that the model tried."""
        out = scan._coerce({"finds": [
            {"from": "screenplay", "object": "brass porthole",
             "detail": "Invented.",
             "quote": "A brass porthole gleams in the dark."}]}, SRC)
        self.assertEqual(out["finds"], [])
        self.assertEqual(out["unverified_dropped"], 1)

    def test_a_screenplay_find_with_no_quote_is_dropped(self):
        out = scan._coerce({"finds": [
            {"from": "screenplay", "object": "x",
             "detail": "claims the script, shows nothing", "quote": ""}]}, SRC)
        self.assertEqual(out["finds"], [])
        self.assertEqual(out["unverified_dropped"], 1)

    def test_a_direction_find_needs_no_quote(self):
        """The designer's own words are authority. Withholding them for
        want of a citation would refuse what they asked for."""
        out = scan._coerce({"finds": [
            {"from": "direction", "object": "cold blue rim light",
             "detail": "they asked for a colder feel", "quote": ""}]}, SRC)
        self.assertEqual(len(out["finds"]), 1)
        self.assertEqual(out["finds"][0]["from"], "direction")
        self.assertEqual(out["unverified_dropped"], 0)

    def test_a_direction_find_may_not_carry_a_citation(self):
        """A quote here files as SCRIPT_EXPLICIT downstream and puts the
        designer's words in the screenplay's mouth."""
        out = scan._coerce({"finds": [
            {"from": "direction", "object": "x", "detail": "d",
             "quote": "Behind him - an airlock hatch."}]}, SRC)
        self.assertEqual(out["finds"][0]["quote"], "")

    def test_an_unattributed_find_is_treated_as_direction(self):
        """Defaulting to `screenplay` would manufacture citations."""
        out = scan._coerce({"finds": [
            {"object": "x", "detail": "no from field", "quote": ""}]}, SRC)
        self.assertEqual(out["finds"][0]["from"], "direction")

    def test_whitespace_differences_do_not_fail_a_real_quote(self):
        """Screenplays wrap; a quote re-flowed across lines is still the
        text. Only the WORDS have to match."""
        out = scan._coerce({"finds": [
            {"from": "screenplay", "object": "hatch", "detail": "d",
             "quote": "Behind   him -  an\n  airlock hatch."}]}, SRC)
        self.assertEqual(len(out["finds"]), 1)

    def test_a_find_with_no_detail_is_not_a_find(self):
        out = scan._coerce({"finds": [
            {"from": "screenplay", "object": "hatch", "detail": "",
             "quote": "Behind him - an airlock hatch."}]}, SRC)
        self.assertEqual(out["finds"], [])

    def test_context_finds_need_no_object(self):
        """Not everything the scene settles is a thing to render."""
        out = scan._coerce({"finds": [
            {"from": "direction", "object": "", "detail": "It reads as farewell."}]}, SRC)
        self.assertEqual(len(out["finds"]), 1)
        self.assertEqual(out["finds"][0]["object"], "")

    def test_a_proposed_brief_comes_back(self):
        out = scan._coerce({"brief": "Show the chamber open.",
                            "brief_reason": "the designer said so",
                            "finds": []}, SRC)
        self.assertEqual(out["brief"], "Show the chamber open.")
        self.assertEqual(out["brief_reason"], "the designer said so")


class TheInstructionsBindTheModel(unittest.TestCase):
    def test_the_text_is_direction_not_a_search_string(self):
        i = flat(scan._instructions({}, {}, "", True))
        self.assertIn("WHAT THE DESIGNER SAID", i)
        self.assertIn("It is not a search string", i)
        self.assertIn("Read it for INTENT", i)

    def test_it_invites_anything(self):
        i = flat(scan._instructions({}, {}, "", True))
        self.assertIn("a question, a correction, a mood, a paste from somewhere else", i)

    def test_it_binds_provenance_both_ways(self):
        i = flat(scan._instructions({}, {}, "", True))
        self.assertIn("Do not paraphrase into it", i)
        self.assertIn("never withhold it for lacking one", i)
        self.assertIn("Never label the designer's words as the screenplay's", i)

    def test_it_asks_for_a_brief_only_when_it_can_improve_one(self):
        self.assertIn("only if you can improve", flat(scan._instructions({}, {}, "", True)))

    def test_a_mood_is_turned_into_something_drawable(self):
        i = flat(scan._instructions({}, {}, "", True))
        self.assertIn("A production designer cannot draw a mood", i)
        self.assertIn("propose what it LOOKS like", i)

    def test_it_says_when_the_scene_was_not_located(self):
        self.assertIn("screenplay scene could not be located",
                      flat(scan._instructions({}, {}, "", False)))


class TheAnchorPicksTheRightScene(unittest.TestCase):
    """The live bug this exposed. Both directions matter, and the first fix
    overshot in the second one."""

    def test_the_most_specific_containing_location_wins(self):
        self.assertIn("inside = [sc for sc in scenes", INS)
        self.assertIn('best = max(inside, key=lambda sc: (len(norm(sc["location"]).split()),',
                      INS)

    def test_a_broader_subject_takes_the_least_invented_match(self):
        """Asking for "terra nova" must not land on "terra nova hangar 02"
        — which the length-only first fix did."""
        self.assertIn('best = min(hits, key=lambda sc: (len(norm(sc["location"]).split()),',
                      INS)

    def test_it_no_longer_stops_at_the_first_overlap(self):
        self.assertNotIn('            best = sc["location"]\n            break', INS)


class TheUiOffersIt(unittest.TestCase):
    def test_it_sits_beside_the_brief(self):
        """User 2026-08-17: "It should be a button next to the purpose
        field on the right." It began beside Required objects, which framed
        it as an object scan."""
        i = JS.index('${step({ n: "01", id: "brief", label: "BRIEF"')
        seg = JS[i:i + 900]
        self.assertIn('data-f="scan-scene"', seg)
        self.assertIn("Tell me about this panel", seg)

    def test_it_is_not_offered_on_a_frozen_panel(self):
        """Both surfaces gate it — the workbench on `frozen`, the breakdown
        row on its per-panel `ro`. It proposes changes to what the panel
        says, which an approved take settles."""
        i = JS.index('${step({ n: "01", id: "brief", label: "BRIEF"')
        self.assertIn('${frozen ? "disabled" : ""}', JS[i:i + 900])
        j = JS.index('<span class="f-label" style="display:flex;align-items:center;gap:10px">Purpose')
        self.assertIn('${ro ? "" : `', JS[j:j + 200])

    def test_the_breakdown_row_offers_it_beside_purpose_too(self):
        """It began beside Required objects on both surfaces, which framed
        it as an object scan; the user asked for "next to the purpose
        field on the right"."""
        self.assertEqual(JS.count("Tell me about this panel"), 2)
        j = JS.index('<span class="f-label" style="display:flex;align-items:center;gap:10px">Purpose')
        self.assertIn('data-f="scan-scene"', JS[j:j + 400])

    def test_the_modal_says_what_actually_happens(self):
        """Copy set by the user 2026-08-17: "Any info provided will be
        considered during script rescan, because that is what is
        happening." The earlier draft listed the KINDS of thing you could
        say, which sold the idea rather than describing the mechanism."""
        i = JS.index("function scanScreenplayDialog")
        seg = " ".join(JS[i:i + 2200].split())
        self.assertIn("Any info provided will be considered during script rescan", seg)
        self.assertIn("In your own words", seg)
        self.assertIn("Nothing changes until you accept it", seg)
        self.assertNotIn("Ask one question", seg,
                         "the original framing asked for a query")
        self.assertNotIn("Say anything.", seg)

    def test_the_modal_opens_the_screenplay_in_a_new_tab(self):
        i = JS.index("function scanScreenplayDialog")
        seg = JS[i:i + 3000]
        self.assertIn("Open screenplay ↗", seg)
        self.assertIn('window.open("/api/screenplay/file", "_blank", "noopener")', seg)

    def test_a_proposal_states_whose_fact_it_is(self):
        """Drawn, not implied: the screenplay's own line, or plainly that
        it came from you."""
        self.assertIn("THE SCREENPLAY SAYS", JS)
        self.assertIn("FROM WHAT YOU SAID", JS)
        self.assertIn('<blockquote class="scan-quote">', JS)

    def test_the_brief_can_be_accepted_on_its_own(self):
        self.assertIn('data-f="use-brief"', JS)
        self.assertIn("PROPOSED BRIEF", JS)
        self.assertIn("await acceptBrief(r.brief)", JS)

    def test_the_brief_goes_through_the_journaled_endpoint(self):
        """Same path as the workbench's own Edit brief — journaled, lock
        re-stamped, refused on an approved take."""
        self.assertIn("/purpose`", JS)

    def test_nothing_changes_until_a_proposal_is_accepted(self):
        i = JS.index("function scanScreenplayDialog")
        seg = JS[i:i + 6500]
        self.assertIn("const added = await accept(b.dataset.add, b.dataset.quote", seg)
        self.assertIn("Nothing changes until you accept it", seg)

    def test_the_quote_travels_with_the_object(self):
        self.assertIn('data-quote="${esc(f.quote)}"', JS)
        self.assertIn('json: { add: [{ object: obj, quote: quote || "" }] }', JS)
        self.assertIn('"evidence_class": "SCRIPT_EXPLICIT" if quote else "USER_DIRECTED"',
                      STORE)

    def test_an_unproven_script_claim_is_reported_not_hidden(self):
        self.assertIn("CLAIMED THE SCRIPT AND COULD NOT SHOW IT", JS)

    def test_an_accept_failure_does_not_look_like_a_success(self):
        i = JS.index("function scanScreenplayDialog")
        seg = JS[i:i + 6500]
        self.assertIn("b.textContent = prev;", seg)

    def test_the_endpoint_exists(self):
        self.assertIn('@app.post("/api/specs/{spec_id}/panels/{panel_id}/scan")', MAIN)
        self.assertIn("/scan`", JS)


if __name__ == "__main__":
    unittest.main()
