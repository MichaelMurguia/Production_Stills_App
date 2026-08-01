# Security — threat model, guarantees, and the 2026-07-31 pass

Written by the webapp agent after the first full security pass. Update this
in the same commit as any change that touches auth, file serving, secrets,
tenancy, or backups.

## What is being protected

A filmmaker's unreleased creative work: the screenplay, the Art Direction
Bible, references, renders, and approvals — plus their render-engine API
keys, and (server-side) the Stripe/Railway credentials of the business.

## Trust model by surface

**Standalone install (download buyers, and this machine):** binds to
127.0.0.1 via `run.bat` — the app is reachable only from the user's own
machine. No auth by design; the OS user account is the boundary. API keys
live in the install's `settings.json` and leave the machine only in calls
to the provider they belong to.

**Cloud workspace (one tenant = one Railway service):** the whole app sits
behind the workspace access token (`SCREENBOARD_ACCESS_TOKEN`): pages
redirect to `/login`, APIs return 401, the session cookie is HttpOnly /
SameSite=Lax / Secure-on-HTTPS, comparisons are constant-time, and failed
logins pay a 0.5 s delay. Only `/login`, `/api/login`, `/api/healthz`, and
the stylesheet are reachable unauthenticated. Isolation between tenants is
service-level (separate Railway services, separate volumes); tenant data
exists only on the tenant's volume — repo-derived deploy images contain no
user canon (`data/`, `projects/`, `project_state/`, `settings.json`, and
the Beltminers bible are untracked).

**Storefront (public):** no accounts and no stored payment data — Stripe
Checkout holds PCI. Webhooks are signature-verified. Download and workspace
tokens are 24-byte `token_urlsafe` values; unknown tokens 404. Business
secrets exist only in Railway variables and local shells.

## Standing guarantees (enforced in code, covered by tests)

1. **No traversal from ids.** Every URL-supplied id that becomes a path
   component passes `paths.safe_id()` (alnum-led single component — `..`,
   separators, and backslashes are impossible) or `store._spec_path()`'s
   equivalent regex. Traversal-shaped ids get the same 404 as unknown ids.
2. **Backups are shareable.** A project backup zip contains creative work
   only — API keys are excluded by construction (`app/backup.py`).
3. **Restores are inert.** Restore always creates a NEW project, never
   overwrites, and every archive member is validated against zip-slip
   (absolute paths, drive letters, backslashes, dot segments, unexpected
   roots) before a byte is written, with size caps against zip bombs.
4. **Secrets never echo.** `/api/settings` returns 4-character hints only;
   the flight recorder redacts any field whose name contains
   key/token/secret/b64/image_url (login tokens verified redacted).
5. **Headers.** Both apps send `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` on every
   response.
6. **Release artifacts are clean.** The staged zip is verified to contain
   no `data/`, `projects/`, `project_state/`, `settings.json`, or bible.

## Findings of the 2026-07-31 pass (all fixed)

- Candidate/board path builders accepted raw URL ids — traversal possible
  on Windows via encoded backslashes → `paths.safe_id()` at every builder.
- `activity.LOG` and `insights.CITATION_REPORT` froze their paths at
  import — after a project switch they kept writing to the wrong project
  → computed per call.
- No login throttling → 0.5 s failure delay (with constant-time compare).
- No security headers on either app → added.
- Verified non-findings: settings endpoints return hints only; webhook
  signatures verified; SQLAlchemy ORM throughout (no string SQL); Stripe
  session ids required for `/success`; screenplay/reference file serving
  resolves only server-recorded filenames (sanitized at upload).

## Known accepted risks / future work

- **No CSP yet** — the SPA and login page use inline styles/scripts;
  adding CSP needs a nonce pass. Mitigated by DENY framing + same-origin
  use. Revisit if the app ever embeds third-party content.
- **Single-token workspace auth** — no user accounts, no rotation UI. A
  leaked token = workspace access until re-provisioned. Rotation endpoint
  is future work; cancellation already revokes the whole service.
- **No rate limiting beyond the login delay** — Railway/Cloudflare-level
  limiting is the right home if abuse appears.
- **Tenant volume backups** — the in-app backup zip works in cloud
  workspaces too (download through the browser), but operator-side volume
  snapshots are roadmap item 5, to decide before real subscribers.
