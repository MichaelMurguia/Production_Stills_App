# Retired design plans — the ledger

The design chat's folder sync can resurrect plan files that were already
implemented and deleted (it has, twice — once as untracked files, once as
a commit). **Before implementing ANY `*_PLAN.md` / `*_SNIPPET.html` /
process file, check it against this ledger.** If it's listed, it's done:
delete it again, note the resurrection in the commit, and touch nothing
else. If a resurrected file DIFFERS from what shipped, treat only the
delta as new instructions.

| Plan / file | Implemented | Superseded by |
|---|---|---|
| PRODUCTIONS_PLAN.md (M1–M7 + C1/C2) | ≤ 2026.08.01 releases | — |
| CLEANUP_PLANS.md | ≤ 2026.08.01 | — |
| STORE_ROUTER_PLAN.md (T1–T4) | ≤ 2026.08.01 | rename forwarding (.55 era) |
| LOCKED_STAGE_PLAN.md (L1–L4) | ≤ 2026.08.01 | — |
| STORE_PIPELINE_PLAN.md | ≤ 2026.08.01 | — |
| CONNECTORS_PLAN / CONNECTORS_UI_PLAN (C1–C9) | 2026.08.03.40 | F-plan header renames |
| SETTINGS_FIRST_RUN_PLAN.md (F1–F7) | 2026.08.03.42; F6 backend 2026.08.04.43 | marquee snippet (.52), notice snippet (.53), Authenticate connector grammar (.48). **Resurrected + committed 2026-08-03, retired again** |
| PANEL_CARD_PLAN.md (P1–P9) | 2026.08.03.38 | — |
| MOCK_PARITY_PROCESS.md (D1–D8 + loop) | 2026.08.04.46; loop canonized | executable form: `.claude/skills/design-verify/`. **Resurrected by folder sync 2026-08-06 AND again on 08-07 (bundled with SCAN_CONSOLIDATION); deleted both times** — D1–D8 describe a first-run Settings build that SETTINGS_CONTROL_PANEL_PLAN replaced in .60; D5's active-tab marker has no component left to move |
| PROVIDER_MARQUEE_SNIPPET.html | 2026.08.04.52 | — |
| AI_MODELS_NOTICE_SNIPPET.html | 2026.08.04.53 | — |
| design_handoff/CANONIZATION_PASS.md (R1–R19) | 2026.08.04.57 | — (emptied the Uncanonized table) |
| BAND_CONDENSE_PLAN.md (B1–B3) + BAND_CONDENSE_SNIPPET.html | 2026.08.04.58 | — |
| SETTINGS_CONTROL_PANEL_PLAN.md (P1–P4) | 2026.08.04.60 | mock 18b adopted; 18a re-export (marquee developer names) applied; brand-icon rule app-wide (P3) |
| PRODUCTION_DESIGN_V3_PLAN.md (D1–D6, D8, D9) | 2026.08.04.64 | D7 preset looks pending the plate library (plan file trimmed to D7; PRESET_LOOKS_SHOT_LIST.md kept); five uncanonized rows ruled and emptied |
| ADMIN_CONSOLE_FIX.md (X1–X4) | 2026.08.04.73 | mocks 12a/12b adopted; supersedes S1's density ratification |
| NON_CANON_REVIEW_2026-08-06.md (A1, S1–S3) | 2026.08.04.73 | emptied BOTH queues — app Uncanonized table and store Non-canon table |
| SWATCH_GENERATE_RULING.md (A1) | 2026.08.04.73 | act-where-condition-is-met canonized as the pair to anchored explanation |
| HATCH_RULE.md (H1–H3) | 2026.08.04.79 | audit found zero drift in app/; store gained a mirrored copy + drift contract |
| SIGNIN_BRANDING_PLAN.md (G1–G3) | 2026.08.04.79, corrected .80 | first pass built from prose; GOOGLE_SIGNIN_SNIPPET.html + google-g.svg later delivered and shipped verbatim (radius, asset, approved string). Roboto still unbundled |
| TAKE_ACTIONS_PLAN.md (T1–T3, S1–S2) | 2026.08.04.79; **comparison pass vs corrected mock 14a done 2026.08.05.07** | S1 shipped as the hatch state; render preview needs a tenant endpoint (see changelog); the corrected mock moved the identity tag top-right with a TAKE n OF n ordinal and removed the bar's box/fences/rule; Reject kept as a reported deviation — removing a verb is functionality |
| README_2026-08-06.md (bundle index) | 2026.08.04.79 | 3 of its 6 entries were resurrected ghosts already shipped in .73 |
| BREAKDOWN_INTAKE_PLAN.md (B1–B5) | 2026.08.04.83 | mock 13a-breakdown-intake; Spec ID help copy follows B3 not the mock's auto-fill line (see commit) |
| PALETTE_GROUPS_PLAN.md (§1–§5) | 2026.08.04.92; **re-delivered 2026-08-07 in the two-plan bundle and skipped — verified already shipped** | mocks 15a-palette-groups / 15a-swatch-viewer; **set-as-one-object canonized**; ruled the hero chip amber (reversing the non-canon build) and retired the recolour pencil for a `Recolor` text act; viewer verbs kept as `.text-act` (Courier) per the plan's naming rather than the mock's proportional rendering; column badge left counting references, not rows |
| SCAN_CONSOLIDATION_PLAN.md (§1–§4) | 2026.08.04.97 | mocks 16a-scan-consolidated / 16a-environment-modal; head-and-tail lists and edit-in-a-room canonized; env→language is an INFERENCE (no stored field exists) and the modal says "where its palette comes from" rather than claiming an assignment; `env.light` / `env.material` added, omitted when empty |
| NON_CANON_REVIEW_2026-08-07.md (R1–R7) | 2026.08.04.98 | ruled all seven rows and emptied the table; verb-sits-with-its-object canonized beside act-where-condition-is-met; bulk verdicts withheld until everything judged has been seen; destruction only where its object reads in full; amber confirmed blocking-only. R7 needed no code — Import was already above Delete; only the menu's separating rule was added |
| TAKE_ACTION_BAR_PLAN.md (17a) | 2026.08.05.09 | mock 17a-take-action-bar; superseded T2's one-grammar clause AND the same-day 14a peer cluster; decision-not-code-owns-hierarchy canonized; DERIVE folds to ⋯ before wrap via ResizeObserver; the lightbox's own "→ Light study" left alone (different surface, out of the plan's scope). **Resurrected 2026-08-09 inside Art_Board_Plan.zip; verified already shipped, not re-implemented** |
| CANONIZATION_PASS_2026-08-10.md (R1–R10 + au-* mocks) | 2026-08-10, one commit | Nine Uncanonized rows ruled, table emptied; four Layout canons + two Do-nots added (card-for-a-picture, room-on-inheritance, one-control-two-presentations, geometry-declared, no-amber-exemptions, no-second-bar). Composer amber cut to two; geometry manifest replaces the JS mirror; unanchored register; ramps-are-the-shelf; storage bar deleted; workbench camera collapses; board type above the brief. **Its bundle (Canon_pass.zip) resurrected SHEET_SYSTEM_PLAN.md byte-identical — verified, not re-implemented** — and claimed the board half "is not yet in the tree": stale sync; it shipped 2026-08-10 (see row below). lb-*/ba-* mocks kept, consistent with every prior pass |
| **Root sweep 2026-08-12** — DESIGN_REVIEW_2026-07-30{,b,c}.md, DESIGN_REVIEW_2026-08-02.md, EXTRACTION_GAPS.md + EXTRACTION_GAPS_APPROVED.md, HATCH_CORRECTION_2026-07-30.md, ONE_LIBRARY_PLAN.md (D1–D6), PRODUCTION_DESIGN_PLAN.md (superseded by V3), READ_REVEAL_PLAN.md, SCROLLBAR_AMENDMENT.md | all ≤ 2026-08-08 releases | Deleted under the user's 2026-08-12 ruling: an implemented plan file is deleted in the same commit as its implementation, and this ledger is the memory. Kept because still live: SCOPES_PLAN (parked → Organizations), PRODUCTION_DESIGN_V3_PLAN (trimmed to pending D7) + PRESET_LOOKS_SHOT_LIST, STORE_DESIGN_BRIEF (open handoff to Claude Design) |
| **LOOKBOOK ROLLBACK (user ruling 2026-08-12)** | 2026-08-12 | **The Lookbook surface is deliberately REMOVED, not missing**: no nav tool, no shelf, no sheet authoring, no lookbook PDF sets, no /api/lookbooks routes. The composer survives only as the inline arrange room on stage 05. If ANY plan, bundle or sync re-delivers a Lookbook/shelf/composer-as-view — including SHEET_SYSTEM_PLAN §11 or its mocks — do NOT re-implement; the user ruled the surface out ("too big, and separate from the Board panel"). The sheet MODEL (sheet.py/sheet_render.py) stays as the boards' engine |
| STEP_SEQUENCE_SPEC_2026-08-14.md **Parts 1, 2, 3, 5, 6** + README_2026-08-14.md | 2026-08-14, one commit | Delivered in design_handoff/Hierarchy_Update.zip — **do NOT re-extract that zip: three of its four "plans" are ghosts** (CANONIZATION_PASS_2026-08-10, SHEET_SYSTEM_PLAN, and HARNESS_AUDIT_2026-08-14 which shipped hours earlier the same day), all byte-identical, and 23 of its 25 mocks were already in design_mocks/. Its README repeats the SAME stale "SHEET_SYSTEM_PLAN board half only" claim the 2026-08-10 row already refuted. **Parts 5 (Reference) and 6 (Status) needed no work** — both shipped 2026-08-10/08-14 before the spec arrived. Part 1 is canon (image-is-the-hero outranking Layout patterns, 24/15/11.5, fill-classifies, verbs ink+underlined on one right edge, numbered spine, honest gates, row-not-block gutters, capped measures, 3 Do-nots) + tokens `--band`/`--tile`/`--hairline`. Part 2 built as `.wb-card`, mock hier-4a. **Four reported deviations, all in the Uncanonized row**: Generate stays ghost so Approve keeps the single amber (the mock draws two, against §1.3); OFF rows state the rule in force, not the mock's first-take label; Copy/Download restored into the prompt's reading view (the rail deletion would have destroyed the 2026-08-06 download feature); brief/camera ghost boxes became §1.4 verbs, reversing the user's 2026-08-13 direction. **§2.5's "takes move to the right rail" is DEAD** — it contradicts §2.15 in the same document; the mock and the user (2026-08-14) both put the take at the top. Also fixed the aspect select (hardcoded 16:9 vs the panel's established shape) and a headless `.stor-bar` rule orphaned by canon-pass R6. **Part 3 shipped the same day** — one shared `seqStep()` for both surfaces (vocabulary class generalised `.wb-card` → `.seq`), seven steps, questions promoted out of a bullet with their consequence stated, an honest approve gate, and the two-up opener showing what the board has made (an empty frame at the panel's own ratio states its blocker — the sanctioned exception to *never reserve the shape of the missing thing*). The user's four rulings were applied as given: hybrid ledger (selects while drafting, stated record once confirmed or locked), opens-on-takes approved, creation-card collapse DECLINED, forbidden-dedupe DECLINED. Two self-inflicted bugs caught in the same pass and worth remembering: the restructure script's backslash-guard corrupted a real escape inside preserved markup (`join("
")` became a literal `
` in the forbidden textarea), and the two-up's caption landed in the next grid cell until each panel was wrapped as one item. **Part 4 (stage 02) alone remains — the file is trimmed to it** and the spec forbids starting it until stage 04 has survived a week of real use |
| HARNESS_AUDIT_2026-08-14.md (U1–U6 + R1–R18, first audit-by-use) | 2026-08-14, one commit | Delivered in design_handoff/Harness_Audit_01.zip — **the zip stays in design_handoff/ but do NOT re-extract it: it also carries byte-identical ghosts of HARNESS_PLAN, SHEET_SYSTEM_PLAN, CANONIZATION_PASS_2026-08-10 and 22 shipped mocks** (only au2-carried-notes.png was new, kept in design_mocks/). All six use-found defects fixed and 16 of 18 rows ruled+emptied; user approved the three functionality changes (R17 verbs → Edit + Stop carrying with delete in the Edit modal; U2 lead promotes; U3 stage-04 landing) on 2026-08-14. DEFERRED, still in the Uncanonized table: R2 arrange room, R4 parts 3/4/5/6a/7 — they need the next recording walk (arrange room + style picker first). Canon added: 6 Layout, the dropdown component, 3 Do-nots |
| HARNESS_PLAN.md (recorder + replay harness) | 2026-08-13, one commit | app/static/recorder.js (`?record=1` chip), `app_sha` on /api/healthz, tools/build_harness.py (byte-identical frontend + fixtures.data.js/fixtures.js shim + MANIFEST + honest coverage report), harness//fixtures-*.json gitignored. Two deviations, both deliberate: the plan's recording-walk step 8 names the Lookbook — a surface the user ruled OUT 2026-08-12 (see LOOKBOOK ROLLBACK row); skip that stop, do not resurrect it. And the reported app↔server coupling — syncUrl (app.js:1621) writes server-absolute history URLs, SecurityError on file: origins — is absorbed by the SHIM (fixtures.js wraps history.pushState/replaceState), app.js untouched per the plan's own rule. The plan's shim sketch never initialised `__HARNESS_MISSES__`; fixed in the generated shim, tested |
| SHEET_SYSTEM_PLAN.md (§0 R1–R8 + §1–§13) + SHEET_SYSTEM_TECH_SPEC.md | 2026-08-10, four phased commits; **§11's Lookbook surface rolled back 2026-08-12 — see the row above** | mocks lb-1a..lb-3c + ba-2a..ba-4a (kept in design_mocks/); one sheet grammar for boards and lookbooks — sheet.py/sheet_render.py, packers moved from assemble (aliased back), assemble_board a thin caller (letterbox via allow_letterbox per R2), INK board default (R6), elastic/fixed type floor (R1), R3 variant→block mapping, R4 derived-take STRIP with the swap note, R5 vocabulary split, R7 "breakdown" rename, composer + Lookbook tool, canon §13 items 1–10 folded. Tech-spec R1 nit: the 18×12 print rung is unreachable by canon types — tested via an injected test-only frac. **The delivery zips Art_Board_Plan.zip / Art_Board_Ruling.zip stay in design_mocks/ — do NOT re-extract their plan files; both are this row** |

- **RULE_PASS_2026-08-16_A_RULES.md** — implemented 2026-08-16. Eight rules
  folded into `DESIGN_SYSTEM.md`; seven Uncanonized rows emptied. Two
  refusals shipped as code: the logline back to 15px/400 `--ink` (promote by
  tier and position before size), and `✓ SETTLED` replacing `✓ CONFIRMED` on
  frozen steps, with the head counting `n OF n STEPS SETTLED`. `.auth-state`
  retired in favour of `.busy.busy-inline`.
- **STEP_SEQUENCE_SPEC_2026-08-14.md** — superseded 2026-08-16, NOT pending.
  Parts 1-3 shipped (the step vocabulary, stage 04, stage 03). Its Part 4
  forbade starting stage 02 until stage 04 had a week of real use; stage 02
  was rebuilt anyway and the rebuild is ratified by RULE_PASS Part B. Do not
  implement Part 4.
- **RULE_PASS_2026-08-16_C_SEQUENCE.md** — implemented 2026-08-16. Eight
  rows cleared. Ratified: stage 04's six steps (all four mock deviations —
  the build followed canon, the mock did not), stage 03's transfer, the
  35mm window and fitted image, the empty frame as a way in, the palette
  plate and Choose plates, the stale-tab bar. Corrected: the ledger
  freezes on the LOCK not the confirmation; the manifest moved to step 05;
  the film rolls gained arrow-key stepping. C8 (arrange room) deferred a
  second time and stays in the table.
