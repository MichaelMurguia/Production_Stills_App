# Implementation plan v2 — getting the designed layouts into the app

**For the coding agent. Read `app/static/DESIGN_SYSTEM.md` first. Work top to
bottom; one task per commit.**

This plan follows a full read of `app.js` (2,226 lines). It maps every existing
feature into the new layouts — nothing is dropped, no endpoint or data shape
changes, every existing handler is preserved and re-parented.

## Why the app only got colors and fonts

The redesign replaced `styles.css` and `index.html`, but `app.js` generates most
of the DOM at runtime (`renderDashboard`, `openSpecEditor`, `renderBoardPanels`,
`renderCard`, `renderReferences`, `renderWizard`). The structure of every
data-driven region is still v1. These tasks restructure those functions' output.

## Feature inventory the layouts must carry (do not drop any)

Boards, per panel: model/size/aspect selects (3 providers incl. the ChatGPT
pipeline) · auto-attached style anchor badges · subject reference groups with
required-object pre-checking and the 14-image limit counter · **Preview prompt**
· **Draft prose** (editable prose → generate) · Generate with cancelable busy ·
candidate cards with warnings, model-notes `<details>`, timestamps.
Candidate actions: Approve · Reject (with reason) · Delete forever · purge all
rejected · ✂ Crop (region → new reference) · → Reference (promote) · 🖌 Repair
(paint-mask overlay, brush size, engine choice) · → Light study (derive a
geometry-locked board).
Boards, per sheet: derived panels (deterministic palette + generated materials)
· assembly (readiness badges, canvas size select, board gallery).
Spec editor: board types with conditional slugline fields (INT/EXT, location,
time-of-day, atmosphere) · per-panel light select from the Bible's atmosphere
catalog · weak-inference budget · scene paragraph · render intent · forbidden
elements · design-language / scene-lesson scope checkboxes with inference note ·
unresolved-questions report · AUTO-FILLED badge and drafted-by line · panel
allocation % · required-object chips with has-ref state and subject picker ·
Validate report · Approve & lock / Create revision / Unlock & edit.
References: lookbook/research grouping · approve / reject / reinstate / delete /
crop. Global: lightbox (zoom, pan, arrows) · cropper · repair overlay · busy
with cancel + elapsed · toasts.

---

## Task 1 — Dashboard: lead with the blocker, not the counts

`renderDashboard()` (~line 390).

`#dash-missing` currently renders `<h2>Missing dependencies</h2>` + a `<ul>` of
raw strings. Change it to one row per entry in `state.missing_dependencies`:
a kind badge, the text, and a resolving action button (`showView("specs")` etc.).
Derive the badge (`HOLD`/`GAP`/`SIZE`) from the string in one small mapping
function. When the list is empty, state the next stage action instead of "All
core dependencies satisfied" — a screen with no verb is not finished.
`#dash-cards` stays as-is in the sidebar; do not add a fifth card.

**NEEDS DATA:** if `missing_dependencies` is flat prose, render the string as-is
and note the gap. Never parse prose to fake structure.

## Task 2 — Evidence ledger: make HOLD readable

`addLedgerRow` (~1580). Every row already carries
`border-left: 2px solid transparent`. Set `borderLeftColor` from the status
select (`HOLD` → `var(--hold)`, `REMOVE` → `var(--bad)`) and tint non-PASS rows
`var(--panel)`. Hook the status select's `change` so the tint follows edits.
Do not touch the six-column grid.

## Task 3 — Spec editor: state why it cannot lock, keep every field

`openSpecEditor` (~1314). The editor's *content* is right and stays: subject,
mode, board type + conditional slugline fields (`updateSettingVis` logic is
untouched), weak budget, scene, intent, forbidden, scope checkboxes, panels,
ledger, report. Changes:

1. **Gate strip.** Under the `<h3>`, whenever the sheet is not lockable, render
   the CANNOT-LOCK strip (Courier amber label, reason, "Jump to first" button).
   Compute from the DOM: count HOLD rows whose object matches a panel's required
   objects — the same rule Validate applies, run continuously. Disable
   **Approve & lock** while the gate shows (`:disabled` styling exists). New CSS
   marked `/* UNCANONIZED */` + logged.
