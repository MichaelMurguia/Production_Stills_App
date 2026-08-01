# Webapp Guide — for the agent developing the app and the service

Written 2026-08-01. This is the development-facing companion to
`docs/DEPLOYMENT.md` (operations). Read both before changing anything in
`storefront/`; read `CLAUDE.md` and `app/static/DESIGN_SYSTEM.md` before
changing anything in `app/`.

## The system in one picture

```
                    ┌──────────────────────────────────────────┐
 filmmaker's        │  app/ — Screenboard Studio (THE PRODUCT) │
 machine / future   │  FastAPI + vanilla JS. Internal. Never   │
 cloud workspace    │  deployed by us. Ships to buyers as a    │
                    │  release zip; will also run per-tenant   │
                    │  in the future cloud service.            │
                    └──────────────────────────────────────────┘
                                       ▲ packaged into (git archive)
                                       │ never imports across
                    ┌──────────────────────────────────────────┐
 www.screenboard    │  storefront/ — sales site (THE SERVICE)  │
 studio.com         │  FastAPI + SQLAlchemy + Stripe Checkout. │
 (Railway)          │  Public. Sells licenses/subscriptions,   │
                    │  serves the release zip.                 │
                    └──────────────────────────────────────────┘
```

Two codebases, one repo, hard boundary: **no imports across `app/` ↔
`storefront/`; nothing from `data/` or `project_state/` is ever served
publicly or packaged into a release.**

## How the storefront works

### Routes (`storefront/app/main.py`)

| Route | What it does |
|---|---|
| `GET /` | Landing + pricing. Plans whose price ID is unset render as disabled buttons with the condition stated. |
| `GET /checkout/{plan}` | Creates a Stripe Checkout session, 303-redirects to Stripe. Plan slugs: `download-personal`, `download-business`, `cloud-personal`, `cloud-business`. |
| `GET /success?session_id=` | Retrieves the session from Stripe; if paid, fulfills (idempotent) and shows license token / subscription confirmation. |
| `GET /download/{token}` | Serves the release zip if the token belongs to a PAID purchase; 404 unknown token, 503 missing artifact. |
| `POST /stripe/webhook` | Signature-verified. `checkout.session.completed` → fulfill; `customer.subscription.deleted` → mark purchase CANCELED. |
| `GET /healthz` | `{ok, rev}` — the git commit currently serving. First stop when asking "did my deploy land?" |

### Fulfillment — the invariant that matters most

`_fulfill()` is called from **two racing paths**: the webhook (usually wins)
and the success page (covers webhook failure; the buyer still gets their
license). It is **idempotent on `stripe_session_id`** — whichever path runs
second gets the existing row back. Any edit to fulfillment must preserve:

1. Idempotency (never a second license for the same session).
2. Both entry points calling the same function.
3. Detached-safe returns — relationships (`purchase.license`) are loaded
   *before* `expunge_all()`; templates receive detached objects.

### Stripe objects are not dicts

Fields like `session.metadata` and `session.customer_details` are
StripeObjects: attribute access works, **dict `.get()` raises**. Use the
`_sget()` helper for any field that may be absent. This was a production
500; the regression test in `storefront/tests/` mimics attribute-only
objects specifically so it stays caught.

### Data model (`storefront/app/db.py`)

- `purchases` — one row per completed checkout: `kind` (download|cloud),
  `tier` (personal|business), email, Stripe ids, `status` (PAID|CANCELED).
  **This table is the source of truth for entitlements** — the future
  provisioning system grants/revokes cloud workspaces from it.
- `licenses` — download credential: unique `token` gates the zip,
  `downloads_used` counts (bookkeeping, not a cap).

Schema changes: `create_all` creates tables but never alters them; additive
columns go in the `init_db()` micro-migration block (see `tier`). Anything
destructive requires introducing Alembic first.

## Requirements — the rules continued development must hold

**Product app (`app/`):**
- The pipeline is strictly sequential and gated; gates are readable as
  state before they are hit (disabled control + stated condition + link),
  never only as errors after the fact.
- Renders are never upscaled; undersized panels are flagged for regen.
- UI follows `app/static/DESIGN_SYSTEM.md` (amber = one signal, Courier =
  machine data). Never rename existing CSS classes.
- It must keep working as a **standalone offline app** — it ships to
  download buyers who run it locally with their own API keys. No feature
  may quietly grow a dependency on our servers.

**Storefront (`storefront/`):**
- Missing configuration is a visible, stated gate — never a crash and
  never a mystery 500.
- Displayed prices are hardcoded in `index.html`; a price change in Stripe
  and the template are one change, same commit.
- Same design language (tokens copied into `store.css`); one amber primary
  action per view; no frameworks, fonts, gradients, rounded corners, emoji.
- Secrets only in Railway variables / local shells. `data/settings.json`
  is the *product's* key store and has nothing to do with the storefront.
- The release zip never contains `data/` or `project_state/`.

**Both:** update the relevant doc (`WEBAPP_GUIDE`, `DEPLOYMENT`,
`DESIGN_SYSTEM`) in the same commit as the change it describes.

## Developing and shipping

- **Product app:** `run.bat` at repo root (uvicorn, auto-reload).
- **Storefront locally:** `cd storefront && uvicorn app.main:app --port
  8100 --reload`. SQLite, checkout gated unless Stripe env vars are set.
  Webhooks locally: `stripe listen --forward-to localhost:8100/stripe/webhook`.
- **Tests:** `cd storefront && python -m unittest discover -s tests -v`
  (fulfillment idempotency + Stripe-shaped objects). Run before any push
  that touches `storefront/app/`. Product-app tests: `python -m unittest
  discover -s tests -v` at repo root.
- **Deploy = push to `main`.** Railway builds `storefront/` only (root
  directory setting). Confirm with `/healthz` that the new rev is serving.
  Rollback: redeploy a previous deployment in the Railway dashboard.
- A failed deploy keeps the previous one serving; the site does not go
  down because a build broke.

## Roadmap (agreed, not yet built)

1. **Cloud workspace provisioning** — the real second project. Consumes
   `purchases` rows (kind=cloud, status=PAID) to create per-tenant hosted
   instances of the product app; CANCELED revokes. Design not started —
   do not improvise it into the storefront.
2. **License recovery** — customer-facing "find my license by email".
3. **Transactional email** — license/receipt mail beyond Stripe's.
4. **Go-live** — Stripe activation + live keys swap; checklist in
   `docs/DEPLOYMENT.md`. No code change involved.
