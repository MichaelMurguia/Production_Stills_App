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

**Keys are wrapped at rest** (2026-08-23): Windows DPAPI, bound to the
user account, so the file is inert on another machine or profile. That
closes *file exfiltration*, not the OS-user boundary — nothing tells a
customer where to unzip, so the install folder is routinely Downloads,
Desktop or Documents, all OneDrive-synced by default on Windows 11, and a
plaintext key there synced to Microsoft's cloud and every other device on
the account. A plaintext file from an earlier version is wrapped once at
boot. Where no wrap is available the app stores plaintext and **says so**
via `secrets_at_rest` on `/api/settings`; a wrap we cannot perform is
never reported as one.

**Cloud workspace (one tenant = one Railway service):** the whole app sits
behind the workspace access token (`SCREENBOARD_ACCESS_TOKEN`): pages
redirect to `/login`, APIs return 401, the session cookie is HttpOnly /
SameSite=Lax / Secure-on-HTTPS, comparisons are constant-time, and failed
logins pay a 0.5 s delay. Only `/login`, `/api/login`, `/api/healthz`, and
the stylesheet are reachable unauthenticated. Studio API keys are wrapped on the volume with
AES-GCM under `SCREENBOARD_SECRET_KEY`, a per-workspace Railway variable —
held off the volume on purpose, so a volume snapshot, a disk leak, or a
restore onto another service yields ciphertext. **This is not a defence
against us**: we hold that variable, and encryption whose key the operator
also holds protects against everyone except the operator. Stated plainly
rather than dressed up (ruled 2026-08-23); the only real fixes would be a
browser-held key or not taking keys at all, and neither is built.
Isolation between tenants is
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
4. **Secrets never echo.** `/api/settings` returns 4-character hints only
   — swept live 2026-08-23 across all 42 parameterless GET routes with a
   sentinel key: none returned it. The flight recorder redacts by field
   name (key/token/secret/b64/image_url) **and by value**: every credential
   the install holds is matched literally in any string, plus a shape match
   (`sk-`/`AIza`-style) for a key being verified before it is stored.

   The value pass was added after this audit found the name-only rule
   reachable. The middleware logs `str(e)[:500]` on a raised route and the
   response body on any 4xx/5xx, both under `error`, which matched no
   marker. A custom engine's `base_url` is user-supplied, so an upstream
   that echoes the credential in its error message wrote the key into
   `data/activity_log.jsonl` — and that file rides a project backup, which
   guarantee 2 calls shareable. Proven end to end against a local endpoint,
   then fixed; `tests/test_credentials_stay_put.py` holds the proof.
5. **Headers.** Both apps send `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` on every
   response.
6. **Release artifacts are clean.** The staged zip is `git archive HEAD --
   app requirements.txt run.bat README.md INSTALL.md VERSION` — built from
   committed content, not the worktree, so an untracked secret cannot reach
   it by construction. Verified 2026-08-23: 143 files, six top-level
   entries, no `settings.json`, `data/`, `projects/`, `project_state/`, or
   bible.

   `scripts/export_package.py` — a developer convenience, never the
   product — did walk the worktree, and on a standalone install
   `SCREENBOARD_HOME` **is** the repo root, so it would have zipped
   `settings.json` with live keys, `.claude/settings.local.json`, and 1716
   files of `data/` (3028 files total). It now packages `git ls-files`
   output only (789 files) and refuses outright if a forbidden path is ever
   tracked.
7. **Authored tutorials cannot become an injection surface** (2026-08-17).
   A tutorial is content written through a text box and then rendered into
   the app, so it is treated as untrusted even though its author holds the
   workspace token. Bodies are escaped first and only `**bold**` and
   `` `code` `` are restored — **HTML is never rendered**, and there is no
   path by which authored text reaches `innerHTML` unescaped. A step's
   `goto` and its act button's `goto` must match a single-leading-slash
   same-origin path (`//host` and absolute URLs are refused at save), so a
   tutorial cannot navigate a studio off-app; an `api` advance condition is
   a *read* of what the user already did, never a call the tutorial makes.
   Ids that become filenames pass the module's own `ID_RE`, and the
   state-recording route rejects a traversing id with the same 404 as an
   unknown one. Authoring is gated on `SCREENBOARD_DEBUG_TOOLS` — the CMS
   routes 404 for a customer exactly as Debug tools do — while the read
   bundle and the state routes stay open, because a studio must be able to
   run and dismiss its own onboarding.

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
