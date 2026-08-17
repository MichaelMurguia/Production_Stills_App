"""A LOCK is not a FREEZE.

User 2026-08-16: "If I have not generated a panel, and I edit a breakdown,
I need to be able to edit that panel in the breakdown. If it has an
approved panel rendered - then I should be blocked and informed why, but
NOT if there is no approved panel. It should be allowed."

The server has always worked this way. `save_spec` on a locked sheet calls
`_refuse_frozen_edits`, which refuses a panel's own fields only when THAT
panel has an approved take, and the board-level fields only when some
panel does. The UI disabled every input the moment the sheet locked, so a
locked breakdown with nothing rendered was read-only for a reason the
server would never have enforced — and the only way forward was Unlock &
edit, which VOIDS the approval, or a whole revision.

What is pinned here is the UI agreeing with the server."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
STORE = (ROOT / "app/store.py").read_text(encoding="utf-8")


def editor() -> str:
    i = JS.index("async function openSpecEditor")
    return JS[i:JS.index("\nasync function ", i + 10)]


class TheServerRuleIsPerPanel(unittest.TestCase):
    def test_a_locked_save_is_filtered_not_refused(self):
        i = STORE.index("def save_spec")
        seg = STORE[i:i + 1500]
        self.assertIn("_refuse_frozen_edits(spec_id, current, spec)", seg)
        self.assertNotIn("is already approved and locked", seg,
                         "a locked sheet is amendable, not sealed")

    def test_only_an_approved_panel_freezes_its_own_fields(self):
        i = STORE.index("def _refuse_frozen_edits")
        seg = STORE[i:i + 1400]
        self.assertIn("approved = approved_takes_by_panel(spec_id)", seg)
        self.assertIn("if not approved:\n        return", seg,
                      "nothing approved means nothing frozen")
        self.assertIn("refuse_if_panel_approved(spec_id, pid,", seg)

    def test_board_fields_freeze_only_once_something_is_approved(self):
        i = STORE.index("def _refuse_frozen_edits")
        self.assertIn("refuse_if_any_panel_approved(spec_id, changed_board)",
                      STORE[i:i + 1400])


class TheEditorAgreesWithIt(unittest.TestCase):
    def test_it_derives_the_per_panel_freeze(self):
        e = editor()
        self.assertIn("const approvedPanelIds = new Set(approvedCands.map(c => c.panel_id));", e)
        self.assertIn("const panelFrozen = pid => approvedPanelIds.has(String(pid).toUpperCase());", e)

    def test_a_panel_row_freezes_on_its_own_take(self):
        self.assertIn("const ro = panelFrozen(pid) || carriedSet.has(pid);", JS)

    def test_board_fields_gate_on_boardFrozen_not_locked(self):
        """Every board-level input used to carry `locked ? disabled`."""
        e = editor()
        self.assertNotIn('${locked ? "disabled" : ""}', e,
                         "a lock alone must not disable an input")
        self.assertGreater(e.count('${boardFrozen ? "disabled" : ""}'), 10)

    def test_save_survives_a_lock(self):
        """With nothing approved there is plenty to save, and no way to
        save it was the whole complaint."""
        e = editor()
        self.assertIn('${allFrozen ? "" : `\n        <button class="primary" id="sp-save">Save</button>', e)

    def test_approve_and_lock_does_not_come_back(self):
        """Editable is not unapproved — the sheet is still locked."""
        self.assertIn('${locked ? "" : `<button class="ghost" id="sp-approve">', JS)

    def test_adding_a_panel_or_a_row_survives_a_lock(self):
        e = editor()
        self.assertIn("""${allFrozen ? "" : '<button class="ghost" id="sp-add-panel">""", e)
        self.assertIn("""${allFrozen ? "" : '<button class="ghost" id="sp-add-ledger">""", e)


class TheStripStatesWhichCase(unittest.TestCase):
    def test_it_distinguishes_all_three(self):
        """"LOCKED — read-only" was simply false in two of the three
        states, and a gate that lies is worse than no gate."""
        e = editor()
        self.assertIn("nothing has been rendered from it yet", e)
        self.assertIn("panels have an\n             approved take", e)
        self.assertIn("Every panel has an approved take", e)

    def test_it_never_claims_read_only_outright(self):
        self.assertNotIn("Approved and read-only — objects, panels, and the ledger cannot change here",
                         JS)


class OpeningABreakdownLandsOnIt(unittest.TestCase):
    def test_the_editor_scrolls_into_view_once(self):
        """It renders below the list, so the head sat ~1500px down and the
        lock strip — the only place offering Unlock & edit — was off-screen
        (user: "'Unlock and Edit' needs to appear at the top")."""
        e = editor()
        self.assertIn("openSpecEditor._last !== specId", e)
        self.assertIn('panel.scrollIntoView({ block: "start" })', e)

    def test_a_rerender_does_not_scroll(self):
        """Confirming a step re-renders; scrolling then would throw the
        reader back to the top on every tick."""
        e = editor()
        self.assertIn("openSpecEditor._last = specId;", e)


if __name__ == "__main__":
    unittest.main()