- **RULE_PASS_2026-08-16_D_SETTINGS.md** — implemented 2026-08-16.
  Productions as Settings' first tab ratified, with a gap in the strip
  marking the one tab you act on rather than set. D2 ruled via A3.
- **RULE_PASS_2026-08-16_E_STORE.md** — implemented 2026-08-16. Both store
  rows cleared. The fleet table stays whole and gains a headline;
  UNREACHABLE splits from CANNOT MEASURE. Responsive imagery ratified.
- **RULE_PASS_2026-08-16_B_STAGE02.md** + **README_2026-08-16.md** —
  implemented 2026-08-16. Stage 02's direction ratified in full; six
  corrections shipped: one card with two lives from one renderer, diagrams
  disclosed once per panel and forbidden where real frames exist, never
  padding to three, four text roles with the essay behind one door, no
  italic and films out of Courier, provenance leading the captured card,
  and the escape hatch leaving the grid and stopping being drawn twice.
  B10's defect closed — a take that rode the grammar says so on the hero
  and in the lightbox.

- **`docs/BUGFIX_PLAN_2026-08-12.md`** — retired 2026-08-17 (adversarial
  review F15). A `*_PLAN.md` left in the tree for five days against this
  project's own 2026-08-12 ruling that an implemented plan is deleted in
  the same commit and ledgered here. It was the three-agent review of
  releases .14–.21; its items shipped across that week's commits. Moved to
  `docs/history/` rather than deleted so the review's reasoning survives —
  it is not binding and must not be implemented again.

