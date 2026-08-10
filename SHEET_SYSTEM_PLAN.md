# SHEET_SYSTEM_PLAN.md — one grammar for boards and lookbooks

**For the coding agent.** Read `app/static/DESIGN_SYSTEM.md` first, then this
whole file before writing anything — it replaces a stage-05 mechanism as well
as adding a tool, and doing half of it leaves the app with two of everything.

Supersedes `LOOKBOOK_PLAN.md` (delete it if present; it contained a claim —
"a board can be placed into a lookbook" — that its own model could not honour).

New files: `app/sheet.py`, `app/sheet_render.py`.
Touches: `app/assemble.py`, `app/main.py`, `app/paths.py`,
`app/static/app.js`, `app/static/index.html`, `app/static/styles.css`,
`app/static/DESIGN_SYSTEM.md`.

Mocks in `design_mocks/`:

| mock | shows |
|---|---|
| `lb-1a-composer.png` | the composer — tray, fitted sheet, slot + binding rail |
| `lb-1b-art-direction.png` | ART_DIRECTION filled, GALLERY style |
| `lb-1c-subject-study.png` | SUBJECT_STUDY filled, INK style with parchment inset |
| `lb-1d-scene-board.png` | SCENE_BOARD filled, 15 beats |
| `lb-2a-sheet-size.png` | the size ladder and its recommendation |
| `lb-2b-three-rungs.png` | three densities on three rungs |
| `lb-3a-six-styles.png` | **the six sheet styles — one list for boards and pages** |
| `lb-3b-ladder-media.png` | **print and screen ladders, one legibility rule** |
| `lb-3c-board-archetype.png` | **a stage-05 board drawn as a sheet** |
| `ba-2a-compose.png` | stage 05 composing — panel selected, snapped |
| `ba-2c-crop-zoom-rotate.png` | crop, zoom, rotation, pixel budget |
| `ba-2d-fill-empty-slot.png` | filling an empty slot from the breakdown |
| `ba-3a-includes.png` | colour, material and annotations on a board |
| `ba-3b-include-gates.png` | each include alone, and the gated state |
| `ba-4a-division.png` | **what stage 05 keeps and what moves** |

---

## 0. Rulings on `SHEET_SYSTEM_TECH_SPEC.md` (R1–R8)

Five accepted, three overruled. Where a ruling changes this plan, the section
below it has been amended — this file stays the single source of truth.

**R1 — caption floor. Diagnosis accepted, both fixes overruled.**
Appendix A's arithmetic is right and catches a real contradiction: with
`min` taken over all blocks, HERO+PRINCIPLES cannot land on 12×8, and my
"scales with width" note cancels width out of the inequality. Both were errors.

But **prose is not exempt from legibility** — a PRINCIPLES block set at 7 pt is
unreadable, and a class of text allowed to be illegible defeats the rule. And
the screen floor does not drop to 20 px to make a test produce a prettier
spread; that is letting the implementation choose the ruling, which this
project has already canonized against.

The real distinction is not prose-vs-caption, it is **fixed rect vs own
column**:

- A **caption** sits in a fixed rect under an image. It cannot grow without
  colliding, so its size is fixed by `caption_frac` and it *drives* the
  recommendation.
- **Prose** (`PALETTE` labels, `SPEC` rows, `PRINCIPLES` bullets) owns its own
  column and reflows. It does not drive the recommendation, and it is
  **computed as `max(authored_frac × width, floor)`** — it grows to the floor
  and takes the extra vertical room. Prose blocks therefore can never set
  under the floor, and can never force a sheet to a larger rung.

Screen floor stays **24 px** (the project's own screen minimum; a board is not
exempt from it either). The consequence is accepted honestly: on screen,
`CLUSTER` and `BEATS` both land on 3840 — two rungs, not three. The
three-distinct-rungs story is the **print** story, and print still gives it
exactly as drawn in `lb-2b`: HERO → 12×8 (12.7 pt), a 14 px floor → 18×12
(13.3 pt), BEATS → 36×24 (17.2 pt). Amend §6 and §12; do not amend the mock.

