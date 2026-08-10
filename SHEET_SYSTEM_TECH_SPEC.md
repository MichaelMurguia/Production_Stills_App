# SHEET_SYSTEM_TECH_SPEC.md — implementation design for SHEET_SYSTEM_PLAN.md

**By the coding agent, 2026-08-09; rulings folded in 2026-08-10.** The build
is greenfield (user-confirmed): sheets, lookbooks and the composer do not
exist yet; stage-05 boards do. Claude Design ruled on R1–R8 (Art_Board_Ruling
bundle → revised `SHEET_SYSTEM_PLAN.md` §0, now at repo root): R2/R3/R4/R5/R8
accepted, R1/R6/R7 overruled with better mechanisms. **This spec is final and
implementation-ready** — §1 records each resolution as ruled; the revised plan
is the design authority where they differ.

---

## 1. Resolutions to the design spec's open points

### R1 — Type floor: RULED — elastic vs fixed, floors 12 pt / 24 px fixed.

Diagnosis accepted, both of my fixes overruled. Nothing is exempt from
legibility; the real distinction is **fixed rect vs own column**:

- **Fixed** type (captions under images — all slot-bearing blocks) cannot
  grow without colliding: size is `caption_frac × width`, and it **drives**
  `recommend()`.
- **Elastic** type (`PALETTE`, `SPEC`, `PRINCIPLES` — owns its column,
  reflows) renders at `max(frac × width, floor)`: it grows to the floor,
  takes the vertical room, never sets under the floor, never drives the
  recommendation.
- Floors are **fixed per medium**: PRINT 12 pt, SCREEN **24 px** (unchanged —
  the floor is not lowered to widen a test spread). Consequence accepted by
  the ruling: on screen CLUSTER and BEATS both land 3840; the three-rungs
  story is print's (12×8 / 18×12 / 36×24). Worked-outcomes table in the
  revised plan §6 is the test oracle.

One test nit, resolved here as a tech call: the 18×12 print case ("14 px-
floored stack", worst fixed frac 0.01029) is not constructible from the
twelve canon types — every real stack lands 12×8 (HERO), 24×16 (CLUSTER /
MATERIAL / VERSUS) or 36×24 (the rest). The test exercises the ladder
mechanism by injecting a test-only block-type entry with frac 0.01029
(monkeypatched `BLOCK_TYPES`, never shipped); the canon set stays closed at
twelve.

### R2 — Letterboxing: one renderer, explicit flag. RULED — accepted as written.

`render_sheet(sheet, scale, *, allow_letterbox=False)`. Sheet preview/export
paths use the default and **raise** `SheetError` on a shortfall (export is
gated first, so reaching it is a bug — per plan §10). `assemble_board` calls
with `allow_letterbox=True`, preserving its shipped contract exactly:
letterbox + warning + regeneration flag on `TOO_SMALL` ([app/assemble.py]
~407–425), same `AssemblyError` cases, same endpoint. No behaviour change to
stage 05.

### R3 — Existing-variant mapping for `/arrange`. RULED — accepted verbatim.

Actual variants are `aspect` (default), `allocation`, `grid`, `hero:<panel>`
(`assemble.check_variant`). `/arrange` maps the spec's current variant to the
BOARD sheet's layout block:

| board variant | block sequence |
|---|---|
| `aspect` | `GRID` (aspect-first mode, packs via `aspect_rects`) |
| `allocation` | `CLUSTER` (packs via `layout_rects`) |
| `grid` | `GRID` (packs via `grid_rects`) |
| `hero:<p>` | `HERO` holding `<p>` **+** `GRID` (aspect-first) holding the rest |

The `BOARD` archetype now reads "optional `HERO` + one layout block +
optional `PALETTE`, `MATERIAL` + canon footer" (revised plan §3). The
replaces-column is corrected too: `CLUSTER` replaces `allocation`, `GRID`
replaces `grid` **and** `aspect`.

### R4 — Derived strip migration. RULED — accepted, plus the swap note.

Today's boards render approved `MATERIALS` / `PALETTE` **panel renders** into
a bottom strip. The plan's `PALETTE` block has 0 slots (app-drawn from a
stage-02 group) and `MATERIAL` binds references — neither can hold a render.
`/arrange` places existing MATERIALS/PALETTE takes into a `STRIP` block
appended last, captioned from the panel titles. **Ruled addition:** the
composer names the swap on that strip — one Courier line, `RENDERED AS PANELS
· THE PALETTE BLOCK CAN DRAW THESE FROM STAGE 02`, with the block swap as its
action. Nothing dropped, nothing left for the user to diagnose.

