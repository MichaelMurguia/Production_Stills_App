"""Stop 1 of the first-user-test plan: nothing is lost, nothing refuses silently.

Ada's session, 2026-08-23 (FEEDBACK_PLAN_2026-08-23.md, items B1/B2/B3.2).
Three of these are things a user hit in the first forty minutes of the first
real test, and all three share a shape: the app knew something and did not
say it.

  B1  An answer rendered as saved that was never saved.
  B2  Two controls refused with no statement of what they wanted.
  B3.2 A launcher that reinstalled its dependencies on every start and
       introduced itself by the wrong product name.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
BAT = (ROOT / "run.bat").read_text(encoding="utf-8")
INSTALL = (ROOT / "INSTALL.md").read_text(encoding="utf-8")


def block(start: str, end: str) -> str:
    """Source between two markers — bounded by the next real landmark rather
    than a character count, which drifts into the following function as the
    file grows."""
    i = JS.index(start)
    return JS[i:JS.index(end, i)]


class AnAnswerIsNeverShownAsSavedUnlessItWas(unittest.TestCase):
    """B1.1 — 'if I reload the page I can tell you that stuff's going away.
    I don't know where.'"""

    def test_the_save_is_awaited(self):
        b = block("const saveAnalysis = ", "const renderAnalyzeLock")
        self.assertIn("async a =>", b)
        self.assertIn('await api("/api/wizard/analysis"', b)

    def test_the_failure_is_stated_to_the_user(self):
        b = block("const saveAnalysis = ", "const renderAnalyzeLock")
        self.assertIn("toast(", b)
        self.assertIn("Not saved", b)
        self.assertNotIn(".catch(() => {})", b,
                         "the swallow is the whole bug")

    def test_a_failed_save_rolls_the_cache_back(self):
        """The cache is read on the next load. Leaving a failed answer in it
        would tell the same lie one refresh later, which is exactly how this
        looked like data loss rather than a failed request."""
        b = block("const saveAnalysis = ", "const renderAnalyzeLock")
        self.assertIn("const prev = wizAnalysis;", b)
        self.assertIn("wizACacheSet(prev", b)

    def test_the_local_copy_is_still_set_first(self):
        """Typing must not wait on a round trip. The fix is honesty about
        the outcome, not a slower input."""
        b = block("const saveAnalysis = ", "const renderAnalyzeLock")
        self.assertLess(b.index("wizACacheSet(a)"), b.index("await api"))

    def test_the_recovery_path_also_speaks(self):
        """B1.2. The migration of a browser-only analysis up to the server is
        the path that RECOVERS work; silent failure there strands the read in
        one tab's localStorage."""
        i = JS.index("if (!wizAnalysis && localAnalysis) {")
        seg = JS[i:i + 900]
        self.assertNotIn(".catch(() => {})", seg)
        self.assertIn("could not be uploaded", seg)

    def test_no_write_path_swallows_its_failure(self):
        """B1.2 swept the file. The remaining `catch(() => {})` calls are all
        READS — health polls and status badges, where a toast on every failed
        poll would be noise. A write that appears here again is a regression."""
        for m in re.finditer(r"catch\(\(\) => \{\}\)", JS):
            seg = JS[max(0, m.start() - 320):m.start()]
            self.assertNotRegex(
                seg, r'method:\s*"(PUT|POST|DELETE)"',
                f"a write at offset {m.start()} swallows its own failure")


class ARefusalSaysWhatItWants(unittest.TestCase):
    """B2.1 — 'why isn't it allowing you to repair region. I don't know why
    that's a bug.' The author could not diagnose his own disabled button on a
    call; a customer has no chance."""

    def test_the_repair_dialog_has_a_gate_line(self):
        self.assertIn('data-f="gate"', JS)

    def test_it_names_which_condition_is_unmet(self):
        b = block("const gate = $(\"[data-f=gate]\"", "let erasing = false;")
        for state in ("PAINT THE REGION, THEN SAY WHAT CHANGES",
                      "NOTHING PAINTED YET",
                      "SAY WHAT SHOULD CHANGE IN THE PAINTED REGION"):
            self.assertIn(state, b, state)

    def test_it_reads_before_the_first_stroke(self):
        """A gate that only appears after you interact has already failed the
        person who was looking for it."""
        i = JS.index('instr.addEventListener("input", update);')
        self.assertIn("update();", JS[i:i + 160])

    def test_the_condition_is_not_only_a_tooltip(self):
        """The previous state of this control: a disabled button whose only
        explanation was a hover title nobody hovers."""
        b = block("const gate = $(\"[data-f=gate]\"", "let erasing = false;")
        self.assertIn("gate.textContent", b)


