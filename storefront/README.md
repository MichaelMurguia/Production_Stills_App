# Screenboard Studio — Storefront

Public sales site for Screenboard Studio: one-time **download license** and
monthly **cloud subscription**, both via Stripe Checkout. Separate from the
production tool in `app/` — deploying this exposes nothing internal.

Quick-start lives here; the full operational reference (architecture
boundary, env vars, runbook, status) is `docs/DEPLOYMENT.md` at the repo
root, maintained per `agents/14_devops_engineer.md`.

## Layout

```
storefront/
  app/main.py        routes: landing, checkout, success, download, webhook
  app/db.py          SQLAlchemy models: Purchase, License
  app/settings.py    all config from environment variables
  app/templates/     Jinja2 pages (design language mirrors the app)
  app/static/        store.css
  releases/          place the downloadable zip here (see below)
  railway.json       Railway start command
```

## Run locally

```
cd storefront
pip install -r requirements.txt
uvicorn app.main:app --port 8100 --reload
```

Without Stripe env vars the site runs with checkout visibly disabled (the
buttons render gated, with the unmet condition stated). Uses SQLite locally;
no database setup needed.

## Stripe setup (once)

1. In dashboard.stripe.com create four products — Download Personal/Business
   (one-time prices) and Cloud Personal/Business (monthly recurring). Copy
   the four price IDs.
2. Set env vars (see `.env.example`): `STRIPE_SECRET_KEY` plus the four
   `STRIPE_PRICE_*` variables.
3. Add a webhook endpoint at `<BASE_URL>/stripe/webhook` for events
   `checkout.session.completed` and `customer.subscription.deleted`; copy the
   signing secret into `STRIPE_WEBHOOK_SECRET`.
   (Local testing: `stripe listen --forward-to localhost:8100/stripe/webhook`.)

Fulfillment is idempotent: the webhook and the success page can both record
the purchase; whichever runs first wins.

## Railway setup (once)

1. New service from this GitHub repo; set **Root Directory** to `storefront`.
2. Add the **Postgres** plugin — Railway injects `DATABASE_URL` automatically.
3. Set the Stripe variables plus `BASE_URL=https://<your-domain>`.
4. Generate a domain (or attach a custom one), then point the Stripe webhook
   at it.

## The release artifact

`GET /download/<token>` serves `releases/screenboard-studio.zip` (override with
`DOWNLOAD_FILE`). Package a release from the repo root with:

```
git archive -o storefront/releases/screenboard-studio.zip HEAD -- app data/settings.example.json requirements.txt run.bat README.md INSTALL.md
```

and commit it, or stage it on a Railway volume. If the file is missing the
download route returns 503 rather than a broken zip.

## Not built yet (deliberately)

- Cloud workspace provisioning — a subscription is recorded and Stripe bills
  it, but creating the customer's hosted instance is a separate project. The
  success page tells subscribers provisioning details arrive by email.
- Receipt/license emails beyond Stripe's own receipts.
- A customer-facing "re-find my license" page (lookup by session or email).
