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
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASS)
            s.send_message(msg)
    except Exception as e:
        raise MailError(f"mail send failed: {e}") from e