class ApprovingAPanelOpensBoardsVisibly(unittest.TestCase):
    """B2.2 — 'I see another bug. The board is still locked.' It was not a
    lock bug: approving is what opens stage 05 and the band never re-read, so
    Boards opened silently on the next navigation instead."""

    def test_every_approval_refreshes_the_band(self):
        n = 0
        for m in re.finditer(r"\$\{c\.candidate_id\} approved\.`\); refresh\(\);", JS):
            self.assertIn("updateBand();", JS[m.end():m.end() + 700],
                          "an approval that does not re-read the band")
            n += 1
        self.assertGreaterEqual(n, 2, "gallery and workbench both approve")

    def test_withdrawal_refreshes_it_too(self):
        """Withdrawing can CLOSE 05 again — the same fact reversed, and just
        as invisible if the band is stale."""
        n = 0
        for m in re.finditer(r"/unapprove`\)", JS):
            self.assertIn("updateBand()", JS[m.end():m.end() + 700])
            n += 1
        self.assertGreaterEqual(n, 2)

    def test_the_locked_stage_states_its_count(self):
        """Even the author guessed the wrong rule about his own gate live on
        the call — 'you might have to generate three panels'. It wants one,
        and now says so."""
        i = JS.index('label: "RENDER AND APPROVE PANELS"')
        seg = JS[i:i + 500]
        self.assertIn("tally:", seg)
        self.assertIn("ONE IS ENOUGH", seg)
        self.assertIn("NONE APPROVED YET", seg)

    def test_the_tally_reads_a_key_that_exists(self):
        """`ss.breakdowns.total` does not exist — the summary calls it
        `drafts`. A tally silently reading zero is worse than none."""
        i = JS.index('label: "DRAFT & LOCK A BREAKDOWN"')
        self.assertIn("ss.breakdowns?.drafts", JS[i:i + 400])
        self.assertNotIn("ss.breakdowns?.total", JS)
        from app import insights
        src = (ROOT / "app/insights.py").read_text(encoding="utf-8")
        self.assertIn('"drafts": len(drafts)', src)
        self.assertIn('"candidates": cand_total', src)

    def test_the_tally_is_never_amber(self):
        """Amber marks the current stage, the one primary action, and focus.
        A gate's count is a statement of fact."""
        i = CSS.index(".bp-tally")
        self.assertNotIn("--accent", CSS[i:i + 260])
        self.assertIn("--ink-faint", CSS[i:i + 260])


class TheLauncherIntroducesTheRightProduct(unittest.TestCase):
    """B3.2 — reported repeated Windows security warnings."""

    def test_it_no_longer_names_the_proof_project(self):
        """Customers downloading Screenboard Studio were greeted by
        'Beltminer Production Stills' — the proof production's name, leaked
        into the shipped launcher."""
        self.assertNotIn("Beltminer", BAT)
        self.assertIn("Screenboard Studio", BAT)

    def test_dependencies_do_not_reinstall_on_every_launch(self):
        """A network fetch from a batch script at every start: slow,
        offline-hostile, and a behaviour heuristic scanners score against an
        unsigned script."""
        self.assertIn("python -c \"import fastapi", BAT)
        self.assertIn("if errorlevel 1 (", BAT)
        i = BAT.index("python -m pip install")
        self.assertLess(BAT.index("if errorlevel 1 ("), i,
                        "pip must run only behind the probe")

    def test_the_probe_covers_every_declared_dependency(self):
        """A dependency added to requirements.txt but missing from the probe
        would never trigger the install, and the app would fail to boot after
        an upgrade with no explanation."""
        probe = BAT[BAT.index('python -c "import') : BAT.index('" >nul')]
        for module in ("fastapi", "uvicorn", "multipart", "PIL",
                       "google.genai", "openai", "pypdf", "cryptography"):
            self.assertIn(module, probe, module)
        declared = [ln.split(">")[0].split("=")[0].split("[")[0].strip()
                    for ln in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
                    if ln.strip() and not ln.startswith("#")]
        self.assertEqual(len(declared), 8,
                         "a dependency changed — update the probe in run.bat")

    def test_a_failed_install_says_why_instead_of_vanishing(self):
        self.assertIn("Dependency install failed", BAT)
        self.assertIn("exit /b 1", BAT)

    def test_the_antivirus_case_is_documented_separately(self):
        """The existing section covers 'unknown publisher', which is a
        different dialog from a different subsystem — following it would not
        have helped him, and the docs implied it would."""
        self.assertIn("If your antivirus warns about a trojan or virus", INSTALL)
        i = INSTALL.index("If your antivirus warns")
        seg = INSTALL[i:i + 1500]
        self.assertIn("different", seg.lower())
        self.assertIn("exclusion", seg.lower())
        self.assertIn("detection name", seg.lower(),
                      "an unnamed false positive cannot be submitted to a vendor")


