# Screenboard Studio — Architecture

*Current to 2026-08-02 (release 2026.08.01.33). Companion to
`docs/INTENT.md` (why), `docs/WEBAPP_GUIDE.md` (storefront specifics),
`docs/DEPLOYMENT.md` (infra runbook), `docs/SECURITY.md`.*

## The two apps, one repo

| | `app/` — the product | `storefront/` — the store |
|---|---|---|
| Stack | FastAPI + vanilla-JS SPA (no build step) | FastAPI + SQLAlchemy + Stripe + Jinja |
| Deploys | Never deployed from here; tenants build from repo root; standalone ships as a versioned zip | Railway, root dir `storefront` |
| State | Files under `SCREENBOARD_HOME` | Postgres (SQLite in tests) |
| Docs | this file, `INTENT.md`, `app/static/DESIGN_SYSTEM.md` | `WEBAPP_GUIDE.md`, `STORE_DESIGN_SYSTEM.md` |

Hard boundary: no imports across the two; nothing from `data/` or
`project_state/` is served publicly or packaged into a release zip.

## Product app modules (`app/`)

| Module | Owns |
|---|---|
| `main.py` | Every HTTP route; workspace auth middleware (`SCREENBOARD_ACCESS_TOKEN` gate, `/api/healthz` + login exempt); activity middleware (flight recorder: every mutating call w/ body, outcome, ms); no-cache middleware for UI files; the production-design 423 gate on breakdown creation |
| `paths.py` | The multi-production filesystem: `set_project(slug)` reassigns every mutable path at call time (no `from .paths import X` anywhere); `SWITCH_LOCK` guards every flip-work-restore sequence (the summary sweep) and counter allocation; `HOME` = `SCREENBOARD_HOME` or repo root; `safe_id()` traversal guard for URL-supplied ids |
| `store.py` | All file-backed records: screenplay (extracts text at import → `_extracted.txt`), references (intake transcodes to JPEG/PNG/WEBP — `RENDER_SAFE_FORMATS`), subjects, specs + locks, `project_name()` |
| `insights.py` | Derived truth: `blocking()` (HOLD/GAP/SIZE/CITE + CARE advisories), `stage_summary()` (band + gate chain data incl. `scan_done`, `interview_answered`), slugline `locations()` map, keyword derivation, citation re-check, friendly activity feed |
| `wizard.py` | Scene Scan (schema-forced JSON), re-run merge semantics (confirmed survives by name; new arrives PROPOSED), faction self-check, bible drafting (`_bible_instructions` — DIRECTOR'S ANSWERS ARE BINDING) |
| `autofill.py` | Breakdown research pass: `_screenplay_bytes()` prefers the stored extraction (text/plain, cache-friendly prefix); `_instructions` carries the evidence-class rules; JSON parse + spec normalization |
| `generate.py` | Engines. `PROVIDERS` (gemini / openai / openai-chat / custom); prompt compilation (`render_context` via `bible.py` selective injection; raises when no rendering language — no template fallback); renders, repairs (region composite — outside-mask pixels carried over unchanged), re-render (full-size re-performance), style probes, lessons; `_render_ready()` compose-time transcode backstop; `_wrap_engine_error` classifies content-policy refusals |
| `bible.py` | Art Direction Bible parsing: `##` design languages, `### Environments`, atmospheres; `render_context(haystack, languages, lessons, environments)` builds the per-panel prompt block; `sections_catalog()` feeds the sheet scope UI |
| `assemble.py` | Board math + composition: `_variant_rects` (aspect-first default: justified rows, aspect > scale > crop; grid; hero; allocation), `slot_map()` (same geometry + verdicts, incl. TOO_SMALL — the no-upscale rule made visible), `assemble()` (records `rects` + `panels_used` for the structural view AND draws the 4K composite with `_type_scale` typography) |
| `backup.py` | One-zip-per-production backup (never `settings.json`), zip-slip-guarded restore that always creates a NEW production, `days_since_backup` care data |
| `activity.py` | Append-only `data/activity_log.jsonl` per production, secrets redacted |
| `validation.py` + `scripts/` | The canon rule engine (stdlib-only): `validate_spec` (structure, budgets, PASS coverage, project presence), `audit_spec`, `compile_prompt` (stable spec hash) — the app imports these rather than reimplementing rules |

### Frontend (`app/static/`)

`index.html` holds the shell, sticky chrome (header 58px + pipeline band,
z 45/44) and one `<template>` per view. `app.js` (~5.5k lines) renders
everything; `styles.css` is the whole design system — **class names are
frozen** (app.js generates markup against them).

Key client subsystems: the band (`updateBand` — cursor colors, LOCKED
cells, self-healing lock verification on click), `gateChain()` (one model
feeding the lock popover and the stage checklist; optional steps never
count), the judging room (rail/stage/side), the sheet editor (panels +
evidence ledger + live lock gate mirroring `validate_spec`), the
Productions library (cards with reach bands from `/api/projects/summary`),
persistent UI state (`uiGet/uiSet`, localStorage namespaced per
production), engine gating (`fillProviderSelect` / `providerOptions` —
unconfigured omitted, failed-test keys disabled with reason, applied to
every selector including modals).

### Data layout (per production)

```
<base>/data/
  screenplay/<file> + _extracted.txt     app_state.json (counters, bible_rev)
  interview.json                         wizard_analysis.json
  references/{originals,thumbs,quarantine,references.json}
  subjects.json                          specs/*.json + locks.json
  boards/<SPEC_ID>/CAND-*.{json,png} + BOARD-*.{json,png}
  activity_log.jsonl                     rejection_lessons.json
<base>/context/01_ART_DIRECTION_BIBLE.md
<base>/project_state/ (approval log, rejection history)
```
`<base>` = `HOME` for the legacy root layout, else `HOME/projects/<slug>/`.
Install-level: `HOME/settings.json` (keys), `active_project.json`.

### Key flows

- **Generate a panel**: locked sheet → compile (bible scope + carried
  rejections + references) → engine → candidate JSON+PNG → judged in the
  room → status POST → optional promote to reference (`promoted_ref`
  back-link).
- **Assemble**: slot map verdicts must all read OK → `assemble` records
  `rects`/`panels_used` + draws composite → client lands on the
  structural board; identical takes+variant re-assembly is disabled.
- **Switch production**: `POST /api/projects/activate` → `set_project` →
  full page reload (every view re-reads).

## Storefront + tenant infrastructure (`storefront/`)

- **Entitlement truth** = `purchases` table; `provisioner.reconcile()`
  converges: PAID cloud purchase → Railway service + volume + env + domain
  (idempotent, failures land on `workspace.detail`); CANCELED → revoke.
- **Wildcard router** (`tenant_proxy.py`, wraps the FastAPI app as ASGI):
  `*.screenboardstudio.com` → look up ACTIVE+PAID workspace by subdomain →
  stream-proxy to its `*.up.railway.app` (only ever that suffix — loop/
  SSRF guard). Unclaimed hosts → selling 404; unreachable tenant → trust
  503 with honest status + retry. Claim/rename is live on row commit.
- **Doors**: buttons use `railway_url` until a healthz probe flips
  `domain_live`; renames reset it.
- **Fleet**: `/admin/tenants/update` rebuilds every ACTIVE tenant at the
  storefront's own commit (deploys drain: overlap 60s / draining 300s so
  renders survive); UI files ship `no-cache` so browsers can't hold old
  builds. Releases: CalVer `VERSION`, immutable zips, CI enforces
  freshness + probes the live site and the router 404 post-deploy.

## Extension points

- **New engine**: Settings → custom engines (OpenAI-compatible base URL);
  `PROVIDERS` + aspect contracts in `generate.py`.
- **New pipeline stage**: nav band markup + `STAGE_ORDER` + `gateChain` +
  `stage_summary` + DESIGN_SYSTEM entry (band numbering is documented).
- **New reference role**: `store.SUGGESTED_ROLES` (+ jurisdiction copy);
  style vs subject kind decides auto-attach.
