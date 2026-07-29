# Discrepancy report — `design_mocks/` vs `IMPLEMENTATION_PLAN.md` v2

**From the coding agent, for Claude Design.** Purpose: everything below is a
gap, conflict, or open question between the eight mocks, the written plan, and
the shipped code. Nothing here is a complaint — the mocks are the strongest
statement yet of what this product should feel like. But the plan implements
a subset of them, and several mock elements assume data or features that do
not exist. Plan v3 should resolve each item: adopt it (with a task and, where
needed, a data note), defer it (marked as a later phase), or cut it.

Every claim below was verified against the code as of 2026-07-29
(`app/static/app.js` ~2,236 lines — the plan's line anchors are still accurate
within ±10).

---

## 1. The headline gap: information architecture

The mocks depict a **five-stage pipeline** that the plan does not build:

| Mocks | Plan / current app |
|---|---|
| `01 SCREENPLAY · 02 PRODUCTION DESIGN · 03 BREAKDOWNS · 04 PANELS · 05 BOARDS`, each stage with a live status subline (`2 locked · 3 drafts · 1 blocked`), a `HERE` chip, engine health dots in the header | Four nav stages (`01 Dashboard · 02 Production Design · 03 Breakdowns · 04 Boards`) + Research + Settings after the gap. No task renames, renumbers, or adds sublines to the nav. |
| No Dashboard tab — the dashboard *is* the landing surface under the band (1a) | Dashboard is stage 01 |
| Screenplay promoted to its own stage 01 (4a: "Promoted out of the dashboard. The root dependency deserves its own room.") | Screenplay is a panel on the Dashboard |
| Boards split into **04 Panels** (judging room, 3b) and **05 Boards** (assembly, 4b) | One Boards tab; Task 4 builds the judging room inside it, assembly stays a section within it |

**Needed in v3:** either new tasks covering the IA change (nav rebuild, view
re-mapping, stage-status sublines — see §4 for the data those sublines need),
or an explicit statement that mocks 1a/4a/4b nav chrome is a later phase and
tasks 1–7 build into the current four-stage nav.

## 2. The mock set itself shows three different navigation schemes

- **1a / 2a / 3a:** the numbered stage band with sublines; Settings top-right.
- **3b / 4b:** no band at all — header carries a text label (`STAGE 04 —
  PANELS`, `STAGE 05 — BOARD ASSEMBLY`).
- **4c / 4d:** plain text tabs `Status · Pipeline · Research`.

`DESIGN_SYSTEM.md` calls the pipeline band "the product's spine." Which of the
three is canonical, and does the band persist on every screen? The coder
cannot pick this; v3 must.

## 3. Mock screens with no corresponding task in the plan

**4a — Screenplay stage.** The locations table (slugline × scene count ×
detail meter × sheet link) requires **screenplay scene parsing that exists
nowhere in the backend**. The wizard's analysis captures `key_locations` as a
flat name list — no scene counts, no coverage scoring. Bigger: the REPLACE
panel promises *"page citations on existing sheets are re-checked and flagged
where they no longer match."* The current data model cannot do this — evidence
`source` is deliberately free text; the spec editor's own tooltip states
"nothing looks it up." Either cut that promise or spec a real mechanism (it is
a substantial feature). The right-column facts (sha256, size, uploaded-at,
downstream counts) are all available or computable.

**4b — Assembly slot map.** Per-slot verdicts are computable today (layout
allocations live on the spec; candidate dimensions on the candidate;
`assemble.py` already flags smaller-than-slot panels at assembly time) — but
the *pre-assembly* slot-map preview is a new component with no task. Also:
**"Change layout" is not an existing feature.** Layout lives inside the locked
spec; changing it today means Unlock/Revise → edit → re-approve. A layout
picker needs a defined workflow (and probably plan permission to touch a spec
field post-lock — currently forbidden by design).

**4d — Settings.** Engine cards with POWERS/billing copy, key-source chips
(`CONNECTED` / `ENV VAR` — knowable from settings), default-engine toggle
(exists as `preferred_provider`). No task covers this restructure. See §4.1
for the provider-count problem.

