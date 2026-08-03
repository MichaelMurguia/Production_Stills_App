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
# Preferred: a PROJECT token from the tenants project (Settings → Tokens).
# Scoped to that project only, and the client resolves project/environment
# ids from it — one variable configures everything.
RAILWAY_PROJECT_TOKEN = os.environ.get("RAILWAY_PROJECT_TOKEN", "")
RAILWAY_API_URL = os.environ.get("RAILWAY_API_URL", "https://backboard.railway.com/graphql/v2")
RAILWAY_PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "")
RAILWAY_ENVIRONMENT_ID = os.environ.get("RAILWAY_ENVIRONMENT_ID", "")
# When set (e.g. "app.screenboardstudio.com"), tenants get
# studio-<n>.<base> custom domains instead of *.up.railway.app — needs the
# one-time wildcard CNAME described in docs/DEPLOYMENT.md.
TENANT_DOMAIN_BASE = os.environ.get("TENANT_DOMAIN_BASE", "").strip(".")

# Store-owner account emails (comma-separated). Studios purchased under
# these addresses are provisioned with SCREENBOARD_DEBUG_TOOLS=1 — the
# in-app Debug tools (mock engine, text edit) exist ONLY there.
OWNER_EMAILS = {e.strip().lower()
                for e in os.environ.get("OWNER_EMAILS", "").split(",")
                if e.strip()}
TENANT_REPO = os.environ.get("TENANT_REPO", "MichaelMurguia/Production_Stills_App")
TENANT_BRANCH = os.environ.get("TENANT_BRANCH", "main")


def railway_configured() -> bool:
    return bool(RAILWAY_PROJECT_TOKEN or (RAILWAY_API_TOKEN and RAILWAY_PROJECT_ID))


# --- Transactional mail (license recovery) --------------------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or 587)
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")

# --- Accounts (passwordless: magic links + Google OIDC) -------------------
# SESSION_SECRET unset → per-boot ephemeral secret (sessions reset on each
# deploy; set it in production). Google vars unset → the button hides.
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")

# Pre-launch gate: while set, every store page serves the coming-soon
# overlay until the visitor enters this password (signed cookie, 30 days).
# Unset -> no gate. Tenant studios, the webhook, health, admin, and the
# site-text feed are never gated.
PREVIEW_PASSWORD = os.environ.get("PREVIEW_PASSWORD", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# --- Entitlement-data export (operator backup) ----------------------------
# Unset = the endpoint does not exist (404). Long random value; treat like
# the Stripe secret key.
ADMIN_EXPORT_TOKEN = os.environ.get("ADMIN_EXPORT_TOKEN", "")