**R2 — `allow_letterbox` flag. Accepted as written.** Correct call: one
renderer, stage 05's shipped contract preserved by an explicit opt-in.

**R3 — hero boards need two blocks. Accepted.** "One layout block" was too
strict, and the real variant list (`aspect`, `allocation`, `grid`,
`hero:<panel>`) is better than the three I named from the mock. §3's BOARD
archetype is amended to *optional `HERO` + one layout block*; the mapping table
in R3 is adopted verbatim.

**R4 — derived strip migration. Accepted, with one addition.** The conflict is
real: today's MATERIALS/PALETTE are rendered panels, and the `PALETTE` block is
app-drawn. Putting existing takes into a trailing `STRIP` loses nothing, which
is right. **Add:** the composer must *name the swap* rather than leave the user
to infer it — a one-line Courier note on that strip, `RENDERED AS PANELS · THE
PALETTE BLOCK CAN DRAW THESE FROM STAGE 02`, with the block swap as its action.
An empty gap the user must diagnose is the failure this app keeps ruling out.

**R5 — two vocabularies, split by surface. Accepted.** The plan did say both
things; this resolution is what §13's canon line actually means. Stage-05's
`slot_map` shape does not change; `TOO_SMALL` maps to `SLOT_PIXELS` at the
sheet boundary only.

**R6 — board default style. Overruled: `INK`, not `CONTACT`.** `CONTACT` is
flush with a hairline keyline; today's boards draw each panel on `PANEL_BG`
with a label beneath, which is **matted** — that is `INK`. Choosing `CONTACT`
would flip every existing board to a layout it has never had, which is a
regression dressed as a default. `INK`'s ground moves from warm charcoal
`#2a2723` to `#131418` and that shift is **accepted deliberately**, on the same
principle as the type floor: when unification changes shipped output, change
the output — do not fork the style to preserve the old look.

**R7 — the word "sheet". Flag accepted, mitigation overruled.** Copy discipline
does not fix one word meaning two things in one app; it just asks everyone to
remember. Stage 03's artifact is renamed: **it is a breakdown, not a breakdown
sheet.** The nav already says Breakdowns; "sheet" in that surface's prose is
incidental and is removed in this pass. "Sheet" then means exactly one thing.

**R8 — retired take-bar plan. Accepted.** Already deleted from the drop-in with
its mock; it should not have survived the shipped report. Only `lb-*` and
`ba-*` mocks enter `design_mocks/`.

---

## 0.1 The ruling this plan exists to implement

Boards (stage 05) and lookbooks were designed apart and grew three duplicate
mechanisms — two style vocabularies, two layout engines, two sizing rules —
plus one contradiction: a board is 16:9 and a page is 3:2.

**A board is a sheet with a `BOARD` archetype.** One renderer, one style list,
one ladder, one set of blocks.

Stage 05 keeps what it is actually for — judging whether a scene's approved
panels are ready, and saying so before a render is spent. It stops owning
presentation. `ba-4a-division.png` is the division; build to it.

| stays in stage 05 | moves to the sheet grammar |
|---|---|
| slot readiness, the never-upscale gate | the five board styles |
| assembly, board records, spec hash | layout variants (default/grid/hero) |
| promotion to `SCENE_REFERENCE` | colour + material studies |
| crop, drag-resize, add-a-panel (§5) | the 4K constant |

Stage 05 gains exactly one new action beside Assemble: **Arrange this board**,
which opens the composer on a pre-made `BOARD` sheet carrying this scene's
slots. Readiness travels with it and is not recomputed — the composer must
never grow a second opinion about whether a panel is big enough.

---

## 1. Storage and identity

`paths.SHEETS_DIR = DATA / "sheets"`, `paths.LOOKBOOKS_DIR = DATA / "lookbooks"`.
Add both to `ensure_dirs()` and to the `_project_base` globals block beside
`BOARDS_DIR`. IDs via `store.next_counter` — `SH` for sheets, `LB` for lookbooks.

A sheet is a standalone record. A lookbook is an ordered list of sheet ids plus
a title. A board sheet may belong to no lookbook — that is the stage-05 case.

