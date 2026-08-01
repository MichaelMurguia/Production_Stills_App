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


def init_db() -> None:
    Base.metadata.create_all(engine)
    # create_all never adds columns to tables that already exist; patch the
    # known additive columns so early deployments upgrade in place.
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE purchases ADD COLUMN tier VARCHAR(16) DEFAULT ''"))
    except Exception:
        pass  # column already present


def session() -> Session:
    return Session(engine)
