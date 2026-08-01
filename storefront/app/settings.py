from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # storefront/

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_DOWNLOAD_PERSONAL = os.environ.get("STRIPE_PRICE_DOWNLOAD_PERSONAL", "")
STRIPE_PRICE_DOWNLOAD_BUSINESS = os.environ.get("STRIPE_PRICE_DOWNLOAD_BUSINESS", "")
STRIPE_PRICE_CLOUD_PERSONAL = os.environ.get("STRIPE_PRICE_CLOUD_PERSONAL", "")
STRIPE_PRICE_CLOUD_BUSINESS = os.environ.get("STRIPE_PRICE_CLOUD_BUSINESS", "")

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8100").rstrip("/")

# Railway's Postgres plugin injects DATABASE_URL as postgres://...; SQLAlchemy
# requires the postgresql:// scheme, so normalize it here.
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'storefront.db'}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DOWNLOAD_FILE = Path(os.environ.get("DOWNLOAD_FILE", ROOT / "releases" / "screenboard-studio.zip"))

# --- Cloud workspace provisioning (Railway GraphQL API) -------------------
# All empty until the operator grants them; the provisioner treats missing
# config as a stated gate — workspaces queue as PENDING, nothing crashes.
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
RAILWAY_API_URL = os.environ.get("RAILWAY_API_URL", "https://backboard.railway.com/graphql/v2")
RAILWAY_PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "")
RAILWAY_ENVIRONMENT_ID = os.environ.get("RAILWAY_ENVIRONMENT_ID", "")
TENANT_REPO = os.environ.get("TENANT_REPO", "MichaelMurguia/Production_Stills_App")
TENANT_BRANCH = os.environ.get("TENANT_BRANCH", "main")


def railway_configured() -> bool:
    return bool(RAILWAY_API_TOKEN and RAILWAY_PROJECT_ID and RAILWAY_ENVIRONMENT_ID)