```json
{
  "sheet_id": "SH-0001",
  "archetype": "BOARD",
  "style": "GALLERY",
  "medium": "SCREEN",
  "size": [3840, 2160],
  "size_source": "RECOMMENDED",
  "spec_id": "SPEC-0004",
  "masthead": {"title": "THE BELTMINERS",
               "subject": "BELT RIG EXTERIOR",
               "binding": {"kind": "SPEC_FIELD", "id": "SPEC-0004", "field": "subject"}},
  "spine": false,
  "blocks": [
    {"block_id": "B-0001", "type": "CLUSTER",
     "heading": {"text": "...", "binding": {...}, "bound_hash": "sha256:...", "state": "BOUND"},
     "caption": {"text": "...", "state": "AUTHORED"},
     "slots": [
       {"slot_id": "S1", "spec_id": "SPEC-0004", "candidate_id": "CAND-0102",
        "frac": {"x": 0.0, "y": 0.0, "w": 0.62, "h": 1.0},
        "crop": {"x": 0.0, "y": 0.06, "w": 1.0, "h": 0.88, "rotate": 0.0},
        "annotation": {"n": 1, "text": "...", "binding": {...}}}
     ]}
  ]
}
```

**Slot geometry is fractional**, exactly as `assemble.slot_map` already reports
it. Print/screen pixels are always derived, never stored — that is what makes
a size change free and what makes preview and export agree.

---

## 2. The block library — twelve types, closed set

`caption_frac` is the type's size as a fraction of sheet width, so the
legibility floor is resolution- and medium-independent. Values are the authored
px at the 1360-wide mocks ÷ 1360. This table is canon.

`elastic` marks type that owns its own column and reflows (R1). Elastic type is
rendered at `max(frac × width, floor)` — it grows to the floor and takes the
extra vertical room, so it never sets under the floor and never drives the size
recommendation. Fixed type sits in a rect under an image, cannot grow without
colliding, and **is** what drives the recommendation.

| type | slots | caption_frac | authored px | elastic | replaces |
|---|---|---|---|---|---|
| `HERO` | 1 | 0.01471 | 20 | no | board `hero:<panel>` variant |
| `CLUSTER` | 2–5 | 0.00882 | 12 | no | board `allocation` variant |
| `STRIP` | 3–8 | 0.00625 | 8.5 | no | — |
| `BEATS` | 6–15 | 0.00662 | 9 | no | — |
| `GRID` | 4–12 | 0.00662 | 9 | no | board `grid` + `aspect` variants |
| `ORTHO` | 4 | 0.00588 | 8 | no | — |
| `PALETTE` | 0 | 0.00699 | 9.5 | **yes** | board colour study |
| `MATERIAL` | 3–6 | 0.00699 | 9.5 | no | board material study |
| `SPEC` | 0 | 0.00699 | 9.5 | **yes** | — |
| `PRINCIPLES` | 0 | 0.00809 | 11 | **yes** | — |
| `LINEUP` | 4–10 | 0.00625 | 8.5 | no | — |
| `VERSUS` | 2 | 0.00772 | 10.5 | no | — |

Twelve covers every region in the nine reference boards **and** every region of
a stage-05 board. Do not add a thirteenth without a designer ruling.

`_layout_rects`, `_grid_rects` and `_aspect_rects` in `assemble.py` are not
deleted — they become the packing functions for `CLUSTER`, `GRID` and `GRID`'s
aspect-first mode. Move them to `sheet.py` and have `assemble.py` import from
there, so there is one implementation.

Variant mapping for `/arrange` (R3, adopted verbatim):

| board variant | block sequence |
|---|---|
| `aspect` | `GRID` (aspect-first mode) |
| `allocation` | `CLUSTER` |
| `grid` | `GRID` |
| `hero:<p>` | `HERO` holding `<p>` **+** `GRID` (aspect-first) holding the rest |

