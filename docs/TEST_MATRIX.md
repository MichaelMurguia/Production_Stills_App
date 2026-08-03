# Test Completeness Review

*2026-08-02, against release 2026.08.01.33; counts updated through
2026-08-04 (release 2026.08.04.43). Suites: `tests/` (116 tests, 14
files) and `storefront/tests/` (68 tests, 10 files). Since the original
review: P1 items 1–3 closed by `test_p1_lifecycle.py` (13 route-driven
tests); `test_debug_tools.py` (mock engine incl. a full zero-cost
pipeline walkthrough, text overrides, owner gating); the connectors
session's catalog/enable/generate coverage; `test_narrative.py` (F6
backend — Anthropic/OpenRouter dispatch, gating, settings surface);
storefront gained `test_seo.py` and `test_site_text.py`. Known flake:
one provisioner test can reach the real network through the
`_domain_serves` probe when a row's url/railway_url diverge — seen once;
stub it if it recurs. Both run in CI on every push;
the convention (CLAUDE.md) is that every feature/bugfix updates tests in
the same commit. The audit batch (`docs/AUDIT_2026-08-02.md`) added
`test_audit_fixes.py` to both suites: traversal guards, canvas bounds,
corrupt-state resilience, quarantine enforcement, restore staging,
webhook payment gating, refunds, revoke discipline, claim-race index,
OAuth state binding, admin header tokens, magic-link throttle.*

## What is well covered

**Product app** — auth gate + healthz; the full productions lifecycle
(create/activate/rename-by-slug/duplicate/typed-delete/summary/first-run);
breakdown gating (423 both creation paths, cleared by bible save, project
field + validator regression); screenplay efficient-format conversion +
legacy backfill; reference render-ready transcode + compose rescue;
interview persistence (+ backup inclusion); no-template art direction;
UI no-cache; backup/restore security (zip-slip, size caps, settings
exclusion — `test_backup_security`); board layout math
(`test_assemble_layout`: aspect/grid/hero variants, no-upscale verdicts);
bible section parsing + selective injection (`test_bible`); generation
units (`test_generate_units`: aspect catalog, prompt pieces); wizard
re-run merge semantics; path/project isolation (`test_paths_projects`).

**Storefront** — fulfillment idempotency + Stripe-shaped access;
provisioning converge/retry/revoke + fleet update (drain config, pinned
sha, failure recording); magic-link lifecycle (single-use, uniform
response, tamper-proof sessions); avatars; naming (validation, owner-only,
claim/rename button state, terms line); custom-domain→router migration +
reliable doors (LIVE/PROVISIONING states); version listing; recovery +
admin export/reconcile/wildcard gates; tenant proxy (pass-through,
forwarding, stated 404 anatomy, 503 + Retry-After + reassurance page,
last-answered row, off-railway SSRF guard, POST bodies); /pipeline page
(content, true numbers, downscaled images).

## Gaps, prioritized

### P1 — untested behavior that guards money, canon, or data
1. **Sheet lifecycle beyond creation**: `PUT /api/specs/{id}` (save),
   `/approve` (lock + hash mint), `/revise`, `/unlock`, `DELETE` — the
   lock/hash contract is the product's core promise and has no direct
   functional test (the rule engine is tested only via `validate`).
2. **Candidate lifecycle**: status transitions (approve/reject + reason →
   lessons), `promote` (reference back-link), `purge-rejected`, image
   serving 404s. All exercised only in production.
3. **Assemble endpoint**: `POST /assemble` happy path with tiny synthetic
   PNGs — record shape (`rects`, `panels_used`), composite exists,
   duplicate-assembly semantics; `slot-map` TOO_SMALL verdict through the
   API (unit-tested in `test_assemble_layout`, not the route).
4. **Stripe webhook route**: partially closed by the audit batch
   (unpaid-session gate, async-payment fulfill, refund events are now
   driven through the route with a patched `construct_event`). Still
   untested through the route: signature rejection, the
   `customer.subscription.deleted` → revoke path.

### P2 — model-call seams (fake the engine, test the plumbing)
5. `autofill_spec` end-to-end with a stubbed draft function — spec
   normalization, budget stamping, ledger construction from model JSON
   (malformed-JSON path included).
6. `wizard.draft_bible` with a stub — interview backfill merge, reference
   attach goes through `_render_ready`, BINDING instructions present.
7. `generate` request assembly — that a generation composes rendering
   language + carried rejections + refs, and that `_wrap_engine_error`
   classification is covered beyond the two inline cases (it is tested
   ad-hoc, not in the suite).

### P3 — worth having
8. Region repair compositing (outside-mask pixels byte-identical) with
   synthetic images.
9. Router × storefront session interplay (cookies never forwarded across
   tenants — currently true by construction, untested).
10. `/api/settings` engines shape + custom-engine CRUD + test-result
    recording (`engine_tests` drives all UI gating; shape drift would
    silently kill the gates).
11. Frontend: no JS test rig exists. The jsdom repro harness built for
    the sheet-editor TDZ bug (scratchpad `repro.js`) proved its worth the
    same day; promoting it into `tests/js/` with 3-4 smoke mounts (sheet
    editor populates, band locks compute, provider selects gate) would
    have caught two of today's live bugs pre-ship.

### Known structural quirks (accepted, documented here)
- App tests share one process; `paths` redirection (`_redirect_home`) is
  the isolation mechanism — new tests must use it.
- Storefront tests share one SQLite file per run; use unique
  session/subdomain ids (a name collision bit once already).
- `python -m unittest … | tail` masks exit codes — always
  `set -o pipefail` (this escaped red tests into pushes twice).

## Recommendation

Close P1 items 1–3 next (they protect the canon-lock contract and the
board pipeline — roughly a dozen tests against existing fixtures), stub
seams for P2 after, and adopt the jsdom smoke rig when frontend churn
next slows down.
