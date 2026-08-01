from __future__ import annotations

import datetime as dt
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
    status: Mapped[str] = mapped_column(String(16), default="PAID")  # PAID | CANCELED
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    license: Mapped["License | None"] = relationship(back_populates="purchase", uselist=False)
    workspace: Mapped["Workspace | None"] = relationship(back_populates="purchase", uselist=False)


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
    # The studio's subdomain label. Uniqueness is enforced in the app (a DB
    # unique constraint would break on pre-claim '' rows).
    subdomain: Mapped[str] = mapped_column(String(63), default="")
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


def init_db() -> None:
    Base.metadata.create_all(engine)
    # create_all never adds columns to tables that already exist; patch the
    # known additive columns so early deployments upgrade in place.
    for ddl in ("ALTER TABLE purchases ADD COLUMN tier VARCHAR(16) DEFAULT ''",
                "ALTER TABLE accounts ADD COLUMN picture VARCHAR(500) DEFAULT ''",
                "ALTER TABLE workspaces ADD COLUMN subdomain VARCHAR(63) DEFAULT ''",
                "ALTER TABLE workspaces ADD COLUMN railway_url VARCHAR(255) DEFAULT ''",
                "ALTER TABLE workspaces ADD COLUMN domain_live INTEGER DEFAULT 0"):
        try:
            with engine.begin() as conn:
                conn.execute(text(ddl))
        except Exception:
            pass  # column already present


def session() -> Session:
    return Session(engine)
