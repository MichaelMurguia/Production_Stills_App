"""Transactional mail over stdlib SMTP — env-gated like Stripe and Railway.

Unconfigured is a first-class state: callers check configured() and render
the gate; nothing crashes. No provider SDK — any SMTP endpoint works
(Resend, Postmark, SES, a Gmail app password) via five variables.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from . import settings


class MailError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def send(to: str, subject: str, body: str) -> None:
    if not configured():
        raise MailError("SMTP is not configured")
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    # Port decides the handshake, and getting it wrong looks exactly like
    # a dead host: 465 is implicit TLS (the server speaks TLS from the
    # first byte), 587/25 are plaintext-then-STARTTLS. Calling starttls()
    # on 465 hangs until the timeout — which is what production was
    # doing (2026-08-06: "Connection unexpectedly closed: timed out").
    implicit_tls = int(settings.SMTP_PORT) == 465
    # Sends run in background tasks now, so this bounds a worker rather
    # than a page load — but a wedged connection still holds a thread.
    opener = smtplib.SMTP_SSL if implicit_tls else smtplib.SMTP
    try:
        with opener(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
            if not implicit_tls:
                s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASS)
            s.send_message(msg)
    except Exception as e:
        # The host and port are not secrets, and without them the error
        # is unactionable — a timeout says nothing about WHICH endpoint.
        raise MailError(
            f"mail send failed via {settings.SMTP_HOST}:{settings.SMTP_PORT} "
            f"({'implicit TLS' if implicit_tls else 'STARTTLS'}): {e}") from e


# --- what actually happened, for the owner --------------------------------
# A send failure is invisible by design: the visitor gets a uniform
# response so the store cannot be used to test which addresses exist, and
# the only trace was a print() in the platform log. This ring buffer is
# the owner's window — in memory, last 10, cleared on deploy, never shown
# to anyone but an OWNER_EMAILS session.

_recent: list[dict] = []


def record(kind: str, to: str, error: str) -> None:
    import datetime as dt
    _recent.insert(0, {
        "at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "kind": kind,
        # Never the full address: the log is a diagnostic, not a mailing list.
        "to": (to.split("@")[0][:3] + "…@" + to.split("@")[-1]) if "@" in to else to,
        "error": error[:200],
    })
    del _recent[10:]


def recent() -> list[dict]:
    return list(_recent)
