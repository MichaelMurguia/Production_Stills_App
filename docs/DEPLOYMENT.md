# Deployment & Commerce — DevOps Reference

Written 2026-07-31 by the DevOps agent. This is the operational truth for how
this project is sold, hosted, and deployed. The app development agent must
read this before touching `storefront/` or anything deployment-related.

## The product

Screenboard Studio itself is the product, sold to other filmmakers two ways,
each in a Personal and a Business tier (four SKUs total, one Stripe product
each — prices as of 2026-08-01: $119 / $249.99 one-time, $9.99 / $29.99
monthly):

1. **Download license** — one-time Stripe payment; buyer receives a license
   token and downloads a packaged release zip. Runs on their hardware with
   their own render-engine API keys.
2. **Cloud subscription** — monthly Stripe subscription for a hosted
   workspace. Billing works today; workspace provisioning is NOT built yet
   (see "Not built" below).

Plan slugs are `download-personal`, `download-business`, `cloud-personal`,
`cloud-business` (checkout URLs and session metadata); the purchase row
stores kind and tier separately. **Displayed prices are hardcoded in
`storefront/app/templates/index.html` — changing a price in Stripe requires
updating that template in the same change.**

## The two-app architecture — the one rule that must never break

```
Production_Stills_App/          this repo
├── app/          INTERNAL — Screenboard Studio itself. Local tool.
│                 Holds user API keys (data/settings.json), screenplay,
│                 canon. NEVER deployed. No public exposure, ever.
└── storefront/   PUBLIC — the sales site. FastAPI + SQLAlchemy + Stripe.
                  Deploys to Railway. Contains no pipeline code and reads
                  nothing from app/ or data/ at runtime.
```

The boundary is enforced by Railway's **Root Directory = `storefront`**
setting: the deployed service builds and serves only that folder. Do not add
imports from `storefront/` into `app/` or vice versa. Do not "conveniently"
serve internal data from the storefront.

## Hosting

- **Provider:** Railway (railway.com), account owned by the user, GitHub repo
  attached. Deploys trigger on push to `main`.
