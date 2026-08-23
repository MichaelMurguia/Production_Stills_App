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
| `cinematography.py` | The production's cinematography grammar: which of the eight the production defaults to, per-panel override or refusal (`resolve()`, `NONE`), the render block it injects after the camera, and the stamp each take records. Styles themselves come from `style_docs` |
| `composition.py` | Scene composition check — a cinematography supervisor before the spend. Validates suggested camera values against `store.CAMERA_FIELDS` so a proposal cannot name an axis the app does not have |
| `corrections.py` | Correction intake — a rejection becomes structure rather than prose, so the next take is told what was wrong in terms the prompt can carry |
| `looks.py` | Board looks — presentation presets for arranged BOARD sheets. A look is a sheet-level property, never a movie parameter |
| `palette_plate.py` | One palette, one reference image: renders a swatch group to a single plate of pure colour, since engines study these images and text on them would be studied too |
| `revisions.py` | Revision identity — a spec id and its `_R<n>` siblings are one creative unit; resolves board ids, locked revisions and per-panel revision floors |
| `scan.py` | Tell the app anything about a panel: re-reads the screenplay and proposes what that panel should say, as evidence the user accepts item by item |
| `storage.py` | What the install is holding and whether there is room for the next render — one volume per cloud studio, so a full disk is a stated condition rather than a failed write |
| `store.py` | All file-backed records: screenplay (extracts text at import → `_extracted.txt`), references (intake transcodes to JPEG/PNG/WEBP — `RENDER_SAFE_FORMATS`), subjects, specs + locks, `project_name()` |
| `style_docs.py` | The three anchor style libraries, parsed from `docs/CINEMATOGRAPHY_STYLES.md`, `docs/WORLD_TEXTURE_STYLES.md` and `docs/RENDERING_STYLES.md`. One parser, three documents — a document is the source of truth, so editing a style there changes the picker and every future prompt, and there is never a second list in the client. Served by `GET /api/styles/{library}`. Two scripts sit beside it: `scripts/render_style_prompts.py` generates the calibration prompts from the rendering document (so a prompt can never describe a style the app lacks), and `scripts/import_style_plates.py` turns a folder of renders into the picker's three-frame plates, refusing rather than guessing at a filename it cannot map. `wizard.style_depth()` expands a picked style back to its full document entry — every mechanic and its Avoid list — for the Bible drafter, matched on the directive verbatim so an edited answer stays the director's own. Style prompts are never injected into renders: anchors reach a panel through the Bible's own global sections, and a second path would be a second source |
| `insights.py` | Derived truth: `blocking()` (HOLD/GAP/**KEY**/SIZE/CITE + CARE advisories; a row may carry a `stage` hint naming the stage it blocks when `action` does not imply one — the KEY row's action is `settings`, which is no stage), `stage_summary()` (band + gate chain data incl. `scan_done`, `interview_answered`), `stage_rank()`/`frontier_rank()` (pipeline order — blockers sort by the door that resolves them, and the lead never names a stage beyond where the user is), slugline `locations()` map, `screenplay_digest()` (the same parse walked scene by scene — headings, cue lines, snapshots and counted observations — which is what the live read surface is made of, because the model's read is one opaque call), keyword derivation, citation re-check, friendly activity feed |
| `wizard.py` | Scene Scan (schema-forced JSON), re-run merge semantics (confirmed survives by name; new arrives PROPOSED), faction self-check, bible drafting (`_bible_instructions` — DIRECTOR'S ANSWERS ARE BINDING) |
| `autofill.py` | Breakdown research pass: `_screenplay_bytes()` prefers the stored extraction (text/plain, cache-friendly prefix); `_instructions` carries the evidence-class rules; JSON parse + spec normalization |
| `generate.py` | Engines. `PROVIDERS` (gemini / openai / openai-chat / custom); **`engine_credentials()` + `capability()` (2026-08-18) — the single answer to "what does this install hold" and "can this role actually run", read by `/api/settings`, the header dots, `insights.blocking()`'s KEY row and the client's setup-vs-control-panel switch; it replaced four separate copies of that question**; prompt compilation (`render_context` via `bible.py` selective injection; raises when no rendering language — no template fallback); renders, repairs (region composite — outside-mask pixels carried over unchanged), re-render (full-size re-performance), style probes, lessons; `_render_ready()` compose-time transcode backstop; `_wrap_engine_error` classifies content-policy refusals |
| `imaging.py` | Display-tier image derivatives (`VARIANTS`: `thumb`≤512 / `md`≤1600 WebP + `full`): one `variant_path` builder — lazy, mtime-guarded, never upscales, falls back to source. Display-only (never a render/size-gate input). `generate` & `store` resolve candidate/reference tiers through it and warm them at write/intake. See `docs/IMAGE_SERVING.md` |
| `bible.py` | Art Direction Bible parsing: `##` design languages, `### Environments`, atmospheres; `render_context(haystack, languages, lessons, environments)` builds the per-panel prompt block; `sections_catalog()` feeds the sheet scope UI |
| `assemble.py` | Stage 05's judgement: `_variant_rects` (aspect-first default: justified rows, aspect > scale > crop; grid; hero; allocation — packers imported from `sheet.py`, aliased under their old names), `slot_map()` (geometry + verdicts incl. TOO_SMALL — the no-upscale rule made visible; measures against `sheet_render.content_rect`, the single geometry authority), `assemble_board()` (a thin caller since SHEET_SYSTEM: builds an ephemeral `BOARD` sheet and renders it via `render_sheet(allow_letterbox=True)` — same gates, record shape, warnings and endpoint as always) |
| `sheet.py` | The sheet grammar's model (SHEET_SYSTEM_PLAN, rulings R1–R8): `BLOCK_TYPES` (twelve, closed set, elastic flag per R1), `ARCHETYPES` seeds, the shared packers (`grid_rects`/`layout_rects`/`aspect_rects` — one layout implementation for boards and sheets), fractional geometry (block frac in content, slot frac in block; pixels always derived), `LADDERS` + `recommend()` (fixed floors 12 pt/24 px; elastic type renders `max(frac×W, floor)` and never drives the rung), `readiness()` (`TYPE_FLOOR`/`SLOT_PIXELS`, one list — stage-05 `TOO_SMALL` maps across at this boundary only, R5), caption bindings with sha256 staleness (never auto-adopt; rebind/author are the only two acts), idempotent `arrange_board()` (R3 variant→block mapping, cap-aware chunking, hero → `HERO`+`GRID`; R4 derived takes travel as a captioned trailing `STRIP`), `fill_candidates()` (the arrange room's tray), sheet CRUD on `_atomic_write_json`. Lookbook CRUD removed 2026-08-12 with the Lookbook surface rollback |
| `sheet_render.py` | One renderer for preview and export (`render_sheet(sheet, scale, allow_letterbox=False)` — the composer preview is this at a smaller scale, so preview and output cannot drift): `STYLE_INK` (six styles; `INK` is the boards', ground `#131418` per R6), all type from `caption_frac × pixel width`, cover-crop with **no upscaling ever** (sheets raise `RenderShortfall`; only the assemble path letterboxes+flags, R2), slot crop/rotate applied inside a never-rotating frame, gated `export_sheet` (PNG/PDF; `export_lookbook` removed with the 2026-08-12 rollback) |
| `backup.py` | One-zip-per-production backup (never `settings.json`), zip-slip-guarded restore that always creates a NEW production, `days_since_backup` care data |
| `mockflow.py` | The debug dry-run engine (Settings → Debug tools): scan/bible/breakdown text derived deterministically from the screenplay, renders drawn or reused from the library — everything stamped MOCK, no model calls, no cost. Owner-linked: exists only where `SCREENBOARD_DEBUG_TOOLS` is set (the provisioner sets it for OWNER_EMAILS studios); customers never see the tab, endpoints, or provider |
| `connectors.py` | Provider connectors (CONNECTORS_PLAN, 2026-08-03): one credential unlocks a synced catalog of image models. OpenRouter (PKCE one-click; `or:` ids render via chat-completions image path) and fal.ai (`fal:` ids via the async queue; unsupported parameter families listed but not enableable — a stated gate). State in install-level `connectors.json` (gitignored — holds live keys); enabled records join `all_providers()`; injected HTTP for tests |
| `narrative.py` | The narrative role's extra homes (F6 backend, 2026-08-04): Anthropic Messages API on the stored key, OpenRouter chat completions on the connector key — stdlib HTTP, injected for tests. `autofill._draft` dispatches every JSON research pass; `wizard.draft_bible` adds both for markdown. Settings: `narrative_provider`, `anthropic_model` |
| `tutorials.py` | Authored onboarding as content (2026-08-17). Tutorials are JSON documents: packaged in `app/content/tutorials/` (ship with the app, reach the fleet on push) merged over by `SCREENBOARD_HOME/tutorials/` (a studio's own, survives deploys; a `{"deleted": true}` stub hides a packaged one). `content/tutorial_schema.json` is the single declaration of the whole vocabulary — kinds, surfaces, the predicate grammar with the contexts each may be used in, and the **anchor registry** (name → selector), which is why authored content survives a redesign. `validate()` reports every problem at once; `live()` drops anything invalid so broken content is inert, never half-run. Seen-state per install in `HOME/tutorial_state.json` (status/step/rev/version — raising a tutorial's `rev` re-shows it). Authoring is owner-gated (`SCREENBOARD_DEBUG_TOOLS`, same gate as Debug tools); consuming is open, because a customer's studio must run its own FTUE. Reference: `docs/TUTORIALS.md` |
| `activity.py` | Append-only `data/activity_log.jsonl` per production, secrets redacted |
| `validation.py` + `scripts/` | The canon rule engine (stdlib-only): `validate_spec` (structure, budgets, PASS coverage, project presence), `audit_spec`, `compile_prompt` (stable spec hash) — the app imports these rather than reimplementing rules |

### Frontend (`app/static/`)

`index.html` holds the shell, sticky chrome (header 58px + pipeline band,
z 45/44) and one `<template>` per view. `app.js` (~5.5k lines) renders
everything; `styles.css` is the whole design system — **class names are
frozen** (app.js generates markup against them).

Two more scripts since 2026-08-17: `tutorial.js` — the tutorial runtime,
loaded after app.js on every install, which drives the app's own router
and reads its `api`/`showView` globals; and `tutorial-admin.js` — the CMS,
injected lazily the first time Settings → Tutorials is opened, so a
customer's studio never downloads it. The whole coupling between the app
and the tutorial engine is **two dispatched events**: `sb:api` from the
`api()` chokepoint after every successful call, and `sb:view` from
`showView` after every render. That is how a step waits for the user to
actually do the thing it asked for without a hook at fifty call sites.

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
(`renderArrangeRoom`, rebuilt 2026-08-12 from the Reflow Lab prototype:
tiles are the real takes ghosted via md-tier cover backgrounds; linked
edge/corner resize, split-docking, claim arrows, bench/trash/+, grid +
film-ratio snap, live SHORT hatch. The client edits only the
rows→columns→cells STRUCTURE during a gesture and commits it whole via
`PUT /api/sheets/{id}/arrangement`; `sheet.set_arrangement` maps
structure to slot geometry server-side — the stored truth — and
`derive_arrangement` infers a structure for pre-existing BOARD sheets
by guillotine slicing. The Lookbook nav tool, shelf and sheet authoring
were rolled back earlier the same day).

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
Install-level: `HOME/settings.json` (keys), `active_project.json`,
`text_overrides.json` (see below).

**UI text lives in two layers** (2026-08-23). Alt-click rewrites used to
write only `HOME/text_overrides.json` — this install, this volume, gone on
a replacement, invisible to every other studio and to the downloadable app.
They now stack:

| Layer | File | Reach |
| --- | --- | --- |
| Shipped | `app/content/ui_text.json` (in the repo) | rides every deploy — every studio, every downloadable copy |
| Local | `HOME/text_overrides.json` | this install only; wins on conflict so an editor sees their own words |

`POST /api/debug/text-overrides/publish` promotes local into shipped where
the checkout is writable, and on a hosted studio writes nothing and returns
the JSON to commit — it never reports success for an edit that reached one
volume. The GET is deliberately **open** while PUT/DELETE/publish stay
owner-gated: shipped copy is published product text and a customer's studio
must render it whether or not its owner has debug tools. Storefront copy is
a different mechanism entirely (`site_texts` in Postgres, one service, no
deploy needed) — see `docs/WEBAPP_GUIDE.md`.

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

## The rendering anchor is upstream of the Bible

`bible.Rendering Language` is not an independent statement of the medium
— it is a transcription of the **BOARD_RENDERING_STYLE anchor**'s
document entry (`docs/RENDERING_STYLES.md`, via `style_docs`). The bible
is the half that reaches a render: `render_context` carries the section
into every panel prompt and into the Model Test's entire brief.

Until 2026-08-22 the drafter wrote it once and nothing kept it in step.
A production set Photo Real after the Bible was written, ran the Model
Test, and got an oil painting — because the section still said
Production Painting and listed "photographic detail" under Avoid.

`bible.sync_from_anchors()` rebuilds the section from the entry on
either kind of drift: the anchor naming a **different** style, or the same
style whose **document entry has been edited** (the director changes what
Production Painting *is* by editing `RENDERING_STYLES.md`, and that has to
reach the productions using it). Hand edits to that section are therefore
not a supported concept — the place to change what a style means is the
style document, which is the same canon the picker reads. It runs on the interview
save and once per production at boot; it is deterministic and free, so
there is no button and no model call. It fires only on a real
contradiction, so a hand-tuned section that still names the right style
is left alone. `bible.anchor_conflicts()` is the one answer to "do these
two agree?", read by the Bible panel (to state it) and by `sample_probe`
(to refuse before spending).

## The screenplay is stored twice, and only one copy costs money

Every production keeps both:

- `data/screenplay/_extracted.txt` — **the only copy a model ever sees.**
  Every scan, autofill and redraft reads it through
  `store.screenplay_text_cached()`.
- `data/screenplay/<original>` — the raw upload (usually a PDF), served to
  the USER at `/api/screenplay/file` so they can read their own script.
  **Never sent to a model.**

The reason is token cost, and it is not marginal: a PDF bills per page on
every call, the calls repeat across scans, drafts and redrafts, and text
prompt-caches between them while a PDF does not. On the draft this rule
was written against, 131 KB of text against 339 KB of PDF.

`autofill._screenplay_bytes()` is the single model-facing reader. When the
extraction is empty it **refuses and names the fix** rather than falling
back to the original — that fallback existed, and it silently switched
every future call to the expensive format with nothing on screen to say
so. If a new feature needs the screenplay, read the cached text; do not
open `SCREENPLAY_DIR / rec["file"]` outside the user-facing route.

Both copies ride in a backup: a restore that lost the PDF would leave the
user unable to read their own screenplay even though the pipeline still ran.
