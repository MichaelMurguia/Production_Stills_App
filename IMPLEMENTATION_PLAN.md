# Implementation plan v3 — final. Supersedes v2.

**For the coding agent.** Written against `DESIGN_HANDOFF.md` and the
2026-07-29 baseline (main @ 7108dcd: nine new read-only endpoints, layout
variants, the four uncanonized patterns). Every open decision in the handoff
§3 is resolved below — all ten recommendations are **accepted**, with the
adjustments noted. v2's tasks 1–6 are carried forward inside the build order.
One task per commit.

---

## Part A — Canonizing the four patterns (fold into DESIGN_SYSTEM.md, clear the table)

These shipped well. Canonical form, so they stop being provisional:

1. **Blocking rows** (`.block-row`, `.block-kind`). Canonical: the row grid is
   `badge · text · action`, badge column fixed-width (52px, Courier 9.5–10.5px,
   bordered in its status color, never filled), rows separated by
   `--line-soft` top borders, action is a text-colored amber link-button, not
   a bordered button. The DO-THIS-NEXT lead (`.next-*`) is the first blocking
   item promoted into the `.panel-lead`: Courier amber kicker, one-line verb
   headline (Archivo 600, ~21px), one supporting sentence max, primary button
   right. Merge rule: DO-THIS-NEXT is a presentation of `blocking[0]`, never a
   second list.
2. **Recent feed** (`.recent-row`, `.recent-ts`). Canonical: timestamp column
   flex-none Courier `--ink-faint`, text Archivo 13px `--ink-dim`, IDs inside
   the text in Courier `--ink`. No icons, no dots, no dividers — the timestamp
   column is the rhythm.
3. **Coverage meter** (`.loc-meter`). Canonical: 4 segments, 11×4px, 3px gap;
   filled = `--ok`; a single amber first segment means "thin — inference will
   be spent here"; empty = `--line-soft`. This is the project's only meter
   vocabulary — reuse it anywhere "how much support exists" appears (e.g. the
   canon budget), rather than inventing bars.
4. **Slot map** (`.slotmap`, `.slot`, `.slot-verdict`). Canonical: slots on
   `--bg2` inside a `--line` frame with 10px gutters; each slot carries its
   panel ID chip top-left and verdict chip bottom-right (status-color border,
   never filled); TOO-SMALL slots tint border + text `--bad` with the
   `--bad-line` border; title/canon blocks are labeled `APP-DRAWN`. The slot
   map is read-only geometry — actions live outside it.

Move each from the uncanonized table into the proper DESIGN_SYSTEM.md
sections (Components / Layout patterns), delete the table rows, changelog it.

## Part B — Decisions (handoff §3, all accepted; adjustments in bold)

1. **Nav**: numbered stage band from 1a/2a/3a, persistent everywhere;
   `01 SCREENPLAY · 02 PRODUCTION DESIGN · 03 BREAKDOWNS · 04 PANELS ·
   05 BOARDS` + gap + `Status · Research · Settings`. Status = landing view.
   Sublines from `stage_summary`; `HERE` chip = active view; stage top-border:
   `--ok` complete, `--accent` current, `--line` not-reached, `--bad` only if
   the stage carries a blocker. Discard 3b/4b/4c/4d header variants. **Use
   `PROD. DESIGN` if the label overflows its `minmax(0,1fr)` track.**
2. **Five-stage IA ships now.** Screenplay stage = coverage table +
   citation report + file card + upload (re-parented from dashboard). 04 =
   judging room (v2 Task 4 verbatim, plus B-adjustments below). 05 = assembly
   + slot map. Dashboard content becomes Status.
