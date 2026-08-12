from __future__ import annotations

import datetime as dt
import math
import secrets

from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from . import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class Purchase(Base):
    """One row per completed Stripe Checkout — download license or cloud
    subscription. stripe_session_id is the idempotency key: the webhook and
    the /success page can both try to fulfill, whichever lands first wins."""

    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # "download" | "cloud"
    tier: Mapped[str] = mapped_column(String(16), default="")  # "personal" | "business"
    email: Mapped[str] = mapped_column(String(320))
    stripe_session_id: Mapped[str] = mapped_column(String(255), unique=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), default="")
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), default="")
    # Lets charge.refunded / dispute events find their purchase.
    stripe_payment_intent: Mapped[str] = mapped_column(String(255), default="")
    # PAID | CANCELED | REFUNDED | EXPIRED (a code trial that ran out)
    status: Mapped[str] = mapped_column(String(16), default="PAID")
    # --- trials -----------------------------------------------------------
    # Two kinds, deliberately different in who governs the ending:
    #   "card" — a Stripe trial with a payment method captured. Stripe
    #            converts it to a paid subscription on its own; we only
    #            display the date. Its ending is a Stripe event.
    #   "code" — an operator-granted duration with NO payment method.
    #            Nothing external will ever end it, so reconcile does:
    #            past trial_ends_at the purchase goes EXPIRED and the
    #            studio is revoked like any other lapsed entitlement.
    # Naive UTC (SQLite drops tzinfo) — compare against dt.datetime.utcnow(),
    # the same convention LoginToken.expires_at proved.
    trial_kind: Mapped[str] = mapped_column(String(8), default="")
    trial_ends_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    trial_code: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    license: Mapped["License | None"] = relationship(back_populates="purchase", uselist=False)
    workspace: Mapped["Workspace | None"] = relationship(back_populates="purchase", uselist=False)

    @property
    def trial_days_left(self) -> int:
        """Days remaining, rounded up so a part-day still reads as a day;
        0 once it is over. Display only — entitlement is decided by
        status, and the exact date is always shown beside this number."""
        if not self.trial_ends_at:
            return 0
        seconds = (self.trial_ends_at - dt.datetime.utcnow()).total_seconds()
        return math.ceil(seconds / 86400) if seconds > 0 else 0

    @property
    def on_trial(self) -> bool:
        return bool(self.trial_kind and self.status == "PAID"
                    and self.trial_ends_at
                    and self.trial_ends_at > dt.datetime.utcnow())


class License(Base):
    """Download credential for a one-time purchase. The token gates
    /download/<token>; downloads_used is bookkeeping, not a hard cap."""

    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: secrets.token_urlsafe(24))
    downloads_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    purchase: Mapped[Purchase] = relationship(back_populates="license")


class Workspace(Base):
    """A hosted tenant instance of the product app, provisioned on Railway
    for a cloud subscription. `purchases` stays the entitlement truth; this
    row records what was built for it and how the buyer reaches it.
    status: PENDING (queued — config missing or not yet attempted),
    ACTIVE (service live), FAILED (last attempt errored; detail says why,
    reconcile retries), REVOKED (subscription canceled, service deleted)."""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    # The studio's subdomain label. Uniqueness is enforced by a partial
    # unique index (WHERE subdomain <> '' — see init_db); pre-claim '' rows
    # stay exempt. The app-level clash check remains for friendly errors.
    subdomain: Mapped[str] = mapped_column(String(63), default="")
    # The name this studio last released (rename). While unclaimed, the
    # router forwards it to the current address — stale doors and old
    # bookmarks keep working instead of landing on the unclaimed page.
    prev_subdomain: Mapped[str] = mapped_column(String(63), default="")
    access_token: Mapped[str] = mapped_column(String(64), default=lambda: secrets.token_urlsafe(24))
    railway_service_id: Mapped[str] = mapped_column(String(64), default="")
    railway_url: Mapped[str] = mapped_column(String(255), default="")
    domain_live: Mapped[int] = mapped_column(Integer, default=0)
    railway_volume_id: Mapped[str] = mapped_column(String(64), default="")
    url: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(String(600), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=lambda: dt.datetime.now(dt.timezone.utc),
        onupdate=lambda: dt.datetime.now(dt.timezone.utc))

    purchase: Mapped[Purchase] = relationship(back_populates="workspace")


class FleetState(Base):
    """One row (id=1): the commit the tenant fleet was last pushed to.
    Railway redeploys the storefront on every push to main; on boot the
    storefront compares its own RAILWAY_GIT_COMMIT_SHA to this marker and
    auto-runs the fleet update when they differ (user ruling 2026-08-12:
    updates follow the push — no operator step, no token on a laptop).
    The marker advances only on a zero-failure run, so a partial rollout
    retries on the next boot instead of stranding a studio."""

    __tablename__ = "fleet_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_updated_sha: Mapped[str] = mapped_column(String(64), default="")


