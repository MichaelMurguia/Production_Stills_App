"""Store token contracts (design-verify step 4 for `storefront/`).

The store is a separate design system, not an exempt one. These are the
mechanical assertions STORE_DESIGN_SYSTEM.md can be checked against —
run on every push, so drift fails the build instead of the eye.

The first test exists because of a real five-day defect: `--hold` was
used by the engine band's condition row (ruled by STORE_PRICING_PLAN K1)
and never defined, so CSS fell back to inherited ink and the designer's
ruling silently was not happening on the live store.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os
import tempfile

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(
        tempfile.mkdtemp(prefix="storefront-tokens-"), "t.db").replace("\\", "/"))

CSS = (ROOT / "app/static/store.css").read_text(encoding="utf-8")
TEMPLATES = ROOT / "app/templates"


def block(sel: str) -> str:
    bodies = re.findall(re.escape(sel) + r"\s*{([^}]*)}", CSS)
    assert bodies, f"missing rule: {sel}"
    return "\n".join(bodies)


class StoreTokenTests(unittest.TestCase):
    def test_every_token_used_is_defined(self):
        """A var(--x) with no --x renders as inherited ink and silently
        drops whatever the designer ruled. Never again."""
        defined = set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", CSS, re.MULTILINE))
        used = set(re.findall(r"var\((--[a-z0-9-]+)", CSS))
        for html in TEMPLATES.glob("*.html"):
            used |= set(re.findall(r"var\((--[a-z0-9-]+)",
                                   html.read_text(encoding="utf-8")))
        missing = sorted(used - defined)
        self.assertEqual(missing, [],
                         f"used but never defined in store.css: {missing}")

    def test_hold_is_the_condition_color(self):
        """--hold carries every stated condition on the store: the engine
        band's one condition row, setup notices, the router's status
        blocks. Inherited unchanged from the app system."""
        self.assertIn("--hold: #7d8fd0", CSS)
        self.assert_decl(".eb-hold", "color: var(--hold)")

    def test_warn_stays_deleted(self):
        """It aliased the accent — the same defect the app deleted in R3.
        A second amber token is how an accent budget quietly breaks."""
        self.assertNotIn("--warn:", CSS)
        self.assertNotIn("var(--warn)", CSS)

    def test_trait_marks_are_css_not_copy(self):
        """§4: the ■/□ marks are the system's, so a template that types
        them by hand can drift out of the palette."""
        self.assert_decl(".t-yes::before", 'content: "■ "')
        self.assert_decl(".t-yes::before", "color: var(--ok)")
        self.assert_decl(".t-no::before", 'content: "□ "')

    def test_amber_fills_stay_within_budget(self):
        """§8: 1–2 amber fills per page. Counted on the RENDERED page, not
        in the template — account.html carries three `btn-primary` in
        mutually exclusive branches (signed-in download, token-fallback
        download, sign-in form) and never shows more than one at once.
        Source-counting would report a violation that does not exist."""
        from fastapi.testclient import TestClient

        from app.main import store
        c = TestClient(store)
        for path in ("/", "/trial", "/pipeline", "/account", "/recover",
                     "/signin"):
            r = c.get(path)
            if r.status_code != 200:
                continue
            fills = r.text.count("btn-primary")
            self.assertLessEqual(fills, 2,
                                 f"{path} renders {fills} amber fills — "
                                 "§8 caps a page at two")

    def test_admin_console_is_courier_and_status_colored(self):
        """The operator console (NON-CANON 2026-08-06): machine tables in
        Courier, one-word states in status colors, never amber."""
        self.assert_decl(".admin-table .st-live", "color: var(--ok)")
        self.assert_decl(".admin-table .st-held", "color: var(--hold)")
        self.assert_decl(".head-admin", "font-family: var(--mono)")

    # -- helper ------------------------------------------------------------

    def assert_decl(self, sel: str, decl: str) -> None:
        self.assertIn(decl, block(sel), f"{sel}: missing '{decl}'")


if __name__ == "__main__":
    unittest.main()
