"""RULED (user) 2026-10-07: no on-page explanations or instructions.

"Scan all tabs and pages for instructions and explanations. Remove them.
Labels are fine. No explanations or instructions."

Six rulings, guarded here as a standing contract so a later change cannot
quietly grow the prose back:

1. A gate keeps its disabled control and is a SHORT LABEL + the LINK that
   fixes it.
2. On-page cost statements are removed; the world-build consent is the
   short label "Can take up to an hour".
3. Modals and dialogs that explain are kept.
4. Tooltips and `?` help are kept.
5. Empty states are short labels; toasts say what happened; an error
   toast keeps its reason and drops its advice.
6. Labels stay.

Modal bodies, tooltips, the tutorial and the Workflow/FAQ reference tabs
are deliberately out of scope of these assertions — rules 3 and 4.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def templates() -> str:
    """The view templates — the always-visible page surfaces — without
    the Settings reference tabs (Workflow, FAQ), which are documentation
    the reader opens on purpose."""
    out = []
    for m in re.finditer(r'<template id="(tpl-[\w-]+)">(.*?)</template>', HTML, re.S):
        body = m.group(2)
        for sub in ("workflow", "faq"):
            body = re.sub(r'<div data-subview="%s".*?\n    </div>\n' % sub, "", body,
                          flags=re.S)
        out.append(body)
    return "\n".join(out)


class NoLedesOrHintsInTheTemplates(unittest.TestCase):
    def test_no_hint_paragraphs(self):
        self.assertNotIn('class="hint"', templates())

    def test_no_cost_lines(self):
        t = templates()
        self.assertNotIn('class="cost', t)
        for phrase in ("COSTS A MODEL CALL", "SPENDS MONEY", "ADVISORY"):
            self.assertNotIn(phrase, t, phrase)

    def test_no_explanatory_footnotes(self):
        t = templates()
        for cls in ("door-foot", "sec-foot", "door-nature",
                    "lib-intro", "firstrun-para", "fr-notice", "prod-start-note"):
            self.assertNotIn(cls, t, cls)
        # `.f-note` survives only as an EMPTY host that app.js fills with
        # data (a scene count, a picked line number) — never static prose.
        self.assertNotRegex(t, r'class="f-note mono"[^>]*>\s*[^<\s]')

    def test_the_labels_stay(self):
        t = templates()
        for label in ("STAGE 01 OF 5", "Script Inventory", "Current screenplay",
                      "Break it down for me", "Blank sheet", "Spec ID",
                      "<th>SPEC ID</th>", "SET DEFAULT MODELS", "YOUR ACCOUNTS"):
            self.assertIn(label, t, label)


class TheRenderedSurfacesCarryNoProse(unittest.TestCase):
    def test_the_status_lead_has_no_support_line(self):
        self.assertNotIn("next-support", JS)
        self.assertNotIn("BLOCK_SUPPORT", JS)

    def test_the_checklist_rows_have_no_sub_lines(self):
        self.assertNotIn('class="sc-sub"', JS)
        self.assertNotIn("NOTHING HERE IS BLOCKED BY US", JS)

    def test_the_world_consent_is_the_short_label(self):
        self.assertIn('const WORLD_CONSENT = "Can take up to an hour";', JS)


class GatesAreALabelAndALink(unittest.TestCase):
    def test_the_bible_gates(self):
        for snippet in ('<span class="k">NEEDS THE BIBLE</span>',
                        'NEEDS THE BIBLE &middot;',
                        'why: "NEEDS THE BIBLE", act: "Open it"'):
            self.assertIn(snippet, JS, snippet)

    def test_the_ai_model_gates_link_to_settings(self):
        self.assertIn('data-f="up-gate-go">Connect one ↗</button>', JS)
        self.assertIn('data-f="analyze-gate-go">Connect one ↗</button>', JS)

    def test_a_locked_stage_04_links_to_breakdowns(self):
        self.assertIn("NEEDS A LOCKED BREAKDOWN &middot;", JS)
        self.assertIn('data-f="to-specs">Open Breakdowns ↗</button>', JS)

    def test_cannot_lock_reasons_are_labels(self):
        i = JS.index("const computeGate = () => {")
        seg = JS[i:i + 2600]
        self.assertIn("REQUIRED OBJECT(S) WITHOUT A PASS ROW", seg)
        self.assertNotIn("the model can't promote its own guesses", seg)


class EmptyStatesAndToasts(unittest.TestCase):
    def test_empty_states_are_labels(self):
        for label in ("NO PANELS YET", "NO BREAKDOWNS YET", "NOTHING UNCAST",
                      "NO ACTIVITY YET", "NO SCREENPLAY YET"):
            self.assertIn(label, JS, label)
        self.assertNotIn("Examples will appear here from your panels.", JS)

    def test_toasts_say_what_happened(self):
        self.assertIn('toast("Bible saved");', JS)
        for advice in ("— Breakdowns are open", "— review below",
                       "Review them under CARRIED REJECTIONS",
                       "check the gallery in a minute"):
            self.assertNotIn(advice, JS, advice)

    def test_an_error_toast_keeps_its_reason(self):
        self.assertIn("toast(`The read did not finish: ${err.message}`, true);", JS)
        self.assertIn("toast(`Not saved — ${err.message}`, true);", JS)


if __name__ == "__main__":
    unittest.main()
