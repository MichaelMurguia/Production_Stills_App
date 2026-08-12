# Screenboard Studio — Architecture

*Current to 2026-08-10 (sheet grammar + camera revision on top of release
2026.08.05.20). Companion to `docs/INTENT.md` (why),
`docs/WEBAPP_GUIDE.md` (storefront specifics), `docs/DEPLOYMENT.md`
(infra runbook), `docs/SECURITY.md`.*

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
| `imaging.py` | Display-tier image derivatives (`VARIANTS`: `thumb`≤512 / `md`≤1600 WebP + `full`): one `variant_path` builder — lazy, mtime-guarded, never upscales, falls back to source. Display-only (never a render/size-gate input). `generate` & `store` resolve candidate/reference tiers through it and warm them at write/intake. See `docs/IMAGE_SERVING.md` |
| `bible.py` | Art Direction Bible parsing: `##` design languages, `### Environments`, atmospheres; `render_context(haystack, languages, lessons, environments)` builds the per-panel prompt block; `sections_catalog()` feeds the sheet scope UI |
| `assemble.py` | Stage 05's judgement: `_variant_rects` (aspect-first default: justified rows, aspect > scale > crop; grid; hero; allocation — packers imported from `sheet.py`, aliased under their old names), `slot_map()` (geometry + verdicts incl. TOO_SMALL — the no-upscale rule made visible; measures against `sheet_render.content_rect`, the single geometry authority), `assemble_board()` (a thin caller since SHEET_SYSTEM: builds an ephemeral `BOARD` sheet and renders it via `render_sheet(allow_letterbox=True)` — same gates, record shape, warnings and endpoint as always) |
| `sheet.py` | The sheet grammar's model (SHEET_SYSTEM_PLAN, rulings R1–R8): `BLOCK_TYPES` (twelve, closed set, elastic flag per R1), `ARCHETYPES` seeds, the shared packers (`grid_rects`/`layout_rects`/`aspect_rects` — one layout implementation for boards and sheets), fractional geometry (block frac in content, slot frac in block; pixels always derived), `LADDERS` + `recommend()` (fixed floors 12 pt/24 px; elastic type renders `max(frac×W, floor)` and never drives the rung), `readiness()` (`TYPE_FLOOR`/`SLOT_PIXELS`, one list — stage-05 `TOO_SMALL` maps across at this boundary only, R5), caption bindings with sha256 staleness (never auto-adopt; rebind/author are the only two acts), idempotent `arrange_board()` (R3 variant→block mapping, cap-aware chunking, hero → `HERO`+`GRID`; R4 derived takes travel as a captioned trailing `STRIP`), `fill_candidates()` (the arrange room's tray), sheet CRUD on `_atomic_write_json`. Lookbook CRUD removed 2026-08-12 with the Lookbook surface rollback |
| `sheet_render.py` | One renderer for preview and export (`render_sheet(sheet, scale, allow_letterbox=False)` — the composer preview is this at a smaller scale, so preview and output cannot drift): `STYLE_INK` (six styles; `INK` is the boards', ground `#131418` per R6), all type from `caption_frac × pixel width`, cover-crop with **no upscaling ever** (sheets raise `RenderShortfall`; only the assemble path letterboxes+flags, R2), slot crop/rotate applied inside a never-rotating frame, gated `export_sheet` (PNG/PDF; `export_lookbook` removed with the 2026-08-12 rollback) |
| `backup.py` | One-zip-per-production backup (never `settings.json`), zip-slip-guarded restore that always creates a NEW production, `days_since_backup` care data |
| `mockflow.py` | The debug dry-run engine (Settings → Debug tools): scan/bible/breakdown text derived deterministically from the screenplay, renders drawn or reused from the library — everything stamped MOCK, no model calls, no cost. Owner-linked: exists only where `SCREENBOARD_DEBUG_TOOLS` is set (the provisioner sets it for OWNER_EMAILS studios); customers never see the tab, endpoints, or provider |
| `connectors.py` | Provider connectors (CONNECTORS_PLAN, 2026-08-03): one credential unlocks a synced catalog of image models. OpenRouter (PKCE one-click; `or:` ids render via chat-completions image path) and fal.ai (`fal:` ids via the async queue; unsupported parameter families listed but not enableable — a stated gate). State in install-level `connectors.json` (gitignored — holds live keys); enabled records join `all_providers()`; injected HTTP for tests |
| `narrative.py` | The narrative role's extra homes (F6 backend, 2026-08-04): Anthropic Messages API on the stored key, OpenRouter chat completions on the connector key — stdlib HTTP, injected for tests. `autofill._draft` dispatches every JSON research pass; `wizard.draft_bible` adds both for markdown. Settings: `narrative_provider`, `anthropic_model` |
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
count), the judging room (rail/stage/side), the breakdown editor (panels +
evidence ledger + live lock gate mirroring `validate_spec`), the
Productions library (cards with reach bands from `/api/projects/summary`),
persistent UI state (`uiGet/uiSet`, localStorage namespaced per
production), engine gating (`fillProviderSelect` / `providerOptions` —
unconfigured omitted, failed-test keys disabled with reason, applied to
every selector including modals), the deep-link router (2026-08-12:
`VIEW_PATH`/`PATH_VIEW` translate stage paths — `/breakdowns/<spec>`,
`/panels/<spec>[/<panel>]`, `/boards/<spec>[/arrange|/<board-id>]` — to
internal views; `applyRoute` seeds the persisted selection state,
`syncUrl` keeps the address honest on every selection change, popstate
walks history; the server boots the stamped SPA for any non-API path and
the auth gate carries `?next=` through /login), and the arrange room
(`renderArrangeRoom` — the composer scoped to a spec's BOARD sheet,
rendered inline on stage 05 by `Arrange this board`; server-rendered
preview via `POST /api/sheets/{id}/render` fetched as a blob · rail of
slot verbs; DOM overlays for selection/drag consume the renderer's
X-Sheet-Geometry manifest and never print; the fill popover verdicts
takes against `slotNeedFromRect` client-side. The Lookbook nav tool,
shelf and sheet authoring were rolled back 2026-08-12).

