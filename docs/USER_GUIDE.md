# Screenboard Studio — User Guide

*Working draft toward the full manual. Current as of 2026-07-29 (plan v3 UI,
C1–C15). Everything here describes shipped behavior, verified against the
running app.*

---

## 1. What this app is

Screenboard Studio builds **canon-locked art direction boards** for a
screenplay: native-4K production walls assembled from individually generated
panels, each panel justified by screenplay evidence and anchored to approved
reference images.

The failure mode it exists to prevent: image models **reinterpreting approved
work**. Once you approve something, the system makes drift structurally
difficult — approved specs are hash-locked, approved references have fixed
jurisdictions, every render re-anchors to approved canon instead of extending
an edit chain, and nothing is ever upscaled.

The engine is project-agnostic. Project content lives in the Art Direction
Bible and the data folder, not in code — *The Beltminers* is the proving
project.

You are the Production Designer. The app is your art department: it
researches, drafts, renders, and files paperwork — but **nothing becomes
canon without your approval**, and every approval is journaled.

## 2. The mental model

**The pipeline is strictly sequential** and the navigation band *is* the
pipeline:

> 01 SCREENPLAY → 02 PROD. DESIGN → 03 BREAKDOWNS → 04 PANELS → 05 BOARDS

Later stages are gated on earlier ones: only a saved Bible gives renders
their language; only a **locked** breakdown sheet can generate panels; a
board assembles only from **approved** panels. Gates are always shown as
state (a disabled button with its reason beside it), never sprung as errors.

Core vocabulary:

| Term | Meaning |
|---|---|
| **Reference** | An image in the library with exactly one **role** — its jurisdiction. `CHARACTER_LIKENESS — JOHN STANNER` controls John's face and build, *not* his costume or lighting. References are PROVISIONAL until approved; approved ones are **canon anchors**. |
| **Style anchors** | Three special role families: `BOARD_RENDERING_STYLE` (how panels are painted), `CINEMATOGRAPHY_STYLE` (how the film is photographed), `BOARD_LAYOUT_STYLE` (how a finished board is laid out). The first two auto-attach to **every** generation, style-only; the third governs assembly grammar and never enters a panel render. |
| **Breakdown sheet** (specification) | The brief you'd give a concept artist, written down and enforceable: subject, board type, slugline setting, scene paragraph, render intent, panels, forbidden elements, and the evidence ledger. Sheets are DRAFT until **approved & locked**. |
| **Evidence ledger** | One row per visible object, saying why it may exist: the evidence class (screenplay-explicit → user-directed → weak inference), the cited quote or source, and a state — PASS renders, HOLD blocks the lock, REMOVE marks for removal. |
| **Spec hash** | Locking a sheet mints a content hash. Every candidate records the hash it was generated against — the audit trail of *exactly what brief* produced *exactly what image*. |
| **Candidate / take** | A generated render. Always `CANDIDATE — UNAPPROVED` until you judge it. Rejected takes stay on file (dimmed) as a record, with your reason carried into future prompts as rejection feedback. |
| **Board** | The assembled 4K wall. Itself a candidate needing your approval; once approved it can be promoted to a `SCENE_REFERENCE` so future renders anchor to it. |
| **Lessons** | Standing project-wide rules (Settings on the Production Design page) injected into every prompt. Rejection reasons feed panel-scoped feedback automatically. |
| **Prohibited inventions** | The never-render list, seeded from rejection history, enforced on every board. Shown on Status. |

## 3. Reading the screen

**Header** — project name, two **engine dots** (credentials only: filled
green = key saved, blue = environment variable, hollow = none; never a fake
"connected"), and the three tools: **Status · Research · Settings**.

**The band** — five stages, each cell showing a live status subline
("2 locked · 1 draft", "11 approved of 26"). The top border tells you where
things stand: **green** complete, **amber** the current stage (the one you're
viewing, otherwise the work frontier), **red** carrying a blocker, grey not
reached. The `HERE` chip marks the stage you're standing in.

**Status** (the landing page) — leads with **DO THIS NEXT**: the single next
action, which is always the first blocker when anything blocks. Below it,
the **Blocking** list — every obstacle as a row with a kind badge and a
resolving jump:

| Kind | Meaning | Resolve |
|---|---|---|
| `HOLD` | Required objects on a draft sheet lack PASS evidence rows | Review the sheet's ledger |
| `GAP` | A missing input — no screenplay, no approved Master Board, a subject with no approved reference | Add the missing piece |
| `SIZE` | An approved render is smaller than its board slot | Regenerate larger — never upscaled |
| `CITE` | A cited quote no longer exists in the current screenplay draft | Review the flagged rows |

The sidebar carries library counts, the **Recent** feed (from the activity
log, newest first), and the prohibited-inventions chips.

## 4. Stage 01 — Screenplay

