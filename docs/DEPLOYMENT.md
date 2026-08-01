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
| `RAILWAY_PROJECT_TOKEN` | PREFERRED — a project token from the tenants project (Settings → Tokens). Scoped to that project only; project/environment ids resolve from it, so nothing else is needed |
| `RAILWAY_API_TOKEN` | Alternative: account token (Bearer auth); requires `RAILWAY_PROJECT_ID` too |
| `RAILWAY_PROJECT_ID` | Railway project that holds tenant workspaces (recommend a dedicated "screenboard-tenants" project) |
| `RAILWAY_ENVIRONMENT_ID` | OPTIONAL — auto-resolved ("production" by name, else the only environment); set only to override |
| `TENANT_REPO` | GitHub repo tenant services deploy from (default `MichaelMurguia/Production_Stills_App`) |
| `TENANT_BRANCH` | Branch tenants deploy (default `main`) |
| `TENANT_DOMAIN_BASE` | e.g. `screenboardstudio.com` — studios live at `<name>.<base>`, served by the **wildcard tenant router** built into the storefront (`app/tenant_proxy.py`): the storefront reverse-proxies each studio host to that tenant's `*.up.railway.app` service. **One-time setup, never per customer:** in the Railway dashboard attach the custom domain `*.<base>` to the STOREFRONT service (Settings → Networking) and create the DNS records Railway prints — the wildcard CNAME and, for the wildcard certificate, the `_acme-challenge` record it asks for. After that, claiming or renaming a studio is live the moment the row commits: no DNS, no certificates, no Railway domain calls, no per-service domain caps. Reconcile deletes any legacy per-tenant custom domains left from the pre-router design. The `railway.app` URL keeps working throughout, and account/success buttons keep using it until the branded address passes the health probe (`domain_live`) |

| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM` | Transactional mail for `/recover` AND magic-link sign-in (any SMTP endpoint — Resend/Postmark/SES). Unset → both state the gate |
| `ADMIN_EXPORT_TOKEN` | Long random value enabling `GET /admin/export?token=…` (entitlement backup). Unset → the endpoint 404s |
| `SESSION_SECRET` | Long random value signing account-session cookies. Unset → per-boot secret (sessions reset each deploy) — set in production |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | "Continue with Google" (OIDC). Create at console.cloud.google.com → Credentials → OAuth client (web) with redirect URI `https://www.screenboardstudio.com/auth/google/callback`. Unset → the button hides; magic links still work |

All provisioning variables are optional: while unset, cloud purchases
queue as PENDING workspaces with the condition stated on the row — nothing
crashes, and the success page honestly says the workspace is being
prepared. The SMTP and export variables are likewise optional gates.

## Data safety (tier A, 2026-08-01)

The `purchases`/`licenses`/`workspaces` tables are the entitlement truth —
losing them means losing the record of who owns what. Two layers:

1. **Railway Postgres backups** — confirm the plugin's backup policy in the
   Railway dashboard (Database → Backups) and enable scheduled backups if
   they aren't on. This is a dashboard setting; do it once at go-live.
2. **App-level export** — set `ADMIN_EXPORT_TOKEN`, then fetch
   `https://www.screenboardstudio.com/admin/export?token=…` on a schedule
   (weekly cron, or by hand after each sale while volume is low) and keep
   the JSON somewhere safe. Wrong or missing token → 404; the endpoint
   never exists until configured.

## CI

`.github/workflows/ci.yml` runs both suites on every push and PR — in
isolated per-surface environments with a storefront boot-import check (the
2026-08-01 502 was a dependency masked by a shared install; isolation makes
that class turn red in CI). Railway deploys `main` on push regardless (it
cannot wait for CI) — so the standing rule is: suites green locally before
pushing to `main`, and a red X on `main` means roll back (Railway
dashboard → previous deployment) or fix forward immediately.

**Every deploy is verified automatically:** the `verify-deploy` job (main
pushes only) waits up to 10 minutes for `/healthz` to serve the pushed
commit, then probes `/`, `/terms`, `/privacy`, `/recover`. A red
`verify-deploy` means the site is down or serving a stale revision —
GitHub emails the pusher; roll back first, diagnose second.

Secrets live ONLY in Railway variables and local shells. Never in the repo,
never in `data/settings.json` (that file is for the internal app's
render-engine keys and is a different concern entirely).

## Stripe wiring

- Checkout: `GET /checkout/{plan}` for the four plan slugs
  (`download-personal|download-business` mode=payment,
  `cloud-personal|cloud-business` mode=subscription) redirects to
  Stripe-hosted Checkout. PCI stays Stripe's problem; no card data ever
  touches this code.
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

Releases are VERSIONED (CalVer, the `VERSION` file at repo root):
`/download/<token>` serves the newest `screenboard-studio-<v>.zip`; any past
version stays available via `?version=` and the account page's ALL VERSIONS
list. Versioned zips are IMMUTABLE — changing `app/` after staging a version
turns CI red until VERSION is bumped and restaged. Package a release from
repo root (bump VERSION, commit, then):

