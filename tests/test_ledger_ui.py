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
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


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

    def test_brief_and_camera_are_verbs_on_the_shared_edge(self):
        """SUPERSEDED 2026-08-14. The user's 2026-08-13 direction upgraded
        these from quiet text-acts to ghost BUTTONS, and HARNESS_AUDIT R11
        ratified that with U4's nowrap fix. STEP_SEQUENCE_SPEC §1.4 rules
        the whole surface instead: at 11.5px colour alone cannot separate a
        verb from the fact beside it, so a verb is full ink + underlined and
        every verb on the surface aligns to ONE right edge. Mock
        hier-4a shows both as verbs, and the box is what goes. The
        substance the user asked for — these two must not read as part of
        the string they act on — is what §1.4 delivers."""
        self.assertIn('class="verb" data-f="brief-edit"', JS)
        self.assertIn('class="verb" data-f="cam-open"', JS)
        for decl in ("text-decoration: underline", "white-space: nowrap"):
            self.assertIn(decl, CSS[CSS.index(".seq .verb, .seq .text-act"):][:420])


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
        # §1.3/§2 (STEP_SEQUENCE_SPEC): the tile carries the object's
        # STATE in Courier (REF / + REF) rather than a prose verb, but the
        # act behind it is unchanged — the full widget, never a bare
        # lightbox. What the user ruled was the destination, not the word.
        self.assertIn('data-viewref="${esc(o)}"', JS)
        self.assertIn(">REF</button>", JS)
        i = JS.index('data-viewref="${esc(o)}"')
        self.assertIn("View the matching reference plate(s)", JS[i:i + 200])
        j = JS.index("$$(\"[data-viewref]\", card)")
        seg = JS[j:j + 1100]
        self.assertIn("viewObjectReferences", seg,
                      "the tile opens the widget, not a lightbox")
        self.assertIn("gs.flatMap(pickFor)", seg,
                      "and it opens on the plates SELECTED for that object, "
                      "not the whole library group (user 2026-08-15)")
        self.assertIn("function viewObjectReferences", JS)
        # Bounded by the function's end, not a guessed character count — a
        # fixed slice stops covering the code the moment the function
        # grows, and this one already walked off twice (2026-08-14/15).
        i = JS.index("function viewObjectReferences")
        block = JS[i:JS.index(chr(10) + "const SHELVES", i)]
        # E3 (RULE_PASS_2 E, 2026-08-18): the thin-anchor warning was a
        # three-sentence paragraph AFTER the grid. It is a Courier fact at
        # the head now, beside the count, and its verb was already there.
        self.assertIn("THIN ANCHOR — ONE ANGLE STEERS EVERY RENDER", block)
        self.assertNotIn("One plate is a thin", block)
        self.assertIn('data-f="vr-add"', block)
        # E0: jurisdiction is ONE renderer now, shared with the library
        # shelf — and it is not drawn at all where there is none to state.
        self.assertIn("jurisRows(r.controls, r.does_not_control)", block)
        self.assertIn('<div class="juris ok">CONTROLS ', JS)
        self.assertIn("NO JURISDICTION SET", JS)

    def test_the_gallery_uses_the_library_grid_not_a_shrinking_column(self):
        """User-hit 2026-08-14: a flex column shrank five cards to 76px
        and .ref-card's overflow:hidden clipped every image. The library's
        own grid gives each card its natural height."""
        # Bounded by the function's end, not a guessed character count — a
        # fixed slice stops covering the code the moment the function
        # grows, and this one already walked off twice (2026-08-14/15).
        i = JS.index("function viewObjectReferences")
        block = JS[i:JS.index(chr(10) + "const SHELVES", i)]
        # E1 (2026-08-18): the modal answers "do these plates cover the
        # angles?" — a comparison. The plates ARE the surface: one row at
        # full width, own ratios, md tier, not thumbs under five text rows.
        self.assertIn('class="vr-strip${narrowed ? " vr-only" : ""}"', block,
                      "a filmstrip of the thing being judged, optionally "
                      "narrowed to the plates that actually ride")
        self.assertIn("size=md", block, "not thumb tier — this is the judging")
        self.assertNotIn("flex-direction:column", block)
        self.assertNotIn('class="primary" data-f="vr-close"', block,
                         "a dismissal is not the view's primary action")

    def test_the_widget_is_the_existing_dialog_approved_and_refreshing(self):
        """Upload is now the SECOND door — `+ REF` first asks whether the
        library already holds the plate (user 2026-08-16) — but when the
        answer is "new" it must still be this same dialog, approved, and
        refreshing the caller."""
        self.assertIn('addReferenceDialog({ head: "PROP_REFERENCE", title: obj }', JS)
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