class AnAnswerHasAWayToSaveIt(unittest.TestCase):
    """The half the first attempt missed. Hardening the transport fixed a
    save that was never being ATTEMPTED: Enter was the only commit, so
    typing and clicking away discarded the answer with no request — which
    is why there was no feedback either. Reported twice, once by Ada on the
    call and once by the fix's own test."""

    def edit(self) -> str:
        return block("answerBtn.onclick = () => {", "if (defer) defer.onclick =")

    def test_the_answer_button_becomes_the_save_button(self):
        """User-corrected 2026-08-24: "The answer button should become save,
        not spawn a new button." The second attempt added a Save BESIDE the
        Answer button that opened the field — two controls for one act, with
        the now-meaningless Answer still sitting there. One control, whose
        label always names what pressing it does next."""
        b = self.edit()
        self.assertIn('answerBtn.textContent = "Save"', b)
        self.assertIn('answerBtn.className = "primary"', b)
        self.assertIn("answerBtn.onclick = commit;", b)

    def test_no_second_button_is_created(self):
        b = self.edit()
        self.assertNotIn('document.createElement("button")', b,
                         "the row's own buttons change role; none are spawned")

    def test_decide_later_becomes_cancel_while_editing(self):
        """The other button in the row would otherwise still offer to defer
        a question the user is in the middle of answering."""
        b = self.edit()
        self.assertIn('defer.textContent = "Cancel"', b)

    def test_discarding_restores_the_buttons_own_label(self):
        b = self.edit()
        self.assertIn("const wasLabel = answerBtn.textContent;", b)
        self.assertIn("answerBtn.textContent = wasLabel;", b)

    def test_clicking_away_saves_rather_than_discards(self):
        """A surprise save is recoverable. A silent discard is the bug."""
        b = self.edit()
        self.assertIn("input.onblur", b)
        self.assertIn("commit()", b)

    def test_escape_discards_and_the_row_says_so(self):
        b = self.edit()
        self.assertIn('if (e.key === "Escape") return discard();', b)
        self.assertIn("ENTER SAVES · ESC DISCARDS", b)

    def test_the_three_paths_cannot_double_fire(self):
        """The button, Enter and blur all commit; without a latch, clicking
        Save also blurs and the answer saves twice."""
        b = self.edit()
        self.assertIn("let settled = false;", b)
        self.assertIn("if (settled) return;", b)

    def test_success_is_claimed_only_after_the_save_resolves(self):
        """The old toast fired synchronously beside a fire-and-forget PUT,
        so 'Answer saved' was printed whatever happened."""
        b = self.edit()
        self.assertIn("const ok = await patch(", b)
        i = b.index("const ok = await patch(")
        self.assertIn("if (ok && v) toast(", b[i:i + 240])

    def test_patch_reports_the_outcome(self):
        b = block("const patch = async updates", '$("[data-f=answer]", row)')
        self.assertIn("const ok = await saveAnalysis(a);", b)
        self.assertIn("return ok;", b)


class StageFourIsCompleteWhenAPanelIsApproved(unittest.TestCase):
    """The deadlock behind 'Approved a panel, 5 did not unlock'.

    The VIEW named "boards" is stage 04, Panels; the view named "assembly"
    is stage 05, Boards. Stage 04's completion read `bo.assembled` — the
    count of assembled BOARDS, which is stage 05's own output. So 04 could
    never complete, the frontier never advanced past it, and 05 rendered
    LOCKED however many panels were approved. Clicking the locked cell let
    you through, which is why it survived: it looked like a cosmetic lie
    rather than a stuck gate."""

    def test_stage_four_reads_the_panels_summary(self):
        b = block("const complete = {", "const BLOCK_STAGE")
        self.assertIn("boards: (pn.approved || 0) > 0", b)

    def test_it_no_longer_reads_the_boards_summary(self):
        b = block("const complete = {", "const BLOCK_STAGE")
        self.assertNotIn("boards: (bo.assembled", b,
                         "stage 04 cannot be gated on stage 05's output")

    def test_stage_five_still_reads_boards(self):
        b = block("const complete = {", "const BLOCK_STAGE")
        self.assertIn("assembly: (bo.approved || 0) > 0", b)

    def test_the_two_definitions_of_done_now_agree(self):
        """The frontier (which draws the lock) and the gate chain (which
        explains it) disagreed: the chain opened 05 on an approved panel
        while the frontier demanded an assembled board. A lock whose own
        popover finds nothing outstanding is the shape of that bug."""
        chain = block('label: "RENDER AND APPROVE PANELS"', "];")
        self.assertIn("(ss.panels?.approved || 0) > 0", chain)
        comp = block("const complete = {", "const BLOCK_STAGE")
        self.assertIn("pn.approved", comp)


