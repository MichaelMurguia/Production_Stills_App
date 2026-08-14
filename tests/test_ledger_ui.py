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

    def test_object_offer_recomputes_every_open(self):
        """Rows created earlier could only see rows that existed before
        them (user-hit 2026-08-13) — the offer recomputes on open."""
        self.assertIn('objSel.addEventListener("mousedown", () => syncObjects(objSel.value))',
                      JS)

    def test_citation_searches_the_reference_library(self):
        """A real visible suggestion list — the native datalist proved
        inert (user-hit 2026-08-13). Typing stays free."""
        self.assertNotIn("sp-ref-list", JS)
        self.assertIn("const paintSug = () => {", JS)
        self.assertIn('srcInput.addEventListener("input", paintSug)', JS)

    def test_a_locked_ledger_reads_as_a_document(self):
        css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
        self.assertIn("#sp-ledger select:disabled, #sp-ledger input:disabled",
                      css)
        i = css.index("#sp-ledger select:disabled")
        self.assertIn("border-color: transparent", css[i:i + 300])


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


class AddReferenceInPlacePins(unittest.TestCase):
    def test_unreferenced_objects_offer_the_widget_in_both_lives(self):
        self.assertIn('data-addref="${esc(o)}"', JS)
        self.assertIn(">Add reference</button>", JS)
        self.assertIn(">+ REF</button>", JS)

    def test_referenced_objects_offer_view_as_the_full_widget(self):
        """User 2026-08-14: a bare lightbox hid that only ONE rear-view
        plate anchored the object. View is the full reference widget —
        every matching plate with role + jurisdiction, the thin-anchor
        warning, and Add another plate in place."""
        self.assertIn('data-viewref="${esc(o)}"', JS)
        self.assertIn(">View</button>", JS)
        self.assertIn(">view</button>", JS)
        self.assertIn("function viewObjectReferences", JS)
        i = JS.index("function viewObjectReferences")
        block = JS[i:i + 2600]
        self.assertIn("THE RENDER WORKS FROM EXACTLY WHAT IS BELOW", block)
        self.assertIn("One plate is a thin", block)
        self.assertIn('data-f="vr-add"', block)
        self.assertIn("CONTROLS ", block)

    def test_the_widget_is_the_existing_dialog_approved_and_refreshing(self):
        self.assertIn("addReferenceDialog({ head: \"PROP_REFERENCE\", title: b.dataset.addref }",
                      JS)
        self.assertIn("{ approve: true, onDone: () => renderBoardPanels(specId) }",
                      JS)
        self.assertIn('confirmLabel: approve ? "Add & approve" : "Add to library"',
                      JS)


class RepairEraserPins(unittest.TestCase):
    def test_the_painter_has_a_paint_erase_pair(self):
        self.assertIn('data-f="mode-paint"', JS)
        self.assertIn('data-f="mode-erase"', JS)

    def test_strokes_carry_the_mode_and_both_surfaces_replay_it(self):
        self.assertIn("erase: erasing", JS)
        i = JS.index("const redraw = () => {")
        self.assertIn('st.erase ? "destination-out" : "source-over"',
                      JS[i:i + 900])
        j = JS.index("// Paint punches transparency into the mask")
        self.assertIn('st.erase ? "source-over" : "destination-out"',
                      JS[j:j + 500])

    def test_repair_needs_at_least_one_paint_stroke(self):
        self.assertIn("strokes.some(s => !s.erase)", JS)


if __name__ == "__main__":
    unittest.main()