### R5 — Readiness vocabularies split by surface. RULED — accepted.

The plan says both "one failure vocabulary" and "keep the API field names it
already returns". Resolution: **stage-05's `slot_map` shape does not change**
(`not_ready: [{panel_id, status}]`, statuses `TOO_SMALL` etc. — its tests and
UI stay untouched). The **sheet** surface uses the plan's §7 shape verbatim
(`blocked: [{kind: TYPE_FLOOR|SLOT_PIXELS, ...}]`). `TOO_SMALL` maps to
`SLOT_PIXELS` at the sheet boundary only. One vocabulary *per surface*, which
is what §13's canon line actually says.

### R6 — Stage-05 board default style. RULED — `INK`, not `CONTACT`.

Today's boards draw each panel on `PANEL_BG` with a label beneath — that is
**matted**, which is `INK`; `CONTACT` is flush and would change every
existing board's layout. `INK` is the default for `/arrange`-created and
legacy-assembled boards. Its ground moves from the board's warm charcoal
`#2a2723` to `#131418`, deliberately — the style is not forked to preserve
the old tone (canon 8).

### R7 — Word collision: "sheet". RULED — stage 03's artifact is a *breakdown*.

Copy discipline overruled; the word is renamed at the source. All UI copy
saying "breakdown sheet" becomes "breakdown" (~16 strings across `app.js`,
`index.html`, `DESIGN_SYSTEM.md`; the nav already says Breakdowns). CSS class
names (`.sheet-count` etc.) are **not** renamed — CLAUDE.md forbids it; the
rename is copy and prose only. Ships in Phase 3 with the Lookbook surface,
so "sheet" acquires its one meaning in the same release that introduces it.

### R8 — Mock numbering. RULED — accepted; the ruling bundle already dropped
the retired take-bar plan and its colliding 17a mock. The 15 `lb-*` / `ba-*`
mocks are installed in `design_mocks/`.

---

## 2. Storage and data model

- `paths.SHEETS_DIR = DATA / "sheets"`, `paths.LOOKBOOKS_DIR = DATA /
  "lookbooks"` — added to the `_project_base` globals block and
  `ensure_dirs()`, exactly like `BOARDS_DIR`.
- One JSON per record, written with `store._atomic_write_json`:
  `data/sheets/SH-0001.json`, exports under `data/sheets/SH-0001/export/`;
  `data/lookbooks/LB-0001.json`. IDs via `store.next_counter("sheet", "SH")` /
  `("lookbook", "LB")`.
- Sheet record: as the plan's §1 schema, plus two fields:
  - `rev` (int, bumped on every save) — drives preview cache-busting and lets
    tests assert save-on-every-edit;
  - `created_at` / `updated_at` ISO stamps (matching board records).
- Invariants enforced at save: `style` ∈ the six; `archetype` ∈ the seven;
  block `type` ∈ the twelve; slot count within the type's range; every `frac`
  and `crop` component in [0, 1] (`rotate` in degrees, any float); captions
  carry `binding`+`bound_hash` or `state: "AUTHORED"`; `size_source` ∈
  {`RECOMMENDED`, `CHOSEN`}. Violations raise `SheetError` → HTTP 422.
- A lookbook is `{lookbook_id, title, sheets: [sheet_id...], created_at}`.
  Deleting a sheet removes its id from every lookbook (single-user app; done
  inline, not by GC).

