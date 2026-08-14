"""Evidence ledger + workbench scope UX (user 2026-08-13) — JS pins.

The ledger's panel and object are selectable, not typed; the citation
searches the reference library; a scoped revision's workbench lands on
the revised panel and locks carried ones.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


class LedgerRowPins(unittest.TestCase):
    def test_panel_and_object_are_selects(self):
        i = JS.index("function addLedgerRow")
        block = JS[i:i + 3000]
        self.assertIn('<select data-f="panel_id"', block)
        self.assertIn('<select data-f="object"', block)
        self.assertNotIn('<input type="text" data-f="panel_id"', block)

    def test_object_offers_only_unrowed_required_objects(self):
        self.assertIn("— every required object has a row —", JS)
        self.assertIn("const syncObjects = keep", JS)

    def test_citation_searches_the_reference_library(self):
        self.assertIn('list="sp-ref-list"', JS)
        self.assertIn('dl.id = "sp-ref-list"', JS)


class WorkbenchScopePins(unittest.TestCase):
    def test_lands_on_the_revised_panel(self):
        self.assertIn("revisedFirst || pids[0]", JS)

    def test_carried_panels_state_the_lock(self):
        self.assertIn('title="Carried — not in this revision', JS)
        self.assertIn("CARRIED — NOT IN THIS REVISION", JS)
        self.assertIn('["generate", "prose", "compcheck", "brief-edit", "cam-open"]',
                      JS)

    def test_brief_and_camera_are_real_buttons(self):
        self.assertIn('class="ghost" data-f="brief-edit"', JS)
        self.assertIn('class="ghost" data-f="cam-open"', JS)


if __name__ == "__main__":
    unittest.main()
