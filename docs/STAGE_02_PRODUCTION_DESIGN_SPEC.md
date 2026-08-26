# Stage 02 — Production Design

**A specification for redesign.** Written 2026-08-26 from the shipped code,
for the design agent. It describes what this stage *is for*, every control
on it, every gate, and what must not change. It does not prescribe a
layout — that is the thing being asked for.

Source of truth for the current build: `app/static/index.html`
(`<template id="tpl-wizard">`), `app/static/app.js` (`renderWizard`,
lines ~4519–6877), `app/wizard.py`, `app/bible.py`.

---

## 1. What this stage is for

Screenboard Studio turns a screenplay into canon-locked art-direction
boards. The pipeline is strictly sequential and each stage is gated on the
one before it:

```
01 Screenplay → 02 PRODUCTION DESIGN → 03 Breakdowns → 04 Panels → 05 Boards
```

**Stage 02's single output is the Art Direction Bible** —
`context/01_ART_DIRECTION_BIBLE.md`. Everything on this page exists to
produce, correct, or verify that one document. Nothing downstream can
start until it is saved: stage 03 returns HTTP 423 without it.

The Bible is not a summary. Sections of it are spliced verbatim into every
render prompt for the rest of the production. A sentence written here is
read by an image model months later, on a panel nobody has thought of yet.
That is the weight the page carries, and the reason its copy is blunt
about consequence.

**The user is a director or production designer**, not an engineer. They
are making creative decisions with money attached: every render costs, and
a wrong decision here propagates into every board.

---

## 2. The five steps, and why they are in this order

The page presents five numbered steps in one scrolling column, with a
header strip and a step rail.

| # | Step | Produces | Gated on |
|---|---|---|---|
| 1 | **Style anchors** | Four look decisions | nothing |
| 2 | **Script scene scan** | Design languages, environments, locations, subjects, questions, period, logline | a screenplay + an AI model |
| 3 | **Cast the film** | Subject cards in the Reference library | the scan (or manual) |
| 4 | **Art Direction Bible** | The document | anchors + scan + cast |
| 5 | **Test your model** | Sample renders per engine | a saved Bible |

**Order rulings that must survive a redesign:**

- **Anchors lead.** What the director wants it to *feel* like is stated
  before the machine reads anything (ruling 2026-08-07). Step 1 has no
  dependency and is never gated.
- **Casting follows the scan, not the interview.** Steps 3 and 4 were
  swapped from an earlier plan (LOCKED_STAGE_PLAN L3).
- **The Bible is fourth,** because it consumes the first three.
- **The model test is last,** because it renders *from* the saved Bible.

A redesign may change the visual arrangement of these five. It may not
change what depends on what.

---

## 3. Header strip

Three elements, currently in one panel:

- `FIVE STEPS → ART DIRECTION BIBLE` — the page's one sentence.
- **The screenplay fact** (`#wiz-screenplay`) — which file this production
  read. Stage 01's output, restated here because every step below reasons
  about it.
- **The step rail** (`#wiz-rail`) — five numbered chips. A chip goes
  `--ok` when its step's badge reads APPROVED; the current chip is
  bordered. Clicking scrolls to the step with a band offset.

**Rule:** the rail's done-mark derives from the step badge, never from its
own calculation. Two sources for one fact is how they drift.

---

## 4. Step 1 — Style anchors

Four columns in one grid, under two group labels: **THE MOVIE** (three
columns) and **THE BOARDS** (one column). That split is load-bearing —
three of these describe the film, one describes how the film is *drawn*.

### The four anchors

| Role | Label | SETS | NOT |
|---|---|---|---|
| `WORLD_TEXTURE` | World Texture | wear, patina, entropy | subjects · palette · light |
| `COLOR_PALETTE` | Color Palette | hue, value key, saturation | framing · light source · medium |
| `CINEMATOGRAPHY_STYLE` | Cinematography | light behaviour, contrast, source, the framings it allows | palette · a panel's hour |
| `BOARD_RENDERING_STYLE` | Board Rendering | medium, brushwork, finish | content · palette · the world |

Those SETS/NOT lines are not decoration. Each anchor has a **jurisdiction**
— the parts of a render it controls — and overlap between them is the
mechanism by which prompts contradict themselves. The lines are how a
director learns the boundary. **They must survive in any redesign.**

### Anatomy of an anchor column

Every column carries the same parts, in this order:

1. **Head** — the anchor name (with a tooltip explaining it) and a state
   badge (`NONE` / `IN WORDS` / a picture count).
