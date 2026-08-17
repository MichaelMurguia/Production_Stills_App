"""No route may file SCRIPT_EXPLICIT for a line the screenplay does not
contain.

Adversarial review 2026-08-17, findings F6/F7/F21. The app verified the
class it COULD NOT check — a WEAK_INFERENCE cannot self-promote to PASS —
and skipped the only falsifiable one: SCRIPT_EXPLICIT asserts a verbatim
line exists in a document the server is holding, and nothing opened it.
The incentive ran backwards, because classifying strongly was the route to
a row that needed no human.

Three routes wrote such rows:

- `autofill._coerce` — the PRIMARY one. Every evidence row of every
  breakdown, with the model's chosen class, status and source.
- `scan.scan_panel` — on an anchor MISS it verified the model's citation
  against the sheet's own model-written `scene` prose and filed the result
  as the screenplay's word.
- `store.amend_panel_objects` — filed on the mere PRESENCE of a quote
  string in the request body.

And `insights.citation_check`, the standing net, was blind to all of it:
`_QUOTE_RE` only inspects text inside literal quote marks, so a row whose
source was a bare sentence never even incremented `checked`.

Demotion target is WEAK_INFERENCE, not STRONG (user ruling 2026-08-17): a
row whose cited line is absent is not a strong inference FROM the
screenplay, and WEAK spends the CANON_EXTRACTION budget of 2, so a draft
whose citations mostly cannot be found hits the cap and stops."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCREENPLAY = (
    "INT. TERRA NOVA SECURE BAY - NIGHT\n"
    "Behind him - an airlock hatch.\n"
    "SAL crosses the empty bay.\n"
)
ABSENT = "A shrine of welded scrap stands in the corner."


class TheOnePredicate(unittest.TestCase):
    """insights.quote_is_in_screenplay — one question, four callers."""

    def setUp(self):
        from app import insights
        self.real = insights.screenplay_text
        insights.screenplay_text = lambda: SCREENPLAY

    def tearDown(self):
        from app import insights
        insights.screenplay_text = self.real

    def test_a_real_line_is_found(self):
        from app import insights
        self.assertTrue(insights.quote_is_in_screenplay("Behind him - an airlock hatch."))

    def test_an_absent_line_is_not(self):
        from app import insights
        self.assertFalse(insights.quote_is_in_screenplay(ABSENT))

    def test_extraction_damage_is_tolerated(self):
        """PDF extraction mangles spacing and dashes; a citation is absent
        only when even its letters are gone."""
        from app import insights
        for q in ("Behind him — an airlock hatch.",
                  "Behind  him -   an airlock   hatch.",
                  "behind him an airlock hatch"):
            self.assertTrue(insights.quote_is_in_screenplay(q), q)

    def test_a_fragment_too_short_to_be_a_citation_is_refused(self):
        from app import insights
        self.assertFalse(insights.quote_is_in_screenplay("SAL"))

    def test_no_screenplay_means_nothing_is_sourced_to_it(self):
        """The honest answer, not a free pass."""
        from app import insights
        insights.screenplay_text = lambda: ""
        self.assertFalse(
            insights.quote_is_in_screenplay("Behind him - an airlock hatch."))


class TheNarrativeDraftRoute(unittest.TestCase):
    """F21 — the primary route, and the one that wrote almost every row."""

    def setUp(self):
        from app import insights
        self.real = insights.screenplay_text
        insights.screenplay_text = lambda: SCREENPLAY

    def tearDown(self):
        from app import insights
        insights.screenplay_text = self.real

    def _coerce(self, rows):
        from app import autofill
        return autofill._coerce(
            {"subject": "s", "scene": "sc", "panels": [
                {"id": "P01", "title": "t", "purpose": "p",
                 "required_objects": ["x"], "allocation_percent": 100}],
             "evidence_ledger": rows},
            "T_V001", "CANON_EXTRACTION", "SCENE")

    def test_a_verifiable_citation_stays_script_explicit(self):
        out = self._coerce([{"panel_id": "P01", "object": "airlock hatch",
                             "evidence_class": "SCRIPT_EXPLICIT", "status": "PASS",
                             "source": "Behind him - an airlock hatch."}])
        row = out["evidence_ledger"][0]
        self.assertEqual(row["evidence_class"], "SCRIPT_EXPLICIT")
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["quote"], "Behind him - an airlock hatch.")
        self.assertEqual(out["citations"]["demoted"], 0)

    def test_a_fabricated_citation_demotes_to_weak_inference_and_holds(self):
        out = self._coerce([{"panel_id": "P01", "object": "a shrine of welded scrap",
                             "evidence_class": "SCRIPT_EXPLICIT", "status": "PASS",
                             "source": ABSENT}])
        row = out["evidence_ledger"][0]
        self.assertEqual(row["evidence_class"], "WEAK_INFERENCE")
        self.assertEqual(row["status"], "HOLD")
        self.assertEqual(row["quote"], "")
        self.assertEqual(row["source"], "Citation not found in the screenplay")

    def test_the_demoted_row_keeps_what_the_model_claimed(self):
        """The row is the only record the object was proposed; the model's
        text moves to `rationale` rather than vanishing."""
        out = self._coerce([{"panel_id": "P01", "object": "shrine",
                             "evidence_class": "SCRIPT_EXPLICIT", "status": "PASS",
                             "source": ABSENT, "rationale": "it fits the space"}])
        r = out["evidence_ledger"][0]["rationale"]
        self.assertIn("Model cited this as SCRIPT_EXPLICIT", r)
        self.assertIn(ABSENT, r)
        self.assertIn("it fits the space", r)

    def test_the_demotions_are_counted_for_the_user(self):
        out = self._coerce([
            {"panel_id": "P01", "object": "a", "evidence_class": "SCRIPT_EXPLICIT",
             "status": "PASS", "source": ABSENT},
            {"panel_id": "P01", "object": "b", "evidence_class": "SCRIPT_EXPLICIT",
             "status": "PASS", "source": "SAL crosses the empty bay."},
        ])
        self.assertEqual(out["citations"], {"claimed": 2, "demoted": 1})

    def test_a_demoted_row_now_spends_the_weak_budget(self):
        """The point of WEAK over STRONG: a draft whose citations cannot be
        found hits the CANON_EXTRACTION cap instead of sailing through."""
        out = self._coerce([
            {"panel_id": "P01", "object": f"o{i}",
             "evidence_class": "SCRIPT_EXPLICIT", "status": "PASS", "source": ABSENT}
            for i in range(3)])
        weak = [r for r in out["evidence_ledger"]
                if r["evidence_class"] == "WEAK_INFERENCE"]
        self.assertEqual(len(weak), 3)
        # They land at HOLD, so they do not yet consume the PASS budget —
        # the user promoting them is what spends it, which is the gate.
        self.assertTrue(all(r["status"] == "HOLD" for r in weak))

    def test_the_weak_demotion_rule_is_untouched(self):
        """The pre-existing guard still stands: a model may not self-promote
        weak evidence to PASS."""
        out = self._coerce([{"panel_id": "P01", "object": "x",
                             "evidence_class": "WEAK_INFERENCE", "status": "PASS",
                             "source": "whatever"}])
        self.assertEqual(out["evidence_ledger"][0]["status"], "HOLD")


class TheHandWrittenRoute(unittest.TestCase):
    """F6 — store.amend_panel_objects, added 2026-08-17."""

    def setUp(self):
        from app import insights, paths
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        self._old = {k: getattr(paths, k)
                     for k in ("SPECS_DIR", "SPEC_LOCKS", "APPROVAL_LOG")}
        (home / "specs").mkdir(parents=True)
        (home / "state").mkdir(parents=True)
        paths.SPECS_DIR = home / "specs"
        paths.SPEC_LOCKS = home / "specs" / "locks.json"
        paths.APPROVAL_LOG = home / "state" / "approval_log.md"
        (paths.SPECS_DIR / "T_V001.json").write_text(json.dumps({
            "specification_id": "T_V001", "subject": "t",
            "mode": "CANON_EXTRACTION", "board_type": "SCENE",
            "panels": [{"id": "P01", "title": "t", "purpose": "p",
                        "required_objects": []}],
            "evidence_ledger": [],
        }), encoding="utf-8")
        self.real = insights.screenplay_text
        insights.screenplay_text = lambda: SCREENPLAY

    def tearDown(self):
        from app import insights, paths
        insights.screenplay_text = self.real
        for k, v in self._old.items():
            setattr(paths, k, v)
        self.tmp.cleanup()

    def _row(self):
        from app import store
        return store.get_spec("T_V001")["evidence_ledger"][-1]

    def test_a_real_quote_files_script_explicit(self):
        from app import store
        r = store.amend_panel_objects("T_V001", "P01", add=[
            {"object": "airlock hatch", "quote": "Behind him - an airlock hatch."}])
        self.assertEqual(r["unverified_citations"], [])
        self.assertEqual(self._row()["evidence_class"], "SCRIPT_EXPLICIT")

    def test_a_fabricated_quote_files_user_directed_not_script_explicit(self):
        """The user asked for the object, so their direction stands — only
        the citation was false."""
        from app import store
        r = store.amend_panel_objects("T_V001", "P01", add=[
            {"object": "a shrine of welded scrap", "quote": ABSENT}])
        self.assertEqual(r["unverified_citations"], ["a shrine of welded scrap"])
        row = self._row()
        self.assertEqual(row["evidence_class"], "USER_DIRECTED")
        self.assertEqual(row["source"], "User direction")
        self.assertEqual(row["quote"], "")
        self.assertIn("a shrine of welded scrap", r["added"])


class TheScanRoute(unittest.TestCase):
    """F6's second half — an anchor miss must not produce a citation."""

    def test_an_anchor_miss_marks_every_find_as_direction(self):
        from app import scan
        prose = "The bay holds a shrine of welded scrap, ringed by votive candles."
        out = scan._coerce({"finds": [
            {"from": "screenplay", "object": "votive candles",
             "detail": "Candles ring the shrine.",
             "quote": "ringed by votive candles"}]}, prose, from_screenplay=False)
        self.assertEqual(len(out["finds"]), 1)
        self.assertEqual(out["finds"][0]["from"], "direction",
                         "the screenplay was never read, so nothing is sourced to it")
        self.assertEqual(out["finds"][0]["quote"], "")

    def test_an_anchor_hit_still_verifies_normally(self):
        from app import scan
        out = scan._coerce({"finds": [
            {"from": "screenplay", "object": "airlock hatch", "detail": "d",
             "quote": "Behind him - an airlock hatch."}]}, SCREENPLAY,
            from_screenplay=True)
        self.assertEqual(out["finds"][0]["from"], "screenplay")


class TheStandingNetSeesThemNow(unittest.TestCase):
    """F7 — citation_check read only quoted spans, so it never looked at the
    rows these routes write."""

    def test_it_reads_the_quote_field(self):
        src = (ROOT / "app/insights.py").read_text(encoding="utf-8")
        self.assertIn('quotes = [str(row.get("quote", "")).strip()] if row.get("quote")', src)
        self.assertIn("_QUOTE_RE.findall(str(row.get(\"source\", \"\")))", src,
                      "kept as the legacy reader for older rows")

    def test_a_script_explicit_row_with_no_citation_is_itself_reported(self):
        src = (ROOT / "app/insights.py").read_text(encoding="utf-8")
        self.assertIn('"no_citation": True', src)

    def test_the_predicate_is_not_reimplemented(self):
        """One question, one implementation — the whole point of F21's fix."""
        src = (ROOT / "app/insights.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("def quote_is_in_screenplay"), 1)
        for mod in ("app/autofill.py", "app/store.py"):
            body = (ROOT / mod).read_text(encoding="utf-8")
            self.assertIn("quote_is_in_screenplay", body, mod)


if __name__ == "__main__":
    unittest.main()
