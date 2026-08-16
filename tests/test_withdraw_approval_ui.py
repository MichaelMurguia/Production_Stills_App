"""An approved panel can go back to draft WITHOUT being rejected
(user 2026-08-16: "I need to be able to put an approved panel back into
draft without having to reject it").

`generate.unapprove_candidate` and `POST .../unapprove` were both built
earlier the same day — and nothing in the UI ever called either. So the
only route out of an approval was Reject, whose reason is carried verbatim
into every future prompt for that panel as a DIRECTOR'S CORRECTION.
Rejecting to unlock an edit means every later take of that panel is
steered by a criticism of an image that was never actually wrong.

This is the third capability found built-but-unreachable in one day (the
prompt editor's Save, the prompt editor itself, this) — hence the last
class here, which asserts the endpoint has a caller at all."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


class TheUiOffersIt(unittest.TestCase):
    def test_the_workbench_offers_withdraw_on_an_approved_take(self):
        self.assertIn('if (c.status === "APPROVED") actApprove.append(mk("Withdraw approval"', JS)

    def test_the_gallery_offers_it_too(self):
        """The gallery is where a user lands when reviewing what is already
        approved, so it is where they notice one should go back."""
        self.assertIn('wd.textContent = "Withdraw approval";', JS)

    def test_both_callers_hit_the_unapprove_endpoint(self):
        self.assertEqual(JS.count("/unapprove`"), 2)
        self.assertNotIn('{ status: "CANDIDATE" }', JS,
                         "withdrawing is its own verb, not a status write")

    def test_it_is_offered_only_where_there_is_an_approval(self):
        self.assertIn('if (c.status === "APPROVED") actApprove.append', JS)

    def test_it_is_not_styled_as_a_danger_act(self):
        """Reject is destructive and reads that way. Withdrawing loses
        nothing — the take keeps its image and stays in the strip — so
        dressing it as danger would push people back toward Reject."""
        i = JS.index('mk("Withdraw approval"')
        seg = JS[i:i + 400]
        self.assertIn('"text-act"', seg)
        self.assertNotIn("danger", seg)
        self.assertNotIn("act-reject", seg)


class TheCopySaysHowItDiffersFromReject(unittest.TestCase):
    def test_it_says_nothing_rides_future_prompts(self):
        """The whole point. A user who cannot tell these apart will keep
        using Reject, which is the behaviour this replaces."""
        i = JS.index('mk("Withdraw approval"')
        self.assertIn("carries nothing into future prompts", JS[i:i + 1400])

    def test_the_gallery_copy_says_it_too(self):
        i = JS.index('wd.textContent = "Withdraw approval";')
        self.assertIn("unlike Reject it records no reason", JS[i:i + 400])

    def test_it_says_the_take_survives(self):
        i = JS.index('mk("Withdraw approval"')
        self.assertIn("the take is untouched", JS[i:i + 900])


class TheBackendWasAlreadyThere(unittest.TestCase):
    def test_the_store_verb_exists_and_is_not_a_rejection(self):
        i = GEN.index("def unapprove_candidate")
        seg = GEN[i:i + 1400]
        self.assertIn('record["status"] = "CANDIDATE"', seg)
        self.assertIn('record.pop("status_reason", None)', seg,
                      "no reason survives, so nothing reaches rejection_feedback")

    def test_the_snapshot_survives_the_withdrawal(self):
        """What was once approved, and against what, stays true."""
        i = GEN.index("def unapprove_candidate")
        self.assertNotIn('pop("approved_spec"', GEN[i:i + 1400])

    def test_it_refuses_when_there_is_no_approval(self):
        i = GEN.index("def unapprove_candidate")
        self.assertIn("is not approved — nothing to withdraw", GEN[i:i + 1400])

    def test_the_endpoint_exists(self):
        self.assertIn('@app.post("/api/specs/{spec_id}/candidates/{cand_id}/unapprove")', MAIN)


class NoCapabilityIsLeftUnreachable(unittest.TestCase):
    """Three things in one day were built end-to-end and never surfaced.
    A POST route with no caller is a feature that does not exist."""

    def test_every_candidate_route_has_a_caller(self):
        routes = re.findall(
            r'@app\.post\("/api/specs/\{spec_id\}/candidates/\{cand_id\}/([a-z-]+)"\)', MAIN)
        self.assertTrue(routes, "the scan found no routes — it has stopped testing anything")
        for r in routes:
            # A caller may append a query string, so match the segment
            # rather than the end of the template literal.
            self.assertRegex(JS, rf"/{re.escape(r)}[`?]",
                             f"POST .../{r} has no caller in app.js")


if __name__ == "__main__":
    unittest.main()