class TrialCode(Base):
    """An operator-granted free trial of arbitrary duration — no payment
    method, no Stripe object. The code is the capability: whoever holds it
    can redeem it once per account, up to max_uses times in total, until
    it is disabled or its own expires_at passes.

    Redeeming creates an ordinary cloud Purchase carrying trial_kind
    "code" and a trial_ends_at, so a code trial is provisioned, named,
    proxied and revoked by exactly the machinery a paid studio uses.
    """

    __tablename__ = "trial_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    days: Mapped[int] = mapped_column(Integer, default=14)
    tier: Mapped[str] = mapped_column(String(16), default="personal")
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    # The code's own shelf life (not the trial's). Null = never stale.
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    disabled: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    def state(self) -> str:
        """One word for the operator table — the row states itself."""
        if self.disabled:
            return "DISABLED"
        if self.expires_at and self.expires_at <= dt.datetime.utcnow():
            return "STALE"
        if self.uses >= self.max_uses:
            return "SPENT"
        return "LIVE"

    def redeemable(self) -> bool:
        return self.state() == "LIVE"


class Account(Base):
    """A store account — identity is a verified email (Google OIDC or a
    consumed magic link). No passwords exist anywhere in this system.
    Purchases link by email; the account is a viewing lens, the purchase
    row remains the entitlement truth."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    google_sub: Mapped[str] = mapped_column(String(64), default="")
    picture: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    last_login_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))


class SiteText(Base):
    """Owner page-text rewrites (debug tool, 2026-08-03): exact original
    text -> replacement, applied client-side on every store page. Edited
    only by OWNER_EMAILS accounts; content is public by nature (it IS the
    page copy). Postgres because the store's disk is ephemeral."""

    __tablename__ = "site_texts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original: Mapped[str] = mapped_column(String(500), unique=True)
    replacement: Mapped[str] = mapped_column(String(500), default="")


class LoginToken(Base):
    """One magic link: single-use, 30-minute expiry. Naive-UTC datetimes
    throughout (SQLite drops tzinfo; comparisons stay consistent)."""

    __tablename__ = "login_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: secrets.token_urlsafe(24))
    expires_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=lambda: dt.datetime.utcnow() + dt.timedelta(minutes=30))
    used: Mapped[int] = mapped_column(Integer, default=0)


def _is_duplicate_ddl_error(e: Exception) -> bool:
    """Distinguish 'column/index already there' (expected, idempotent) from
    a genuinely broken database. Swallowing everything once hid a down DB
    at import — the service then served with unmigrated tables."""
    msg = str(e).lower()
    return any(k in msg for k in ("duplicate column", "duplicate key",
                                  "already exists", "duplicate object"))


def init_db() -> None:
    Base.metadata.create_all(engine)
    # create_all never adds columns to tables that already exist; patch the
    # known additive columns so early deployments upgrade in place. The
    # partial unique index enforces subdomain uniqueness at the DB (the
    # claim race), leaving pre-claim '' rows exempt.
    for ddl in ("ALTER TABLE purchases ADD COLUMN tier VARCHAR(16) DEFAULT ''",
                "ALTER TABLE purchases ADD COLUMN trial_kind VARCHAR(8) DEFAULT ''",
                "ALTER TABLE purchases ADD COLUMN trial_ends_at TIMESTAMP NULL",
                "ALTER TABLE purchases ADD COLUMN trial_code VARCHAR(32) DEFAULT ''",
                "ALTER TABLE purchases ADD COLUMN stripe_payment_intent VARCHAR(255) DEFAULT ''",
                "ALTER TABLE accounts ADD COLUMN picture VARCHAR(500) DEFAULT ''",
                "ALTER TABLE workspaces ADD COLUMN subdomain VARCHAR(63) DEFAULT ''",
                "ALTER TABLE workspaces ADD COLUMN railway_url VARCHAR(255) DEFAULT ''",
                "ALTER TABLE workspaces ADD COLUMN domain_live INTEGER DEFAULT 0",
                "ALTER TABLE workspaces ADD COLUMN prev_subdomain VARCHAR(63) DEFAULT ''",
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_workspaces_subdomain "
                "ON workspaces (subdomain) WHERE subdomain <> ''"):
        try:
            with engine.begin() as conn:
                conn.execute(text(ddl))
        except Exception as e:
            if not _is_duplicate_ddl_error(e):
                raise  # connectivity/permission problems must be loud


def session() -> Session:
    return Session(engine)