## 3. `app/sheet.py` — model, geometry, recommendation, bindings

Constants (canon tables, single source of truth):

```python
BLOCK_TYPES = {  # type: (slots_min, slots_max, caption_frac, elastic)
    "HERO": (1, 1, 0.01471, False), "CLUSTER": (2, 5, 0.00882, False),
    "STRIP": (3, 8, 0.00625, False), "BEATS": (6, 15, 0.00662, False),
    "GRID": (4, 12, 0.00662, False), "ORTHO": (4, 4, 0.00588, False),
    "PALETTE": (0, 0, 0.00699, True), "MATERIAL": (3, 6, 0.00699, False),
    "SPEC": (0, 0, 0.00699, True), "PRINCIPLES": (0, 0, 0.00809, True),
    "LINEUP": (4, 10, 0.00625, False), "VERSUS": (2, 2, 0.00772, False),
}
ARCHETYPES = {...}            # revised plan §3 (BOARD: optional HERO + layout)
STYLES = ("GALLERY", "CONTACT", "NEWSPRINT", "BLUEPRINT", "PLATE", "INK")
LADDERS = {                   # R1 ruling: floors fixed, never width-scaled
    "PRINT":  {"ratio": (3, 2), "rungs": [(12, 8), (18, 12), (24, 16), (36, 24)],
               "unit": "in", "floor": 12.0},   # points, fixed
    "SCREEN": {"ratio": (16, 9), "rungs": [(1920, 1080), (2560, 1440),
               (3840, 2160), (5120, 2880)], "unit": "px", "floor": 24.0},
}
```

Public functions (all raise `KeyError` for missing ids, `SheetError` for
invalid operations):

