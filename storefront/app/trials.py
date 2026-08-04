"""Trials — two kinds, one entitlement machine.

**Card trial** (`trial_kind="card"`): an ordinary Stripe subscription that
begins in trial with a payment method captured at signup. Stripe converts
it on its own; the store only records the date and shows it. Nothing here
governs its ending — `customer.subscription.*` events do.

**Code trial** (`trial_kind="code"`): an operator grants an arbitrary
duration to someone by handing them a code. No payment method exists, so
no external system will ever end it — `expire_due()` does, from
`reconcile()`, and the studio is then revoked exactly like a canceled
subscription.

Both kinds produce a normal cloud `Purchase`, so provisioning, naming,
proxying and revocation are the paths already proven in production. A
trial is an entitlement with an end date, not a separate product.
"""
from __future__ import annotations

import datetime as dt
import secrets

from sqlalchemy import select

from . import db, settings

# No I/O/0/1 — codes get read aloud off a screen and typed by hand.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_PREFIX = "SB"


class TrialError(Exception):
    """A stated refusal — the message is shown to the visitor verbatim."""


def generate_code() -> str:
    """SB-XXXX-XXXX. 32^8 ≈ 1.1e12 — unguessable at store traffic, and
    still short enough to read over a phone."""
    body = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"{CODE_PREFIX}-{body[:4]}-{body[4:]}"


def normalize(code: str) -> str:
    """Accept what a human types: any case, spaces, missing dashes."""
    raw = "".join(ch for ch in (code or "").upper() if ch.isalnum())
    if raw.startswith(CODE_PREFIX):
        raw = raw[len(CODE_PREFIX):]
    # Shape includes the alphabet: I/O/0/1 never appear in a real code, so
    # a word like "nonsense" is malformed rather than merely unknown — and
    # the visitor gets the more useful of the two refusals.
    if len(raw) != 8 or any(ch not in _ALPHABET for ch in raw):
        return ""
    return f"{CODE_PREFIX}-{raw[:4]}-{raw[4:]}"


def create_code(s, days: int, tier: str = "personal", max_uses: int = 1,
                note: str = "", valid_days: int = 0) -> db.TrialCode:
    """Mint a code. `days` is the trial's length; `valid_days` is the
    code's own shelf life (0 = never stale)."""
    days = max(1, min(int(days or 1), settings.TRIAL_CODE_MAX_DAYS))
    max_uses = max(1, min(int(max_uses or 1), 1000))
    expires = (dt.datetime.utcnow() + dt.timedelta(days=int(valid_days))
               if valid_days else None)
    for _ in range(8):  # collision is ~impossible; still, never loop forever
        code = generate_code()
        if not s.scalar(select(db.TrialCode).where(db.TrialCode.code == code)):
            break
    row = db.TrialCode(code=code, days=days, tier=(tier or "personal"),
                       max_uses=max_uses, note=(note or "")[:200],
                       expires_at=expires)
    s.add(row)
    s.commit()
    s.refresh(row)
    return row


def active_trial_for(s, email: str) -> db.Purchase | None:
    """The live trial this address already holds, if any."""
    email = (email or "").strip().lower()
    if not email:
        return None
    rows = s.scalars(select(db.Purchase).where(
        db.Purchase.email == email,
        db.Purchase.kind == "cloud",
        db.Purchase.status == "PAID")).all()
    return next((p for p in rows if p.on_trial), None)


def has_entitlement(s, email: str) -> bool:
    """Any live cloud studio — paid or trial. A customer who already has a
    studio is not offered a trial; they are offered their studio."""
    email = (email or "").strip().lower()
    if not email:
        return False
    return bool(s.scalar(select(db.Purchase).where(
        db.Purchase.email == email,
        db.Purchase.kind == "cloud",
        db.Purchase.status == "PAID")))


def redeem(s, code: str, email: str) -> db.Purchase:
    """Turn a code into a live cloud entitlement for `email`.

    Every refusal is stated in the profession's terms and never reveals
    whether an unknown code exists. Raises TrialError; returns the new
    Purchase (uncommitted work already committed) on success.
    """
    email = (email or "").strip().lower()
    if not email:
        raise TrialError("Sign in first — a trial belongs to an account.")
    normalized = normalize(code)
    if not normalized:
        raise TrialError("That code is not the right shape — "
                         f"they look like {CODE_PREFIX}-A1B2-C3D4.")
    row = s.scalar(select(db.TrialCode).where(db.TrialCode.code == normalized))
    if row is None:
        raise TrialError("That code is not recognized.")
    state = row.state()
    if state == "DISABLED":
        raise TrialError("That code has been withdrawn.")
    if state == "STALE":
        raise TrialError("That code has passed its own expiry date.")
    if state == "SPENT":
        raise TrialError("That code has already been used its full number "
                         "of times.")
    if has_entitlement(s, email):
        raise TrialError("This account already has a studio — "
                         "open it from your account page.")

    ends = dt.datetime.utcnow() + dt.timedelta(days=row.days)
    purchase = db.Purchase(
        kind="cloud",
        tier=row.tier or "personal",
        email=email,
        # No Stripe object exists for a code trial, but the column is the
        # table's idempotency key and must stay unique and recognizable.
        stripe_session_id=f"trial_code:{normalized}:{secrets.token_hex(8)}",
        status="PAID",
        trial_kind="code",
        trial_ends_at=ends,
        trial_code=normalized,
    )
    s.add(purchase)
    row.uses += 1
    s.commit()
    s.refresh(purchase)
    return purchase


def expire_due(s) -> list[db.Purchase]:
    """Code trials whose time is up become EXPIRED. Card trials are never
    touched here — Stripe owns their ending, and a clock skew must never
    revoke a studio someone is paying for.

    Returns the rows it changed so reconcile can report them.
    """
    now = dt.datetime.utcnow()
    due = s.scalars(select(db.Purchase).where(
        db.Purchase.status == "PAID",
        db.Purchase.trial_kind == "code",
        db.Purchase.trial_ends_at.is_not(None),
        db.Purchase.trial_ends_at <= now)).all()
    for p in due:
        p.status = "EXPIRED"
    if due:
        s.commit()
    return due


def ending_soon(s, within_days: int = 3) -> list[db.Purchase]:
    """Live code trials inside their last `within_days` — for the operator
    console, so a conversation can happen before a studio goes dark."""
    now = dt.datetime.utcnow()
    edge = now + dt.timedelta(days=within_days)
    return list(s.scalars(select(db.Purchase).where(
        db.Purchase.status == "PAID",
        db.Purchase.trial_kind == "code",
        db.Purchase.trial_ends_at.is_not(None),
        db.Purchase.trial_ends_at > now,
        db.Purchase.trial_ends_at <= edge)).all())
