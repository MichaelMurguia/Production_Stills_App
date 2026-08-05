"""Trials, both kinds.

**Card trial** — a Stripe subscription that starts in trial with the
payment method captured; Stripe converts it and the webhook keeps our
copy of the date honest. We must never end one ourselves.

**Code trial** — an operator grant with no payment method. Nothing
external will ever end it, so reconcile does: past its date the purchase
goes EXPIRED and the studio is revoked through the same path a canceled
subscription takes.

Run from storefront/:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-trials-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import auth, db, provisioner, settings, trials  # noqa: E402
from app.main import store  # noqa: E402
import app.main as main  # noqa: E402


def _mk_account(email: str) -> None:
    with db.session() as s:
        if not s.scalar(select(db.Account).where(db.Account.email == email)):
            s.add(db.Account(email=email))
            s.commit()


def _signed_in(email: str) -> TestClient:
    """A client carrying a real signed session cookie — the same value the
    magic link would set."""
    _mk_account(email)
    c = TestClient(store)
    c.cookies.set(auth.SESSION_COOKIE, auth.make_session(email))
    return c


class FakeRailway:
    """Enough of the Railway client for provisioning and revocation —
    same return shapes as the real module (strings, not dicts)."""

    def __init__(self):
        self.deleted: list[str] = []
        self.n = 0

    def create_service(self, name):
        self.n += 1
        return f"svc-{self.n}"

    def create_volume(self, service_id, mount_path):
        return f"vol-{self.n}"

    def upsert_variables(self, service_id, variables):
        return None

    def set_start_command(self, service_id, cmd):
        return None

    def create_domain(self, service_id):
        return f"tenant-{self.n}.up.railway.app"

    def service_domains(self, service_id):
        return [f"tenant-{self.n}.up.railway.app"]

    def create_custom_domain_records(self, service_id, domain):
        return []

    def configure_graceful_deploys(self, service_id):
        return None

    def redeploy(self, service_id):
        return None

    def deploy_latest(self, service_id, commit_sha=""):
        return None

    def delete_service(self, service_id):
        self.deleted.append(service_id)


# ----------------------------------------------------------- code trials

class CodeTrialTests(unittest.TestCase):
    def setUp(self):
        self.email = f"trial-{uuid.uuid4().hex[:8]}@example.com"

    def _code(self, **kw) -> db.TrialCode:
        with db.session() as s:
            row = trials.create_code(s, **{"days": 30, **kw})
            s.expunge_all()
            return row

    def test_code_shape_is_typeable(self):
        code = trials.generate_code()
        self.assertRegex(code, r"^SB-[A-Z2-9]{4}-[A-Z2-9]{4}$")
        for banned in ("I", "O", "0", "1"):
            self.assertNotIn(banned, code.split("-", 1)[1],
                             "ambiguous characters must never appear")

    def test_normalize_accepts_what_humans_type(self):
        code = trials.generate_code()
        raw = code.replace("-", "").lower()
        self.assertEqual(trials.normalize(raw), code)
        self.assertEqual(trials.normalize(f"  {code.lower()}  "), code)
        self.assertEqual(trials.normalize("nonsense"), "")

    def test_redeem_creates_a_cloud_entitlement_with_an_end_date(self):
        row = self._code(days=45, tier="business")
        with db.session() as s:
            p = trials.redeem(s, row.code.lower().replace("-", ""), self.email)
            self.assertEqual(p.kind, "cloud")
            self.assertEqual(p.tier, "business")
            self.assertEqual(p.status, "PAID")
            self.assertEqual(p.trial_kind, "code")
            self.assertTrue(p.on_trial)
            self.assertEqual(p.trial_days_left, 45)
            self.assertTrue(p.stripe_session_id.startswith("trial_code:"))
            self.assertEqual(p.stripe_subscription_id, "",
                             "a code trial has no Stripe object at all")
            code = s.scalar(select(db.TrialCode).where(
                db.TrialCode.code == row.code))
            self.assertEqual(code.uses, 1)

    def test_a_code_is_spent_after_its_uses(self):
        row = self._code(max_uses=2)
        with db.session() as s:
            trials.redeem(s, row.code, f"a-{self.email}")
            trials.redeem(s, row.code, f"b-{self.email}")
            with self.assertRaises(trials.TrialError) as ctx:
                trials.redeem(s, row.code, f"c-{self.email}")
            self.assertIn("full number of times", str(ctx.exception))

    def test_withdrawn_and_stale_codes_state_their_refusal(self):
        row = self._code()
        with db.session() as s:
            s.get(db.TrialCode, row.id).disabled = 1
            s.commit()
            with self.assertRaises(trials.TrialError) as ctx:
                trials.redeem(s, row.code, self.email)
            self.assertIn("withdrawn", str(ctx.exception))

        stale = self._code(valid_days=1)
        with db.session() as s:
            s.get(db.TrialCode, stale.id).expires_at = (
                dt.datetime.utcnow() - dt.timedelta(minutes=1))
            s.commit()
            with self.assertRaises(trials.TrialError) as ctx:
                trials.redeem(s, stale.code, self.email)
            self.assertIn("expiry", str(ctx.exception))

    def test_unknown_code_never_reveals_whether_it_exists(self):
        with db.session() as s:
            with self.assertRaises(trials.TrialError) as ctx:
                trials.redeem(s, "SB-ZZZZ-ZZZZ", self.email)
            self.assertEqual(str(ctx.exception), "That code is not recognized.")

    def test_one_studio_per_account(self):
        a, b = self._code(), self._code()
        with db.session() as s:
            trials.redeem(s, a.code, self.email)
            with self.assertRaises(trials.TrialError) as ctx:
                trials.redeem(s, b.code, self.email)
            self.assertIn("already has a studio", str(ctx.exception))

    def test_expiry_revokes_the_studio_through_reconcile(self):
        row = self._code(days=7)
        fake = FakeRailway()
        settings.RAILWAY_API_TOKEN = "tok"
        settings.RAILWAY_PROJECT_ID = "proj"
        settings.RAILWAY_ENVIRONMENT_ID = "env"

        def unconfigure():
            settings.RAILWAY_API_TOKEN = ""
            settings.RAILWAY_PROJECT_ID = ""
            settings.RAILWAY_ENVIRONMENT_ID = ""
        self.addCleanup(unconfigure)
        with db.session() as s:
            p = trials.redeem(s, row.code, self.email)
            pid = p.id
        provisioner.reconcile(railway=fake)
        with db.session() as s:
            ws = s.scalar(select(db.Workspace).where(
                db.Workspace.purchase_id == pid))
            self.assertEqual(ws.status, "ACTIVE", "a trial gets a real studio")
            service_id = ws.railway_service_id
            # Wind the clock past the grant.
            s.get(db.Purchase, pid).trial_ends_at = (
                dt.datetime.utcnow() - dt.timedelta(minutes=1))
            s.commit()

        out = provisioner.reconcile(railway=fake)
        self.assertEqual(out["expired"], 1)
        self.assertEqual(out["revoked"], 1)
        self.assertIn(service_id, fake.deleted,
                      "the tenant service must actually be deleted")
        with db.session() as s:
            p = s.get(db.Purchase, pid)
            ws = s.scalar(select(db.Workspace).where(
                db.Workspace.purchase_id == pid))
            self.assertEqual(p.status, "EXPIRED")
            self.assertFalse(p.on_trial)
            self.assertEqual(ws.status, "REVOKED")
            self.assertIn("trial ended", ws.detail)
            self.assertEqual(ws.subdomain, "",
                             "the name returns to the pool")

    def test_a_card_trial_is_never_expired_by_our_clock(self):
        """Stripe owns a subscription with a payment method on it. If our
        sweep touched card trials, a clock skew would revoke a studio
        someone is paying for."""
        with db.session() as s:
            p = db.Purchase(kind="cloud", tier="personal",
                            email=f"card-{self.email}",
                            stripe_session_id=f"cs_{uuid.uuid4().hex}",
                            stripe_subscription_id=f"sub_{uuid.uuid4().hex}",
                            status="PAID", trial_kind="card",
                            trial_ends_at=dt.datetime.utcnow() - dt.timedelta(days=3))
            s.add(p)
            s.commit()
            pid = p.id
            self.assertEqual(trials.expire_due(s), [])
            self.assertEqual(s.get(db.Purchase, pid).status, "PAID")


# ------------------------------------------------------------ the routes

class TrialRouteTests(unittest.TestCase):
    def setUp(self):
        self.email = f"route-{uuid.uuid4().hex[:8]}@example.com"

    def test_trial_page_states_the_gate_when_trials_are_closed(self):
        saved = settings.TRIAL_DAYS
        settings.TRIAL_DAYS = 0
        self.addCleanup(setattr, settings, "TRIAL_DAYS", saved)
        r = TestClient(store).get("/trial")
        self.assertEqual(r.status_code, 200)
        self.assertIn("NOT SWITCHED ON YET", r.text)
        self.assertNotIn("/trial/start/cloud-personal", r.text)
        # The code door stays open — codes never needed Stripe.
        self.assertIn("/trial/redeem", r.text)

    def test_start_redirects_with_a_stated_reason_when_closed(self):
        saved = settings.TRIAL_DAYS
        settings.TRIAL_DAYS = 0
        self.addCleanup(setattr, settings, "TRIAL_DAYS", saved)
        r = TestClient(store).get("/trial/start/cloud-personal",
                                  follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertIn("/trial?error=", r.headers["location"])

    def test_one_time_plans_cannot_be_trialed(self):
        r = TestClient(store).get("/trial/start/download-personal",
                                  follow_redirects=False)
        self.assertEqual(r.status_code, 404)

    def test_redeeming_signed_out_holds_the_code_across_sign_in(self):
        with db.session() as s:
            row = trials.create_code(s, days=21)
            code = row.code
        c = TestClient(store)
        r = c.post("/trial/redeem", data={"code": code},
                   follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertEqual(r.headers["location"], "/signin?trial=1")
        self.assertIn(main.TRIAL_COOKIE, r.cookies)
        # The sign-in page says the code is safe.
        self.assertIn("REDEEMS ITSELF", c.get("/signin?trial=1").text)

        # Completing a magic-link sign-in redeems it on the spot.
        with db.session() as s:
            t = db.LoginToken(email=self.email)
            s.add(t)
            s.commit()
            token = t.token
        r = c.get(f"/auth/verify?token={token}", follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertEqual(r.headers["location"], "/account?trial=1")
        self.assertIn(auth.SESSION_COOKIE, r.cookies,
                      "the session must survive the redirect rewrite")
        with db.session() as s:
            p = s.scalar(select(db.Purchase).where(
                db.Purchase.email == self.email))
            self.assertIsNotNone(p)
            self.assertEqual(p.trial_kind, "code")
            self.assertEqual(p.trial_days_left, 21)

    def test_redeeming_signed_in_lands_on_the_account(self):
        with db.session() as s:
            code = trials.create_code(s, days=10).code
        c = _signed_in(self.email)
        r = c.post("/trial/redeem", data={"code": code.lower()},
                   follow_redirects=False)
        self.assertEqual(r.headers["location"], "/account?trial=1")
        page = c.get("/account").text
        self.assertIn("TRIAL", page)
        self.assertIn("NO CARD ON FILE", page)

    def test_a_bad_code_returns_a_stated_error_not_a_500(self):
        c = _signed_in(self.email)
        r = c.post("/trial/redeem", data={"code": "SB-QQQQ-QQQQ"},
                   follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertIn("error=", r.headers["location"])
        self.assertIn("not+recognized", r.headers["location"].replace("%20", "+"))

    def test_trial_page_reports_a_running_trial_instead_of_selling(self):
        with db.session() as s:
            code = trials.create_code(s, days=12).code
        c = _signed_in(self.email)
        c.post("/trial/redeem", data={"code": code})
        page = c.get("/trial").text
        self.assertIn("Your trial is running.", page)
        self.assertIn("12 DAYS LEFT", page)
        self.assertNotIn("Start the trial", page)


# ----------------------------------------------------- card trial + Stripe

class CardTrialTests(unittest.TestCase):
    def test_checkout_asks_stripe_for_a_trial_with_the_card_taken(self):
        captured = {}

        class FakeSession:
            url = "https://stripe.test/session"

            @staticmethod
            def create(**kw):
                captured.update(kw)
                return FakeSession()

        saved_days, saved_key, saved_price = (
            settings.TRIAL_DAYS, settings.STRIPE_SECRET_KEY,
            settings.STRIPE_PRICE_CLOUD_PERSONAL)
        settings.TRIAL_DAYS = 14
        settings.STRIPE_SECRET_KEY = "sk_test"
        settings.STRIPE_PRICE_CLOUD_PERSONAL = "price_cloud_personal"
        real = main.stripe.checkout.Session
        main.stripe.checkout.Session = FakeSession

        def restore():
            settings.TRIAL_DAYS = saved_days
            settings.STRIPE_SECRET_KEY = saved_key
            settings.STRIPE_PRICE_CLOUD_PERSONAL = saved_price
            main.stripe.checkout.Session = real
        self.addCleanup(restore)

        r = TestClient(store).get("/trial/start/cloud-personal",
                                  follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertEqual(captured["mode"], "subscription")
        self.assertEqual(captured["subscription_data"]["trial_period_days"], 14)
        self.assertEqual(captured["payment_method_collection"], "always",
                         "without this the card is never taken and the "
                         "conversion silently fails on day N")
        self.assertEqual(captured["metadata"]["trial_days"], "14")
        self.assertEqual(captured["line_items"][0]["price"],
                         "price_cloud_personal",
                         "a trial runs on the real plan price")

    def test_fulfillment_records_the_trial_window(self):
        sid = f"cs_{uuid.uuid4().hex}"
        session = type("S", (), {
            "id": sid, "mode": "subscription",
            "metadata": {"plan": "cloud-personal", "trial_days": "14"},
            "customer_details": {"email": f"card-{uuid.uuid4().hex[:6]}@example.com"},
            "customer": "cus_1", "subscription": "sub_1",
            "payment_intent": None, "payment_status": "no_payment_required"})()
        purchase = main._fulfill(session)
        self.assertEqual(purchase.kind, "cloud")
        self.assertEqual(purchase.trial_kind, "card")
        self.assertTrue(purchase.on_trial)
        self.assertEqual(purchase.trial_days_left, 14)

    def test_conversion_clears_the_countdown(self):
        """When Stripe converts the subscription, the account page must
        stop counting down — the entitlement now stands on its own."""
        sid = f"cs_{uuid.uuid4().hex}"
        sub = f"sub_{uuid.uuid4().hex}"
        with db.session() as s:
            s.add(db.Purchase(
                kind="cloud", tier="personal", email="conv@example.com",
                stripe_session_id=sid, stripe_subscription_id=sub,
                status="PAID", trial_kind="card",
                trial_ends_at=dt.datetime.utcnow() + dt.timedelta(days=3)))
            s.commit()

        main._handle_subscription_updated({"id": sub, "status": "active",
                                           "trial_end": None})
        with db.session() as s:
            p = s.scalar(select(db.Purchase).where(
                db.Purchase.stripe_subscription_id == sub))
            self.assertEqual(p.trial_kind, "")
            self.assertIsNone(p.trial_ends_at)
            self.assertFalse(p.on_trial)
            self.assertEqual(p.status, "PAID", "the studio keeps running")

    def test_stripes_trial_end_corrects_our_copy(self):
        sid = f"cs_{uuid.uuid4().hex}"
        sub = f"sub_{uuid.uuid4().hex}"
        with db.session() as s:
            s.add(db.Purchase(
                kind="cloud", tier="personal", email="corr@example.com",
                stripe_session_id=sid, stripe_subscription_id=sub,
                status="PAID", trial_kind="card",
                trial_ends_at=dt.datetime.utcnow() + dt.timedelta(days=14)))
            s.commit()
        real_end = dt.datetime.utcnow() + dt.timedelta(days=9)
        main._handle_subscription_updated({
            "id": sub, "status": "trialing",
            "trial_end": int(real_end.replace(
                tzinfo=dt.timezone.utc).timestamp())})
        with db.session() as s:
            p = s.scalar(select(db.Purchase).where(
                db.Purchase.stripe_subscription_id == sub))
            self.assertEqual(p.trial_days_left, 9)


# ------------------------------------------------------ operator console

class AdminTrialTests(unittest.TestCase):
    def setUp(self):
        self.saved = settings.ADMIN_EXPORT_TOKEN
        settings.ADMIN_EXPORT_TOKEN = "admin-token-for-tests"
        self.addCleanup(setattr, settings, "ADMIN_EXPORT_TOKEN", self.saved)
        self.c = TestClient(store)
        self.tok = settings.ADMIN_EXPORT_TOKEN

    def test_console_is_gated_like_every_other_admin_endpoint(self):
        self.assertEqual(self.c.get("/admin/trials").status_code, 404)
        self.assertEqual(
            self.c.get("/admin/trials?token=wrong").status_code, 404)
        self.assertEqual(
            self.c.get(f"/admin/trials?token={self.tok}").status_code, 200)

    def test_minting_a_code_shows_it_in_the_console(self):
        r = self.c.post("/admin/trials/new", data={
            "token": self.tok, "days": 60, "tier": "business",
            "max_uses": 5, "valid_days": 0, "note": "DP intro call"},
            follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        page = self.c.get(f"/admin/trials?token={self.tok}").text
        self.assertIn("DP intro call", page)
        self.assertIn("0 / 5", page)
        self.assertIn("LIVE", page)

    def test_days_are_bounded_by_config(self):
        self.c.post("/admin/trials/new", data={
            "token": self.tok, "days": 99999, "tier": "personal",
            "max_uses": 1, "valid_days": 0, "note": "bounds check"})
        with db.session() as s:
            row = s.scalars(select(db.TrialCode).order_by(
                db.TrialCode.id.desc())).first()
            self.assertEqual(row.days, settings.TRIAL_CODE_MAX_DAYS)

    def test_withdraw_and_end_now(self):
        with db.session() as s:
            code = trials.create_code(s, days=30, note="to withdraw").code
        self.c.post("/admin/trials/disable",
                    data={"token": self.tok, "code": code})
        with db.session() as s:
            row = s.scalar(select(db.TrialCode).where(
                db.TrialCode.code == code))
            self.assertEqual(row.state(), "DISABLED")

        email = f"end-{uuid.uuid4().hex[:8]}@example.com"
        with db.session() as s:
            live = trials.create_code(s, days=30).code
            trials.redeem(s, live, email)
        self.c.post("/admin/trials/end",
                    data={"token": self.tok, "email": email})
        with db.session() as s:
            p = s.scalar(select(db.Purchase).where(db.Purchase.email == email))
            self.assertEqual(p.status, "EXPIRED")


if __name__ == "__main__":
    unittest.main()


# ------------------------------------------------------- the admin hub

class AdminHubTests(unittest.TestCase):
    """The store's operator console: one page, two ways in. A signed-in
    owner needs no token; everyone else needs the shared one; everything
    else 404s (an admin surface must not confirm its own existence)."""

    def setUp(self):
        self.saved_tok = settings.ADMIN_EXPORT_TOKEN
        self.saved_owners = settings.OWNER_EMAILS
        settings.ADMIN_EXPORT_TOKEN = "hub-token-for-tests"
        self.owner = f"owner-{uuid.uuid4().hex[:8]}@example.com"
        settings.OWNER_EMAILS = {self.owner}
        self.addCleanup(setattr, settings, "ADMIN_EXPORT_TOKEN", self.saved_tok)
        self.addCleanup(setattr, settings, "OWNER_EMAILS", self.saved_owners)

    def test_owner_session_opens_the_hub_without_a_token(self):
        c = _signed_in(self.owner)
        r = c.get("/admin")
        self.assertEqual(r.status_code, 200)
        self.assertIn("MINT A TRIAL CODE", r.text)
        self.assertIn("DEBUG TOOLS", r.text)
        self.assertIn("OPERATIONS", r.text)
        # No secret is ever printed into the page for a session owner.
        self.assertNotIn(settings.ADMIN_EXPORT_TOKEN, r.text)

    def test_a_signed_in_stranger_gets_nothing(self):
        c = _signed_in(f"stranger-{uuid.uuid4().hex[:8]}@example.com")
        self.assertEqual(c.get("/admin").status_code, 404)

    def test_signed_out_needs_the_token(self):
        c = TestClient(store)
        self.assertEqual(c.get("/admin").status_code, 404)
        self.assertEqual(
            c.get(f"/admin?token={settings.ADMIN_EXPORT_TOKEN}").status_code, 200)
        self.assertEqual(
            c.get("/admin", headers={
                "authorization": f"Bearer {settings.ADMIN_EXPORT_TOKEN}"}
            ).status_code, 200)

    def test_the_admin_link_shows_only_for_an_owner(self):
        self.assertIn('href="/admin"', _signed_in(self.owner).get("/").text)
        self.assertNotIn(
            'class="head-admin"',
            _signed_in(f"buyer-{uuid.uuid4().hex[:8]}@example.com").get("/").text)
        self.assertNotIn('class="head-admin"', TestClient(store).get("/").text)

    def test_minting_from_the_hub_needs_no_token_for_an_owner(self):
        c = _signed_in(self.owner)
        r = c.post("/admin/trials/new", data={
            "token": "", "days": 21, "tier": "personal", "max_uses": 1,
            "valid_days": 0, "note": "hub mint"}, follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertTrue(r.headers["location"].startswith("/admin?ok="))
        self.assertIn("hub mint", c.get("/admin").text)

    def test_the_old_console_address_still_works(self):
        """It is in the runbook — it redirects to the hub."""
        c = _signed_in(self.owner)
        r = c.get("/admin/trials", follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertEqual(r.headers["location"], "/admin")

    def test_ops_buttons_call_the_same_functions_as_the_runbook(self):
        c = _signed_in(self.owner)
        r = c.post("/admin/ops", data={"token": "", "action": "reconcile"},
                   follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertIn("reconcile", r.headers["location"])
        # Unknown actions are stated, never executed.
        r = c.post("/admin/ops", data={"token": "", "action": "rm -rf"},
                   follow_redirects=False)
        self.assertIn("unknown", r.headers["location"])

    def test_debug_tools_left_the_account_page(self):
        c = _signed_in(self.owner)
        page = c.get("/account").text
        self.assertNotIn("owner-textedit", page,
                         "the customer view is not the operator console")
        self.assertIn("/ADMIN", page.upper())


class BothEditionsTrialTests(unittest.TestCase):
    """User ruling 2026-08-06: both editions trial. Personal takes the
    page's one amber fill as the common path; Business sits beside it as
    a ghost — §8 forbids two fills side by side."""

    def setUp(self):
        self.saved = (settings.TRIAL_DAYS, settings.STRIPE_SECRET_KEY,
                      settings.STRIPE_PRICE_CLOUD_PERSONAL,
                      settings.STRIPE_PRICE_CLOUD_BUSINESS)
        settings.TRIAL_DAYS = 5
        settings.STRIPE_SECRET_KEY = "sk_test"
        settings.STRIPE_PRICE_CLOUD_PERSONAL = "price_p"
        settings.STRIPE_PRICE_CLOUD_BUSINESS = "price_b"

        def restore():
            (settings.TRIAL_DAYS, settings.STRIPE_SECRET_KEY,
             settings.STRIPE_PRICE_CLOUD_PERSONAL,
             settings.STRIPE_PRICE_CLOUD_BUSINESS) = self.saved
        self.addCleanup(restore)

    def test_both_acts_render_with_one_fill(self):
        page = TestClient(store).get("/trial").text
        self.assertIn("Start Personal Trial", page)
        self.assertIn("Start Business Trial", page)
        self.assertIn('btn-primary" href="/trial/start/cloud-personal"', page)
        self.assertIn('btn-secondary" href="/trial/start/cloud-business"', page)
        self.assertEqual(page.count("btn-primary"), 1,
                         "two fills side by side is exactly what §8 forbids")

    def test_business_trial_opens_a_business_subscription(self):
        captured = {}

        class FakeSession:
            url = "https://stripe.test/s"

            @staticmethod
            def create(**kw):
                captured.update(kw)
                return FakeSession()

        real = main.stripe.checkout.Session
        main.stripe.checkout.Session = FakeSession
        self.addCleanup(setattr, main.stripe.checkout, "Session", real)
        r = TestClient(store).get("/trial/start/cloud-business",
                                  follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertEqual(captured["line_items"][0]["price"], "price_b")
        self.assertEqual(captured["metadata"]["plan"], "cloud-business")
        self.assertEqual(captured["subscription_data"]["trial_period_days"], 5)
        self.assertEqual(captured["payment_method_collection"], "always")

    def test_an_edition_without_a_price_is_simply_not_offered(self):
        settings.STRIPE_PRICE_CLOUD_BUSINESS = ""
        page = TestClient(store).get("/trial").text
        self.assertIn("Start Personal Trial", page)
        self.assertNotIn("Start Business Trial", page)


class ExpiryPickerTests(unittest.TestCase):
    """CODE EXPIRES is the code's own shelf life, counted from minting —
    a different clock from DAYS, which is the trial's length counted from
    redemption. The picker offers the common answers and defers to a
    number field for anything else (user, 2026-08-06)."""

    def setUp(self):
        self.saved_tok = settings.ADMIN_EXPORT_TOKEN
        self.saved_owners = settings.OWNER_EMAILS
        settings.ADMIN_EXPORT_TOKEN = "expiry-token"
        self.owner = f"expiry-{uuid.uuid4().hex[:8]}@example.com"
        settings.OWNER_EMAILS = {self.owner}
        self.addCleanup(setattr, settings, "ADMIN_EXPORT_TOKEN", self.saved_tok)
        self.addCleanup(setattr, settings, "OWNER_EMAILS", self.saved_owners)
        self.c = _signed_in(self.owner)

    def _mint(self, **form):
        self.c.post("/admin/trials/new", data={
            "token": "", "days": 30, "tier": "personal", "max_uses": 1,
            "note": f"probe {uuid.uuid4().hex[:6]}", **form})
        with db.session() as s:
            row = s.scalars(select(db.TrialCode).order_by(
                db.TrialCode.id.desc())).first()
            s.expunge_all()
            return row

    def test_the_picker_offers_five_ten_and_custom(self):
        page = self.c.get("/admin").text
        for value in ('value="0"', 'value="5"', 'value="10"',
                      'value="30"', 'value="90"', 'value="custom"'):
            self.assertIn(value, page)
        self.assertIn("valid_days_custom", page)

    def test_a_picked_value_sets_the_shelf_life(self):
        row = self._mint(valid_days="5")
        self.assertIsNotNone(row.expires_at)
        days = round((row.expires_at - dt.datetime.utcnow()).total_seconds() / 86400)
        self.assertEqual(days, 5)
        self.assertEqual(row.state(), "LIVE")

    def test_custom_defers_to_the_number_beside_it(self):
        row = self._mint(valid_days="custom", valid_days_custom=17)
        days = round((row.expires_at - dt.datetime.utcnow()).total_seconds() / 86400)
        self.assertEqual(days, 17)

    def test_never_leaves_the_code_without_an_expiry(self):
        self.assertIsNone(self._mint(valid_days="0").expires_at)

    def test_the_shelf_life_is_bounded_and_garbage_is_never_a_500(self):
        row = self._mint(valid_days="custom", valid_days_custom=99999)
        days = round((row.expires_at - dt.datetime.utcnow()).total_seconds() / 86400)
        self.assertEqual(days, settings.TRIAL_CODE_MAX_DAYS)
        # An unparseable pick means no expiry, never a crash.
        self.assertIsNone(self._mint(valid_days="tuesday").expires_at)

    def test_the_two_clocks_stay_independent(self):
        """A code that goes stale cannot shorten a trial already redeemed
        from it — the trial's end date is stamped at redemption."""
        row = self._mint(valid_days="5", days=30)
        email = f"clocks-{uuid.uuid4().hex[:8]}@example.com"
        with db.session() as s:
            p = trials.redeem(s, row.code, email)
            self.assertEqual(p.trial_days_left, 30)
            # Now age the CODE past its shelf life.
            s.get(db.TrialCode, row.id).expires_at = (
                dt.datetime.utcnow() - dt.timedelta(days=1))
            s.commit()
            self.assertEqual(s.get(db.TrialCode, row.id).state(), "STALE")
            self.assertEqual(trials.expire_due(s), [],
                             "a stale code must not end a running trial")
            self.assertEqual(s.get(db.Purchase, p.id).status, "PAID")


