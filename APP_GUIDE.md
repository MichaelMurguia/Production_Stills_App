# Screenboard Studio — App Guide

A standalone local app for building canon-locked art direction boards for a
screenplay. The engine is project-agnostic — **The Beltminers** is the proving
project. Everything runs and stays on your machine; the browser is just the screen.

> **Start with [`docs/INTENT.md`](docs/INTENT.md)** (what the product is and
> how it's used, current to 2026-08-02) and
> [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (the technical map).
> [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) is the screen-by-screen
> walkthrough (2026-07-29 vintage — mechanics still accurate, some chrome
> has moved). This file is the operator's reference: setup, milestones,
> engines, and the canon rules.

## The pipeline band — five stages plus five tools

The navigation band IS the pipeline, in work order:

**01 Screenplay** (the root dependency: file, per-location coverage map,
citation health) → **02 Prod. Design** (the visual concept: wizard, Art
Direction Bible, style anchors, lessons) → **03 Breakdowns** (the script
broken into per-board breakdowns) → **04 Panels** (the judging room:
generate takes, review, approve) → **05 Boards** (readiness: the slot map,
Assemble, and the Arrange-this-board door into the composer). Each stage
cell carries a live status subline and a progress-colored top border.

In the header: **Status** (the landing page — DO THIS NEXT, everything
blocking, recent activity) · **Reference** (the one library) ·
**Productions** (the multi-project shelf) · **Settings** (engines and
keys). Board presentation lives in the arrange room, inline on stage 05
(see `docs/USER_GUIDE.md` §9). You are the Production Designer; the app
is your art department.

## New project setup (Prod. Design stage)

For a fresh screenplay, the **Setup** wizard establishes art direction:
1. Upload the screenplay (stage 01).
2. **Style reference images** — three columns, one per style anchor: *Art
   board layout style* (how the finished board is laid out), *Cinematography
   style* (how the film is photographed — upload a spread of stills), and
   *Rendering style* (how panels are painted). Files upload on selection,
   approved with the matching role; each column shows its images with per-image
   delete and a use-in-draft toggle. Subject reference photos (actors,
   vehicles, props) belong on the Research page.
3. **Analyze screenplay** — the research model proposes the project's *design languages* (factions / cultures / technology families); confirm, rename, or drop.
   It also recommends **cast & key subjects** (characters, vehicles, props) as
   tags: click one and it becomes a title card — name, role epithets, and terse
   traits drawn from the script. Upload reference photos into a card (mosaic
   grid) and each becomes an approved reference with the card's role (e.g.
   `CHARACTER_LIKENESS — JOHN STANNER`). Cards live in `data/subjects.json`;
   deleting a card keeps its references.
4. **Interview** — touchstones, medium, palette, never-list. Blanks get model
   proposals marked (PROPOSED).
5. **Draft & review** — the model writes an Art Direction Bible in the app's
   section schema; you edit and save. Nothing is overwritten without you.

The bible is fully data-driven: any `##` section that isn't a system section is
a design language; a `Keywords:` line inside a section (or scene lesson) sets
its auto-match triggers. Specs carry an explicit **Art direction scope**
(checkboxes in the spec editor) choosing which design languages and scene
lessons apply — keyword inference is only the fallback for specs that predate
an explicit selection.

## Start the app

Double-click **`run.bat`** (or run `python -m app` from this folder).
Your browser opens at `http://127.0.0.1:8765`. Close the console window to stop the app.

## Current status

| Milestone | Status |
|---|---|
| M1 — Project skeleton, screenplay import, reference library with roles and approval | ✅ Built |
| M2 — Specification editor backed by the canon validators (+ continuous CANNOT-LOCK gate) | ✅ Built |
| M3 — Panel generation (Gemini / GPT Image 2 / ChatGPT pipeline, selectable per generation) | ✅ Built — needs a Google Gemini and/or OpenAI API key |
| M4 — Automated image audit (Claude vision) | Deliberately skipped — the director is the audit; revisit only as drift comparison |
| M5 — 4K board assembly + typography + derived strips + slot map (no upscaling); layout arranged in the composer since 2026-08-10 | ✅ Built |
| M6 — Revision workflow (Create revision, Unlock & edit with canon guards, journaled) | ✅ Built |
| M7 — Region repair (paint a mask, describe the change, pick the engine — GPT Image 2 true masked edit or Gemini guided edit; result is a new take) | ✅ Built |
| M8 — Activity log + debrief surfaces (`data/activity_log.jsonl` flight recorder; Recent feed, blockers, stage summary in-app; Claude reads the log on request) | ✅ Built |
| 2026-07-29 — Plan v3 UI (five-stage band, judging room, screenplay coverage + citation re-check, canonical design system, in-app dialogs) | ✅ Built |

## The workflow

1. **Status / Screenplay** — Status leads with DO THIS NEXT and the blocking
   list (HOLD/GAP/SIZE/CITE rows with resolving jumps) plus the recent-
   activity feed; the Screenplay stage holds the file, the per-location
   coverage map, and the citation re-check. Upload drafts on stage 01 —
   cited quotes are re-searched on every replace and breaks surface as CITE
   blockers, never as silent edits.
2. **Research** — upload reference images and assign each a *narrow role*
   (e.g. `CHARACTER_LIKENESS — JOHN`, `VEHICLE_GEOMETRY — GT40 REAR`,
   `BOARD_LAYOUT_STYLE` for Master Board #001). A reference controls only what
   its role says it controls. Approve a reference to make it a canon anchor;
   reject it and the file is physically quarantined so it can never be attached
   to a generation again.
3. **Breakdowns** — create a breakdown (Production Generation
   Specification) per board:
   panels (purpose, required/forbidden objects, layout %), forbidden elements,
   and the object-level evidence ledger. **Validate** runs the same
   deterministic canon checks as `scripts/validate_spec.py` and
   `scripts/audit_spec.py`. **Approve & lock** freezes the spec with a content
   hash — locked specs can only be *revised* (a new numbered revision), never
   silently edited. Approvals are appended to `project_state/approval_log.md`.

### Choosing a generation model

Each panel's generate row has a **Model** dropdown:

- **Gemini (Nano Banana Pro)** — the compiled spec prompt goes straight to
  `gemini-3-pro-image`.
- **GPT Image 2 (direct)** — the same compiled prompt goes straight to
  OpenAI's `gpt-image-2`.
- **ChatGPT pipeline** — reproduces how chatgpt.com generates images: GPT-5.6
  first rewrites the compiled spec into flowing render prose (under a
  zero-invention instruction that preserves every required/forbidden item),
  then calls `chatgpt-image-latest` — the same image model ChatGPT uses. The
  rewritten prompt is saved with the candidate (expand "model notes / rewritten
  prompt" on the card) so you can audit exactly what was rendered.

All backends receive the identical compiled prompt, style bible, lessons-learned
list, and approved reference images, and every candidate records which model
produced it — so you can A/B the same locked spec across models. The OpenAI
options need an OpenAI key in Settings. Caveat: OpenAI flags output above
2560×1440 as experimental, so prefer Gemini for 4K renders.

### Render prose as a first-class artifact

**Draft prose** (next to Preview prompt) has GPT-5.6 rewrite the compiled spec
into render prose *without* generating an image. Review and edit the text, then
**Generate from this prose** — the edited text goes to whichever model is
selected, verbatim. The candidate archives both the canonical compiled spec
prompt and your exact edited render prompt (`prompt_source: "edited"`), so every
board is reproducible: same prose + same references + same model = same recipe.

### Deleting specifications

Each row of the Specifications table has a **Delete** button — it permanently
removes the spec, its lock, and every candidate image generated from it, and
journals the deletion in the approval log. Canon guard: a spec with any
APPROVED candidate or assembled board refuses deletion — that output is locked
canon; reject it first if you truly mean to destroy it.

### Deleting rejected candidates

Rejected candidate cards have a **Delete forever** button, and when a board has
any rejected candidates a **Delete all rejected** button appears at the top of
the takes filmstrip in the judging room. Deletion is permanent (image + record removed from disk) and
only allowed for REJECTED candidates — reject first, then delete. Each deletion
is logged to `project_state/rejection_history.md`, and rejection reasons stay in
the lessons-learned list, so the institutional memory outlives the file.

### Board types and the SETTING block

Every spec has a **board type** governing slugline discipline:
- **SCENE** — one screenplay scene. Full slugline (INT/EXT — LOCATION — TIME),
  extracted from the script by auto-fill; one time of day for every panel.
- **LOCATION** — a place across times. INT/EXT + location at board level;
  **time of day chosen per panel** (a select on each panel card).
- **ASSET** — prop / vehicle / character. No slugline; panels get neutral,
  even subject presentation.
- **LIGHTING_STUDY** — derived: use **→ Light study** on any approved panel.
  The panel is promoted to a `LOCATION_GEOMETRY` anchor (scope: geometry and
  composition only, never lighting) and a draft board is created with one
  panel per approved atmosphere from the Bible's Lighting Language. Same
  place, same camera — only the light changes.
- **MASTER** — presentation grammar.

The compiled prompt gains a `SETTING` block (e.g. `INT. CHARLIE'S CABIN —
DUSK`) that explicitly OVERRIDES the hour/hue of any attached style image.
Time-of-day fields offer screenplay times (DAWN…NIGHT) plus the Bible's
approved atmosphere studies.

### Derived panels & harvesting

- **Derive palette** (judging room rail → DERIVED): dominant colors sampled straight
  from the board's approved panels' pixels — a measurement, not a generation;
  zero drift by construction. Lands as a PALETTE candidate for approval.
- **Derive materials**: a generated close-up materials strip whose only allowed
  sources are the board's own approved panels (attached as `MATERIAL_SOURCE`) —
  this cabin's timber, not generic timber. Lands as a MATERIALS candidate.
- **✂ Crop** (any approved candidate or reference): drag-select a region — e.g.
  one cell of the master board — and it becomes a new approved reference with
  its own narrow role. Harvest cells; never attach whole boards as content.

### Style vs reference — two different things

- **Art direction (style)** — HOW it looks. Two halves: *board rendering style*
  (the painting: medium, brushwork, finish) and *cinematography style* (the
  photography: light, palette, atmosphere). Carried by the Art Direction Bible
  (words) and by style images with roles `BOARD_RENDERING_STYLE` /
  `CINEMATOGRAPHY_STYLE` — approved style images attach to **every** generation
  automatically, and their prompt scope says style only, never content.
- **References (subject)** — WHAT things are: an actor's likeness, the GT40's
  geometry, a prop, a location. Attached per panel via checkboxes; each
  controls only its narrow role. `BOARD_LAYOUT_STYLE` (the master board) is
  style-kind but board-assembly grammar, so it stays a manual attachment.

### Where render style comes from

`context/01_ART_DIRECTION_BIBLE.md` is the single authoritative source of
rendering language (editable on the Prod. Design page). The prompt
compiler injects the sections that apply to each panel: Visual Identity,
Rendering Language, Lighting Language, and Character Presentation always;
faction design + material language (Resistance / GRM / Beltminer) when the
panel's content involves that faction (Resistance is the default human world);
and scene-locked lessons (Charlie's Workshop, GT40, …) when the panel matches
their subject — add a new `###` subsection under "Current Locked Scene-Specific
Lessons" and it is matched by its title automatically. Board-presentation and
process sections are reserved for board assembly, not painted panels. The
bible's Drift Prevention Rule is enforced on the prose rewriter, which acts as
the Art Direction Guardian.

## Canon guarantees enforced in code

- Unsupported objects can never pass validation (`unsupported_max` is pinned to 0).
- Approved references have locked role assignments.
- Rejected references are quarantined on disk.
- Approved specs are hash-locked; to edit one, either **Create revision** (keeps
  the approved version as history) or **Unlock & edit** (voids the approval —
  journaled in the approval log — and returns the spec to DRAFT for in-place
  editing; re-approving mints a new hash, and existing candidates keep the hash
  they were generated against).
- **The upstream promise:** nothing upstream of an approval can ever change. A
  spec with APPROVED candidates or boards refuses both unlock and deletion —
  approved canon is immutable together with the exact spec it was approved
  against. To edit anyway, either create a revision, or first reject that
  approved output (an explicit, journaled act of destruction).
- Every approval is timestamped in the approval log.

## Where things live

- `data/references/` — reference library (originals, thumbnails, quarantine)
- `data/screenplay/` — current screenplay
- `data/specs/` — specification JSON files + `locks.json`
- `project_state/` — governance state shared with the original scripts

The `scripts/` validators remain usable from the command line and are the same
code the app calls.