2. **Replace `panel.scrollIntoView(...)` at ~1445** (and the gate's jump) with
   `window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 80,
   behavior: "smooth" })`. `scrollIntoView` is banned project-wide.
3. **Group the form.** The `.grid-form` is one undifferentiated 2-column pour of
   13 fields. Split into three `.spec-section`s: *Identity* (subject, mode,
   board type, canvas), *Setting* (the four conditional slugline fields — keep
   their `data-setf` hooks), *Direction* (scene, intent, forbidden, weak
   budget). Same inputs, same IDs, same collect() — only grouping changes.
4. Keep the unresolved-questions report, AUTO-FILLED badge, drafted-by line, and
   the locked-state button pair (Create revision / Unlock & edit) exactly where
   they are semantically: badges in the `<h3>`, report directly below it.

## Task 4 — Boards: the judging room (largest task, split into 4 commits)

`renderBoardPanels` (~1889) + `renderCard` (~1773). Today each panel is a
stacked `.panel` containing spec recap, reference pickers, generation row, and a
`.ref-grid` of equal-size candidate cards — reading a render means scrolling
a wall of equal-weight blocks.

Target: three-region layout per the design (`3b`), as one flex row inside
`#board-panels`:

**4a — Left rail (~230px): panel list.** One entry per `spec.panels`: latest
candidate thumbnail, panel ID (Courier), readiness dot (green = approved
candidate, amber = candidates but none approved, red = latest approved candidate
carries a size warning, hollow = no candidates). Clicking selects; store the
selection so `renderBoardPanels` re-renders into the same panel. Below the list:
the derived-panels entry (PALETTE / MATERIALS) and the assembly entry with its
readiness count — clicking them shows those sections in the center. The rail
replaces today's vertical stack as navigation; nothing is removed.

**4b — Center: the selected panel's stage.** Top strip: panel ID chip, title,
purpose, allocation %, required/forbidden (Courier, `--ink-faint`). Then the
**current candidate** (newest, or newest approved) at the largest size that
fits, on `--field`. Status label on the left under the image; the action group
on the right — all existing `renderCard` actions for that candidate, unchanged
handlers: Approve (the screen's only amber) / Reject / Repair / Crop /
→ Reference / → Light study / Delete forever. Warnings and the model-notes
`<details>` render under the image, not beside it. Below: the takes filmstrip —
every candidate for this panel as a small thumb, rejected at `opacity:.45`
(image only) with the reason on its tooltip; clicking a thumb makes it the
staged candidate; lightbox still opens on the staged image click.

**4c — Center, below the filmstrip: the generation bench.** The existing
`.gen-row` (model/size/aspect selects, Preview prompt, Draft prose, Generate)
moves here unchanged, including the prose textarea flow, the report host, the
cancelable busy, and the purge-rejected control (move purge next to the
filmstrip since that is what it purges). The subject reference groups + style
anchor badges + 14-image counter also live here, directly above the Generate
button, since they are generation inputs — same checkboxes, same
`checkedRefs()`.

**4d — Right rail (~300px): provenance of the staged candidate.** All Courier,
`--ink-dim`: model, `width×height`, image_size/aspect, created_at, attached
reference IDs, and the carried warnings. Populate from fields already on the
candidate object (`c.model`, `c.width`, `c.references`, `c.warnings`,
`c.created_at`) — **no new data needed.** When the staged item is an assembled
board, show `panels_used` instead.

Derived panels and assembly keep their existing controls and galleries; they
render in the center when selected in the rail, with the same buttons, busy
hosts, and handlers.

New layout CSS (`.board-rail`, `.board-stage`, `.board-side`) — mark
`/* UNCANONIZED */` and log all three as one pattern row: "judging room layout".

## Task 5 — References: keep the grouping, structure the card

`renderReferences` (~1088). The lookbook/research group headers already exist —
keep them. Card changes only: render `controls:` / `does not control:` as the
two-line Courier jurisdiction block from the design (`CONTROLS …` in `--ok`,
`NOT …` in `--bad`) instead of two grey meta lines. Keep approve / reject /
reinstate / crop / delete exactly as wired, including `.ref-card.REJECTED`
image-only dimming.

## Task 6 — Wizard: step-state badges

`renderWizard()` (~562). Template already has the numbered step spine. Add a
state badge to each step `h2` from data already fetched: step 1 anchor counts
per role, step 2 `wizAnalysis`, step 3 `/api/subjects`, step 5 saved bible,
step 6 samples. Existing `.badge` classes only. Do not restructure the subject
cards, world chips, or bake-off columns.

## Task 7 (optional, ask the user first) — replace native dialogs

Reject reasons, promote role/notes/controls, and crop roles all use browser
`prompt()`; destructive confirms use `confirm()`. Functionally fine, visually
v0, and `prompt()` caps you at one field per question. A single small styled
modal helper (title, fields, confirm/cancel, `--panel2` on `--bg` scrim) would
replace all of them without changing any endpoint. This is the one task that
touches many call sites — do it last, in one commit, only with the user's
go-ahead.

---

## Ground rules

- One task per commit (Task 4 = four commits: rail, stage, bench, side).
- Tokens only; no new hex, grey, or radius. Amber ≤ 1 per screen.
- Machine values Courier, prose Archivo.
- Reuse classes; new patterns get `/* UNCANONIZED */` + a table row.
- Never `scrollIntoView` — and remove the one existing use (~1445).
- No endpoint, action, or data-shape changes. If a task appears to need one,
  stop and report.
- After each task, verify the feature inventory above still all works.

Visual reference: `design_mocks/` in this repo — one PNG per screen:
`1a-dashboard`, `2a-production-design`, `3a-breakdowns`, `3b-boards-judging`,
`4a-screenplay`, `4b-board-assembly`, `4c-research`, `4d-settings`. Read the
relevant PNG before starting its task. The generation bench, repair/crop
overlays, derived panels, and light-study flow have no dedicated mockups — keep
their existing internals and place them per this plan; ask the user for a
mockup if a layout decision feels ambiguous.