class TheGateIsHardToMiss(unittest.TestCase):
    """Reported after the first attempt: 'Works but not obvious enough.'
    The condition was stated, as dim caption text among eight other
    controls in the repair toolbar."""

    def test_it_is_a_chip_not_a_caption(self):
        self.assertIn('class="repair-gate mono"', JS)
        i = CSS.index(".repair-gate")
        seg = CSS[i:i + 300]
        self.assertIn("border:", seg)
        self.assertIn("var(--ink)", seg)

    def test_it_is_still_not_amber(self):
        """Amber marks the action; this is the reason the action cannot be
        taken. Same ruling as the tally."""
        i = CSS.index(".repair-gate")
        self.assertNotIn("--accent", CSS[i:i + 300])

    def test_it_disappears_once_the_gate_is_met(self):
        """An empty bordered box beside an enabled button is noise."""
        b = block("const gate = $(\"[data-f=gate]\"", "let erasing = false;")
        self.assertIn('gate.classList.toggle("hidden", painted && said)', b)


class TheBandActuallyUnlocksFive(unittest.TestCase):
    """Behaviour, not source strings — this runs the real band logic out of
    app.js under node against two states.

    Needed because the string assertions above would have passed against the
    broken code too: `boards: (bo.assembled || 0) > 0` is a perfectly
    plausible line. Only executing it shows that stage 05 never opens.
    Skips where node is unavailable; the source assertions still stand."""

    HARNESS = """
%(order)s
function bandFor(ss) {
  const pd = ss.production_design || {}, bd = ss.breakdowns || {},
        pn = ss.panels || {}, bo = ss.boards || {};
%(complete)s
  const frontier = STAGE_ORDER.find(s => !complete[s]) || "assembly";
  const i = STAGE_ORDER.indexOf(frontier);
  return { frontier, locked: STAGE_ORDER.filter((s, n) => n > i) };
}
const base = { screenplay: "x.pdf", production_design: { bible_saved: true },
               breakdowns: { locked: 1, drafts: 1 } };
const out = {
  none: bandFor({ ...base, panels: { approved: 0, candidates: 3 },
                  boards: { assembled: 0, approved: 0 } }),
  one:  bandFor({ ...base, panels: { approved: 1, candidates: 3 },
                  boards: { assembled: 0, approved: 0 } }),
};
console.log(JSON.stringify(out));
"""

    def band(self) -> dict:
        import json as _json
        import shutil
        import subprocess
        import tempfile
        if not shutil.which("node"):
            self.skipTest("node not available")
        i = JS.index("const STAGE_ORDER = [")
        order = JS[i:JS.index(chr(10), i) + 1]
        a = JS.index("const complete = {")
        complete = JS[a:JS.index("const BLOCK_STAGE", a)]
        src = self.HARNESS % {"order": order, "complete": complete}
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "band.js"
            f.write_text(src, encoding="utf-8")
            r = subprocess.run(["node", str(f)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return _json.loads(r.stdout)

    def test_five_is_locked_until_a_panel_is_approved(self):
        self.assertIn("assembly", self.band()["none"]["locked"])

    def test_five_opens_the_moment_one_panel_is_approved(self):
        """The reported failure: 'Approved a panel, 5 did not unlock.'"""
        b = self.band()["one"]
        self.assertNotIn("assembly", b["locked"])
        self.assertEqual(b["frontier"], "assembly")

    def test_an_assembled_board_is_not_what_opens_stage_five(self):
        """Stage 05 is where boards are MADE. Gating it on a board existing
        is the deadlock, and it reads as plausible in review — which is why
        this test executes the logic instead of reading it."""
        b = self.band()["one"]
        self.assertEqual(b["locked"], [],
                         "nothing should be locked with zero boards assembled")


if __name__ == "__main__":
    unittest.main()
