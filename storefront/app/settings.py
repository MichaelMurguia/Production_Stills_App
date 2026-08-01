from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # storefront/

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_DOWNLOAD = os.environ.get("STRIPE_PRICE_DOWNLOAD", "")
STRIPE_PRICE_CLOUD = os.environ.get("STRIPE_PRICE_CLOUD", "")

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8100").rstrip("/")

# Railway's Postgres plugin injects DATABASE_URL as postgres://...; SQLAlchemy
# requires the postgresql:// scheme, so normalize it here.
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'storefront.db'}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DOWNLOAD_FILE = Path(os.environ.get("DOWNLOAD_FILE", ROOT / "releases" / "screenboard-studio.zip"))
