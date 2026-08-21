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
the same commit. Counts as of 2026-08-10: `tests/` 531, `storefront/tests/`
193. The sheet grammar (SHEET_SYSTEM_PLAN, 2026-08-10) added
`test_sheet.py` (43 tests): the R1 elastic/fixed ladder against the plan's
worked-outcomes table (the unreachable 18×12 print rung is exercised via a
test-only injected frac — the canon set stays closed at twelve), the
one-list export gate (TYPE_FLOOR + SLOT_PIXELS, empty slots and over-crops
included), caption staleness (rebind/author never touch the source),
palette-order preservation, sheets-never-write-SPECS_DIR, idempotent
/arrange with the R3 variant mapping (cap-aware since 2026-08-12) and R4
derived strip, render letterbox-vs-raise parity (R2), gated PNG/PDF
export at exact pixel size, the fill tray, and the stage-05 wiring
(Arrange door opens the room inline; the Lookbook surface is gone —
rollback regressions pin its absence; R7 rename held). `test_assemble_layout.py` passed
unchanged across the packing-function move — the behaviour-preservation
gate. `tests/test_camera.py` (19) covers the same-day camera revision.
The audit batch (`docs/AUDIT_2026-08-02.md`) added
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

**Tutorials** (2026-08-17, `test_tutorials.py` 33 + `TutorialRoutes` in
`test_app_api.py` 6) — the two places an authored-content system rots are
both pinned. **The anchor registry**: every selector in
`content/tutorial_schema.json` is resolved against the real markup, so a
renamed id fails the build instead of stranding a spotlight in front of a
customer. **One vocabulary, two languages**: the predicate kinds the Python
validator accepts and the kinds `tutorial.js` evaluates are read off disk
and compared both ways — a kind the server accepts and the browser ignores
is a tutorial that silently never fires, and a kind only the browser knows
can never be authored. Also: every packaged tutorial validates and the FTUE
is live; the example announcement ships disabled; contexts are enforced
(`first_run` refused as an *advance* condition, `click` refused as a
trigger); `goto` cannot leave the app; install content overrides packaged
by id and a tombstone hides one; a corrupt file does not take the others
down; broken content is inert rather than half-run; state records/resumes
/resets and refuses a traversing id; the CMS is 404 to a customer while the
runtime bundle is open to every studio; and invalid content is refused with
every reason at once.

**The read, as it happens** (2026-08-20, `test_read_progress.py` 18 +
`TheReadPanelIsLegibleAndHasOneAmber` in `test_design_tokens.py` 6) — the
live progress surface is only defensible because every number on it is
measured, so that is what is tested: sluglines become numbered scenes in
page order, cue lines attach to the scene they are spoken in, a transition
(`FADE OUT.`, `CUT TO:`) is never reported as a person, and the snapshot
contains the screenplay's own characters. Then the commentary as
arithmetic — every `speaks in N of M` matches a recount of the parse,
`lead` vs `recurring` is a stated threshold, a location seen once is never
"a place the script keeps coming back to", and the interior/exterior split
sums to the scene total. Then the surface: the ladder is fed by
`/api/screenplay/digest` and by nothing else (a second source is a second
answer to "what is in this screenplay"), the model phase states in words
that it has no per-scene progress, a read survives leaving the view, and
the panel carries exactly one amber and invents no colours.

**No control bytes in source** (2026-08-20, `test_no_control_bytes.py` 2)
— a standing byte-level contract. Twice a `\b` authored through a shell
heredoc reached a source file as a real backspace (0x08), producing a
regex that compiles, runs, raises nothing and silently never matches: the
digest stopped reporting shouted props, and the tutorial editor stopped
labelling ID errors. Both failures are *silence*, so no behavioural test
could catch them. This one makes the byte itself the failure, across every
`.py/.js/.json/.css/.html/.md` in the tree.

**Credentials as a blocker** (2026-08-18, `test_credential_blocker.py`
19) — `generate.capability()` across the states that matter: nothing
configured, a settings key, an environment key, a key that failed its own
test (not usable, and `failed` set so the copy can differ), an untested key
(usable — never proven to fail), a narrative-only credential leaving the
image role down, and the mock engine (runnable without making the install
*configured*, so Settings still offers its setup form). Then the rows
themselves: one row while both roles are down, none when configured,
per-role consequence and stage, failing-vs-missing copy, the sort position
(screenplay leads, KEY outranks the board-layout gap), and that the KEY row
becomes the next action once the draft is in. `KindsAreFullyWired` scans
`insights.py` for every kind the server can emit and asserts each has a
verb, a badge rule and a support line — a kind with no verb silently reads
"Open". `OneAuthority` pins the consolidation: the client no longer
recomputes whether a key exists, and the settings route no longer rebuilds
the engine block. **The fixtures clear `OPENAI_API_KEY`/`GEMINI_API_KEY`
from the environment** — without that these tests pass or fail depending on
the developer's shell, which on this machine exports both.

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