3. **Engines**: three cards in Settings (pipeline card annotated "uses the
   OpenAI key", key controls read-only there); header dots stay two
   (credentials: `--ok` saved, `--hold` env, hollow none; no polling);
   default toggle has all three; show `last_test` PASS/FAIL + date on cards.
4. **Candidate actions**: primary group beside the staged render = **Approve
   panel** (amber, relabeled from "Approve") · Reject · → Reference; ghost
   secondary row directly beneath = 🞂 Repair · ✂ Crop · → Light study ·
   Delete forever (danger; **only rendered when the staged candidate is
   REJECTED**, as today's logic already does). No overflow menus.
5. **Reference chips**: ALL default; STYLE = BOARD_LAYOUT_STYLE,
   BOARD_RENDERING_STYLE, CINEMATOGRAPHY_STYLE; SCENE = SCENE_REFERENCE,
   LOCATION_GEOMETRY; SUBJECT = everything else. Counts client-side; the
   lookbook/research group headers remain inside filtered results. `used_in`
   renders as Courier `USED IN n RENDERS`, `--ink-faint`, only when n > 0.
6. **Reject copy**: "Rejecting quarantines the file from the pipeline;
   Reinstate returns it to provisional review." Keep Reinstate.
7. **Gate rule**: CANNOT-LOCK counts **required objects lacking a PASS row**
   (missing/HOLD/REMOVE all block). Prefer the backend `evidence_gaps()` if
   exposed; otherwise mirror client-side. Strip lists each distinct failing
   validate condition (PASS gaps, allocation ≠ 100, empty sources, weak
   budget) as its own line; "Jump to first" targets the first PASS-gap row
   (no `scrollIntoView` — the `window.scrollTo` recipe from v2). Approve &
   lock disabled while gated.
8. **Real ID formats everywhere**: `CAND-0026`, `REF-0007`, `OBJ-003`, `P01`.
   LOCKED badge ⇔ spec status APPROVED; DRAFT/REVIEWED render as DRAFT.
9. **Bible REV badge**: style it where 2a shows it — Courier, bordered,
   `--ink-faint`, `REV n` from `/api/style-bible.rev`.
10. **Ledger stays editable** (disabled-when-locked as today). Adopt mock 3a's
    reading order via header labels: `ID · OBJECT · SOURCE · CITED EVIDENCE ·
    STATE` where SOURCE = the `evidence_class` select and CITED EVIDENCE =
    the free-text `source` input. Task 2 tinting applies (inline style or
    `.flagged` class so it beats the zebra rule).

**Product rulings honored:** layout is presentation grammar — mock 4b's
"Change layout" is the **variant picker** (`default | grid | hero:<panel>`)
driving `slot-map?variant=` previews live, variant recorded at assemble, the
locked sheet untouched; never upscale; citation re-check is report-only —
CITE blockers surface in Status/screenplay, copy never promises mutation.

## Part C — Build order (one commit each)

- **C1 Nav band + view split.** Five stages + tools, sublines from
  `stage_summary`, HERE chip, engine dots, Status as landing. New
  `screenplay` and `assembly` views extracted (move, don't rewrite).
- **C2 Status view.** DO-THIS-NEXT + blocking (Part A.1 canonical form,
  including CITE blockers), recent feed, library counts, prohibited chips.
  Counts cards stay in the sidebar.
- **C3 Screenplay stage.** File card (sha256 first 8, size, uploaded, read
  summary), DOWNSTREAM counts, coverage table (Part A.3 meter), citation
  report panel (report-only copy), upload + REPLACE copy: "A new draft does
  not invalidate approved work — broken citations surface as CITE blockers
  for your review."
- **C4 Ledger** (v2 Task 2 + B10).
- **C5 Spec editor** (v2 Task 3 with B7 gate; three-section grouping;
  scrollIntoView removal).
- **C6–C9 Judging room** (v2 Task 4a–d with B4 action placement; right-rail
  provenance includes ANCHORED-TO reference IDs and CARRIED REJECTIONS =
  this panel's rejected candidates' reasons, from data already fetched).
- **C10 Assembly view.** Slot map (Part A.4) + variant picker + canvas select
  + Assemble (disabled until every slot OK) + board gallery.
- **C11 References** (v2 Task 5 + B5/B6; jurisdiction block `CONTROLS …` in
  `--ok` / `NOT …` in `--bad`).
- **C12 Settings** (B3).
- **C13 Wizard badges** (v2 Task 6 + B9 REV badge). The 2a left-rail spine
  remains Phase 2 — do not build.
- **C14 DESIGN_SYSTEM.md canonization pass** (Part A) — may also ride along
  incrementally with C2/C3/C10.
- **C15 (optional, ask first)** native-dialog replacement (v2 Task 7).

## Ground rules

v2's rules stand (tokens only; amber ≤1/screen; Courier for machine data;
no class renames; no `scrollIntoView`; verify the v2 feature inventory — with
Repair's line updated to "paint-mask overlay, brush size, engine choice" —
after every commit). Data rule, restated per the handoff: **the §1 handoff
endpoints exist and are the whole budget; anything beyond them stops and
reports.**

Precedence when sources disagree: this file > DESIGN_SYSTEM.md > mocks >
existing code. Mocks are layout intent, not pixel contracts — real IDs, real
statuses, three providers, and Part B override anything a mock shows.
