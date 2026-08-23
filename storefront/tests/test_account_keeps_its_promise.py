"""Regression, user-hit 2026-08-22 on the live site.

A customer redeemed a trial code and sat on /account for ten minutes
under the line "your studio is being set up — it appears right here the
moment it's ready". It does not. The page was static: no poll, no
refresh, no timeout, nothing.

Checkout has polled since it existed — `success.html` hits
`/success/status` every eight seconds and reloads when the workspace goes
ACTIVE. A TRIAL redeem lands on /account instead (`/trial/redeem`
redirects to `/account?trial=1`), and this page never learned to. The
copy made a promise only a poller can keep.
"""
from __future__ import annotations

import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ACCOUNT = (ROOT / "app" / "templates" / "account.html").read_text(encoding="utf-8")
SUCCESS = (ROOT / "app" / "templates" / "success.html").read_text(encoding="utf-8")
MAIN = (ROOT / "app" / "main.py").read_text(encoding="utf-8")


class TheAccountPageChecksBack(unittest.TestCase):
    def test_the_wait_lines_are_addressable(self):
        """Both of them — the poller rewrites whichever is on screen."""
        self.assertEqual(ACCOUNT.count('class="license-token" data-ws-wait>'),
                         2, "the pending line and the snag line")

    def test_it_polls(self):
        self.assertIn('fetch("/account/status")', ACCOUNT)
        self.assertIn("setTimeout(poll, 8000)", ACCOUNT)

    def test_it_reloads_when_nothing_is_pending(self):
        i = ACCOUNT.index('fetch("/account/status")')
        seg = ACCOUNT[i:i + 400]
        self.assertIn("if (!d.pending && !d.failed) { location.reload(); return; }",
                      seg)

    def test_a_snag_is_stated_not_spun(self):
        i = ACCOUNT.index('fetch("/account/status")')
        self.assertIn("if (d.failed)", ACCOUNT[i:i + 500])
        self.assertIn("help@screenboardstudio.com", ACCOUNT)

    def test_it_stops_claiming_to_check_eventually(self):
        """A promise the page cannot keep is what put the customer here.
        Twenty minutes, then it says so and names a way out."""
        self.assertIn("ticks >= 150", ACCOUNT)
        i = ACCOUNT.index("ticks >= 150")
        self.assertIn("taking longer than it should", ACCOUNT[i:i + 400])

    def test_it_does_nothing_when_there_is_nothing_to_wait_for(self):
        """An account with every studio live must not poll for ever."""
        self.assertIn('if (!document.querySelector("[data-ws-wait]")) return;',
                      ACCOUNT)


class TheStatusEndpointCarriesStateOnly(unittest.TestCase):
    def endpoint(self):
        i = MAIN.index('@app.get("/account/status")')
        return MAIN[i:MAIN.index('@app.get("/success/status")')]

    def test_it_answers_for_the_signed_in_account_only(self):
        seg = self.endpoint()
        self.assertIn("request.state.account_email", seg)
        self.assertIn("db.Purchase.email == email", seg)

    def test_an_anonymous_caller_learns_nothing(self):
        seg = self.endpoint()
        i = seg.index("if not email:")
        self.assertIn('{"pending": 0, "failed": 0, "active": 0}', seg[i:i + 120])

    def test_it_returns_counts_not_records(self):
        """Same contract as /success/status: state only, never a
        credential, never an address."""
        seg = self.endpoint()
        for leak in ("subdomain", "license", "token", "stripe"):
            self.assertNotIn(leak, seg.lower(), leak)

    def test_the_two_pollers_agree_on_the_shape_of_waiting(self):
        """success.html and account.html are two views of one question.
        They may differ in what they show; they may not differ in when
        they stop waiting."""
        for page in (ACCOUNT, SUCCESS):
            self.assertIn("setTimeout(poll, 8000)", page)
            self.assertIn("location.reload()", page)


class TheTrialRedeemLandsWhereThePollerIs(unittest.TestCase):
    def test_redeem_redirects_to_the_account_page(self):
        i = MAIN.index('def trial_redeem(')
        seg = MAIN[i:i + 1400]
        self.assertIn('RedirectResponse("/account?trial=1"', seg)

    def test_and_provisioning_is_actually_triggered(self):
        """The poller can only report what reconcile does. If redeeming
        stopped scheduling it, the page would poll politely for ever."""
        i = MAIN.index('def trial_redeem(')
        seg = MAIN[i:i + 1400]
        self.assertIn("provisioner.ensure_workspace_row(s, purchase)", seg)
        self.assertIn("background.add_task(provisioner.reconcile)", seg)


if __name__ == "__main__":
    unittest.main()
