"""A cut connection must not read as a failed render (user 2026-08-09).

A long render outlives the request: a gateway cuts the connection at ~1 min but
the engine finishes and the take lands on disk (the raw 4K image, then the
record). The client used to show a 502 "Generation failed" for a render that was
actually completing. Now a gateway cut keeps the pending tile up and polls for
the take. These assert the wiring stays in place (frontend-only behavior).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


class RenderResilienceWiring(unittest.TestCase):
    def test_api_tags_gateway_errors(self):
        i = JS.index("async function api(")
        block = JS[i:i + 900]
        self.assertIn("err.gateway = !(data && data.detail)", block,
                      "api() must mark errors with no app JSON detail as gateway cuts")
        self.assertIn("err.status = res.status", block)

    def test_poll_helper_watches_the_candidates_list(self):
        i = JS.index("async function pollForNewTake")
        block = JS[i:i + 1000]
        self.assertIn("/candidates`", block)
        self.assertIn("!beforeIds.has(c.candidate_id)", block,
                      "it must find a candidate that wasn't there before the render")

    def test_generate_polls_on_a_gateway_cut_instead_of_failing(self):
        i = JS.index("const runGenerate = async")
        block = JS[i:i + 3200]
        # snapshots existing takes, then polls when the connection is cut
        self.assertIn("const before = new Set(panelCands.map", block)
        self.assertIn("(err instanceof TypeError) || (err.gateway && err.status >= 500)", block)
        self.assertIn("pollForNewTake(specId, p.id, before", block)
        # a real app error still reports; the cut path never says "Generation failed"
        self.assertIn("Still rendering", block)

    def test_cancel_stops_a_gateway_cut_poll(self):
        # Regression (2026-08-12 review): once the fetch had failed, Cancel
        # only fired ctrl.abort() — nothing was listening, and the spinner
        # ran to the 200s budget. The poll must honor the signal.
        i = JS.index("async function pollForNewTake")
        self.assertIn("signal?.aborted", JS[i:i + 900],
                      "the poll loop must check the abort signal each tick")
        j = JS.index("const runGenerate = async")
        block = JS[j:j + 3200]
        self.assertIn("{ signal: ctrl.signal }", block,
                      "the gateway-cut poll must receive the Cancel signal")
        self.assertIn("ctrl.signal.aborted", block)

    def test_a_landed_take_never_hijacks_another_view(self):
        # Regression (2026-08-12 review): a poll finishing after navigation
        # re-rendered this spec's panels over whatever the user was viewing.
        j = JS.index("const runGenerate = async")
        block = JS[j:j + 3200]
        self.assertIn('$("#board-panels") && $("#board-spec")?.value === specId',
                      block, "landed() must verify the view before re-rendering")



class TheRecordSurvivesAnOddReference(unittest.TestCase):
    """A paid render must never be thrown away by bookkeeping.

    2026-08-15, production: generation returned {"detail": "'sha256'"} —
    a KeyError from the take-record write, which happens AFTER the image
    has come back from the engine. The reference list was built with
    r["sha256"], so one reference missing one field destroyed a render
    the user had already paid for."""

    def test_the_record_reads_references_defensively(self):
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        i = src.index('"references": [{"id": r.get("id"')
        row = src[i:i + 260]
        for f in ('r.get("id"', 'r.get("role"', 'r.get("sha256"'):
            self.assertIn(f, row)
        self.assertNotIn('r["sha256"]', row,
                         "a missing field must not raise after the spend")

if __name__ == "__main__":
    unittest.main()