class MailPathTests(unittest.TestCase):
    """A magic link must not make the visitor wait on SMTP (user-hit
    2026-08-06: 20 seconds), and a failed send must be visible to the
    owner — the visitor's response is uniform by design, so a failure
    otherwise vanishes into the platform log."""

    def setUp(self):
        from app import mailer
        self.mailer = mailer
        self.saved_owners = settings.OWNER_EMAILS
        self.saved_tok = settings.ADMIN_EXPORT_TOKEN
        self.saved_host, self.saved_from = settings.SMTP_HOST, settings.SMTP_FROM
        settings.SMTP_HOST, settings.SMTP_FROM = "smtp.test", "no-reply@test"
        self.owner = f"mail-{uuid.uuid4().hex[:8]}@example.com"
        settings.OWNER_EMAILS = {self.owner}
        settings.ADMIN_EXPORT_TOKEN = "mail-token"
        mailer._recent.clear()

        def restore():
            settings.OWNER_EMAILS = self.saved_owners
            settings.ADMIN_EXPORT_TOKEN = self.saved_tok
            settings.SMTP_HOST, settings.SMTP_FROM = self.saved_host, self.saved_from
        self.addCleanup(restore)

    def test_the_send_happens_after_the_response(self):
        """The route must hand the send to a background task, never call
        it inline — that is the whole 20-second defect."""
        calls = []
        real = self.mailer.send
        self.mailer.send = lambda *a, **k: calls.append(a)
        self.addCleanup(setattr, self.mailer, "send", real)

        import starlette.background as sb
        seen = []
        real_add = sb.BackgroundTasks.add_task

        def spy(self_, fn, *a, **k):
            seen.append(fn.__name__)
            return real_add(self_, fn, *a, **k)
        sb.BackgroundTasks.add_task = spy
        self.addCleanup(setattr, sb.BackgroundTasks, "add_task", real_add)

        r = TestClient(store).post("/auth/email", data={
            "email": f"visitor-{uuid.uuid4().hex[:6]}@example.com",
            "mode": "signin"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("_send_magic_link", seen,
                      "the send must be deferred, not inline")

    def test_a_failed_send_is_recorded_for_the_owner(self):
        real = self.mailer.send

        def boom(*a, **k):
            raise self.mailer.MailError("535 authentication failed")
        self.mailer.send = boom
        self.addCleanup(setattr, self.mailer, "send", real)

        TestClient(store).post("/auth/email", data={
            "email": "someone@example.com", "mode": "signin"})
        log = self.mailer.recent()
        self.assertTrue(log)
        self.assertIn("535", log[0]["error"])
        self.assertNotIn("someone@example.com", log[0]["to"],
                         "the log is a diagnostic, not a mailing list")

    def test_the_visitor_never_learns_the_send_failed(self):
        real = self.mailer.send
        self.mailer.send = lambda *a, **k: (_ for _ in ()).throw(
            self.mailer.MailError("nope"))
        self.addCleanup(setattr, self.mailer, "send", real)
        r = TestClient(store).post("/auth/email", data={
            "email": "quiet@example.com", "mode": "signin"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Check your inbox", r.text)
        self.assertNotIn("nope", r.text)

    def test_the_self_test_reports_the_real_error(self):
        real = self.mailer.send
        self.mailer.send = lambda *a, **k: (_ for _ in ()).throw(
            self.mailer.MailError("535 authentication failed"))
        self.addCleanup(setattr, self.mailer, "send", real)
        c = _signed_in(self.owner)
        r = c.post("/admin/ops", data={"token": "", "action": "test-mail"},
                   follow_redirects=False)
        self.assertIn("FAILED", r.headers["location"])
        self.assertIn("535", r.headers["location"])
