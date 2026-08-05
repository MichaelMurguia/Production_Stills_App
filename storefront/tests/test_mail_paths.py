"""Mail, end to end — the send path and the receive path.

The existing trial tests mock `mailer.send` away, which proves the route
defers it but proves nothing about the message. These tests fake only
the socket: `mailer.send()` runs its real code — port-dependent
handshake, `EmailMessage` construction, recipients — and the message it
would have put on the wire is captured and inspected.

The receive path is the half that had never been tested at all: the URL
inside a delivered magic link is extracted from the captured body and
followed, and the response must be a signed-in session. A link that is
generated correctly but does not work is indistinguishable from a broken
mail server to the person waiting for it (2026-08-06).

Run from storefront/:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import datetime as dt
import os
import re
import smtplib
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmpdir = tempfile.mkdtemp(prefix="storefront-mail-")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(_tmpdir, "test.db").replace("\\", "/"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import auth, db, mailer, settings  # noqa: E402
from app.main import store  # noqa: E402


class Outbox:
    """Fakes the socket, not the mailer. Everything above smtplib —
    message construction, the port→handshake choice, login, recipients —
    is the real code under test."""

    def __init__(self):
        self.sent: list = []
        self.opened: list[tuple[str, str, int]] = []
        self.logins: list[tuple[str, str]] = []
        self.starttls_called = False
        self._fail: Exception | None = None

    def fail_with(self, exc: Exception) -> None:
        self._fail = exc

    def install(self, case: unittest.TestCase) -> "Outbox":
        outbox = self

        class FakeSMTP:
            kind = "plain"

            def __init__(self, host, port, timeout=None):
                if outbox._fail:
                    raise outbox._fail
                outbox.opened.append((type(self).kind, host, port))

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def starttls(self):
                outbox.starttls_called = True

            def login(self, user, password):
                outbox.logins.append((user, password))

            def send_message(self, msg):
                outbox.sent.append(msg)

        class FakeSMTPSSL(FakeSMTP):
            kind = "ssl"

        real = (smtplib.SMTP, smtplib.SMTP_SSL)
        smtplib.SMTP, smtplib.SMTP_SSL = FakeSMTP, FakeSMTPSSL
        case.addCleanup(lambda: setattr(smtplib, "SMTP", real[0]))
        case.addCleanup(lambda: setattr(smtplib, "SMTP_SSL", real[1]))
        return self

    # -- reading what was sent -------------------------------------------

    def last_body(self) -> str:
        return self.sent[-1].get_content()

    def last_to(self) -> str:
        return self.sent[-1]["To"]

    def link(self) -> str:
        """The URL a recipient would click."""
        m = re.search(r"https?://\S+", self.last_body())
        assert m, f"no link in the mail body:\n{self.last_body()}"
        return m.group(0).rstrip(".,)")


def session_email(response) -> str | None:
    """The signed-in address a response establishes.

    Starlette quotes the cookie value (it contains `|` and `@`, which the
    RFC 6265 grammar requires quoting) and the client strips the quotes
    when sending it back — so the jar's stored form is NOT what the
    server ever parses. Unquote before asking the signer, or every
    assertion here fails against perfectly working code.
    """
    raw = response.cookies.get(auth.SESSION_COOKIE)
    return auth.read_session(raw.strip('"')) if raw else None


class MailBase(unittest.TestCase):
    def setUp(self):
        self.saved = (settings.SMTP_HOST, settings.SMTP_PORT,
                      settings.SMTP_USER, settings.SMTP_PASS,
                      settings.SMTP_FROM, settings.BASE_URL)
        settings.SMTP_HOST = "smtp.test"
        settings.SMTP_PORT = 587
        settings.SMTP_USER = "apikey"
        settings.SMTP_PASS = "secret"
        settings.SMTP_FROM = "Screenboard <no-reply@screenboardstudio.com>"
        settings.BASE_URL = "https://www.screenboardstudio.com"

        def restore():
            (settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER,
             settings.SMTP_PASS, settings.SMTP_FROM,
             settings.BASE_URL) = self.saved
        self.addCleanup(restore)
        self.out = Outbox().install(self)
        mailer._recent.clear()
        # https, deliberately: BASE_URL above is https, so _cookies_secure()
        # marks the session cookie Secure — and a client speaking http will
        # refuse to send it back, failing the round trip against code that
        # works perfectly in production. The harness must match the scheme
        # the cookie was issued for.
        self.client = self.browser()
        self.email = f"mail-{uuid.uuid4().hex[:8]}@example.com"

    @staticmethod
    def browser() -> TestClient:
        return TestClient(store, base_url="https://testserver")

    def path_of(self, url: str) -> str:
        return url.replace(settings.BASE_URL, "")


# ------------------------------------------------------------- send path

class SendPathTests(MailBase):
    def test_the_message_is_well_formed_and_addressed(self):
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        self.assertEqual(len(self.out.sent), 1, "exactly one mail per request")
        msg = self.out.sent[-1]
        self.assertEqual(msg["To"], self.email)
        self.assertEqual(msg["From"], settings.SMTP_FROM)
        self.assertTrue(msg["Subject"].strip())
        self.assertTrue(self.out.last_body().strip())

    def test_the_real_handshake_runs_for_the_configured_port(self):
        settings.SMTP_PORT = 587
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        self.assertEqual(self.out.opened[-1], ("plain", "smtp.test", 587))
        self.assertTrue(self.out.starttls_called)
        self.assertEqual(self.out.logins[-1], ("apikey", "secret"))

    def test_implicit_tls_port_never_negotiates(self):
        settings.SMTP_PORT = 465
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        self.assertEqual(self.out.opened[-1][0], "ssl")
        self.assertFalse(self.out.starttls_called,
                         "STARTTLS on 465 hangs until the timeout — the "
                         "exact production defect of 2026-08-06")

    def test_no_credentials_means_no_login_attempt(self):
        settings.SMTP_USER = ""
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        self.assertEqual(self.out.logins, [])
        self.assertEqual(len(self.out.sent), 1)

    def test_an_unconfigured_mailer_sends_nothing_and_states_the_gate(self):
        settings.SMTP_HOST = ""
        r = self.client.post("/auth/email",
                             data={"email": self.email, "mode": "signin"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.out.sent, [])
        self.assertNotIn("Check your inbox", r.text,
                         "an unconfigured mailer must not claim it sent one")

    def test_the_secret_never_appears_in_the_message(self):
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        self.assertNotIn("secret", self.out.last_body())


# ---------------------------------------------------------- receive path

class ReceivePathTests(MailBase):
    """The half that had never been tested: the link that actually
    arrives must sign the recipient in."""

    def test_the_delivered_link_signs_the_recipient_in(self):
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        link = self.out.link()
        self.assertTrue(link.startswith(settings.BASE_URL + "/auth/verify?token="),
                        f"unexpected link: {link}")

        fresh = self.browser()
        r = fresh.get(self.path_of(link), follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertEqual(session_email(r), self.email)
        # The proof that matters is behavioural: the next request is
        # authenticated. A cookie that parses but does not carry is worth
        # nothing to the person who clicked the link.
        self.assertIn(self.email, fresh.get("/account").text)

    def test_the_link_works_exactly_once(self):
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        path = self.path_of(self.out.link())
        first = self.browser().get(path, follow_redirects=False)
        self.assertEqual(first.status_code, 303)
        second = self.browser().get(path, follow_redirects=False)
        self.assertEqual(second.status_code, 200,
                         "a spent link must re-render the page, never sign in")
        self.assertNotIn(auth.SESSION_COOKIE, second.cookies)
        self.assertIn("expired or already used", second.text.lower())

    def test_an_expired_link_is_refused(self):
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        token = self.out.link().rsplit("=", 1)[1]
        with db.session() as s:
            row = s.scalar(select(db.LoginToken).where(
                db.LoginToken.token == token))
            row.expires_at = dt.datetime.utcnow() - dt.timedelta(minutes=1)
            s.commit()
        r = self.browser().get(f"/auth/verify?token={token}",
                               follow_redirects=False)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(auth.SESSION_COOKIE, r.cookies)

    def test_a_forged_token_signs_nobody_in(self):
        r = self.browser().get("/auth/verify?token=not-a-real-token",
                               follow_redirects=False)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(auth.SESSION_COOKIE, r.cookies)

    def test_one_persons_link_never_signs_in_another(self):
        other = f"other-{uuid.uuid4().hex[:8]}@example.com"
        self.client.post("/auth/email", data={"email": other, "mode": "signin"})
        link = self.path_of(self.out.link())
        r = self.browser().get(link, follow_redirects=False)
        self.assertEqual(session_email(r), other,
                         "the token carries its own address, not the last "
                         "one that asked")


# ------------------------------------------------- recovery, both halves

class RecoveryMailTests(MailBase):
    def _purchase(self, email):
        with db.session() as s:
            p = db.Purchase(kind="download", tier="personal", email=email,
                            stripe_session_id=f"cs_{uuid.uuid4().hex}",
                            status="PAID")
            p.license = db.License()
            s.add(p)
            s.commit()
            token = p.license.token
        return token

    def test_recovery_carries_the_real_credential(self):
        token = self._purchase(self.email)
        self.client.post("/recover", data={"email": self.email})
        self.assertEqual(len(self.out.sent), 1)
        self.assertEqual(self.out.last_to(), self.email)
        self.assertIn(token, self.out.last_body(),
                      "the mail must carry the credential it promises")

    def test_no_purchases_means_no_mail_but_the_same_page(self):
        r = self.client.post(
            "/recover", data={"email": f"nobody-{uuid.uuid4().hex[:6]}@example.com"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.out.sent, [],
                         "nothing is mailed to an address with no purchases")
        self.assertIn("Check your inbox", r.text,
                      "and the page must not reveal that — anti-enumeration")

    def test_a_recovery_mail_never_carries_another_account(self):
        mine = self._purchase(self.email)
        theirs = self._purchase(f"neighbour-{uuid.uuid4().hex[:6]}@example.com")
        self.client.post("/recover", data={"email": self.email})
        body = self.out.last_body()
        self.assertIn(mine, body)
        self.assertNotIn(theirs, body)


# ------------------------------------------------ failure stays invisible

class FailurePathTests(MailBase):
    def test_a_dead_host_never_changes_what_the_visitor_sees(self):
        self.out.fail_with(OSError("timed out"))
        r = self.client.post("/auth/email",
                             data={"email": self.email, "mode": "signin"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Check your inbox", r.text)
        self.assertNotIn("timed out", r.text)

    def test_but_the_owner_can_see_it_with_the_endpoint_named(self):
        self.out.fail_with(OSError("timed out"))
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        log = mailer.recent()
        self.assertTrue(log)
        self.assertIn("timed out", log[0]["error"])
        self.assertIn("smtp.test:587", log[0]["error"],
                      "a timeout without its endpoint is unactionable")

    def test_a_successful_send_is_recorded_too(self):
        self.client.post("/auth/email",
                         data={"email": self.email, "mode": "signin"})
        self.assertEqual(mailer.recent()[0]["error"], "",
                         "the log shows successes as well, or an empty log "
                         "is ambiguous between 'fine' and 'never ran'")


if __name__ == "__main__":
    unittest.main()
