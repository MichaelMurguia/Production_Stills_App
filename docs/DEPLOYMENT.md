# Deployment & Commerce — DevOps Reference

Written 2026-07-31 by the DevOps agent. This is the operational truth for how
this project is sold, hosted, and deployed. The app development agent must
read this before touching `storefront/` or anything deployment-related.

## Service registry (as of 2026-08-03)

Every external account this business runs on, why it exists, and where its
credentials live. Keep this table current when a service is added or
dropped. **Screenboard's services are deliberately separate from the
owner's other company** — SendGrid and the other org's Google Workspace are
NOT part of this project and must not be wired into it.

| Service | Role | Key facts | Credentials live |
|---|---|---|---|
| **GoDaddy** | Registrar + DNS for `screenboardstudio.com` | Records: `www` CNAME → Railway, `_railway-verify.www` TXT, Resend sending records, apex 301-forward → www. Free email forwarding NOT available on this domain | GoDaddy account |
| **Railway** (railway.com) | All hosting | Project "studioboards": storefront service (root dir `storefront`) + Postgres. Separate tenants project for cloud studios (project token). Deploys on push to `main`; usage-billed incl. ~$2–5/mo per tenant | Railway dashboard; every app secret is a service Variable |
| **GitHub** | Repo + CI | `MichaelMurguia/Production_Stills_App`; Actions run both suites + release-zip + verify-deploy on every push; Railway watches `main` | GitHub account |
| **Stripe** | All payments | Live + sandbox are parallel universes: 4 products each, webhook endpoint each (`/stripe/webhook`). Sole-proprietor activation. TODO: set support email to `support@screenboardstudio.com` | Keys in Railway variables only |
| **Resend** | OUTBOUND transactional mail only (magic links, license recovery) — sends as `no-reply@`; **cannot receive mail** | Domain verified via GoDaddy DNS. **TODO: rotate the API key (exposed in a chat transcript 2026-08-03)** — new key → Railway `SMTP_PASS` → delete old | Key in Railway `SMTP_PASS` |
| **Google Cloud** | "Continue with Google" sign-in (OIDC) | OAuth web client, redirect `…/auth/google/callback` | `GOOGLE_CLIENT_ID/SECRET` in Railway |
| **Zoho Mail** (setup IN PROGRESS) | INBOUND mail — the human inbox | **Mail Lite purchased ($1/user/mo)**, own org, signup under the owner's personal address; `info@` is the mailbox, `help@`/`support@` to be aliases; destination workflow is forward-to-Gmail + Gmail Send-as via Zoho SMTP. Stalled at: Zoho refusing SMTP ("not available for your account") — the Mail Lite license is likely unassigned to the user. See "Open operational items" | Zoho account (Screenboard-owned) |
| **OpenRouter / fal.ai / OpenAI / Google AI Studio** | Owner's OWN render/narrative keys for the house studio and testing | These are BYOK app credentials, not business infrastructure — every customer brings their own. Never in the repo; live in each install's `settings.json`/`connectors.json` | Per-install, owner's accounts |

Renewal/billing sanity: GoDaddy (annual domain), Railway (monthly usage),
Stripe (per-transaction), Zoho Mail Lite ($1/user/mo),
Resend/GitHub/Google Cloud (free tiers at current volume).

## Open operational items (parked 2026-08-03)

**Email completion** — where it stopped and the exact remaining steps:

1. Zoho admin (mailadmin.zoho.com) → Subscription: confirm Mail Lite is
   active, then Users → `info@` → assign the Mail Lite license (buying
   and assigning are separate — the "SMTP not available for your
   account" error is this).
2. Zoho Mail → Settings → Mail Accounts → POP/IMAP → enable IMAP access.
3. Confirm GoDaddy has Zoho's 3 MX records on `@` (mx/10, mx2/20,
   mx3/50) + SPF merged + DKIM; test-mail `info@` lands in Zoho.
4. Zoho forwarding → owner's Gmail (verify code, keep copy in Zoho).
5. Gmail → Send mail as `info@screenboardstudio.com` via `smtp.zoho.com`
   :465 (app password if MFA). Fallback if Zoho SMTP keeps refusing:
   `smtp.resend.com`:465 user `resend` + the ROTATED key.
6. Aliases `help@` + `support@` on the `info@` user; test all three.
7. Stripe (live) → Business details → support email =
   `support@screenboardstudio.com`.

**Standing security item:** rotate the Resend API key (exposed in a chat
transcript 2026-08-03): Resend → new key → Railway `SMTP_PASS` → delete
old key.