- **RULE_PASS_2_2026-08-16_A_ARRANGE / _B_LOOKS / _C_DOOR / _D_ACTS /
  _E_PICTURES**, **TUTORIAL_RULING_PLAN.md + TUTORIAL_RULING_SNIPPET.html**,
  **TRIAGE_PLAN_2026-08-18.md**, **DENSITY_PASS_2026-08-17.md** and
  **README_2026-08-18.md** — delivered in `design_handoff/Tutorial_Design.zip`,
  implemented 2026-08-18. **Do not confuse the `RULE_PASS_2_*` series with the
  earlier `RULE_PASS_2026-08-16_*` series above** — different subjects
  (ARRANGE/LOOKS/DOOR/ACTS/PICTURES vs RULES/STAGE02/SEQUENCE/SETTINGS/STORE),
  and the near-identical filenames are exactly the trap this ledger exists
  for. Fifteen Uncanonized rows emptied. **`_C_DOOR` was PARTLY REVERSED on
  2026-08-22**: its C1 merged the two breakdown intake doors into one, and
  the user restored two columns. Each of C1's three reasons is answered
  rather than ignored — see the uncanonized row in `DESIGN_SYSTEM.md`. C2
  (the recomputing submit verb) and C3 (the explaining button's removal)
  both stand, narrowed to the door that still holds two acts. **DENSITY_PASS is the one
  exception: only its five rules were canonized.** Its eleven-surface
  relayout is NOT implemented — the twelve `design_boards/*.dc.html` are its
  specification and implementing it without reading them would be
  reinterpretation, which the design-verify authority order forbids. It
  needs its own pass, with the boards. Two deviations from the plans, both
  deliberate: `--ground` was added as a token (the ruling names it and this
  system had none; borrowing a film-roll token by eye is forbidden by that
  token block's own comment), and the CMS's `block` checkbox reads *Stop the
  control being clickable* rather than the plan's *Keep the control
  clickable*, which would have inverted the stored flag on every authored
  step.

- **TUTORIAL_MATERIAL_2026-08-19.md** — delivered in
  `design_handoff/Tut_ModalColors.zip`, implemented 2026-08-19. The tour
  layer is made of board stock; supersedes §3 (the dim) of
  TUTORIAL_RULING_PLAN and adds the material ruling that plan lacked. Also
  ratified `--accent-hover` as-is and closed the `ART_BOARD` mirror's three
  extra vars. **The rest of that zip was a RESURRECTION** — byte-identical
  ghosts of RULE_PASS_2 A–E, TRIAGE_PLAN, DENSITY_PASS and
  TUTORIAL_RULING_SNIPPET, all implemented 2026-08-18 and ledgered above;
  none re-implemented. `TUTORIAL_RULING_PLAN.md` arrived larger than the
  copy that shipped, but the README names the delta as the material plan
  alone, and the ruling plan's own rulings were verified still in place.
  The design boards were refreshed from it (`Tutorial System.dc.html`
  gained turn 3a) and kept in `design_handoff/design_boards/` for the
  density pass, which remains the one unbuilt item.

- **CINEMATOGRAPHY_PLAN_2026-08-25.md** — written after two days and ~20
  renders testing a per-panel cinematography axis that was wired correctly
  end to end and produced almost no visible effect. Implemented
  2026-08-25, in the plan's own order: **C7** (the hedged styles
  rewritten), **C3** (a hedge lint), **C4** (a take says what it was
  rendered from), **R1.5** (per-block prompt composition — the
  instrumentation that corrected the plan's own headline figure and found
  Character Presentation riding every panel whole), **A1** (`docs/
  CAMERA_RECIPES.md` parsed as a fourth style library, 20 framings and 13
  modifier axes), **A2** (the framing as a panel field chosen at breakdown
  time, with the unchosen production default made to yield to it),
  **A3** (the research pass chooses it, with a method and a justification
  the director can argue with), **A4** (the Production Design camera card
  retired), **R1** (a roster is not global — Character Presentation
  selected per panel from the production's own cast, with what was
  withheld stated), **R2** (the Bible read against itself for rules that
  cannot both hold in one frame), **C6** (the style probe renders twice),
  **C9** (a stated per-engine prompt limit, refused before the spend).
  E1 was RESTATED rather than implemented: the plan read a 19,094-character
  prompt against a 1,782-character one and concluded length is the
  constraint; it is not, and acting on it would have thrown away canon the
  panel needed. E4 and C5 were STRUCK by the user before implementation
  (five required objects can appear in a subjective frame — present, not
  sharp), along with a proposed screenplay↔cinematography slider. **C8
  alone is unbuilt** and is not code: a controlled engine comparison
  needing four renders, and the file is trimmed to that item.

- **PRODUCTION_DESIGN_UI_PLAN_2026-08-28.md** — delivered in
  `design_handoff/Prod_Design_01.zip`, implemented 2026-08-29. An
  appearance-only restandardisation of stage 02: §3.1 header, §3.2 anchor
  heroes and the jurisdiction ruling, the palette's own modal, §2.4 cost
  statements and segmented pickers, §3.5 two-column Bible, §3.6 sample
  text-links, and §4's stage bars on the run ladder. §3.3's findings
  order and §3.4's casting block were NOT built at the time and were
  carried as an open row in the Uncanonized table; **both were finished
  2026-08-31** (user: "Build Design Plan and Cast the film are not the
  latest design from the latest handoff. Finish those"), from the copy of
  the plan inside `design_handoff/ProdDes3.zip` — extracted to scratch,
  never back into the tree.

  **ONE ITEM OF §3.3 IS STILL OPEN, and it is not code:** the plan wants a
  120px thumb on each environment row, and an environment has no picture
  anywhere in this app. A slot that can never fill is worse than no slot,
  so it is logged in the Uncanonized table as a question for the designer:
  where should an environment's picture come from? Design languages had an
  answer — references carry a language scope — and use it.

  **THREE OF ITS INSTRUCTIONS WERE DELIBERATELY NOT FOLLOWED**, each
  overruled by a later decision. A future pass that "finishes the plan"
  must not restore them, and `tests/test_production_design_ui.py` fails
  if it does:
  1. Step 02 is **Build Design Plan**, not `Script scene scan` — renamed
     by the user 2026-08-28, after the plan was written.
  2. Step 04's verb is **Build Art Direction Bible**, not `Create`. Same
     rename.
  3. The **camera grammar row stays retired**. Both mocks show
     `CAMERA GRAMMAR — 40mm · eye level · medium wide · DEFAULT FOR EVERY
     PANEL`. It was retired 2026-08-25 (cinematography plan A4) because a
     production-wide default nobody chose contradicted the cinematography
     grammar and defeated the framing axis for two days of renders. Raised
     with the user 2026-08-29; ruling: "dont change camera row".

  **The rest of that zip was a RESURRECTION.** Twelve of its fourteen
  documents are already ledgered above — the whole `RULE_PASS_2_*` series,
  `TUTORIAL_RULING_PLAN` + `_SNIPPET`, `TUTORIAL_MATERIAL_2026-08-19`,
  `TRIAGE_PLAN_2026-08-18` and `DENSITY_PASS_2026-08-17` — and its README
  is the 2026-08-18 one re-dated, still asserting "Nothing here is in
  `docs/RETIRED_PLANS.md`". None were re-implemented. Its
  `design_boards/Production_Design.dc.html` is turn `1a`, not the `3a`/`4a`
  the plan cites, so the build came from the PNG mocks and the plan text;
  both mocks are kept in `design_mocks/`. The zip is deleted.


- **CAST_CHARACTER_SCREEN_2026-09-12.md** — delivered in
  `design_handoff/Cast-character.zip`, implemented 2026-09-12. Extracted
  to scratch and never copied into the tree, so there is no file to
  delete; this row exists so a folder re-sync cannot resurrect it.

  Built: §2 whole — the empty character screen, its 9:16 dashed frame,
  `FULL BODY`, the expand glyph, Generate over Attach, Accept / Reject,
  the description with its large edit button, and the verbatim screenplay
  lines with page refs. The generation contract with it: one picture per
  call, full body at 9:16, prompt = the Bible plus the description, the
  result held PROVISIONAL until Accept. §1's deltas: `n SCENES` on the
  roster card, casting in one gesture from a chip or the manual row, and
  the 12px type floor across both screens. §3 kept its 2026-08-29
  proportions and gained the header's role suffix.

  Same day, the user extended §1 past the roster: "character cards still
  open this prior to generation. What you just implemented is a
  replacement." So the **casting modal is retired** and all four doors —
  the ribbon's uncast tile, the roster's chip, the manual `+ Cast` row,
  and the Reference shelf's `Cast this subject` — cast and land on the
  subject's own screen. Traits kept an editor on §3, since the modal was
  the only place they could be changed and they ride every prompt.

  **One item deliberately NOT built, raised rather than decided:** §2
  says the face crop and the card thumbnail are "derived from the
  accepted full-body image server-side". They are not derived. The
  roster card shows the same 9:16 plate in its 1:1.25 slot under
  `background-size: cover`, which crops to the CENTRE of the body — so a
  character's card is a torso, not a face. Deriving a face crop needs a
  face detector or a second render, and the plan does not say which.

  **And one thing the retirement took with it:** KIND is no longer
  editable anywhere. The read proposes it and it is rarely wrong; when
  it is, the path is deleting the card and re-adding it from the manual
  row, which has a kind select. Named here rather than patched.

  §3's `1.85:1` for a vehicle or prop and §3.3's 120px environment thumb
  are unchanged by this plan; the environment question above is still
  open.

- **LEGIBILITY_FLOOR_2026-09-12.md** + **README_2026-09-12.md** — delivered
  in `design_handoff/font_updates.zip`, implemented 2026-09-12. Extracted
  to scratch, never copied into the tree. The plan says "Fold it into
  `app/static/DESIGN_SYSTEM.md` and delete it"; it is folded into §1.3
  (the type scale) and the Tokens section (the ink tiers and the colour
  floor), and both halves are asserted mechanically by
  `tests/test_design_tokens.py::TheLegibilityFloor`.

  499 of 549 `font-size` declarations moved; the body shorthand went from
  14.5px to 14px; four inline sizes in `app.js` were raised. `--ink-dim`
  and `--ink-faint` were redefined rather than rewritten at 476 call
  sites — the audit's `#6b7278`-on-`#0b0c0e` finding WAS the faint tier,
  so the fault was in the token. Their 41 non-text uses moved to new
  `--line-strong` / `--line-bright` so no border changed value.

  **Three consequences, all raised rather than smoothed over:**

  1. A disabled button's label was `#4a4d52` (~2:1) and is now readable
     ink. The plan leaves no colour for "inactive", and a disabled
     control here usually carries the reason it is disabled.
  2. The cast ribbon's twelve names no longer fit on one line at 14px, so
     they wrap to two — the plan's own "give the label the room". One of
     twelve (COLONEL BEATRIX OKORO) still ellipsises at the second line.
  3. Surfaces that carried three or four label sizes now carry one,
     because everything under 13px collapsed onto the floor.

  **The rest of that zip was a RESURRECTION**, the third of this shape.
  Twelve of its fifteen documents are already ledgered above — the whole
  `RULE_PASS_2_*` series, `TUTORIAL_RULING_PLAN` + `_SNIPPET`,
  `TUTORIAL_MATERIAL_2026-08-19`, `TRIAGE_PLAN_2026-08-18`,
  `DENSITY_PASS_2026-08-17`, `PRODUCTION_DESIGN_UI_PLAN_2026-08-28` and
  `CAST_CHARACTER_SCREEN_2026-09-12` (ledgered hours earlier the same
  day). Its `README_2026-08-19.md` is the 2026-08-18 one re-dated, still
  asserting "Nothing here is in `docs/RETIRED_PLANS.md`". None were
  re-implemented.

  **One passenger is genuinely unledgered and was NOT built:**
  `V3_INSTRUMENT_RULING_PLAN.md` (2026-08-23, "the surface is an
  instrument" — a third founding rule beside amber and Courier, deleting
  every count and tally that exists to reassure rather than to be acted
  on). It is marked `Status: FOR REVIEW`, the drop's own README does not
  list it, and it would retire copy across every surface. Raised, not
  implemented.

- **LEGIBILITY_FLOOR_DELTA_2026-09-12b.md** — delivered in
  `design_handoff/Delta_Update.zip`, implemented 2026-09-12, same day as
  the floor it amends. Extracted to scratch, never copied into the tree.

  Its ruling is the interesting half: **"do not port a colour list. Port
  the rule."** The first pass had replaced a fixed list of greys, and a
  verifier pass found the ones the list missed. So the implementation is
  a lint that computes contrast over every `color:` value
  (`TheColourFloorIsMeasuredNotListed`), and it found what a list could
  not — `--hold` at 5.70:1 colouring 29 glyphs and `--bad` at 4.61:1
  colouring 44.

  Both moved to the rule beside the words, which is where the delta
  already put red ("the red stays on the hairline beside them"). Ten
  marks whose state was ONLY a colour would otherwise have collapsed into
  three identical greys — `.gen-warn`, `.gen-gate`, `.made-blocker`,
  `.req-mark.hold`, the `.stor-line`, `.lb-fill-v`, `.prod-care` and
  `.rail-mark` families — and gained a 2px left rule instead. §4's
  exclusions are honoured: borders, underlines, outlines, backgrounds,
  scrims and swatch values are out of the lint's scope.

  §5 (13.5px gone) and §3 (withheld buttons readable) were already true
  from the floor commit.

  **One thing measured and raised rather than fixed:** `--panel2`
  (#21252a) is the single ground where the floor's OWN inks fall short —
  `--ink-faint` 6.56:1, `--accent` 6.96:1, against 8.33 and 8.83 on
  `--ground`. Complying there means changing an ink the floor fixes or
  darkening a surface token it does not mention. Recorded as a number in
  the token tests so it stays visible.

  The rest of the zip is the same resurrection as `font_updates.zip` a
  few hours earlier, minus nothing and plus this note.

  **A miss in the first pass, user-caught the same day** ("you still have
  9px fonts"): `.bf-sub` was `clamp(8px, 1vw, 13px)` and rendered at 9px
  on a 900px viewport. Two faults behind one symptom. The lint matched
  only a bare `NNpx` and never looked inside `clamp()`; and the board
  frame's type had been exempted on the reasoning that the preview must
  match the exported composite pixel-for-pixel — true of its PALETTE
  (audit #15) and false of its type, because `assemble.assemble_board`
  draws the 4K composite server-side with PIL and never reads this DOM.
  Both are fixed: the preview's type is on the scale, the lint parses
  every length in a font-size and rejects any relative unit outright, and
  it now walks every file `app/static/` serves rather than the two
  obvious ones (which is how `recorder.js`'s 12px chip surfaced).

  **The floor's own mechanism did not reach its own goal, user-caught
  2026-09-12** ("site still has 9px tall fonts - bad. fix."). The plan
  names its fault as "Courier labels rendering at 8–9px cap height" and
  prescribes a 13px font-size floor. Those are two different quantities.
  Measured by pixel scan, Courier New's cap height is 8px at 11.5px, at
  13px, at 14px and at 15px — the face is hinted flat and its cap-to-em
  ratio is tiny — so implementing the plan exactly moved the rendered
  letter height by ZERO, and the fault it was written for survived it.

  Two levers reach cap height, the size and the face, and both moved the
  minimum needed: `--mono` leads with Consolas then Cascadia Mono
  (Consolas is NARROWER than Courier New, so no label costs more room and
  Courier New stays as a fallback), and the Courier step is 15px, which
  renders the same 10px cap Archivo gives at the 14px prose floor. Every
  Courier rule now carries an explicit size — one that inherited the 14px
  body rendered 9px caps.

  Measured after, across six views at 1100px and 1560px: smallest
  rendered cap height 10px (was 8px), smallest font-size 14px, no
  horizontal scroll. `.prod-grid` needed `minmax(0, 1fr)` on the way —
  `1fr` is max-content-floored, so the wider labels pushed it 45px past a
  1100px window.

  **The face change needs a designer's ruling.** Rule 2 names Courier,
  and this changes which mono actually renders; one line in `--mono`
  reverts it, at the cost of going back to 8px caps.

- **TYPE_SCALE_R2_2026-09-12.md** — delivered in
  `design_handoff/font_phase_3.zip`, implemented 2026-09-12 **as a scaled
  ladder, not as written**. Extracted to scratch, never copied into the
  tree. It supersedes §1 (type) of `LEGIBILITY_FLOOR_2026-09-12.md`; that
  document's §2 (colour) still stands, and the zip's own copy now says so
  in a banner.

  **Its criticism was right and its remedy conflicted with a user
  ruling.** R2 opens: "The 13/14 floor flattened the hierarchy: kickers,
  captions and body all read at nearly one size." True — the same
  consequence was logged in the Uncanonized table hours earlier. But R2's
  remedy is a ladder of 10/11/12/13/15/16/18/20/22/24/32 in FONT-SIZE,
  and the same morning the user had ruled: "no case - upper or lower
  should be smaller than 10 px ever," which is a floor on INK. Measured
  here, R2's floor tier renders 7px caps and 5px x-height, and its body
  prose tier 9px caps / 7px x-height — below the ruling, and below the
  8px caps that started the complaint.

  Raised rather than implemented. **The user ruled: proportional — R2's
  ratios, the user's floor.** The ladder is multiplied by 1.5, which puts
  its floor tier at 10px of ink:

      R2   10  11  12  13  15  16  18  20  22  24  32
      here 15  17  18  20  22  24  27  30  33  36  48

  The 12 tier splits by face: Archivo clears at 18px, Courier needs 20px
  because its x-height is 9px at 18.

  **15px and 17px Courier are conditional tiers.** They clear the floor on
  cap height and fail it on x-height (7px and 8px), so they are legal only
  where the text renders uppercase — which is R2's own rule for its
  equivalent tier ("a 10px label that is not uppercase, not tracked and
  not `#a3aab1` or brighter is a defect"). A rule earns one by declaring
  the transform or by being MEASURED rendering uppercase on the page. Of
  291 Courier rules, 68 earned a tight tier and 10 were held back at 20px
  for rendering lowercase.

  **Coverage is honest and partial:** only 90 of 320 Courier selectors are
  reachable on this project's unlocked stages, so the tight tiers are
  populated for stages 01–02, Settings and Projects and conservative
  everywhere else. They grow as breakdowns, panels and boards become
  reachable — never by assumption.

  Live tiers went from 2 to 6. Smallest rendered glyph stays 10px,
  measured at 1280px and 1560px; `.prod-actions` gained `flex-wrap` to
  survive the narrower window.

  The rest of the zip is the same resurrection as the two before it.

- **COPY_DISCIPLINE_2026-09-13.md** — delivered in
  `design_handoff/Copy discapline.zip`, implemented 2026-09-13. Extracted
  to scratch, never copied into the tree. Folded into
  `app/static/DESIGN_SYSTEM.md` under `## Copy`, as the plan asks.

  The rule: a control explains itself by how it looks and what it is
  called, not by a sentence beside it. Three tests — does the label
  already say it (cut), is it a state the user must know (make it a
  mark), is it a rule about behaviour (it belongs in the documentation).

  Found by measuring the rendered page rather than grepping: every
  all-caps Courier run of five words or more inside the stage, then
  classified by hand against the plan's "what stays" list. Eleven cut or
  shortened; the cost notes became tokens; the locked segment is shown
  rather than narrated.

  **Four kept that a mechanical pass would have cut**, each a deliberate
  call and each logged in the Uncanonized table for review:

  1. `SECTION HEADINGS ARE PARSED — DO NOT RENAME`. Not a state and not
     a refusal, so the tests say cut it. It sits on a free-text editor
     where renaming a heading silently breaks the parse — a footgun
     warning, and removing it would be net harm.
  2. `ESC DISCARDS`. Trimmed from `ESC DISCARDS — NOTHING CHANGES UNTIL
     YOU SAVE`, but not removed: ESC is a control with NO visible label,
     so this line is the only place the capability exists.
  3. `SAME LOCATION · SAME BIBLE · SAME ANCHORS`. A `·`-separated run of
     values is data by the plan's own test.
  4. `LOCKED — NO ART DIRECTION BIBLE`. A refusal, which the plan keeps
     explicitly, and which canon separately requires (a gate states its
     blocker).

  **The plan's own caveat applies to the boards, not to this.** It warns
  that its mechanical pass over the 30 design boards also caught lines
  that are data — Hierarchy's slugline and ledger rows, `Production_Boards`'
  sheet spec, the IconStudy legend — and that those want restoring by
  hand ON THE BOARDS. Nothing was restored here because nothing of that
  kind was cut here: sluglines, act headings, `TURNS ON` provenance,
  cast tallies and subject facts were all verified present after the pass.