2. **The SETS / NOT hint.**
3. **Add images** — a file input; uploads land as APPROVED references in
   that role.
4. **The words control** — see below; this is where the anchors differ.
5. **A thumbnail strip** of the pictures attached to that anchor.

**An anchor is SET by a picture OR by words** (ruling 2026-08-16). Both
are complete answers. The badge counts either.

### Three anchors use a catalogue picker; one uses free text

- **World Texture, Cinematography, Board Rendering** each open a **style
  picker modal**, backed by a live-read markdown document
  (`docs/WORLD_TEXTURE_STYLES.md`, `docs/CINEMATOGRAPHY_STYLES.md`,
  `docs/RENDERING_STYLES.md`). Their `<input>` is hidden; a button states
  the current choice by NAME.
- **Color Palette** is free text plus swatches — there is no palette
  catalogue, because swatches are proposed *from* the Bible rather than
  chosen before it.

Two extra controls belong to Board Rendering:

- **Never looks like** (`#wiz-never`) — hard exclusions, translated item
  for item into the Bible's `Rendering Language → Avoid` list.
- These "belong to an anchor but are not its style" controls **travel into
  the picker modal when it opens and go home when it closes** (ruling
  2026-08-16: "only have the button on the main page"). A redesign must
  decide whether to keep that mechanism or place them permanently.

### The style picker modal

Currently one component (`openStylePicker`) serving three libraries.

- A **grid of style cards**. Each card: optional source kicker, a picture,
  the name, a one-line description, and for cinematography a reference-film
  list.
- The picture is either **photographed reference frames** (up to three,
  from the reference library) or a **drawn plate** (an SVG diagram), or a
  stated placeholder — `REFERENCE FRAMES — NOT YET IN THE LIBRARY`.
  **Never pad to three.** A reserved empty shape is forbidden unless it
  states the blocker keeping it empty.
- A **definition paragraph** at the top saying what this axis *is* and what
  it is not.
- **One escape hatch below the grid, after a hairline:** `OR IN YOUR OWN
  WORDS` — a text field plus `+ Add an image`. It is deliberately *not* a
  grid cell: an escape hatch is not a member of the set it escapes.
- Actions: Cancel / **Use this**.

**Design note for the redesign:** these cards are the most image-rich
surface in the app, and the libraries are user-maintained markdown that can
grow. The grid must tolerate 5 styles (texture) and 9 (rendering) and 8
(cinematography) without a scroll trap.

### Colour swatches (Color Palette only)

- **Add swatch** opens a form (name + hex). A swatch is stored as an
  ordinary `COLOR_PALETTE` reference whose *pixels are the solid colour* —
  engines study the image — with name/hex in the notes.
- Swatches render as a **ramp strip** (`#swatch-strip`), one row per design
  language, ordered light→dark, with a **hero** swatch drawn double-width.
- A swatch that belongs to no language gets its own row. An uploaded palette
  plate (not a swatch) renders as a thumbnail row.
- Generated proposals (from step 4) stay client-side until approved; each
  approval creates the reference.

**Known trap, already fixed once:** the adder must be a *button*, never a
live `<input type="color">` — a browser draws that as a filled coloured
square indistinguishable from a real swatch, in the column of a production
that has none.

---

## 5. Step 2 — Script scene scan

One control row: a **Model** select (`gemini` / `openai`, listing only
engines that hold a key) and **Run the Scene Scan** (primary).

The scan reads the screenplay and returns a structured analysis, stored
server-side at `data/wizard_analysis.json` so it survives browser storage.

### What the read presents

A **reveal strip** — the read presents as a summary, not a wall:

1. **LOGLINE** — full width, first. What the read understood.
2. **PERIOD** — a stated value (or `UNSTATED`) with an Edit / State it
   action, and the line: *"Every render is held to this. An unstated period
   constrains nothing — which is how a WW2 aircraft reached a far-future
   salt pan."* That is a real failure this field exists to prevent.
3. **Five stat tiles**, each a link that scrolls to its section:
   DESIGN LANGUAGES · ENVIRONMENTS · LOCATIONS · SUBJECTS · OPEN QUESTIONS.
   **Open questions carry the only coloured number** — `--accent` while any
   remain unanswered. Segments render only when their data exists; there is
   never a `0 ENVIRONMENTS` tile.

### Then four sections