**1a — Dashboard extras beyond Task 1:**
- The BLOCKING rows (`HOLD` held-evidence count per sheet, `GAP` missing
  geometry reference, `SIZE` undersized panel) do not exist in `/api/state` —
  it returns exactly **two fixed prose strings** (screenplay missing, Master
  Board #001 missing) built in `app/main.py:84-89`. Task 1's own NEEDS-DATA
  note anticipated this; the mock needs the richer state.
- The RECENT feed: `data/activity_log.jsonl` records everything needed, but
  **no read endpoint exists**.
- Engine health dots: the only connectivity check is an on-demand POST
  (`/api/settings/test`); there is no passive health state.

**2a — Wizard extras beyond Task 6:** the DOCUMENTS rail, and the
"Art Direction Bible `REV 3`" badge — **the bible has no revision tracking**
(it is a single markdown document; only specs have `revision`). Add tracking,
or drop the badge. "Lessons learned · 7" is available data.

## 4. Element-level conflicts with the shipped app

1. **The mocks show two engines everywhere; the app has three.** `gemini`,
   `openai`, and `openai-chat` (the ChatGPT pipeline: GPT-5.6 rewriting +
   image tool) are all live providers, and the plan's own inventory says all
   three must be carried. 4d needs a third card; 1a's header dots and the
   default-engine toggle need a third entry — or a design decision to demote
   the pipeline provider, which is a product call for Michael, not the coder.
2. **Region repair now has an engine selector** (shipped 2026-07-29: true
   masked edit via GPT Image 2, or guided edit via Gemini with a highlighted
   guide copy). No mock covers the repair overlay — fine — but 4d's copy
   "pre-selected everywhere a Model dropdown appears" now includes the repair
   dialog, and the plan inventory line for Repair should read "paint-mask
   overlay, brush size, engine choice."
3. **4c copy: "reject and it is quarantined for good."** False — rejected
   references have a "Reinstate as provisional" action the plan explicitly
   preserves. Soften the copy or cut reinstate (product call).
4. **4c "USED IN 6 RENDERS"** requires scanning every candidate's `references`
   list across all specs — no count endpoint exists. Client-side aggregation
   is possible but N+1; needs a data note.
5. **4c filter chips `ALL / STYLE / SUBJECT / SCENE`** — the current grouping
   is lookbook/research + per-role groups. The chip taxonomy needs a stated
   role→bucket mapping (e.g. STYLE = BOARD_RENDERING_STYLE, CINEMATOGRAPHY_STYLE,
   BOARD_LAYOUT_STYLE; SUBJECT = likeness/geometry/prop roles; SCENE =
   SCENE_REFERENCE) so the coder doesn't invent one.
6. **3a renders the evidence ledger as a read-only display table** (columns
   ID / OBJECT / SOURCE / CITED EVIDENCE / STATE) while the app's ledger is an
   **editable** six-column grid, and Task 3 rightly keeps it editable (HOLD
   rows must be resolvable in place). Also the mock's SOURCE column mixes two
   real fields — `evidence_class` (`INFERENCE`, `USER_DIRECTED`) and the
   free-text `source` (`SCREENPLAY p.42`). Both exist separately in the data.
   v3 should state: editable or display, and the exact field→column mapping.
7. **ID formats.** Mocks: `C0026`, `REF_0007`, `E03`. Real: `CAND-0026`,
   `REF-0007`, ledger `object_id` `OBJ-003` (and panel ids `P01`). Cosmetic,
   but v3 should direct the coder to render the real formats.
8. **Status vocabulary.** Mocks badge sheets as `LOCKED`; real spec statuses
   are `DRAFT / REVIEWED / APPROVED / REJECTED` with locked ⇔ APPROVED
   (`.badge.LOCKED` exists in CSS, so the presentation is fine — just note the
   mapping). 1a's subline "1 blocked" has no defined rule — presumably "draft
   sheet with required-object evidence gaps" (see §5.1); v3 should define it.
9. **3b shows only three candidate actions** (Reject / → Reference / Approve
   panel). The app has seven (+ Repair, Crop, Light study, Delete forever),
   all preserved by the plan. Where do the other four live — an overflow menu,
   a second row, the provenance rail? v3 must place them. Also "Approve panel"
   vs the app's "Approve": panel approval is per-candidate; the mock's label
   is better but should be consistent.
10. **3b right rail "CARRIED REJECTIONS"** maps to the existing
    rejection-lessons system (panel-scoped rejection reasons injected into
    future prompts). Real data, good feature — v3 should name the source so
    the coder wires it to lessons, not to rejected siblings ad hoc.

## 5. Corrections to plan v2 found during code verification

These are wrong or under-specified in the current plan text itself — carry the
fixes into v3:

1. **Task 3's gate rule is narrower than the real lock rule.** The plan says
   count "HOLD rows whose object matches a panel's required objects." Approval
   actually runs `full_validate`, whose evidence rule
   (`scripts/validate_spec.py:38-42`) is: **every required object needs a PASS
   row with the exact (panel_id, object) pair.** A required object with *no
   row at all*, or a REMOVE row, also blocks — a HOLD-count gate would show
   "lockable" while Approve fails. (Other validate failures — allocation ≠
   100, empty sources, weak-inference budget — also block; the audit's
   "any HOLD row" finding is advisory only and does not block.) The gate strip
   should mirror "required objects lacking a PASS row" and the CANNOT-LOCK
   copy in 3a already matches that rule well.
2. **Task 1's NEEDS-DATA branch is the real branch.** `missing_dependencies`
   is two fixed strings; the HOLD/GAP/SIZE taxonomy in the mock cannot be
   derived from them. Either v3 adds a small read-only state enrichment (held
   rows per draft sheet, geometry-reference gaps, undersized approved panels —
   all computable server-side from existing stores) or Task 1 ships the
   two-string version and the mock's BLOCKING list waits.
3. **Task 2 styling interaction:** `#sp-ledger .ledger-row:nth-child(odd)`
   zebra-stripes with `--bg2`; the non-PASS tint must win specificity (inline
   style or a class) or odd HOLD rows won't visibly change.
4. **Ground-rule tension:** "No endpoint, action, or data-shape changes" is
   incompatible with mocks 1a (blocking list, recent feed, engine dots), 4a
   (locations table, citation re-check), and 4c (used-in counts). v3 should
   either whitelist specific read-only endpoints or explicitly defer those
   mock elements.

## 6. Decisions plan v3 must make (checklist)

- [ ] Canonical navigation scheme (§2) and whether the five-stage IA ships now
      or later (§1).
- [ ] If the IA ships: stage-status sublines need per-stage summary data —
      define the endpoint or the client aggregation.
- [ ] Screenplay stage (4a): in or out; if in, scope the location/coverage
      parser; cut or spec the citation re-check promise.
- [ ] Assembly slot map (4b): in or out; define the "Change layout" workflow
      against locked specs or drop the button.
- [ ] Settings restructure (4d): in or out; resolve the three-provider
      presentation (§4.1).
- [ ] Dashboard data enrichment (§5.2): amend the no-endpoint rule or defer
      the mock's BLOCKING/RECENT panels.
- [ ] Placement of the four candidate actions 3b omits (§4.9).
- [ ] Reference chip taxonomy mapping (§4.5) and reject/reinstate copy (§4.3).
- [ ] Bible `REV` badge: add revision tracking or drop it (§3).
- [ ] Correct Task 3's gate rule to the real validate rule (§5.1).

---

## 7. Buildability assessment (coding-agent follow-up, 2026-07-29)

Michael asked which of the "non-existent feature" promises above are actually
buildable. Answer: nearly all — the data is derivable from existing stores.
**These are being implemented now** as read-only backend enablement plus
minimal UI in the current four-stage nav, so plan v3 can treat them as
existing capabilities rather than gaps:

| Mock promise | Status | How |
|---|---|---|
| 1a BLOCKING rows (HOLD/GAP/SIZE) | **built** | computed server-side: required objects lacking PASS rows per draft sheet; required objects with no approved reference; approved candidates smaller than their 4K slot |
| 1a RECENT feed | **built** | `GET /api/activity` over the existing flight-recorder log |
| Stage-status sublines data | **built** | aggregation in `/api/state` (`stage_summary`) — nav band itself still awaits the §2 decision |
| 4c `USED IN N RENDERS` | **built** | usage counts joined onto `/api/references` |
| 2a Bible `REV n` | **built** | revision counter incremented on every bible save |
| 1a/4d engine dots | **built** | key-configured state + persisted result of the last connection test; no passive polling, no fake "connected" |
| 4b slot map with OK/UNAPPROVED/TOO SMALL | **built** | `GET /api/specs/{id}/slot-map` reusing the assembler's layout math; rendered before any render is spent |
| 4a locations/coverage table | **built** | deterministic slugline parser over the screenplay text (PDF/Fountain/txt), scene counts, stated detail heuristic (description-line count) |
| 4a citation re-check on replace | **built, report-only** | quoted strings in evidence sources are re-searched in the new draft; vanished quotes are *flagged* (dashboard blocker + per-sheet report). Specs are never auto-mutated — locked sheets are immutable by canon rule |
| 4b "Change layout" | **not built** | blocked on a product ruling (edits a locked spec); options being discussed with Michael |

Design implication for v3: the mocks' dashboard, slot map, and coverage table
no longer need to be scoped down. The remaining open items are the ones that
were always design decisions, not data problems: §2 (canonical nav), §1 (IA),
§4.1 (third provider presentation), §4.3 (reject/reinstate copy), §4.9
(action placement), and the Change-layout workflow.
