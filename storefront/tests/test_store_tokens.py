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
        # X4: row acts are verbs, not machine values.
        self.assert_decl(".admin-act", "font-family: var(--sans)")
        self.assert_decl(".admin-table", "table-layout: fixed")
        # X1: the link into the console is styled exactly like the public
        # links beside it — access is not a visual style.
        self.assert_decl(".head-admin", "color: var(--ink-dim)")
        self.assert_decl(".head-admin", "font-size: 13px")
        self.assertNotIn("var(--mono)", block(".head-admin"))
        self.assertNotIn("var(--accent)", block(".head-admin"))

    # -- helper ------------------------------------------------------------

    def assert_decl(self, sel: str, decl: str) -> None:
        self.assertIn(decl, block(sel), f"{sel}: missing '{decl}'")


if __name__ == "__main__":
    unittest.main()


class OwnerChromeTests(unittest.TestCase):
    """User ruling 2026-08-06: the header carries the ADMIN link and
    nothing else — debug lives inside the admin section. The armed chip
    still appears wherever the owner stands, because a mode that changes
    what a click does must state itself and its exit."""

    def setUp(self):
        from app import settings
        self._saved = settings.OWNER_EMAILS
        self.owner = "chrome-owner@example.com"
        settings.OWNER_EMAILS = {self.owner}
        self.addCleanup(setattr, settings, "OWNER_EMAILS", self._saved)

    def _client(self, email=None):
        from fastapi.testclient import TestClient

        from app import auth, db
        from app.main import store
        from sqlalchemy import select
        c = TestClient(store)
        if email:
            with db.session() as s:
                if not s.scalar(select(db.Account).where(
                        db.Account.email == email)):
                    s.add(db.Account(email=email))
                    s.commit()
            c.cookies.set(auth.SESSION_COOKIE, auth.make_session(email))
        return c

    def test_no_debug_button_in_the_header(self):
        page = self._client(self.owner).get("/").text
        self.assertNotIn("head-debug-toggle", page)
        self.assertNotIn(">Debug<", page)
        self.assertIn('class="head-admin"', page,
                      "the ADMIN link is the owner's header chrome")

    def test_the_toggle_lives_on_admin(self):
        self.assertIn("owner-textedit",
                      self._client(self.owner).get("/admin").text)

    def test_the_armed_chip_states_its_real_exit(self):
        self.assertIn("EXIT ON /ADMIN",
                      self._client(self.owner).get("/").text)


class ReviewLedgerTests(unittest.TestCase):
    """The store's review queue must live where a design review looks.

    Store items were logged only as changelog entries for one day
    (2026-08-06) and the review could not find them — a changelog is
    history, a table is a queue. This asserts the structure that fixed
    it, so it cannot quietly regress."""

    STORE_DOC = ROOT.parent / "STORE_DESIGN_SYSTEM.md"
    APP_DOC = ROOT.parent / "app/static/DESIGN_SYSTEM.md"

    def test_the_store_has_a_review_table_before_its_changelog(self):
        text = self.STORE_DOC.read_text(encoding="utf-8")
        self.assertIn("## Non-canon — awaiting review", text)
        self.assertLess(text.index("## Non-canon — awaiting review"),
                        text.index("## Changelog"),
                        "the queue reads before the history, as in the app")
        head = text.split("## Non-canon — awaiting review", 1)[1]
        self.assertIn("| Date | What it is | Where |", head,
                      "it must be a table, not prose")

    def test_the_app_table_routes_a_reviewer_to_the_store(self):
        text = self.APP_DOC.read_text(encoding="utf-8")
        section = text.split("## Uncanonized patterns", 1)[1]
        self.assertIn("STORE_DESIGN_SYSTEM.md", section,
                      "a review that starts in the app's table must be "
                      "told the store keeps its own")