- **DESIGN LANGUAGES — WHAT A PANEL IS ALLOWED TO LOOK LIKE.** One card per
  language. Each has a name, a description, keywords (derivable from the
  screenplay by a keyword pass), and a status: `CONFIRMED` or `PROPOSED`. A
  PROPOSED language must be confirmed or dropped; until then step 2's badge
  stays PROVISIONAL. **The first language is the production's default
  world.** Each becomes a `##` section in the Bible.
- **ENVIRONMENTS — THE LIGHT AND PALETTE OF A PLACE.** Name, notes,
  keywords, an assigned set of locations, and the same PROPOSED/CONFIRMED
  cycle. Each becomes a `###` entry under `## Environments`.
- **LOCATIONS** — a flat finder list in screenplay order. Per row:
  the slugline, its environment (or a stated blank), its breakdown sheet
  (or `NONE`), and a verb. **The verb is withheld, never disabled-looking:**
  without a saved Bible the cell reads `NEEDS THE BIBLE`; with one it is
  `Create breakdown`. Long lists show a head and state their tail.
- **OPEN QUESTIONS** — what the screenplay does not answer. Marked
  `OPTIONAL — YOU CAN DO THIS OVER TIME`. Answers ride the Bible draft.

Also here: **Name the acts** — an action that groups locations into acts.

### Gates and states

- Without a screenplay or a model, the scan states the gate before it is
  hit (`#wiz-analyze-lock`), never as an error after the click.
- A second scan **merges** with the existing analysis rather than replacing
  it — confirmed languages and answered questions survive a re-run.
- Model choice locks after a read.

---

## 6. Step 3 — Cast the film

Subtitle: `CASTING MAKES A CARD IN REFERENCE / SUBJECTS · ITS SCREENPLAY
IDENTITY RIDES EVERY PROMPT`.

This step is **a door into the Reference library's SUBJECTS shelf**, not a
separate store. The card component is shared (`buildSubjectCard`) — one
component, two hosts.

- **`FOUND IN THE SCREENPLAY — UNCAST`** — chips for what the scan found
  and nobody has cast yet, grouped by kind. Casting a chip creates the
  library card and opens its photo chooser in one gesture.
- **Manual add** — name + kind (`CHARACTER` / `VEHICLE` / `PROP`) +
  `+ Cast`. It goes through the same modal as chip-casting; that path used
  to write the card on click and then fire the file dialog separately,
  which is the inconsistency the shared modal removed.
- **A grid of cast subject cards** below.

Kind matters downstream: CHARACTER → likeness reference, VEHICLE →
geometry reference, PROP → prop reference.

---

## 7. Step 4 — Art Direction Bible

Subtitle: `context/01_ART_DIRECTION_BIBLE.md · EDITS REACH EVERY FUTURE
PROMPT`.

### One primary button, whose verb is the next true thing

Ruling 2026-08-22, verbatim: *"I should not have to detail out how
creating, editing and saving should work — make it all one button."*

| State | Button reads | Editor |
|---|---|---|
| empty | **Create Art Direction Bible** | editable |
| unsaved text | **Save Art Direction Bible** | editable |
| saved | **Edit** (ghost) | read-only |
| editing | **Save Art Direction Bible** | editable |

`Regenerate` (ghost) joins it only once a Bible exists, and hides again
while editing. A condition line sits beside them and changes per state
(`FROM THE ANCHORS, THE SCAN AND THE CAST — WRITTEN, SAVED, AND BREAKDOWNS
OPEN` / `YOUR OWN TEXT — SAVING IT OPENS BREAKDOWNS` / `ESC DISCARDS —
NOTHING CHANGES UNTIL YOU SAVE` / nothing when saved). **Escape exits an
edit**, so Edit is never a trap.

**This act row carries exactly one primary verb plus Regenerate.** Other
acts on the document go beneath it.

### Standing notes

`#wiz-notes` — a textarea for anything true of the production that is not
texture, palette, light or medium. Example given in the placeholder: *"1974,
but nobody smokes"*. These ride every draft.

### The editor

A monospace textarea (`#style-bible`), min-height 340px, Courier 13px. It
holds the whole document. Read-only once saved until Edit is pressed.

### What the drafter writes

The draft is a model call taking the four anchors (as words *and* attached
images), the scan, the cast, the standing notes, and the answered
questions. Its output has a **fixed section order** that the rest of the app
parses:

```
# <Project> — Locked Art Direction Bible
## Status
## Overall Visual Identity          ← rides EVERY panel prompt
## Rendering Language               ← rides EVERY panel prompt
   ### Required
   ### Avoid
## Design Languages
## <World 1 name>                   ← selected per panel
## <World 2 name>
   **Design language:** …
   **Color identity:** …
## Environments
   ### <Environment name>           ← selected per panel
## Core Material Language
   ### <World name>
## Lighting Language                ← rides EVERY panel prompt
## Composition Rules
## Character Presentation           ← selected per panel, per cast member
## Production Board Presentation
## Current Locked Scene-Specific Lessons
## Drift Prevention Rule
```

A redesign may present this document differently but **must not change the
headings** — `app/bible.py` parses them, and a renamed section silently
stops reaching renders.

### Check it agrees with itself

A ghost button **below** the editor, visible only when a Bible is saved,
with its report beneath it. It reads the document against itself for two
rules that cannot both hold in one frame, and reports:

- Clean: `Read N characters — no two rules that cannot both hold in one
  frame. Deliberate contrast between different subjects is not counted, and
  is not a fault.`
- Conflicts: a head `N CONFLICTS — ADVISORY, NOTHING WAS CHANGED`, then one
  block per conflict: the two section names in Courier joined by `✕`, each
  rule quoted, and one faint line on what a single frame cannot do while
  both hold.

**It never edits.** It is advisory, it is not run on save (a save happens on
every edit; a paid re-read on each one trains people to stop saving), and a
report never outlives the text it read.

### Generate swatches

A block (`#swatch-gen`) that reads the **saved** Bible and proposes colour
swatches grouped by design language. The act lives here because its
precondition is met here; **its result lands in step 1's Color Palette
column**, and this block says so. Renders only once a save exists.

---

## 8. Step 5 — Test your model

Subtitle: `SAME LOCATION · SAME BIBLE · SAME ANCHORS`.

- **Sample location** — a `<select>` of the production's own screenplay
  locations, from the step 2 scan, plus a free-text fallback. It was a
  `datalist` and that failed a real user: a datalist shows nothing until you
  type, so a director whose screenplay the app had just read saw an empty
  box. *A datalist is a convenience for a field you already know how to
  fill; this is a field whose whole value is that the app knows the
  answers.*
- **Generate a sample from every model** — sends the identical brief (Bible
  + style anchors + the chosen location) to every engine holding a key.
- **Each engine renders TWICE**, and both images show side by side at equal
  size, under one line saying that what differs between them is that
  engine's run-to-run variance and not a decision it made. Neither is
  larger; making one larger would make it the answer, and neither is.
- Per engine: the label, a `DEFAULT` badge if it is the preferred engine,
  the location it rendered, the pair, **Make default**, and
  **Regenerate**.
- The probe **refuses to run** if the Bible contradicts the rendering-style
  anchor, because it would spend a render proving the contradiction.

---

## 9. Cross-cutting rules the redesign must honour

### Gates are readable as state, before they are hit

Never a 422 after a click. Show the disabled control, state the unmet
condition beside it, and link to where it gets resolved. The locations
table's `NEEDS THE BIBLE` is the canonical example — a *withheld verb*,
not a greyed button.

### Step badges

Each step's `<h2>` carries a badge stating where it stands. These exist and
their text is load-bearing:

| Step | LOCKED | PROVISIONAL | APPROVED |
|---|---|---|---|
| 1 | — | `N OF 4 SET` | `4 OF 4 SET` |
| 2 | `NOT RUN` | `N DESIGN LANGUAGES · N PROPOSED` | `N DESIGN LANGUAGES FOUND` |
| 3 | `NONE YET` | `N CAST · N UNCAST` | `N CAST · 0 UNCAST` |
| 4 | `NOT DRAFTED` | — | `SAVED · REV N` |
| 5 | `NEEDS A SAVED BIBLE` | — | `N SAMPLES` |

Badges are commentary and must never block the page if their fetch fails.

### Nothing is lost silently

Every user-authored text on this page — interview answers, standing notes,
question answers, the Bible itself — is expensive to retype. Saves are
**awaited**, failures are **stated**, and a failed save rolls the local
cache back so a reload cannot resurrect an answer the server never took.
This was a real user-caught failure: *"if I reload the page I can tell you
that stuff's going away. I don't know where."*

### Errors are never swallowed

A style library that fails to load and a library that is genuinely empty
look identical on screen. Every such fetch states its failure and names the
document it reads from.

### Amber is a signal

`--accent` marks the current pipeline stage, the one primary action in
view, and focus. Nothing else. On this page that is: the current rail chip,
the one primary button per step, and the unanswered-questions count. A
redesign that adds a fifth amber thing has broken the rule.