**Also parked:** tenant fleet update to the current release
(`/admin/tenants/update` — house studio and tenant-5 run older builds);
product roadmap items live in CONNECTORS_PLAN.md (N5 on demand, N6 truth
pass, fal starter set, Role-01 Gemini fix, narrative-via-OpenRouter).

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
| `PREVIEW_PASSWORD` | Pre-launch gate: while set, every store page serves the coming-soon overlay until this password is entered (signed 30-day cookie). Tenant studios, `/stripe/webhook`, `/healthz`, `/admin/*` and `/api/site-text` are never gated. Unset → site fully open |
| `OWNER_EMAILS` | Comma-separated store-owner account emails. Studios purchased under these addresses are provisioned with `SCREENBOARD_DEBUG_TOOLS=1` — the in-app Debug tools (mock engine, page-text edit) exist only there; customer studios and shipped zips never have them. Unset → no studio gets debug tools |
| `ADMIN_EXPORT_TOKEN` | Long random value enabling the `/admin/*` endpoints (export, reconcile, wildcard, tenants/update). Send it as `Authorization: Bearer <token>` (preferred — query `?token=…` still works but lands in access logs). Unset → the endpoints 404 |

Tenant services additionally get `FORWARDED_ALLOW_IPS=*` from the
provisioner so uvicorn trusts Railway's `X-Forwarded-Proto` and the
workspace session cookie is marked Secure. Existing tenants pick it up
on the next provision sweep; the app also forces Secure whenever it
detects Railway.
| `SESSION_SECRET` | Long random value signing account-session cookies. Unset → per-boot secret (sessions reset each deploy) — set in production |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | "Continue with Google" (OIDC). Create at console.cloud.google.com → Credentials → OAuth client (web) with redirect URI `https://www.screenboardstudio.com/auth/google/callback`. Unset → the button hides; magic links still work |

All provisioning variables are optional: while unset, cloud purchases
queue as PENDING workspaces with the condition stated on the row — nothing
crashes, and the success page honestly says the workspace is being
prepared. The SMTP and export variables are likewise optional gates.

## Trials (built 2026-08-06)

Two doors, both landing on an ordinary cloud studio. See
`docs/WEBAPP_GUIDE.md` for how they work; this is what to set and how to
run them.

| Variable | Default | What it does |
|---|---|---|
| `TRIAL_DAYS` | `14` | Length of the card-backed trial. **`0` closes card trials** — the store still sells normally and the page states the gate. |
| `TRIAL_CODE_MAX_DAYS` | `365` | Ceiling on a minted code, so a typo in the console cannot grant a decade. |

Card trials need nothing else: they run on `STRIPE_PRICE_CLOUD_*`, the
same price ids the paid plans use. Stripe must be able to reach the
webhook (already configured) — add **`customer.subscription.updated`** to
the endpoint's event list so the trial's date and its conversion are
recorded. Without it a converted subscription keeps counting down on the
account page; entitlement is unaffected either way.

**Granting a free trial by hand** (the operator flow):

1. Open `https://www.screenboardstudio.com/admin/trials?token=$ADMIN_EXPORT_TOKEN`.
2. Mint a code: days of access, edition, how many times it may be
   redeemed, optional shelf life for the code itself, and a note saying
   who it is for — the note is the only record of *why*, so write it.
3. Send the person the code and `https://www.screenboardstudio.com/trial`.
   They sign in (Google or a mailed link), paste the code, and their
   studio provisions like any purchase.
4. The console's second table shows every trial, its days left, and its
   studio. **End now** expires a code trial immediately (the studio is
   revoked on the next reconcile, which that button schedules).
   **Withdraw** disables a code without touching trials already redeemed
   from it.

A code trial ends on our clock: `reconcile()` sweeps expired ones on every
run (startup, webhook, `/admin/reconcile`, naming). A card trial ends on
Stripe's — never end one from here; cancel it in Stripe if you must.

## House entitlements (decided 2026-08-03)

Rows whose `stripe_session_id` starts `cs_test_` are the owner's sandbox-era
purchases, kept deliberately: the test-era cloud workspace is the **house
studio** — the owner's own instance holding tutorial and example projects.
Do NOT cancel, revoke, or "clean up" these rows or that tenant service; the
`cs_test_`/`cs_live_` prefix is the permanent discriminator (exclude
`cs_test_` from any revenue counting). Its sandbox subscription can no
longer emit processable webhooks (live signing secret), which is fine — the
house studio is permanent until deliberately removed. Open risk: tenant
volumes have no backup yet; the house studio's tutorial content shares that
exposure (see "Not built").

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
  `checkout.session.completed` (fulfill),
  `customer.subscription.deleted` (mark purchase CANCELED), and
  `customer.subscription.updated` (a card trial's date and its conversion —
  see the Trials section; without it a converted subscription keeps
  counting down on the account page, though entitlement is unaffected).
  `charge.refunded` / `charge.dispute.created` are also handled if
  subscribed.
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
