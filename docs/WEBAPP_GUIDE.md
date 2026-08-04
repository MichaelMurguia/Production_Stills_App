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
| `GET /download/{token}` | Serves the CURRENT release for a PAID token; `?version=` serves any staged past version (resolved only through the file registry). 404 unknown token/version, 503 missing artifact. |
| `POST /stripe/webhook` | Signature-verified. `checkout.session.completed` → fulfill; `customer.subscription.deleted` → mark purchase CANCELED. |
| `GET /healthz` | `{ok, rev}` — the git commit currently serving. First stop when asking "did my deploy land?" |
| `GET`/`POST /recover` | License recovery. Anti-enumeration by construction: identical response either way; details only ever mail to the owning address. SMTP unset → stated gate. |
| `GET /terms`, `GET /privacy` | Plain-language legal pages (Stripe activation expects them). |
| `GET /admin/export?token=` | Entitlement backup (purchases/licenses/workspaces JSON). Exists only when `ADMIN_EXPORT_TOKEN` is set; wrong token → 404. |
| `GET /signin`, `/signup` · `POST /auth/email` · `GET /auth/verify` | Passwordless accounts: magic links (single-use, 30 min, uniform responses) create-or-sign-in on click. No passwords exist anywhere. |
| `GET /auth/google` + `/callback` · `POST /auth/logout` | Google OIDC (stdlib, no SDK): signed state, code exchange, verified-email required. Env-gated — button hides unconfigured. |
| `GET /account` | Signed in: every purchase on the account email — download buttons, workspace doors, studio naming. Signed out: token-as-credential fallback. |
| `POST /studio/name` | Owner-only claim/rename of a studio's subdomain (validated, reserved-listed, unique). Old domains keep answering — Railway serves every domain ever attached. Unclaimed studios carry a random two-word slug, never the purchase number. |

Accounts are a **viewing lens** — `purchases` remains the entitlement
truth, linked by verified email; sessions are HMAC-signed cookies
(`SESSION_SECRET`).

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
  **This table is the source of truth for entitlements** — the
  provisioner grants/revokes cloud workspaces from it.
- `licenses` — download credential: unique `token` gates the zip,
  `downloads_used` counts (bookkeeping, not a cap).