- CRUD: `create_sheet(archetype, style, medium, spec_id=None)` (seeds the
  archetype's block sequence, size `RECOMMENDED`), `get_sheet`, `save_sheet`,
  `delete_sheet`, `list_sheets`. `get_sheet` runs the staleness sweep: for
  every `BOUND` caption, re-resolve, compare sha256 to `bound_hash`, mark
  `STALE` in the returned dict (never persisted by the sweep itself).
- Blocks/slots: `add_block(sid, type, index)`, `remove_block(sid, bid)`,
  `set_slot(sid, bid, slot_id, patch)` (spec/candidate/frac/crop/annotation),
  `set_caption(sid, bid, text=None, binding=None)`,
  `resolve_caption(sid, bid, action)` where action ∈ {`rebind`, `author`} —
  rebind re-resolves and stamps a new hash; author freezes current text as
  `AUTHORED`. Neither ever writes to the source (plan §8; test-enforced).
- Geometry: `layout_rects`, `grid_rects`, `aspect_rects` **move here from
  `assemble.py` verbatim** (names lose the underscore; `assemble` imports
  them). `block_rects(sheet, block, px_w, px_h)` dispatches per type;
  slot fracs are authoritative for slot-bearing blocks, packers only seed
  initial fracs at block creation / `arrange` time. Prose blocks compute their
  own text layout at render.
- Sizing: `type_size(frac, medium, width)` (`frac*width*72` print /
  `frac*width` screen); `rendered_size(block, medium, width)` — elastic type
  is `max(type_size, floor)`, fixed type is `type_size` (R1);
  `slot_pixel_need(sheet, slot)` (print: `frac_w × width_in × 300`; screen:
  `frac_w × width_px`); `recommend(sheet)` — smallest rung where every
  **fixed** block's type clears the floor and no slot's candidate is short,
  per the revised plan §6 pseudocode verbatim; falls back to the top rung.
  All-elastic and empty sheets recommend the bottom rung.
- Readiness: `readiness(sheet)` → §7 shape (R5). `TYPE_FLOOR` entries carry
  `block_id`, computed size and floor; `SLOT_PIXELS` carry `slot_id`, `have`
  (candidate w×h from `generate.list_candidates`) and `need`
  (`slot_pixel_need` for both axes). `ready` is false while either exists.
- Bindings: `resolve_binding(binding) -> str`, dispatch per kind:

  | kind | resolver |
  |---|---|
  | `SUBJECT` | `store.get_subject(id)` |
  | `PANEL` | `store.get_spec` → panel title/purpose |
  | `PALETTE_GROUP` | wizard swatch groups (`wizard.swatches_in_play`), name + swatches **in stored order** |
  | `MATERIAL_ANCHOR` | `store.list_references()` filtered by role |
  | `SCREENPLAY` | `store.screenplay_text_cached()` slice |
  | `JUDGING_NOTE` | `generate.list_candidates(spec_id)` → note on the candidate |
  | `SPEC_FIELD` | `store.get_spec(id)[field]` |

- `arrange_board(spec_id)` — idempotent (`spec_id` → at most one `BOARD`
  sheet, found by scan, created from `assemble.slot_map`'s fractional
  geometry per R3/R4, style per R6). Readiness travels: slots copy the slot
  map's candidate ids; the composer recomputes nothing about approval.
- Lookbooks: `create_lookbook(title)`, `get_lookbook`, `list_lookbooks`,
  `delete_lookbook`, `lookbook_add_sheet(lb, sheet_id_or_spec)`,
  `lookbook_reorder(lb, order)` (order must be a permutation → else 422).

## 4. `app/sheet_render.py` — one renderer for preview and export

- `render_sheet(sheet, scale=1.0, *, allow_letterbox=False) -> PIL.Image`.
  Pixel size = sheet size × scale (print sizes convert at 300 dpi). All type
  = `caption_frac × pixel_width` — no constants. Images cover-crop via the
  same math as `assemble_board` (the code moves into a shared
  `_cover_crop(im, rect, crop)` here); shortfall raises `SheetError` unless
  `allow_letterbox` (R2). Slot `crop` applies before cover (crop rect in
  source-image fractions, then rotation about the crop centre; the frame
  never rotates — plan §5).
- `STYLE_INK[style]` = paper/inset/edge/voice table from §4. Voices resolve
  from **system fonts with fallback chains** (serif → Georgia/Times; mono →
  Consolas/Courier; slab/condensed → Bahnschrift condensed; sans → existing
  `FONT_CANDIDATES`). No fonts are bundled; a missing voice falls back down
  its chain and finally to `assemble._font`'s default. Sheet ink values live
  here (and mirrored in CSS under `.sheet[data-style]` for the DOM shell),
  never in `:root` — `tests/test_design_tokens.py` gains that assertion.
- Block renderers: one function per type; prose blocks (`PALETTE`, `SPEC`,
  `PRINCIPLES`) draw from resolved bindings (`PALETTE` draws the group's
  ordered swatch ramp — order test-enforced). Annotations draw their `n`
  marks per slot plus one `KEY` region in the footer (plan §2 — not a block).
- Export: `export_sheet(sheet_id, fmt)` → PNG at full size or single-page
  PDF; `export_lookbook(lb_id)` → multi-page PDF, one page per sheet at that
  sheet's own size (PIL `save(..., save_all=True, append_images=...)`; pages
  may differ in size). Exports are **refused** (`SheetError`) while
  `readiness` reports anything blocked. Output under
  `data/sheets/<SH>/export/`.