```
python scripts/stage_release.py
```

The zip must never include user canon: `data/`, `project_state/`,
`projects/`, `settings.json`, or `context/01_ART_DIRECTION_BIBLE.md` — all
of these are untracked/gitignored (2026-07-31), so neither the zip nor
tenant deploy images can contain Beltminer work; cloud workspaces start
empty and fill only from their own volume. **Restage the zip after every
release of `app/` features** — a stale zip silently ships old product; the
CI `release-zip` job enforces this by diffing the staged zip against HEAD
and going red with the restage command when they drift.

**Then update the tenant fleet.** Tenant services do NOT follow pushes —
they stay on the build they were provisioned with until told otherwise
(observed live 2026-08-01: a tenant serving a day-one rev 30+ commits
behind main). The cloud edition sells "updates land the day they ship",
so after every release of `app/` features hit:

```
GET https://www.screenboardstudio.com/admin/tenants/update?token=<ADMIN_EXPORT_TOKEN>
```

It rebuilds every ACTIVE studio from repo head via
`provisioner.update_tenants()` (per-service failures land on the
workspace row's `detail` and retry on the next run). Verify with any
tenant's `/api/healthz` — `rev` must match the released commit.

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
   website = https://www.screenboardstudio.com). Stripe reviews the site —
   `/terms` and `/privacy` exist for this; **read both pages yourself
   before submitting** (they are plain-language drafts, not legal advice).
2. In **live mode**, recreate the four products/prices (same names/amounts).
3. In live mode, add a webhook endpoint for the same URL and two events.
4. In Railway, replace all six `STRIPE_*` values with live ones
   (`sk_live_...`, four live `price_...`, live `whsec_...`).
5. Enable Railway Postgres backups and set `ADMIN_EXPORT_TOKEN`; pull one
   export and confirm it parses (see "Data safety").
6. Set the `SMTP_*` variables and send yourself a `/recover` mail.
7. Confirm the latest `main` is green in GitHub Actions.
8. Run one real purchase with a real card, then refund it from the Stripe
   dashboard. Confirm license + download + webhook 200.

Sandbox and live are fully parallel universes in Stripe: the sandbox
products/webhook stay intact for future testing; the code is identical in
both and driven purely by which keys are configured.

## Cloud workspace provisioning — setup & permissions (added 2026-07-31)

Built and tested against a fake Railway client; the first live provision is
a **supervised test** (like the Stripe sandbox pass) — if Railway's GraphQL
schema has drifted from `storefront/app/railway.py`, the workspace lands
FAILED with the exact API error recorded on the row.

What the operator must grant, one time:

1. **Railway API token** — railway.com → Account Settings → Tokens. A
   *team/account* token (not project-scoped) so the provisioner can create
   services. Set as `RAILWAY_API_TOKEN` on the **storefront** service.
   This token can control the whole Railway account — treat it like the
   Stripe secret key.
2. **A tenants project** — create an empty Railway project (recommend
   `screenboard-tenants`, separate from the storefront's project so tenant
   blast radius is isolated). Copy its project id and its production
   environment id (both visible in the project's URL / settings) into
   `RAILWAY_PROJECT_ID` and `RAILWAY_ENVIRONMENT_ID`.
3. **GitHub access** — the Railway GitHub app must have access to this
   repo in that project's scope (already true for the storefront; confirm
   for the tenants project on first provision).
4. **Cost awareness** — each tenant is one Railway service + one volume
   billed by usage to the operator's account (idle FastAPI ≈ $2–5/mo).
   Tenant costs scale linearly with subscribers; the Personal tier margin
   depends on it.

Lifecycle (all driven by `provisioner.reconcile()` — startup, after cloud
fulfillment, after subscription webhooks): PAID cloud purchase → service
created from `TENANT_REPO` (repo root, `uvicorn app.main:app`), volume at
`/workspace`, env `SCREENBOARD_HOME=/workspace` +
`SCREENBOARD_ACCESS_TOKEN=<workspace token>`, generated
`*.up.railway.app` domain → row ACTIVE; buyer collects URL + token on the
success page (revisitable). CANCELED → service deleted, row REVOKED
(token kept as the record). Probe a tenant with `GET /api/healthz`.

## Not built (deliberate scope cuts, do not silently "fix")

- License recovery ("find my license by email") page.
- Transactional emails beyond Stripe's own receipts.
- Tenant volume backups / export-my-data — decide before real subscribers.

## Design language

The storefront mirrors the app's design system (tokens copied into
`storefront/app/static/store.css`): amber marks exactly one primary action
per view, Courier carries machine data (tokens, prices' terms, metadata),
square corners, no gradients, no emoji. `app/static/DESIGN_SYSTEM.md`
remains the canonical statement of that language; the storefront follows it
but does not add to its Uncanonized table (it is a separate surface).