- `workspaces` — one per cloud purchase: status
  PENDING|ACTIVE|FAILED|REVOKED, `access_token` (the tenant's login),
  Railway service/volume ids, `url`, and `detail` (the stated reason
  whenever the row isn't ACTIVE).

### Cloud workspace provisioning (built 2026-07-31)

`provisioner.reconcile()` converges workspaces toward the purchases
table — one tenant Railway service per PAID cloud purchase (repo root,
`uvicorn app.main:app`, volume at `/workspace`, generated domain), deleted
on CANCELED. It runs at startup, after cloud fulfillment, and after
subscription webhooks; it never raises, every step is idempotent, and
every failure lands on the workspace row as `detail`. The Railway GraphQL
client (`railway.py`) is **injected**, so `tests/test_provisioner.py`
drives the whole machine with a fake — unconfigured-gate, provision-once,
failure-retry, and revoke are all covered. Missing `RAILWAY_*` config is a
stated gate: rows queue PENDING, the success page says the workspace is
being prepared, and the buyer's revisitable success URL is the pickup
point for the workspace URL + access token once ACTIVE.

The product app's cloud-mode contract (all env-gated; unset = standalone
behavior, byte-identical and offline):

- `SCREENBOARD_HOME` — relocates projects, settings, and all user data
  (tenants point it at their volume).
- `SCREENBOARD_ACCESS_TOKEN` — puts the whole app behind the workspace
  login; `/api/healthz` stays open as the provisioner's probe.
- Multi-project save/load lives in the product app itself (Settings →
  Projects) and works identically standalone and hosted.

Schema changes: `create_all` creates tables but never alters them; additive
columns go in the `init_db()` micro-migration block (see `tier`). Anything
destructive requires introducing Alembic first.

### The admin hub (built 2026-08-06)

`GET /admin` is the owner's one page: debug tools (store text editing),
trial codes, and the operations that were previously curl-only
(`reconcile`, fleet update, entitlement export). `_admin_gate()` is
satisfied **two ways** — a signed-in `OWNER_EMAILS` session, or the
shared `ADMIN_EXPORT_TOKEN` as query param or bearer header. The session
path is what makes the page usable in a browser without pasting a secret
into the address bar; the token path keeps every existing runbook and
curl command working unchanged. Both are closed sets and failure is
always 404 — an admin surface must not confirm its own existence.

The header renders an `ADMIN` link only for an owner session
(`request.state.is_owner`, already computed by the security-headers
middleware for every request). `/admin/trials` redirects to `/admin`
because it is in the runbook.

### Trials — two kinds, one entitlement machine (built 2026-08-06)

`storefront/app/trials.py`. Both kinds create an ordinary cloud
`Purchase`, so provisioning, naming, proxying and revocation are the
paths already proven in production. A trial is an entitlement with an end
date, never a separate product or a crippled mode — the trialist gets the
whole cloud edition.

**Card trial** (`trial_kind="card"`). `/trial/start/{plan}` opens a normal
Stripe Checkout in `subscription` mode with `subscription_data.
trial_period_days = TRIAL_DAYS` and, critically,
`payment_method_collection="always"` — without that flag Stripe may skip
collection and the day-N conversion silently fails. It runs on the plan's
real price id; nothing separate is configured. Stripe converts it on its
own: **we never end a card trial**, and `expire_due()` deliberately skips
them so a clock skew can never revoke a studio someone is paying for.
`customer.subscription.updated` (handled by `_handle_subscription_updated`,
extracted so it is testable without a signed event) keeps our copy honest:
Stripe's `trial_end` corrects the date while trialing, and the move to
`active` clears the window so the account page stops counting down.
Cancellation is unchanged — `customer.subscription.deleted` → CANCELED →
revoked.

**Code trial** (`trial_kind="code"`). An operator mints a code in
`/admin/trials` (gated by `ADMIN_EXPORT_TOKEN`, like every other admin
route) carrying its own length, edition, redemption count and optional
shelf life. Codes are `SB-XXXX-XXXX` over an alphabet with no I/O/0/1 —
they get read aloud and typed by hand. Redemption needs a signed-in
account (a trial belongs to an identity), and one live studio per account
is enforced. There is no payment method and no Stripe object, so **nothing
external will ever end one**: `reconcile()` calls `trials.expire_due()`
first on every run, past-date purchases become `EXPIRED`, and the existing
revocation branch deletes the tenant service and releases the name.

A visitor who submits a code while signed out does not lose it: it rides a
signed 30-minute cookie (`sb_trial`) through the sign-in round trip and
redeems itself the moment an identity exists (`_consume_trial_code`, called
from both the magic-link and Google completions). The redirect rewrite
preserves the `Set-Cookie` headers already on the response — losing them
would sign the user straight back out.

Tests: `tests/test_trials.py` (24) covers code shape and normalization,
every stated refusal, one-studio-per-account, the expiry sweep revoking a
real service through reconcile, the card-trial checkout arguments
(including `payment_method_collection`), fulfillment recording the window,
Stripe's date correcting ours, the conversion clearing the countdown, and
the whole operator console.

### The wildcard tenant router (built 2026-08-01)

Branded studio addresses (`<name>.TENANT_DOMAIN_BASE`) are served by the
storefront itself, not by per-tenant Railway custom domains. `app` in
`main.py` is a `TenantProxy` (`tenant_proxy.py`) wrapping the FastAPI app
(exported as `store`): every request's Host is inspected — storefront
hosts pass through untouched; a claimed, ACTIVE, PAID studio subdomain is
reverse-proxied (streaming both ways, long read timeout for renders) to
that workspace's `railway_url`. Unknown or revoked studio hosts get a
stated 404 page, an unreachable tenant a stated 503 (styled, auto-retry).
That styled page also replaces anything Railway's edge answers for a
tenant mid-redeploy — upstream 502/503, or a 404 stamped
`x-railway-fallback: true` — on browser navigations (GET/HEAD accepting
HTML): raw platform error pages must never flash on a branded address
(seen on a12-oxcart during the .60 fleet update). The app's own 404s
carry no fallback stamp and pass through; non-HTML clients always keep
the true upstream status. Safety invariant:
the proxy only ever forwards to a `*.up.railway.app` host taken from the
workspace row — never to a user-influenced or branded host (loop risk).
The wildcard domain `*.<base>` is attached to the storefront service once
(see DEPLOYMENT.md); claiming/renaming a studio therefore needs zero DNS
or Railway calls and is live on row commit. `tests/test_tenant_proxy.py`
drives the router with an `httpx.MockTransport` — pass-through, proxying,
stated 404s, the off-railway guard, and request bodies are all covered.

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

**Hardening baseline (audited 2026-08-02, `docs/AUDIT_2026-08-02.md`) —
do not regress:** fulfillment follows the money (webhook gates on
`payment_status`; refunds/disputes flip status via the stored payment
intent); REVOKED is stamped only after the Railway delete succeeds and
releases the subdomain; subdomain uniqueness is a DB partial unique
index, not a check-then-set; `reconcile()` runs under a process lock;
OAuth state is expiring and cookie-bound; admin endpoints accept
`Authorization: Bearer`; magic links are throttled per address; the
tenant proxy strips inbound `X-Forwarded-*`, validates upstream hosts by
parsed hostname, and refuses websockets on tenant hosts.

**SEO surface (pass of 2026-08-03) — keep consistent:** exactly four
public pages (`/`, `/pipeline`, `/terms`, `/privacy`) are indexable and
listed in `/sitemap.xml`; `robots.txt` disallows everything
transactional, and those pages ALSO carry `noindex` meta (account,
success, signin/signup, recover, both router pages). Canonicals and
`og:url` always build from `BASE_URL`, never the request host. The
index page's JSON-LD offer prices must change in the same commit as the
displayed prices (same rule as the price/template pairing above). Every
tenant-host response — proxied studio traffic and router pages alike —
carries `X-Robots-Tag: noindex`; private studios are never crawlable.
Tests: `tests/test_seo.py`.

**Owner page-text rewrites** (debug tool, 2026-08-03): `/api/site-text`
— public GET (the overrides are the live page copy, applied by a
base-template script for every visitor), owner-only PUT/DELETE
(`OWNER_EMAILS` session accounts; everyone else sees 404 and never
receives the editor script). Overrides live in the `site_texts` table —
never on disk (ephemeral). Owner controls sit on Your Screenboard;
Alt-click rewrites in place. Tests: `tests/test_site_text.py`.

**Trials never become a second product.** A trial is a cloud `Purchase`
with an end date; anything that would give trialists a different app, a
watermark, or a reduced feature set is out of scope by design. Two rules
protect the money: we never end a card trial (Stripe owns any entitlement
with a payment method behind it), and a code trial always has an operator
name on it (redemption requires a signed-in account).

## Developing and shipping

- **Product app:** `run.bat` at repo root (uvicorn, auto-reload).
- **Storefront locally:** `cd storefront && uvicorn app.main:app --port
  8100 --reload`. SQLite, checkout gated unless Stripe env vars are set.
  Webhooks locally: `stripe listen --forward-to localhost:8100/stripe/webhook`.
- **Tests — both suites green before any push** (see CLAUDE.md § Testing;
  every feature updates its tests in the same commit):
  `cd storefront && python -m unittest discover -s tests -v` (fulfillment
  idempotency, Stripe-shaped objects, provisioning) and
  `python -m unittest discover -s tests -v` at repo root (bible model,
  merge semantics, board layout, size rules, keyword derivation, project
  paths, and TestClient functional passes over the auth gate and projects
  lifecycle).
- **Deploy = push to `main`.** Railway builds `storefront/` only (root
  directory setting). Confirm with `/healthz` that the new rev is serving.
  Rollback: redeploy a previous deployment in the Railway dashboard.
- A failed deploy keeps the previous one serving; the site does not go
  down because a build broke.

## Roadmap (agreed, not yet built)

1. ~~Cloud workspace provisioning~~ — **built 2026-07-31** (see section
   above). Remaining: grant the `RAILWAY_*` variables and run the
   supervised first live provision (`docs/DEPLOYMENT.md` setup section).
2. ~~License recovery~~ — **built 2026-08-01** (`/recover`, SMTP-gated,
   anti-enumeration).
3. ~~Transactional email~~ — **built 2026-08-01** for recovery mail
   (stdlib SMTP via `mailer.py`); purchase-confirmation mail beyond
   Stripe's receipts still open.
4. **Go-live** — Stripe activation + live keys swap; checklist in
   `docs/DEPLOYMENT.md` (now includes backups, SMTP, CI, legal review).
5. **Tenant data care** — operator-side volume snapshots + retention
   promise; decide before real subscribers. In-app project backups and
   the entitlement export (tier A) exist.