- `assemble.assemble_board` becomes: build the ephemeral BOARD sheet from its
  slot map (not persisted — `/arrange` persistence is the user's door), call
  `render_sheet(..., allow_letterbox=True)`, then write the board record,
  spec hash, and warnings exactly as today. Public signature, `AssemblyError`
  cases, `/api/specs/{spec_id}/assemble`, and `slot_map` unchanged.
  `_type_scale` is retired inside the sheet path; its label/sub floor problem
  resolves because sheet type comes from `caption_frac` (plan §6's known
  consequence — board density drops slightly; deliberate).

## 5. API (`app/main.py`)

Exactly the plan's §9 surface. Implementation notes:

- **Declare `GET /api/lookbooks/candidates` before `GET /api/lookbooks/{lb}`**
  (FastAPI route capture). `/candidates` reuses `generate.list_candidates`
  per spec and annotates `placed_in` by scanning sheet records once per call.
- `POST /api/sheets/{sh}/render` takes `{scale}` and returns `image/png`
  bytes (the frontend object-URLs them). Response carries
  `X-Sheet-Rev` so the client can drop stale previews.
- Error mapping: `KeyError` → 404, `SheetError` → 422, matching the app's
  existing conventions. Export endpoints return the §7 blocked list as the
  422 body when gated — the UI shows state before the act, so hitting this is
  the API contract, not the UX.
- `POST /api/specs/{spec_id}/arrange` → `sheet.arrange_board`; 404 unknown
  spec, 422 unlocked spec (mirrors assemble's gate).

## 6. Frontend (`app/static/app.js`, `index.html`, `styles.css`)

- `index.html`: the plan's Lookbook button between Reference and Productions
  in `#tools-nav`. `app.js`: `lookbook: renderLookbook` added to `views`,
  **not** to `STAGE_ORDER`.
- `renderLookbook` states: (a) lookbook list / empty state (archetypes as the
  primary act); (b) the composer. Persisted via `uiSet`/`uiGet` keys
  `lb.open`, `lb.sheet`, `lb.block` (already production-namespaced).
- **Composer**: left `.sheet-tray` (186px, twelve blocks in PANEL / EVIDENCE
  groups, draggable); centre preview; right rail (300px) per the plan §11.
  The preview is an `<img>` fed by `POST /render` at a scale fitted to the
  column (server-rendered — preview and export share one renderer, plan §10),
  re-fetched debounced (~150 ms) after every mutating call, keyed on `rev`.
- **Overlays are DOM, never ink** (plan §11): an absolutely-positioned layer
  over the preview draws slot outlines, selection, binding dots, snap guides
  and size chips from the sheet's fractional geometry — nothing app-chrome
  enters `render_sheet`.
- **Slot editing** (Phase 4):
  - *Drag-resize*: pointer events on overlay rect edges; live feedback moves
    the DOM rect only; soft snap to neighbour edges and canvas thirds
    (threshold 0.008 frac); on pointerup `PUT .../slots/{s}` with the new
    `frac`, then preview refresh. Every drop saves — no session, no button.
  - *Crop/zoom/rotate*: modal reusing the existing `cropper` overlay pattern
    (app.js ~L72), extended with a rotate control and ratio chips (`SLOT`,
    `16:9`, `2.39:1`, `4:3`, `1:1`, `FREE`). Writes `crop` normalized to the
    source image. Over-budget crops are kept; the slot's rail row flips to
    its blocked state (never an error dialog — gates read as state).
  - *Fill an empty slot*: click → in-place popover of approved candidates
    (from `/api/lookbooks/candidates`), each marked `FITS` / `NEEDS A CROP` /
    `TOO SMALL` computed client-side from candidate dimensions vs
    `slot_pixel_need` values the readiness payload already carries.
- **Stage 05**: gains `Arrange this board` beside Assemble (calls `/arrange`,
  navigates to the composer); loses the variant chips (`app.js` ~L8081 —
  layout is a sheet property now). There is no style picker or studies toggle
  to remove (they never existed).
- CSS: new `.sheet-tray`, `.sheet-stage`, `.sheet[data-style]` ink blocks
  (namespaced custom properties, e.g. `--sheet-paper`), rail components reuse
  existing panel/rail classes. No renames of existing classes. Amber stays
  signal-only: selection, the one primary act, focus. Machine data in
  Courier. At most one `.panel-lead` (the blocked-export panel, only while
  blocked).
- Design-system bookkeeping in the same commits: `## Uncanonized patterns`
  row for the composer; §13's eight canon lines folded into
  `DESIGN_SYSTEM.md`; changelog lines; `/design-verify` run for every
  UI-touching phase; plan file deleted at the end and the mocks kept.

## 7. Tests (`tests/test_sheet.py` + touched suites)

All of the revised plan's §12 list (its worked-outcomes table is the oracle),
plus:

- `recommend`: HERO+PRINCIPLES → (12, 8) print (elastic PRINCIPLES does not
  drag it); ORTHO floors print at (36, 24); 18×12 middle rung via a test-only
  injected frac 0.01029 (R1 nit — canon set stays closed); SCREEN: HERO-led
  → 1920, CLUSTER **and** BEATS → 3840; all-elastic sheet → bottom rung with
  rendered type at `max(frac × width, floor)`; size change mutates no `frac`.
- `readiness`: one list, both kinds, `ready` flips only when empty; slot_map
  parity — a `TOO_SMALL` stage-05 slot surfaces as `SLOT_PIXELS` on the
  arranged sheet.
- Bindings: stale detection via hash; `rebind`/`author` never mutate the
  source; `author` survives further source drift; palette order preserved.
- `render_sheet` raises on a short slot; `allow_letterbox=True` letterboxes
  and warns (assemble parity); a sheet operation never writes `SPECS_DIR`
  (assert via the storage-guard pattern in `tests/test_storage_guard.py`).
- `/arrange` idempotent (same `sheet_id` twice); variant mapping — `hero:<p>`
  → `HERO`+`GRID`, `allocation` → `CLUSTER`, `aspect`/`grid` → `GRID`;
  derived-strip spec arranges MATERIALS/PALETTE takes into a trailing `STRIP`
  carrying the R4 swap note — nothing dropped.
- Route order: `/api/lookbooks/candidates` resolves as candidates, not as
  lookbook id "candidates".
- `tests/test_assemble_layout.py` passes **unchanged** after the packing move
  (behaviour-preservation gate). `test_design_tokens.py`: sheet ink allowed
  only under `.sheet[data-style]`.
- All tests run against a temp home via the `tests/test_app_api.py` redirect
  pattern; no fakes needed beyond the existing ones.

## 8. Phases (each lands green + committed; UI phases run /design-verify)

All rulings landed — no phase is blocked.

1. **Model** — `paths`, `sheet.py` (CRUD, geometry move, recommend,
   readiness, bindings), `test_sheet.py`, `test_assemble_layout.py` unchanged.
   No UI.
2. **Renderer** — `sheet_render.py` (INK board default per R6), export,
   `assemble_board` refactor, `/arrange` with the R3 mapping + R4 strip.
3. **Lookbook surface** — API remainder, nav button, list/empty states,
   composer read-only (preview, style, size ladder, blocks add/remove,
   caption rail with bindings and stale acts), the R7 "breakdown" rename.
4. **Slot editing + gates** — fill/drag/crop-zoom-rotate, export gating UI,
   stage-05 Arrange button + variant-chip removal, canon fold (items 1–10 of
   the revised plan §13), plan deletion, RETIRED_PLANS ledger entry.

## Appendix A — why §6/§12 could not both hold (kept for the design record)

With `worst = min(caption_frac)` over **all** blocks: HERO+PRINCIPLES print
worst is PRINCIPLES 0.00809 → 0.00809·12·72 = 6.99 pt < 12 → cannot recommend
12×8 (lands 24×16). Prose exemption fixes it (HERO: 0.01471·12·72 = 12.7 ≥ 12).
Screen, scaled floor: `frac·w ≥ 24·(w/1920)` ⇔ `frac ≥ 0.0125` — width
cancels; only HERO ever passes, every other sheet falls through to 5120.
Screen, fixed floor F: CLUSTER→1920 needs F ≤ 1920·12/1360 = 16.94;
BEATS→3840 needs F > 2560·9/1360 = 16.94 — the same number, so no F satisfies
both. (My F = 20 proposal was overruled: the floor is not tuned to widen a
spread. Ruled resolution: F stays 24, elastic type renders at max(size,
floor), and the two-rung screen outcome is accepted as the honest result.)