The root dependency gets its own room.

- **The coverage table** ("what the script gave us"): every location the
  deterministic slugline parser found, with scene count and a **detail
  meter** — four segments; green segments show how much the script actually
  describes; a single amber segment means *thin* — a breakdown here will
  lean on inference, and inference is budgeted. Locations already covered by
  a sheet show its LOCKED/DRAFT chip (with a held-row count when evidence
  blocks the lock); uncovered ones offer **Draft a sheet**, which jumps to
  Breakdowns with the location pre-filled.
- **The file card**: size, SHA-256, upload time, and what the read produced.
  **Downstream of this file**: design languages, sheets, cited evidence
  rows, approved panels — everything hanging off this exact draft.
- **Replacing the draft**: upload a new file any time. Approved work is
  never invalidated. Instead, every quoted citation on every sheet is
  **re-searched in the new text**; quotes that vanish surface as CITE
  blockers and in the Broken Citations panel here — for *your* review.
  Nothing is auto-corrected; locked sheets are immutable by canon rule.

Accepted formats: PDF, FDX, Fountain, TXT. (PDF text extraction is used for
the coverage map and citation check; an image-only PDF disables those two
features but nothing else.)

## 5. Stage 02 — Production Design

Six steps produce the **Art Direction Bible** — the locked lookbook every
render obeys. Each step's header badge states where it stands.

1. **Style reference images** — the three anchors, one column per role, each
   stating its jurisdiction (`CONTROLS … / NEVER …`). Files upload approved.
2. **Read the screenplay** — the research model proposes the project's
   **design languages** (distinct visual cultures: factions, eras,
   technology families). Confirm, rename, or drop; each becomes a Bible
   section selectable per sheet. The analysis locks after a successful run;
   unlock to re-read.
3. **Cast & key subjects** — recommended subjects become title cards (name,
   epithets, traits from the script). Photos uploaded into a card enter the
   library approved under the card's role (e.g. `VEHICLE_GEOMETRY — GT40`).
4. **Interview** — touchstones, medium, palette, never-list. Blanks come
   back marked (PROPOSED).
5. **Draft & review** — the model writes the Bible in the app's section
   schema; you edit and save. Saving increments the **REV** counter shown on
   the editor and the band.
6. **Model bake-off** — the same brief to every engine; pick a default.

The Bible is data-driven: any non-system `##` section is a design language;
a `Keywords:` line sets its auto-match triggers. Sheets carry an explicit
**Art direction scope** (checkboxes) choosing which design languages and
scene lessons apply — keyword inference is only the fallback. The Bible's
Drift Prevention Rule is enforced on the prose rewriter, which acts as the
Art Direction Guardian.

## 6. Stage 03 — Breakdowns

**Drafting.** Describe the board ("Charlie's cabin — the workshop scenes
with the GT40") and **Run breakdown**: the research pass reads the whole
screenplay and drafts the sheet — panels, objects, and an evidence ledger
where **every claim cites its source** and unknowns are left honest (HOLD).
Or create a blank sheet and write it yourself. Two modes:
`CANON_EXTRACTION` (official board — strict evidence, tight weak-inference
budget) and `DESIGN_EXPLORATION` (the screenplay is silent; pitch options —
everything is proposed-not-canon until you promote a winner).

**The editor.** Three sections — *Identity* (subject, mode, board type,
canvas), *Setting* (the slugline: INT/EXT, location, time of day,
atmosphere — fields follow the board type), *Direction* (the scene
paragraph, render intent, forbidden elements, weak-inference budget) — then
panels and the ledger.

**Board types** govern slugline discipline: SCENE (one scene, one hour for
all panels), LOCATION (a place across times — light chosen per panel),
ASSET (no slugline; neutral presentation), LIGHTING_STUDY (derived,
geometry-locked), MASTER (presentation grammar).

**Panels.** Each answers one production question (its Purpose), carries
required/forbidden objects and a board-allocation %. Adding a required
object auto-creates its `USER_DIRECTED / PASS` ledger row; green chips mean
reference material exists for that object. The cast picker adds subjects
directly.

**The ledger** reads `ID · Object · Source · Cited evidence · State`.
HOLD rows carry a blue left edge, REMOVE red; non-PASS rows tint darker.
Auto-fill deliberately marks weak inferences HOLD — **the model may not
promote its own guesses**. Read the citation; if you agree, set PASS
yourself (you are the evidence: `USER_DIRECTED`).

**The lock gate.** While anything would fail approval, a `CANNOT LOCK`
strip under the title lists each failing condition — required objects
lacking a PASS row (missing, HOLD, and REMOVE all block), allocation ≠
100%, empty citations, weak budget exceeded — with **Jump to first ↓**, and
**Approve & lock** stays disabled. These are the same rules the server
enforces; the strip just tells you before the button does.

**After locking**: locked sheets are read-only. **Create revision** copies
into a new numbered sheet (the approved version stays as history);
**Unlock & edit** voids the approval (journaled) — and is refused while any
approved candidate or board depends on the sheet. **Delete** removes a sheet
and all its takes, with the same canon guard.

## 7. Stage 04 — Panels: the judging room

Pick a locked sheet; the room has three regions.

**Left rail** — the sheet block (LOCKED · CAN GENERATE), the panel list with
latest-take thumbnails and a readiness mark per panel: green dot = approved
take ready · amber count = takes exist, none approved · red `SIZE` = the
approved take is too small for its slot · `—` = no takes. Below: the
DERIVED entry (palette & materials) and the pointer to assembly.

**Center — the stage.** The panel's question on top (with its allocation %,
role, and aspect), then the **staged take** at full width. Under it:

- the status chip, and the primary actions — **Reject** (asks your reason;
  it is recorded verbatim and carried into this panel's future prompts),
  **→ Reference** (disabled until the take is approved), and **Approve
  panel** — deliberately the only amber on the screen.
- the ghost row — **Repair region**, **Crop → reference** (approved takes
  only; crops enter the library as approved canon), **→ Light study**
  (approved only), and **Delete forever** (rejected takes only).
- warnings, the rejection reason if any, and the model-notes/rewritten
  prompt under a disclosure.

**The takes filmstrip** — every take for this panel; rejected ones dim
(image only) with the reason on hover; click any thumb to stage it. The
purge button (delete all rejected, forever) lives here.

**The generation bench** — model / size / aspect selects, **Preview prompt**
(the exact compiled prompt, free), **Draft prose** (GPT-5.6 rewrites the
spec into editable render prose; *Generate from this prose* sends your
edited text verbatim and archives it with the candidate), and **Generate
candidate** — deliberately *not* amber; approval keeps that budget. Style
anchors auto-attach; subject reference groups pre-check when they match the
panel's required objects; the Courier counter tracks the 14-image limit.

**Right rail — provenance of the staged take.** THIS RENDER (model, pixel
size, run time, spec hash), ANCHORED TO (the exact references attached),
COMPILED PROMPT (excerpt, with Full), and CARRIED REJECTIONS — this panel's
rejected takes and your reasons, i.e. what the next prompt already knows.

### Region repair (M7)

**Repair region** opens the take full-screen: paint over the area to fix,
describe the change, and pick the engine —

- **GPT Image 2 — true masked edit**: pixels outside your paint physically
  cannot change.
- **Gemini — guided edit**: Gemini has no mask API, so it receives the
  source plus a magenta-highlighted guide copy with strict region-only
  instructions. It can drift slightly outside the region — but it is a
  different painter when one engine keeps failing.

The result is a **new take** in the strip (`kind: repair`); the original is
untouched. Subject identities mentioned in your instruction are injected
into the repair prompt automatically.

## 8. Stage 05 — Boards: assembly

**The slot map** shows the exact assembler geometry on a true 4K canvas
before you spend anything: each slot with its panel ID, allocation, and a
verdict — `OK` · `UNAPPROVED` · `TOO SMALL` (the approved render would need
upscaling, which never happens — regenerate larger) · `NO CANDIDATE`. The
title and canon blocks are marked APP-DRAWN: all board typography is drawn
by the app, never by the model.

**Layout variants** — `DEFAULT` (the sheet's allocation; largest leads) ·
`GRID` (all panels equal — the comparison grammar; lighting studies are
always grid) · `HERO P0x` (lead with any panel). Layout is **presentation
grammar, not canon** (director's ruling, 2026-07-29): the chips redraw the
slot map live, the chosen variant is recorded on the board record, and the
locked sheet is never touched.

**Assemble 4K board** enables when every slot reads OK. Canvas choices: 4K
UHD, DCI-flavor wide, print-leaning. The result is a BOARD CANDIDATE —
judge it like any take; approve it, then **→ Reference** promotes it as a
`SCENE_REFERENCE` and future renders anchor to it. That is how consistency
tightens over time without drifting.

**Derived panels** (from the judging room's rail): **Derive palette** —
dominant colors *measured* from the approved panels' pixels, no AI, zero
drift; **Derive materials** — a generated close-up strip whose only allowed
sources are the board's own approved panels. Both land as candidates; both
can join the board as a bottom strip.

## 9. Research — the reference library

Filter chips: `ALL · STYLE · SUBJECT · SCENE` with counts; status counts on
the right. Each card states its jurisdiction as one block — `CONTROLS face ·
hair · build` in green, `NOT costume · light · lens` in red — plus usage:
`AUTO-ATTACHED · ALL RENDERS` for style anchors, `USED IN n RENDERS`
otherwise.

Approve → canon anchor. **Reject quarantines the file from the pipeline**
(it physically moves to quarantine and can never be attached) — and
**Reinstate** returns it to provisional review; the card shows the rejection
date and reason meanwhile. Delete is forever and journaled. **Crop** any
approved image to harvest a region as a new narrow-role reference.

## 10. Settings

- **Engines & keys** — a card per engine: Gemini (`gemini-3-pro-image`),
  OpenAI (`gpt-image-2`), and the **ChatGPT pipeline** (GPT-5.6 rewrites the
  spec into render prose under zero-invention rules, then calls the same
  image model ChatGPT uses — runs on the OpenAI key, no separate
  credential). Status chips are honest: CONNECTED appears only after *your*
  Test passed, otherwise KEY SET / ENV VAR / NO KEY; LAST TEST shows
  PASS/FAIL and when. Note: OpenAI flags output above 2560×1440 as
  experimental — prefer Gemini for 4K.
- **Default engine** — GEMINI / GPT IMAGE 2 / PIPELINE; pre-selected in
  every Model dropdown, always overridable per render.
- The footer states the privacy facts: everything lives in `data/`; the
  approval record is `project_state/approval_log.md`; nothing leaves the
  machine except generation calls.

## 11. Canon guarantees enforced in code

- Unsupported objects can never pass validation (`unsupported_max` = 0).
- Approved references have locked roles; rejected ones are quarantined on
  disk.
- Approved sheets are hash-locked; candidates record the hash they were
  generated against.
- **The upstream promise**: nothing upstream of an approval can change. A
  sheet with approved candidates or boards refuses unlock and deletion; to
  edit anyway, create a revision or first reject that output (an explicit,
  journaled act of destruction).
- Renders are never upscaled — a too-small panel is flagged, not stretched.
- Citation re-checks report; they never mutate a sheet.
- Every approval, rejection, and deletion is journaled
  (`project_state/approval_log.md`, `rejection_history.md`).

## 12. Where everything lives

| Path | Contents |
|---|---|
| `data/references/` | Library originals, thumbnails, quarantine, index |
| `data/screenplay/` | The current draft |
| `data/specs/` | Sheet JSON + `locks.json` |
| `data/boards/<SHEET>/` | Candidates (`CAND-*.png/json`) and boards (`BOARD-*`) |
| `data/settings.json` | API keys, default engine, engine test results |
| `data/subjects.json` | Cast & subject title cards |
| `data/wizard_analysis.json` | The screenplay read |
| `data/activity_log.jsonl` | The flight recorder — every mutating action, rejection reason, and error, timestamped (secrets redacted) |
| `data/citation_report.json` | Latest citation re-check |
| `context/01_ART_DIRECTION_BIBLE.md` | The Bible (also editable in-app) |
| `project_state/` | Approval log, rejection history, prohibited inventions |

The command-line validators in `scripts/` are the same code the app calls.

## 13. Recipes

**Start a new project** — Upload the screenplay (01) → wizard steps 1–6
(02) → draft and lock the first sheet (03) → generate and judge (04) →
assemble (05) → approve the board and promote it to a reference.

**Fight a wrong detail** (e.g. the GT40) — Reject with a *specific* reason
(it feeds the next prompt) → attach tighter geometry references →
regenerate; if the frame is right but the detail is wrong, **Repair region**
and try the other engine when one keeps failing → the winning take gets
approved and its crop harvested as a reference so the fight never repeats.

**New screenplay draft** — Upload on 01; read the toast; review any broken
citations; decide per row whether the sheet still holds.

**Same brief, different painters** — Lock once, generate the same panel with
each engine, compare in the filmstrip; every take records its model.

**Lighting study** — Approve a panel → **→ Light study** → a geometry-locked
draft sheet appears on 03 with one panel per approved atmosphere → trim,
lock, generate. Same place, same camera — only the light changes.

## 14. FAQ

**Why can't I generate?** Only locked sheets generate. The CANNOT-LOCK
strip on the sheet lists exactly what's missing.

**Why is a row on HOLD?** Auto-fill refuses to promote its own guesses.
Read the citation; if you agree, set PASS yourself.

**What does a render cost?** Each is a paid API call on your key — rejected
takes cost the same as approved ones. That is why validation runs *before*
generation, and why the slot map exists.

**2K or 4K?** Iterate at 2K; regenerate final picks at 4K. Hero slots suit
4:3/3:2; strips suit 16:9/21:9. The slot map tells you when a take is too
small for its slot.

**Can I rearrange a board without touching the locked sheet?** Yes — layout
variants at assembly. Presentation, not canon; recorded on the board record.

**Where does my rejection reason go?** Onto the take's record, into the
rejection history, and into the panel's future prompts as rejection
feedback. Write it like a note to a concept artist.

**Does anything leave my machine?** Only generation/analysis calls to the
provider whose key you saved. Everything else is local files you can read.