Existing `MATERIALS` / `PALETTE` panel **renders** are not evidence blocks —
they are takes. `/arrange` appends them as a trailing `STRIP`, captioned from
the panel titles, carrying one Courier note: `RENDERED AS PANELS · THE PALETTE
BLOCK CAN DRAW THESE FROM STAGE 02`, with the swap as its action (R4). Nothing
is dropped, and nothing is left for the user to diagnose.

**Annotations are not a block.** They are the optional `annotation` object on a
slot, plus one `KEY` region rendered in the sheet footer listing them in order.
They claim no band and force no reflow. See `ba-3a-includes.png`.

---

## 3. Archetypes

| archetype | spine | sequence |
|---|---|---|
| `BOARD` | no | optional `HERO` + one layout block + optional `PALETTE`, `MATERIAL` + canon footer |
| `ART_DIRECTION` | yes | 3 × `CLUSTER`, 4 × `CLUSTER`, `STRIP` |
| `SUBJECT_STUDY` | yes | `HERO`, `ORTHO`, `STRIP`, `SPEC`, `MATERIAL`, `VERSUS` |
| `SCENE_BOARD` | yes | `BEATS`, 3 × `STRIP` |
| `LOOK_STYLES` | no | 4 × `CLUSTER`, `PRINCIPLES`, `LINEUP` |
| `FACTION` | no | N columns of `HERO` + `PRINCIPLES` + `GRID` + `PALETTE` |
| `LOCATION` | no | `GRID`, `PRINCIPLES`, `PALETTE` |

Build `BOARD`, `ART_DIRECTION`, `SUBJECT_STUDY`, `SCENE_BOARD` first — those
four have mocks. An archetype is a starting sequence, not a cage: blocks may be
added and removed after creation.

---

## 4. The six sheet styles

`lb-3a-six-styles.png`. One list, used by boards and pages alike. A style
declares four things and **nothing else** — no layout, no size, no content.

| style | paper | inset | edge | voice |
|---|---|---|---|---|
| `GALLERY` | `#efe9dd` warm rag | `#e4ddd0` | matted | serif plates |
| `CONTACT` | `#17181a` lab black | none | flush, hairline keyline | mono, small |
| `NEWSPRINT` | `#d9d4c8` halftone | none | bleeds past its rules | slab + condensed |
| `BLUEPRINT` | `#1c4f7c` + white grid | none | reversed keyline | drafted mono |
| `PLATE` | `#fbfbf9` bright white | none | flush cluster | quiet sans |
| `INK` | `#131418` near black | `#e2ddd0` parchment | matted | bone, mono labels |

Notes the coding agent needs:

- `GALLERY` is the old `GALLERY_PRINT` **and** the old `PARCHMENT` ground —
  they were the same style described twice.
- `PLATE` is the old `LOOKBOOK` board style, renamed. **A style may not be
  named after a feature.**
- `INK`'s **inset** is what lets a dark sheet carry a pale orthographics block
  (`lb-1c`, and reference board 3). This is not a per-block override — block
  ground overrides do not exist. The old `HYBRID` ground is deleted; it was
  reaching for this.
- These are **sheet ink, not app tokens.** Do not add them to `:root`.
  Namespace under `.sheet[data-style]` so nobody mistakes them for design
  tokens. The app chrome around a sheet keeps using `--ink`, `--accent`, etc.

A style owns every app-drawn mark on the sheet: masthead, labels, ramps,
material tiles, annotation marks, canon footer. It never touches a rendered
panel image.

**`INK` is the default style for boards** — `/arrange`-created and legacy
assembled alike (R6). Today's boards draw each panel on `PANEL_BG` with a label
beneath, which is matted, which is `INK`; `CONTACT` is flush and would change
every existing board's layout. `INK`'s ground moves from the board's warm
charcoal `#2a2723` to `#131418`, and that shift is deliberate — the style is
not forked to preserve the old tone, for the same reason boards are not exempt
from the type floor.

---

## 5. Slot editing — crop, zoom, rotate, resize, fill

Unchanged from the stage-05 design; these act on slots and slots are shared, so
they work identically on a board sheet and a lookbook sheet.