### Courier vs Archivo

Courier carries machine data — IDs, statuses, counts, timestamps, roles,
hashes, section names. Archivo carries hierarchy and prose — headings,
labels, sentences. A full sentence in Courier caps reads as a machine
warning; that is a mistake this codebase has made and corrected.

### Forbidden

No CSS framework, no new fonts, no new accent colours, no gradients, no
rounded corners, no emoji.

---

## 10. Data flow — what derives from what

```
screenplay ──► scan ──┬──► design languages ──┐
                      ├──► environments ──────┤
                      ├──► locations          ├──► BIBLE ──► every render prompt
                      ├──► subjects ──► cast ─┤              for the whole production
                      ├──► questions ─────────┤
                      └──► period, logline ───┤
                                              │
four style anchors (pictures + words) ────────┤
standing notes ───────────────────────────────┘
                                              │
saved BIBLE ──┬──► swatch proposals ──► step 1's palette column
              ├──► self-check report
              ├──► model test samples
              └──► UNLOCKS stage 03
```

**One direction that surprises people:** the anchors are upstream of the
Bible, but once the Bible is written it is the Bible that reaches renders.
Changing an anchor afterwards does *not* rewrite the document — the app
reconciles the two and states a clash rather than silently overwriting the
director's edits.

---

## 11. Backing endpoints

Given so the design agent knows what is cheap to read and what costs money.

**Free reads:** `/api/style-bible`, `/api/bible/sections`,
`/api/bible/house-style`, `/api/styles/{library}`, `/api/camera-recipes`,
`/api/references`, `/api/subjects`, `/api/wizard/analysis`,
`/api/wizard/interview`, `/api/wizard/samples`, `/api/cinematography/setting`

**Writes (free):** `PUT /api/style-bible`, `PUT /api/wizard/analysis`,
`PUT /api/wizard/interview`, `POST /api/subjects`,
`POST /api/references/swatch`, `POST /api/references/{id}/hero`,
`POST /api/references/{id}/rescope`, `POST /api/references/{id}/status`

**Model calls (these cost money):** `POST /api/wizard/analyze` (the scan),
`POST /api/wizard/draft-bible`, `POST /api/wizard/swatches`,
`POST /api/wizard/acts`, `POST /api/bible/self-check`,
`POST /api/wizard/samples/{provider}` (**two renders per call**)

Any control that triggers one of the last group must say so before it is
pressed.

---

## 12. Known problems worth solving in the redesign

Stated plainly rather than defended. These are the parts a designer should
feel free to rethink.

1. **The page is long and mostly linear.** Five steps in one scroll, and
   step 2's output alone can run to a logline, a period block, five tiles,
   a design-language list, an environment list, a full locations table and
   a question grid. The rail helps; it may not be enough.

2. **Step 2 does too much.** It is called "Script scene scan" but it owns
   design languages, environments, locations, subjects, open questions,
   period and acts — seven kinds of thing, four of which have their own
   review cycle. It may deserve to be more than one step.

3. **The anchor columns are four narrow cards carrying a lot.** A head, a
   badge, a two-line jurisdiction hint, an upload button, a words control,
   a thumb strip, and for two of them extra controls that travel into a
   modal. They are dense.

4. **Two anchors state themselves with a button, two with a text field.**
   Consistent in code, inconsistent to look at. Whether Color Palette
   should also have a catalogue is an open design question.

5. **Controls that travel into a modal and back** (`Never looks like`) are
   clever and hard to discover.

6. **The swatch ramp has no legend.** A hero swatch is double-width and
   nothing says so.

7. **The 41 uncanonized patterns** in `app/static/DESIGN_SYSTEM.md` include
   several on this page. That table is the review queue.

---

## 13. What must not change

Functionality is not to change as part of design work.

- Every endpoint, action, and data shape stays intact.
- The Bible's section headings stay exactly as written — they are parsed.
- The five steps' dependency order stays.
- The anchor roles (`WORLD_TEXTURE`, `COLOR_PALETTE`,
  `CINEMATOGRAPHY_STYLE`, `BOARD_RENDERING_STYLE`) and their jurisdictions
  stay.
- Existing CSS class names stay. `app.js` generates markup against them and
  the stylesheet deliberately preserves every one so styling and behaviour
  stay decoupled.
- Gates stay readable-as-state.

If the redesign needs a functional change to work, say so as a separate
recommendation rather than folding it into the design.