- **Service config:** Root Directory `storefront`; build is Nixpacks
  (auto-detects Python); start command lives in `storefront/railway.json`
  (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
- **Database:** Railway Postgres plugin, which injects `DATABASE_URL`.
  Locally the storefront falls back to SQLite (`storefront/storefront.db`,
  gitignored). `settings.py` normalizes Railway's `postgres://` scheme to
  `postgresql://` for SQLAlchemy — do not remove that shim.
- **Logs/CLI:** `railway logs` after `railway link`. Rollback = redeploy a
  previous deployment from the Railway dashboard.

## Environment variables (set in Railway → service → Variables)

| Variable | Purpose |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe API key (test key until launch) |
| `STRIPE_WEBHOOK_SECRET` | Signing secret for the webhook endpoint |
| `STRIPE_PRICE_DOWNLOAD_PERSONAL` | Price ID, one-time, "Screenboard Studio Download Personal" ($119) |
| `STRIPE_PRICE_DOWNLOAD_BUSINESS` | Price ID, one-time, "Screenboard Studio Download Business" ($249.99) |
| `STRIPE_PRICE_CLOUD_PERSONAL` | Price ID, monthly, "Screenboard Studio Cloud Personal" ($9.99/mo) |
| `STRIPE_PRICE_CLOUD_BUSINESS` | Price ID, monthly, "Screenboard Studio Cloud Business" ($29.99/mo) |
| `BASE_URL` | Public URL of the storefront, no trailing slash |
| `DATABASE_URL` | Injected by Railway Postgres; local default SQLite |
| `DOWNLOAD_FILE` | Optional override for the release zip path |

Secrets live ONLY in Railway variables and local shells. Never in the repo,
never in `data/settings.json` (that file is for the internal app's
render-engine keys and is a different concern entirely).

## Stripe wiring

- Checkout: `GET /checkout/download` (mode=payment) and `GET /checkout/cloud`
  (mode=subscription) redirect to Stripe-hosted Checkout. PCI stays Stripe's
  problem; no card data ever touches this code.
- Webhook: `POST /stripe/webhook`, signature-verified. Events subscribed:
  `checkout.session.completed` (fulfill) and
  `customer.subscription.deleted` (mark purchase CANCELED).
- **Fulfillment is idempotent on `stripe_session_id`** — both the webhook and
  the `/success` page attempt it; first writer wins. Preserve this when
  editing: it is what makes local dev work without a webhook tunnel and
  production survive webhook retries.
- Local webhook testing: `stripe listen --forward-to
  localhost:8100/stripe/webhook`.

## Data model (storefront only)

`purchases` (kind download|cloud, email, stripe ids, status PAID|CANCELED)
and `licenses` (token gating `/download/<token>`, downloads_used counter).
Tables are created by `db.init_db()` at startup — schema changes currently
mean additive `create_all` only; introduce Alembic before any destructive
migration.

## Release artifact

`/download/<token>` serves `storefront/releases/screenboard-studio.zip`
(missing file → 503, never a broken download). Package a release from repo
root:

```
git archive -o storefront/releases/screenboard-studio.zip HEAD -- app requirements.txt run.bat README.md INSTALL.md
```

The zip must never include `data/` (user canon, screenplay, API keys) or
`project_state/`.

## Local development

```
cd storefront
pip install -r requirements.txt
uvicorn app.main:app --port 8100 --reload
```

Port 8100, so it can run beside the internal app. Unconfigured Stripe is a
first-class state: buy buttons render disabled with the unmet condition
stated (per the project's gate philosophy), checkout returns 503. Never make
missing config look like a crash.

## Status as of 2026-08-01 — sandbox proven, awaiting go-live

Deployed and serving at https://www.screenboardstudio.com (Railway service,
root dir `storefront`, Postgres attached, custom domain `www` via GoDaddy
CNAME + `_railway-verify.www` TXT; bare domain 301-forwards to www at the
registrar). Release zip staged. `/healthz` reports the serving commit.

**Full sandbox test pass 2026-08-01, all green:** download purchase →
license token → zip download; webhook `checkout.session.completed` 200;
subscription purchase; immediate cancellation → `customer.subscription.
deleted` 200 → purchase CANCELED; declined card leaves no record; bad
download token 404s; success-page revisit returns the same license
(idempotency). Bugs found and fixed during testing: DetachedInstanceError
when the webhook fulfills before the browser redirect, and StripeObject
field access (no dict `.get()`) — both regression-tested.

### Go-live checklist (the only remaining work)

1. Activate the Stripe account (business profile, bank account for payouts;
   website = https://www.screenboardstudio.com). Stripe reviews the site.
2. In **live mode**, recreate the four products/prices (same names/amounts).
3. In live mode, add a webhook endpoint for the same URL and two events.
4. In Railway, replace all six `STRIPE_*` values with live ones
   (`sk_live_...`, four live `price_...`, live `whsec_...`).
5. Run one real purchase with a real card, then refund it from the Stripe
   dashboard. Confirm license + download + webhook 200.

Sandbox and live are fully parallel universes in Stripe: the sandbox
products/webhook stay intact for future testing; the code is identical in
both and driven purely by which keys are configured.

## Not built (deliberate scope cuts, do not silently "fix")

- Cloud workspace provisioning for subscribers — a separate project; the
  success page honestly says provisioning details arrive by email.
- License recovery ("find my license by email") page.
- Transactional emails beyond Stripe's own receipts.

## Design language

The storefront mirrors the app's design system (tokens copied into
`storefront/app/static/store.css`): amber marks exactly one primary action
per view, Courier carries machine data (tokens, prices' terms, metadata),
square corners, no gradients, no emoji. `app/static/DESIGN_SYSTEM.md`
remains the canonical statement of that language; the storefront follows it
but does not add to its Uncanonized table (it is a separate surface).