### Data layout (per production)

```
<base>/data/
  screenplay/<file> + _extracted.txt     app_state.json (counters, bible_rev)
  interview.json                         wizard_analysis.json
  references/{originals,thumbs/<REF>.{thumb,md}.webp,quarantine,references.json}
  subjects.json                          specs/*.json + locks.json
  camera_defaults.json (bible-level camera grammar)
  boards/<SPEC_ID>/CAND-*.{json,png,thumb.webp,md.webp} + BOARD-*.{same}
  sheets/SH-*.json + sheets/<SH>/export/ (sheet grammar; rev-stamped)
  lookbooks/LB-*.json + lookbooks/<LB>/<LB>.pdf
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
- **Camera & composition**: four structured per-panel axes — `camera_angle`,
  `camera_lens` (a focal length; presets + custom), `camera_tilt`, `scale` —
  each resolved `panel value → the production default → unset`. The default
  (`store.camera_defaults`, `data/camera_defaults.json`) is baseline-merged
  (`CAMERA_BASELINE` = Eye level · 24mm · Level · Wide) and edited on the Camera
  grammar bar at the top of the Look Interview. `generate._camera_block` expands
  each axis into an authored CAMERA directive placed right after PANEL PURPOSE
  and stated to override the references' framing (it replaced the terse
  `SCALE:`/`COMPOSITION ROLE:` tail). Per-panel edits between takes go through
  `store.amend_panel_camera` (same lock-restamp/journal/frozen contract as
  `amend_panel_purpose`). Full reference: `docs/CAMERA_AND_COMPOSITION.md`.
- **Add a panel post-lock**: the panels workbench appends a panel to a locked
  breakdown (`store.add_panel`) — append-only, so nothing upstream of an
  approval changes; it lands as a 0%-allocation work order, the lock
  re-stamps and the add is journaled (same contract as `amend_panel_purpose`).
- **Assemble**: slot map verdicts must all read OK → `assemble_board`
  builds the ephemeral BOARD sheet, renders it through `render_sheet`
  (letterbox+flag allowed on this path only), records `rects`/
  `panels_used` → client lands on the structural board; identical-takes
  re-assembly is disabled.
- **Arrange / compose** (SHEET_SYSTEM, 2026-08-10): stage 05's
  `POST /api/specs/{id}/arrange` idempotently mints the scene's `BOARD`
  sheet from its slot map (variant read from the latest board record) →
  the composer edits it through the sheet API — `/api/sheets` CRUD,
  `/style`, `/size` (rungs or `"recommended"`), `/blocks`,
  `/blocks/{b}/slots/{s}` (fill/frac/crop), `/blocks/{b}/caption` +
  `/caption/resolve` (`rebind`|`author`), `/readiness`, `/render`
  (preview PNG at a scale), `/export`; lookbooks under `/api/lookbooks`
  (`/candidates` declared before `/{lb}` — route-capture order). Every
  mutation saves and bumps `rev`; a RECOMMENDED size silently follows
  block changes (that is what recommended means).
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

- **New image engine**: three routes — a connector (`connectors.py` REGISTRY + adapter), a custom OpenAI-Images endpoint (Settings → your own endpoints), or a built-in in `generate.PROVIDERS` + aspect contracts.
- **New narrative home**: `narrative.py` backend + `autofill.narrative_choices()` + the role select and `fillNarrativeSelect` in `app.js`.
- **New pipeline stage**: nav band markup + `STAGE_ORDER` + `gateChain` +
  `stage_summary` + DESIGN_SYSTEM entry (band numbering is documented).
- **New reference role**: `store.SUGGESTED_ROLES` (+ jurisdiction copy);
  style vs subject kind decides auto-attach.
- **New image display site**: request the tier the slot needs —
  `?size=thumb` (≤256px), `?size=md` (mid pane), or full (zoom/pixel edit).
  See `docs/IMAGE_SERVING.md`.
