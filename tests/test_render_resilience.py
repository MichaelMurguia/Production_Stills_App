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
        block = JS[i:i + 600]
        self.assertIn("/candidates`", block)
        self.assertIn("!beforeIds.has(c.candidate_id)", block,
                      "it must find a candidate that wasn't there before the render")

    def test_generate_polls_on_a_gateway_cut_instead_of_failing(self):
        i = JS.index("const runGenerate = async")
        block = JS[i:i + 3000]
        # snapshots existing takes, then polls when the connection is cut
        self.assertIn("const before = new Set(panelCands.map", block)
        self.assertIn("(err instanceof TypeError) || (err.gateway && err.status >= 500)", block)
        self.assertIn("pollForNewTake(specId, p.id, before)", block)
        # a real app error still reports; the cut path never says "Generation failed"
        self.assertIn("Still rendering", block)


if __name__ == "__main__":
    unittest.main()
