# Feature inventory — for Claude Design review

*Coding agent, 2026-07-29 (post plan-v3 C1–C15 + first live-use findings).
Every feature the app ships, per surface, with its design status. Narrative
documentation lives in `docs/USER_GUIDE.md`; the UI contract in
`app/static/DESIGN_SYSTEM.md`. Review targets are flagged **⚑**.*

## Chrome (every screen)

| Feature | Behavior | Status |
|---|---|---|
| Brand + project name | From `/api/state.project` | canonical |
| Engine dots | Credentials only: green saved / blue env / hollow none; two dots (two keys) | canonical |
| Tools nav | Status · Research · Settings; active underlined | canonical |
| Pipeline band | 5 stages, live sublines from `stage_summary`, top border --ok/--accent/--bad/--line, HERE chip on viewed stage; amber = viewed stage else work frontier (exactly one) | canonical |
| Scrollbars | Global thin/square/track-invisible per amendment (applied 2026-07-29, amendment files deleted) | canonical |
| Toasts | Bottom notifications; error variant red-edged | canonical |
| App dialogs | `modal()` family: confirm, single-field, multi-field; danger confirms red; Esc/scrim-click cancel | canonical |
| Prompt reading view | **⚑ new** `promptOverlay()` — 900px dialog with scrollable Courier `<pre>`, Copy + Close (user finding #6) | uncanonized |
| Deep links | `#status #screenplay #wizard #specs #boards #assembly #references #settings` | n/a (no UI) |

## Status (landing)

| Feature | Behavior |
|---|---|
| DO THIS NEXT lead | blocking[0] promoted; verb headline, one support sentence, primary jump |
| Blocking rows | HOLD / GAP / SIZE / CITE badges, text with Courier IDs, amber text-action jump |
| Counts cards | approved/provisional refs, approved/draft sheets |
| Recent feed | `/api/activity` — friendly phrasing, timestamp rhythm, IDs in Courier |
| Prohibited inventions | chips from rejection history |

## 01 Screenplay

| Feature | Behavior |
|---|---|
| Coverage table | Deterministic slugline parse; scenes count; canonical 4-segment meter (amber first segment = thin); sheet cell: LOCKED/DRAFT chip + Open sheet / amber held-rows count / Draft a sheet (seeds the breakdown form) |
| File card | CURRENT chip, Courier filename, SIZE / SHA256(8) / UPLOADED / READ facts |
| Downstream counts | design languages, sheets, cited evidence rows, approved panels |
| Broken citations panel | CITE rows with quote excerpt + Review jump; report-only |
| Replace | Upload PDF/FDX/Fountain/TXT; citations re-searched on every upload; toast states result |

## 02 Prod. Design (wizard)

| Feature | Behavior |
|---|---|
| Step-state badges | per-step h2: anchors set, languages found, cards+photos, SAVED · REV n, samples |
| Step 1 anchors | 3 role columns, per-image delete + use-in-draft, jurisdiction copy |
| Step 2 analysis | provider pick, run, lock/unlock, design-language chips (edit/delete via dialog) |
| Step 3 subjects | recommended tags → title cards, photo mosaics, role-stamped uploads |
| Step 4 interview | touchstones/medium/palette/never/notes |
| Step 5 bible | draft → edit → save (confirm dialog); REV badge increments |
| Step 6 bake-off | same brief per engine, Make default |
| Documents | Bible editor (REV badge), Lessons list (add/remove) |

## 03 Breakdowns

| Feature | Behavior |
|---|---|
| Script breakdown form | subject prompt + mode + provider → auto-fill with cited ledger; WIP persists; location hint pre-fill |
| Blank sheet form | manual creation |
| Sheet table | ID, subject, mode, panels, status badges, Open / Delete (guarded, dialog) |
| Editor sections | Identity / Setting (conditional slugline fields) / Direction |
| CANNOT-LOCK gate | continuous, server-rule-exact, one line per condition, Jump to first ↓, Approve & lock disabled while gated |
| Panels | purpose, required chips (green = has reference; auto PASS ledger row), forbidden, per-panel light select, allocation % |
| Ledger | ID/Object/Source/Cited evidence/State; HOLD blue edge, REMOVE red, non-PASS tinted; editable, disabled when locked |
| Scope checkboxes | design languages + scene lessons; inference note |
| Validate / Approve & lock / Create revision / Unlock & edit | all dialog-confirmed; canon guards |

## 04 Panels — judging room

| Feature | Behavior |
|---|---|
| Left rail | SHEET block; panel list with thumbs + readiness (green dot / amber count / red SIZE / —); DERIVED entry; assembly pointer |
| Stage strip | pid chip, question, alloc % · role · aspect |
| Staged render | newest or clicked take, on --field, lightbox on click |
| Primary actions | Reject (reason dialog) · → Reference (disabled till approved; one 3-field dialog) · Approve panel (only amber) |
| Ghost actions | Repair region · Crop → reference (approved only) · → Light study (approved only) · Delete forever (rejected only) |
| Takes filmstrip | all takes; rejected dimmed image-only + reason tooltip; SHOWN outline; purge button |
| Generation bench | model (dynamic: built-ins + custom engines) / size / aspect; Preview prompt; Draft prose → edit → generate verbatim; Generate (not amber); attach counter n SUBJECT + m STYLE = t OF 14 |
| Reference groups | pre-checked on required-object match; style anchors auto-attach badges |
| Provenance rail | THIS RENDER facts; ANCHORED TO thumbs; COMPILED PROMPT — **⚑ Copy / Expand (reading view) / Full-Less** (finding #6); CARRIED REJECTIONS |
| Repair overlay | paint mask + brush, instruction, engine choice (GPT Image 2 true mask / Gemini guided); **⚑ Esc closes; during render the Cancel becomes "Close — render continues"** (finding #2) |
| Derived | palette (measured) + materials (generated, model pick incl. custom engines) |

## 05 Boards — assembly

| Feature | Behavior |
|---|---|
| Header | NOT ASSEMBLED / n BOARDS + live canvas chip; Assemble gated until every slot OK |
| Variant chips | DEFAULT / GRID / HERO Pxx — live slot-map redraw; presentation-only, recorded on board |
| Slot map | exact geometry, ID top-left, verdict bottom-right, TOO SMALL red, APP-DRAWN title block |
| Canvas select | 4K UHD / DCI wide / print-leaning; re-maps live |
| Board gallery | board candidates: approve / reject / promote / delete via standard card |

## Research

| Feature | Behavior |
|---|---|
| **⚑ Compact add row** (finding #3) | one-line intake at top: file · role (datalist) · controls · not · notes · + Add; explanations in tooltips | uncanonized |
| Filter chips | ALL / STYLE / SUBJECT / SCENE with counts; status counts right |
| Cards | badge + REF-id, role, jurisdiction block (CONTROLS green / NOT red), notes, AUTO-ATTACHED / USED IN n / quarantine facts |
| Actions | Approve · Crop · Reject (reason dialog) · Reinstate · Delete (dialog) |

## Settings

| Feature | Behavior |
|---|---|
| Engine cards | Gemini + OpenAI: status chip (CONNECTED only after user's Test), key save/test, POWERS, notes, LAST TEST |
| Pipeline card | USES OPENAI KEY; description; **size cap: its image tool accepts only preset sizes (≈1.5K max)** — bug #5 fixed by mapping to nearest preset |
| **⚑ Your engines** (finding #4) | bring-your-own image API (OpenAI Images contract: base URL + model + key); add via 4-field dialog; rows show model · URL · key hint · LAST TEST + Test/Remove; joins every Model dropdown and the default-engine chips; key stored in settings.json, redacted in the flight recorder | uncanonized |
| Default engine chips | built-ins + customs; saved on click |
| Facts row | data/ · approval log · leaves-machine |
| Workflow & FAQ | rewritten for the five-stage IA |

## Findings actioned 2026-07-29 (this pass)

1. **Scrollbars** — amendment applied verbatim, files deleted per instructions.
2. **Repair exit** — Esc + explicit "Close — render continues" during generation; the take still lands in the strip.
3. **Add reference** — compact top row (⚑ pattern for review).
4. **Custom engines** — full BYO-API feature (⚑ pattern for review).
5. **Pipeline 400** — the Responses image tool accepts only 1024×1024 / 1024×1536 / 1536×1024 / auto; now mapped by orientation; Model tooltip states the ~1.5K cap. Design question ⚑: should the Size select visibly state the cap when PIPELINE is selected?
6. **Prompt access** — Copy / Expand (detached reading view) / Full on the provenance rail (⚑ pattern for review).

## Open design questions

- ⚑ Canonize or refine: compact intake row, custom-engine rows, prompt
  reading view (all marked UNCANONIZED in styles.css and logged in the
  design-system table).
- ⚑ Pipeline size cap surfaced only in a tooltip — worth a visible note on
  the Size select when the pipeline is chosen?
- ⚑ Custom engines currently excluded from the repair dialog (mask support
  varies across OpenAI-compatible servers) — acceptable, or should capable
  engines opt in?
- The 2a wizard left-rail spine remains Phase 2 (per plan v3 C13).