**Crop / zoom / rotate** (`ba-2c-crop-zoom-rotate.png`). The frame never
rotates — the image rotates inside it and auto-fills, and that fill is charged
to the crop budget like any other zoom. Ratio choices are `SLOT`, `16:9`,
`2.39:1`, `4:3`, `1:1`, `FREE`; a ratio other than `SLOT` lets the sheet's
paper show inside the frame, which is how `GALLERY` and `BLUEPRINT` earn their
matte. Cropping past the slot's pixel need is **allowed and kept** — the slot
turns `TOO_SMALL` and export blocks, exactly as a small render does. Reuse the
cover-crop path already in `assemble_board`; do not write a second one.

**Drag-resize** (`ba-2a-compose.png`). Edges drag freely with soft snapping to a
neighbour's edge and to thirds of the canvas. Writes `frac` directly. Every
drag saves — there is no session and no save button.

**Fill an empty slot** (`ba-2d-fill-empty-slot.png`). Clicking an empty slot
offers the breakdown's approved candidates in place, marked `FITS`,
`NEEDS A CROP` or `TOO SMALL` against that slot. No toolbar button claims to
add a panel: the verb sits with the thing it acts on.

---

## 6. Size — one rule, two media

`lb-3b-ladder-media.png`. Ratio is fixed per medium, so a rung change rescales
and **reflows nothing**.

```python
LADDERS = {
    "PRINT":  {"ratio": (3, 2),  "rungs": [(12, 8), (18, 12), (24, 16), (36, 24)],
               "unit": "in", "floor": 12.0},   # points, fixed
    "SCREEN": {"ratio": (16, 9), "rungs": [(1920, 1080), (2560, 1440),
                                           (3840, 2160), (5120, 2880)],
               "unit": "px", "floor": 24.0},   # device px, fixed
}

def type_size(frac, medium, width):
    """PRINT -> points; SCREEN -> device px."""
    return frac * width * 72 if medium == "PRINT" else frac * width

def rendered_size(block, medium, width):
    """Elastic type grows to the floor; fixed type does not."""
    s = type_size(BLOCK_TYPES[block["type"]].frac, medium, width)
    floor = LADDERS[medium]["floor"]
    return max(s, floor) if BLOCK_TYPES[block["type"]].elastic else s

def recommend(sheet):
    """Smallest rung where every FIXED caption clears the floor and every
    slot clears its pixels. Elastic blocks never drive this — they reflow."""
    L = LADDERS[sheet["medium"]]
    fixed = [b for b in sheet["blocks"] if not BLOCK_TYPES[b["type"]].elastic]
    worst = min((BLOCK_TYPES[b["type"]].frac for b in fixed), default=None)
    for w, h in L["rungs"]:
        if worst is not None and type_size(worst, sheet["medium"], w) < L["floor"]:
            continue
        if _any_slot_short(sheet, w):
            continue
        return (w, h)
    return L["rungs"][-1]
```

