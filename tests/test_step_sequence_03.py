"""Stage 03 in the step vocabulary — STEP_SEQUENCE_SPEC Part 3, mock
hier-5a. The spec calls this "a transfer that should cost nothing"; these
assert it transferred rather than being redrawn, and pin the two rulings
that are the user's rather than the designer's."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def block(sel: str) -> str:
    bodies = re.findall(re.escape(sel) + r"\s*{([^}]*)}", CSS)
    assert bodies, f"missing rule: {sel}"
    return "\n".join(bodies)


class TheTransfer(unittest.TestCase):
    def test_one_step_renderer_serves_both_surfaces(self):
        """A second drawing of the same vocabulary is how two surfaces
        start disagreeing — stage 03 binds the same seqStep()."""
        self.assertIn("function seqStep({", JS)
        self.assertEqual(JS.count("function seqStep({"), 1)
        i = JS.index("async function openSpecEditor")
        self.assertIn("seqStep({", JS[i:i + 12000])

    def test_the_vocabulary_class_is_not_the_workbenchs(self):
        self.assertIn('panel.className = "panel spec-editor seq"', JS)
        self.assertIn(".seq .verb, .seq .text-act", CSS)

    def test_seven_sections_in_order(self):
        """Order is the TEMPLATE's, not the source's — the questions step
        is built above it as a const, which is exactly the kind of thing a
        source-order assertion would get wrong."""
        tpl = JS[JS.index("  panel.innerHTML = `"):
                 JS.index('    <div id="sp-report"></div>`;')]
        marks = [tpl.index(m) for m in
                 ('n: "01"', 'n: "02"', "${qStepHtml}", 'n: "04"',
                  'n: "05"', 'n: "06"', 'n: "07"')]
        self.assertEqual(marks, sorted(marks), "the sequence reads 01-07")
        # and each number carries the label the spec gives it
        for n, lab in [("01", "IDENTITY"), ("02", "DIRECTION"),
                       ("04", "SCOPE"), ("05", "PANELS"),
                       ("06", "EVIDENCE"), ("07", "APPROVE & LOCK")]:
            i = tpl.index(f'n: "{n}"')
            self.assertIn(f'label: "{lab}"', tpl[i:i + 200])

    def test_identity_kept_the_controls_a_guess_would_have_deleted(self):
        """The spec's own first pass dropped mode, board type, canvas and
        the slugline fields. They are real controls; step 01 holds them."""
        i = JS.index('label: "IDENTITY"')
        seg = JS[i:i + 6000]
        for probe in ("sp-subject", "sp-mode", "sp-btype", "sp-canvas",
                      "sp-intext", "sp-location", "sp-atmo"):
            self.assertIn(probe, seg, f"step 01 lost {probe}")


class TheBoardOpensOnWhatItMade(unittest.TestCase):
    """§3.15, user-approved: reviewing a specification without seeing the
    pictures it produced is reviewing it blind."""

    def test_it_reads_the_candidates(self):
        i = JS.index("async function openSpecEditor")
        self.assertIn("/candidates`).catch(() => [])", JS[i:i + 900])

    def test_each_panel_is_one_cell_frame_and_caption(self):
        self.assertIn('class="made-item"', JS)
        self.assertIn("flex: 0 0 300px", block(".made-item"),
                      "frame and caption travel together in the strip")

    def test_the_panels_read_along_one_strip(self):
        """User 2026-08-15: nine panels wrapped to three rows and pushed
        the specification off the screen. A board's panels are a sequence,
        and a sequence reads along one line."""
        b = block(".made-grid")
        self.assertIn("display: flex", b)
        self.assertIn("overflow-x: auto", b)
        self.assertNotIn("grid-template-columns", b)
        self.assertIn("cursor: grab", b)
        self.assertIn("cursor: grabbing", block(".made-grid.dragging"))

    def test_the_strip_drags_with_momentum_but_not_under_reduced_motion(self):
        i = JS.index("function dragScroll")
        b = JS[i:JS.index("function seqStep")]
        self.assertIn("pointerdown", b)
        self.assertIn("pointermove", b)
        self.assertIn("requestAnimationFrame(glide)", b)
        self.assertIn("prefers-reduced-motion: reduce", b,
                      "momentum is motion, and motion is opt-out")
        self.assertIn("el.scrollWidth - el.clientWidth", b,
                      "the glide stops at the ends rather than coasting "
                      "into a wall")
        j = JS.index('const madeStrip = $(".made-grid", panel)')
        self.assertIn("dragScroll(madeStrip)", JS[j:j + 140])

    def test_the_empty_frame_is_a_report_not_a_placeholder(self):
        """The sanctioned exception to 'never reserve the shape of the
        missing thing': the frame states the blocker that keeps it
        empty."""
        self.assertIn("NO TAKE YET", JS)
        self.assertIn("made-blocker", JS)
        self.assertIn("color: var(--bad)", block(".made-blocker"))

    def test_every_frame_is_the_same_window(self):
        """User 2026-08-15: frames that took each take's own ratio made a
        ragged strip that would not line up."""
        self.assertIn("aspect-ratio: 3 / 2", block(".made-frame"))
        i = JS.index('class="made-frame made-empty"')
        self.assertNotIn("aspect-ratio", JS[i:i + 120],
                         "the window is the constant, not the take")

    def test_the_frame_never_invents_a_blocker(self):
        """User-caught 2026-08-15: every empty frame carried a hardcoded
        "SIZE —", naming a blocker the panel did not have. A panel that
        has simply never been rendered has no size problem. The slot map
        is the authority, and a status it has no line for says nothing."""
        self.assertNotIn('SIZE — NO APPROVED TAKE FOR THIS SLOT', JS)
        i = JS.index("const VERDICT_LINE")
        seg = JS[i:i + 700]
        for status in ("TOO_SMALL", "UNAPPROVED", "STALE_APPROVAL"):
            self.assertIn(status, seg)
        j = JS.index("const verdictOf")
        self.assertIn('s.status === "OK"', JS[j:j + 260])
        self.assertIn("slot-map", JS, "the verdict comes from the authority")

    def test_an_empty_frame_goes_where_the_picture_gets_made(self):
        """User 2026-08-15: clicking a NO TAKE YET frame opens the panels
        workbench with that panel active. An empty frame has no picture to
        open, so its click is the act that resolves the consequence it
        states — while a filled frame opens its take full size."""
        i = JS.index('$$(".made-item", madeStrip)')
        seg = JS[i:i + 2000]
        self.assertIn('frame.classList.contains("made-empty")', seg)
        self.assertIn("goToPanel(pn.id)", seg)
        self.assertIn("openLightbox(items, idx)", seg,
                      "a filled frame still opens full size")
        j = JS.index("const goToPanel =")
        sel = JS[j:j + 420]
        self.assertIn("panel: pid", sel,
                      "the workbench selects by roomSel.panel")
        self.assertIn("persistRoomSel()", sel)
        self.assertIn('uiSet("boardSpec", specId)', sel)
        self.assertIn('showView("boards")', sel)

    def test_a_draft_states_the_gate_instead_of_going_nowhere(self):
        """Stage 04 lists SIGNED-OFF breakdowns only, so on a draft the
        click would land on whatever sheet stage 04 falls back to — which
        is how it behaved when first written. Gates read as state before
        they are hit."""
        i = JS.index('$$(".made-item", madeStrip)')
        seg = JS[i:i + 2000]
        self.assertIn("if (!locked)", seg)
        self.assertIn("approve & lock this", seg)
        self.assertIn("made-gated", seg)
        self.assertIn("cursor: not-allowed", block(".made-gated"))

    def test_the_frame_never_lies_about_the_take(self):
        self.assertIn("object-fit: contain", block(".made-frame img"))

    def test_it_states_the_stake_in_one_line(self):
        self.assertIn("cannot be assembled until", JS)


class TheGateAndTheQuestions(unittest.TestCase):
    def test_approve_states_its_gate_and_does_not_lie(self):
        """§3.2 — a draft with twelve open questions CAN be approved."""
        self.assertIn("YOU CAN STILL APPROVE", JS)
        i = JS.index("const approveGate")
        self.assertIn("qOpen.length", JS[i:i + 700])
        j = JS.index('id="sp-approve"')
        self.assertNotIn("approveGate", JS[j - 300:j + 300],
                         "the gate states the condition, it does not "
                         "disable the act")

    def test_questions_are_a_step_with_their_consequence(self):
        i = JS.index("const qStepHtml")
        seg = JS[i:i + 1800]
        self.assertIn('label: "OPEN QUESTIONS"', seg)
        self.assertIn("ANSWER ONE AND IT BECOMES CANON", seg)
        self.assertIn("TOLD NOT TO INVENT ONE", seg)

    def test_the_mode_aware_copy_survives(self):
        self.assertIn("EXPLORING IS HOW YOU DECIDE THEM", JS)


class TheLedgerIsHybrid(unittest.TestCase):
    """User ruling 2026-08-14, declining §3.35's always-a-table reading:
    the selects the user directed on 2026-08-13 stay while a sheet is
    drafting; a confirmed or locked ledger reads as the record it is."""

    def test_read_as_document_follows_the_step_not_only_the_lock(self):
        i = JS.index("function addLedgerRow")
        seg = JS[i:i + 2600]
        self.assertIn('const ro = locked || confIs("evidence")', seg)
        self.assertIn('${ro ? "disabled" : ""}', seg)
        self.assertNotIn('${locked ? "disabled" : ""}', seg,
                         "every control in the row follows the one fact")

    def test_drafting_keeps_the_selects(self):
        """confIs() is false on a fresh draft, so ro is false and the
        controls render as controls — the 2026-08-13 direction stands."""
        i = JS.index("const confIs = s =>")
        self.assertIn("uiGet(confKeySpec", JS[i - 400:i + 200])

    def test_the_add_row_act_steps_aside_with_the_controls(self):
        i = JS.index("const addLedgerBtn")
        self.assertIn('confIs("evidence")', JS[i:i + 220])

    def test_a_locked_sheet_still_reads_as_a_document(self):
        b = block("#sp-ledger select:disabled, #sp-ledger input:disabled,\n.panel-card select:disabled")
        self.assertIn("border-color: transparent", b)
        self.assertIn("appearance: none", b)


class ConfirmationsAreAdvisoryHereToo(unittest.TestCase):
    def test_nothing_in_the_sequence_gates_the_act(self):
        i = JS.index("const SPEC_STEPS")
        self.assertIn("advisory", JS[i - 400:i + 200].lower())

    def test_both_states_are_reversible(self):
        # Bounded by the function's end, not a character count — this slice
        # has now walked off its assertion twice as the editor grew.
        i = JS.index("async function openSpecEditor")
        seg = JS[i:JS.index("function cameraSelect(", i)]
        self.assertIn("[data-confirm]", seg)
        self.assertIn("[data-unconfirm]", seg)


if __name__ == "__main__":
    unittest.main()