The floors are **fixed** — never scaled by width. Scaling the screen floor with
width cancels width out of the inequality, which makes a larger rung unable to
fix anything (the tech spec's Appendix A is right about this).

Print: required slot pixels are `frac_w × width_in × 300`.
Screen: required slot pixels are `frac_w × width_px`.

The rule runs opposite to instinct and the UI must not hide that: a **sparse**
sheet authors large type and prints small; a **dense** sheet authors small type
and needs a large sheet to stay legible. Density forces format.

Worked outcomes — these are the test expectations:

| stack | medium | worst fixed frac | lands on | at |
|---|---|---|---|---|
| `HERO` + `PRINCIPLES` | PRINT | 0.01471 (HERO) | 12 × 8 | 12.7 pt |
| trimmed subject study, 14 px floor | PRINT | 0.01029 | 18 × 12 | 13.3 pt |
| `BEATS` scene board | PRINT | 0.00662 | 36 × 24 | 17.2 pt |
| `HERO`-led board | SCREEN | 0.01471 | 1920 | 28.2 px |
| `CLUSTER` board | SCREEN | 0.00882 | 3840 | 33.9 px |
| `BEATS` board | SCREEN | 0.00662 | 3840 | 25.4 px |

`lb-2b-three-rungs.png` is the print row and holds exactly as drawn. **On
screen, `CLUSTER` and `BEATS` both land on 3840** — two rungs, not three, and
that is the honest result of a 24 px floor. Do not lower the floor to widen the
spread.

`size_source` is `RECOMMENDED` until the user picks, then `CHOSEN`. While
`RECOMMENDED`, follow the recommendation silently on every block change — that
is what recommended means.

### Known consequence: shipped board type is under the floor

`assemble._type_scale` computes `label = max(20, int(36 * sc))` — 36 px at
height 2160, i.e. on a 3840-wide canvas. The screen floor at 3840 is 48 px.
**Existing board labels fail this rule.** This is the same complaint the
function's own docstring already records about titles reading tiny on a wall
board. Raise the label and sub scales to clear the floor as part of this work,
and expect the board's visual density to drop slightly. Do not exempt boards
from the rule to preserve the current look.

---

## 7. Export gate — one failure vocabulary

Blocked when **either** a caption would set under the medium's floor, **or** a
slot's candidate is short of the pixels its rendered size needs. Both are
allowed and kept — never discarded, never silently degraded. One list:

```json
{"ready": false,
 "blocked": [
   {"kind": "TYPE_FLOOR",   "block_id": "B-0007", "size": 8.6, "floor": 12.0},
   {"kind": "SLOT_PIXELS",  "slot_id": "S2", "have": [1024, 576], "need": [2160, 1215]}
 ]}
```

One vocabulary **per surface** (R5). Stage 05's `slot_map` shape does not
change — `not_ready: [{panel_id, status}]` with its existing statuses, and its
tests and UI stay untouched. The sheet surface uses the shape above verbatim,
and `TOO_SMALL` maps to `SLOT_PIXELS` at the sheet boundary only. What is
forbidden is two vocabularies inside one surface, which is what §13's canon
line means.

---

## 8. Caption binding

Every caption carries a `binding` or is marked authored.

| state | meaning | UI |
|---|---|---|
| `BOUND` | rendered from its source | `--ok` dot, source named in the rail |
| `AUTHORED` | no upstream source, written here | `--accent` chip on the block |
| `STALE` | source exists, its content hash changed | `--bad` chip, two offered acts |

| kind | source |
|---|---|
| `SUBJECT` | `store.get_subject` |
| `PANEL` | panel title / purpose, `store.get_spec` |
| `PALETTE_GROUP` | a stage-02 palette group, name + **ordered** swatches |
| `MATERIAL_ANCHOR` | `store.list_references`, role-filtered |
| `SCREENPLAY` | `store.screenplay_text_cached` |
| `JUDGING_NOTE` | a note on a candidate, `generate.list_candidates` |
| `SPEC_FIELD` | `store.get_spec` |

Store `bound_hash` (sha256 of resolved text) at bind time; compare on load.
A stale binding offers exactly two acts in the rail: **take the new line**
(rebind, new hash) or **keep and author** (freeze, becomes `AUTHORED`).
**Never auto-adopt.** A sheet is a record of what was approved, and silently
rewriting it is the failure this state exists to prevent.

Palette and material blocks bind to the **whole group, in order** — the order
is the ruling, per the palette-groups canon. A sheet may not reorder swatches.

Both studies are gated on stage 02 holding the work (`ba-3b-include-gates.png`):
the switch stays visible, off and unclickable, and names the stage that would
fill it. A missing include is a gap upstream, not a feature the sheet lacks.

---

## 9. API

```
GET    /api/sheets/{sh}                          full sheet
POST   /api/sheets                               {archetype, style, medium, spec_id?}
DELETE /api/sheets/{sh}
POST   /api/sheets/{sh}/style                    {style}
POST   /api/sheets/{sh}/size                     {size | "recommended"}
POST   /api/sheets/{sh}/blocks                   {type, index}
DELETE /api/sheets/{sh}/blocks/{b}
PUT    /api/sheets/{sh}/blocks/{b}/slots/{s}     {spec_id, candidate_id, crop, frac}
PUT    /api/sheets/{sh}/blocks/{b}/caption       {text} | {binding}
POST   /api/sheets/{sh}/blocks/{b}/caption/resolve  {action: "rebind"|"author"}
GET    /api/sheets/{sh}/readiness                -> §7 blocked list
POST   /api/sheets/{sh}/render                   preview PNG at a scale
POST   /api/sheets/{sh}/export                   {format: "png"|"pdf"}

GET    /api/lookbooks                            list
POST   /api/lookbooks                            {title}
GET    /api/lookbooks/{lb}
DELETE /api/lookbooks/{lb}
POST   /api/lookbooks/{lb}/sheets                {sheet_id} | {archetype,...}
POST   /api/lookbooks/{lb}/reorder               {order: [sheet_id...]}
POST   /api/lookbooks/{lb}/export                {format} — multi-page PDF
GET    /api/lookbooks/candidates                 approved, with placed_in

POST   /api/specs/{spec_id}/arrange              -> creates/returns the BOARD sheet
```

`/arrange` is stage 05's one new door. It is idempotent: a spec has at most one
`BOARD` sheet, created on first call from the spec's current slot map.

`/candidates` is the tray: every `APPROVED` candidate across the production,
`placed_in` populated. Reuse `generate.list_candidates` per spec; do not build
a second index.

---

## 10. Rendering

`app/sheet_render.py`, PIL, same shape as `assemble.py`:

- `render_sheet(sheet, scale) -> Image` — **one function serves preview and
  export**. The composer preview is this renderer at a smaller scale, so
  preview and output cannot drift. (`_type_scale`'s docstring already records
  what happens when they do.)
- All type sizes come from `caption_frac × pixel_width`. No constants.
- Images cover-crop exactly as `assemble_board` does. **No upscaling, ever.**
  Unlike a board, a sheet does not letterbox as a fallback — export is already
  gated on pixels, so a shortfall at render time is a bug and must raise.
- `assemble.assemble_board` becomes a thin caller: build the `BOARD` sheet,
  call `render_sheet`, write the board record as it does today. Its public
  signature, its `AssemblyError` cases and `/api/specs/{id}/assemble` do not
  change.
- PDF: one page per sheet at that sheet's own size. Sheets in one lookbook may
  differ in size; each page carries its own box.

Output to `data/sheets/<SH>/export/`, matching how boards land in `BOARDS_DIR`.

---

## 11. Front end

`index.html` — one button in `nav.tools`, between Reference and Productions:

```html
<button data-view="lookbook" title="Lookbooks — art direction, subject and scene sheets built from approved panels">Lookbook</button>
```

**Do not add a sixth cell to `nav#nav`.** The band is the pipeline; a lookbook
spans it. `app.js`: add `lookbook: renderLookbook` to `views`, and **not** to
`STAGE_ORDER`.

Composer layout per `lb-1a-composer.png`:

- left `.sheet-tray` (186px): the twelve blocks in two groups — PANEL BLOCKS,
  EVIDENCE BLOCKS — glyph plus name, draggable onto the sheet;
- centre: the fitted sheet, one `.sheet[data-style]`, with a Courier line
  stating medium, size and dpi;
- right rail (300px): `SELECTED · <BLOCK>` with per-slot rows (state dot, id,
  candidate, headroom), `CAPTION BINDING` with the three states and the two
  stale acts, `SHEET SIZE` (the §6 ladder, each rung priced in the medium's
  unit), then the readiness footer.

Stage 03 copy: **"breakdown sheet" becomes "breakdown"** throughout (R7). The
nav already says Breakdowns; the word "sheet" now belongs to this system alone.

Stage 05's view gains **Arrange this board** beside Assemble
(`ba-4a-division.png`) and loses its style picker, layout-variant chips and
studies toggles — those are sheet properties now, edited in the composer.

**Composer overlays are app chrome and never print.** Selection outline, slot
marks, binding dots, snap guides and size chips are `--accent` / status tokens
drawn in the DOM over the preview. They must not enter `render_sheet`. This is
the separation stage 05 already keeps between its slot map and its board.

Per `DESIGN_SYSTEM.md`: at most one `.panel-lead` (the blocked-export panel,
and only when something is blocked); amber only for current selection, the one
primary action, and focus; every id, size, count and status in Courier. Persist
the open lookbook, selected sheet and selected block via `uiSet`/`uiGet`,
namespaced per production. An empty lookbook shows the archetypes as the
primary act — never empty rectangles where sheets would go.

---

## 12. Tests

New `tests/test_sheet.py`:

- `recommend` returns 12×8 for `HERO`+`PRINCIPLES` (elastic `PRINCIPLES` does
  not drag it to 24×16), 18×12 for a 14 px-floored stack, 36×24 for a 15-beat
  scene board — the three print cases in `lb-2b`;
- a sheet containing `ORTHO` never recommends below 36×24 print;
- on `SCREEN`: a `HERO`-led sheet recommends 1920, and **both** `CLUSTER` and
  `BEATS` recommend 3840 — assert the true result, not a three-rung spread;
- an all-elastic sheet (`PALETTE`+`SPEC`+`PRINCIPLES`) recommends the bottom
  rung, and its rendered type is `max(frac × width, floor)` — never under it;
- changing size mutates no `frac` on any slot;
- readiness returns a `TYPE_FLOOR` and a `SLOT_PIXELS` entry in one list, and
  `ready` is false while either is present;
- a bound caption whose source changes reports `STALE`; neither `rebind` nor
  `author` mutates the source; `author` survives a further source change;
- palette binding preserves swatch order;
- `render_sheet` raises rather than letterboxing on a short slot;
- a sheet operation never writes to `SPECS_DIR`;
- `/api/specs/{id}/arrange` twice returns the same `sheet_id`;
- a `hero:<p>` spec arranges to `HERO` + `GRID`; an `allocation` spec to
  `CLUSTER`; `aspect` and `grid` to `GRID`;
- a spec with MATERIALS/PALETTE takes arranges them into a trailing `STRIP`
  carrying the swap note — nothing dropped;
- `GET /api/lookbooks/candidates` resolves as candidates, not as a lookbook
  with id "candidates".

Existing suites stay green. `test_assemble_layout.py` must pass unchanged after
the packing functions move — if it needs editing, the move was not behaviour-
preserving. Expect `test_design_tokens.py` to need one addition: sheet ink is
allowed outside `:root` under `.sheet[data-style]`, and only there.

---

## 13. Canon to fold into `DESIGN_SYSTEM.md`, then delete this plan

1. **A tool is not a stage.** The band is the pipeline. A surface that spans the
   production rather than advancing it goes in the header beside Reference.
2. **One grammar per artifact class.** Two surfaces that both arrange approved
   images onto a canvas are one mechanism with two archetypes. Before adding a
   layout engine, name what the existing one cannot express.
3. **A style declares surface, edge and voice — never layout, size or content.**
   And a style may not be named after the feature that uses it.
4. **Derived sizes are recommended, never imposed** — and the cost of moving is
   named in the unit the medium is read in, points or pixels, not adjectives.
5. **One failure vocabulary per surface.** Two ways of being unready are two
   entries in one list, not two mechanisms.
6. **Never auto-adopt an upstream change into approved work.** Report the drift,
   offer take-it or freeze-it, let the user rule.
7. **Composer overlays are app chrome and never enter the artifact.** Anything
   drawn to help the user aim lives in the DOM; the sheet carries only its ink.
8. **A rule applies to shipped output too.** When unification changes what
   already ships — type sizes, a ground colour, a default — change the output.
   Do not exempt it, and do not fork a style to preserve the old look.
9. **Type that owns a column reflows; type in a rect does not.** Prose grows to
   the legibility floor and takes the room; a caption under an image cannot, so
   it is what decides the size. Nothing is ever exempt from being legible.
10. **One word, one meaning.** Two artifacts sharing a name is not fixed by
    copy discipline. Rename one — here, stage 03's artifact is a breakdown.
