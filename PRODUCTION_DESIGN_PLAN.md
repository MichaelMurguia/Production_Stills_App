# PRODUCTION_DESIGN_PLAN.md — the complete stage-02 rebuild

**For the coding agent.** This is the whole Production Design redesign in one
document, superseding nothing but consolidating what was previously spread
across `READ_REVEAL_PLAN.md` (R1–R4), `EXTRACTION_GAPS.md` +
`EXTRACTION_GAPS_APPROVED.md` (Gaps 5–6), and plan v3's C13. Those files
remain authoritative for their details — this states the order, the
dependencies, and what "done" means for the stage.

Mocks: `design_mocks/2a-production-design.png` (stage frame),
`6a-read-reveal.png`, `6b-uncast-triage.png`,
`6c-scope-language-environment.png`, `5b-cast-the-film.png`.
Read `app/static/DESIGN_SYSTEM.md` first. One task per commit.

## Scope

**In scope:** step 2 (the read), step 3 (casting), the extraction changes
behind both, and the sheet-scope selector that consumes environments.

**Explicitly NOT in this plan** — still v1, designed only to the extent of
C13's state badges. Do not restructure them; if one blocks you, stop and
report:

- Step 1 — style reference anchors (three upload columns).
- Step 4 — interview (five free-text fields).
- Step 5 — draft & review (the raw Bible textarea).
- Step 6 — model bake-off.
- The three document panels at the bottom (Bible, lessons, keys).
- The 2a left-rail step spine + DOCUMENTS rail (Phase 2, deferred by ruling).

## Build order

Presentation and extraction interleave deliberately: R1/R3/R4 need no new
data, R2 is built flat then upgraded, and the mocks' environment/PROPOSED
elements light up only after the extraction work.

### P1 — R1 reveal strip
Summary strip as the step's lead (counts → section links, logline inside).
Counts from the existing payload; the ENVIRONMENTS count renders only when
the field exists (0 → omit the count, not `0 ENVIRONMENTS`). Demote step 1's
lead treatment while an unreviewed analysis exists. Detail: `READ_REVEAL_PLAN`
R1.

### P2 — R3 questions as the interview
One answerable row per open question; answered rows get the `--ok` ledger
border; answers append to the interview payload the drafter already reads.
Step 4's intro gains the one-line note. Detail: `READ_REVEAL_PLAN` R3.

### P3 — R4 uncast triage
Capped rows + `▾ n more` + per-row bulk cast. Prominence counts render only
if present (`TODO(prominence)` at the sort site until then). Detail:
`READ_REVEAL_PLAN` R4.

### P4 — R2 locations as a flat finder list
Shared builder with the screenplay stage's coverage table — extract one code
path, do not fork. Flat, screenplay order, no grouping yet. Detail:
`READ_REVEAL_PLAN` R2.

### P5 — Gap 5: confirmed/proposed worlds + faction self-check
`status: CONFIRMED | PROPOSED` on worlds, merge-on-rerun (confirmed survive
by name), the self-check call fed `analysis worlds ∪ Bible language sections`,
failure degrades silently. Chip vocabulary and the new Unlock & re-run copy
per `EXTRACTION_GAPS_APPROVED` §1–2. Reveal strip gains `· n PROPOSED`.

### P6 — Gap 6: environments
Schema addition on the existing analyze call; `## Environments` container in
`SYSTEM_SECTIONS` with level-3 entries; `render_context(environments=…)`;
optional `environments: []` on specs; environment locations assigned verbatim
from the deterministic slugline list. Detail: `EXTRACTION_GAPS_RESPONSE`
Corrections 1–2 + the matching fix, ruled in `EXTRACTION_GAPS_APPROVED`.

### P7 — Environments in the UI
Environment cards in step 2 (mock 6a), P4's finder list flips to grouped
(zero fuzzy matching — it inherits the assigned lists), coverage table
inherits the same grouping, per-row reassign via the existing analysis save
path. Empty state for older payloads per `EXTRACTION_GAPS_APPROVED` §4.

### P8 — Sheet scope: language × environment
Environment selector beside the language checkboxes, the atmosphere-precedence
copy line, and the `PROMPT WILL CARRY` line listing `ENV: <NAME>` between
languages and lessons (mock 6c). Lighting studies inherit the parent's
environments alongside its languages.

### P9 — C13 step-state badges + doc pass
Badges on every step h2 from data already fetched (step 3's reads
`n CAST · m UNCAST`; step 2's reflects PROPOSED count). DESIGN_SYSTEM.md:
PROPOSED chip state beside the vocabulary-picker entry, environment card
anatomy in Components, changelog lines. Update the Workflow subview's chain
copy if environments changed it.

## Done criteria for the stage

- A fresh read presents as a reveal, not a wall: strip → logline → languages
  (with PROPOSED) → environments → grouped locations → answerable questions.
- Re-running preserves every confirmation and manual assignment; Resistance
  arrives PROPOSED on the Beltminers data.
- Casting 8 principals takes one click per row, not 47 clicks.
- A sheet's scope states both what culture and what world it draws from, and
  the carry line proves it.
- Answered questions demonstrably reach the Bible draft.
- Steps 1, 4, 5, 6 still work exactly as before — untouched.

## Ground rules

Tokens only; the reveal strip is the stage's one lead; machine values Courier.
Reuse existing vocabularies (lead, finder list, ledger border, chips, cards) —
nothing here should need an UNCANONIZED marker except possibly the environment
card, which is close enough to the registry-row/card families to check first.
No mutating-endpoint changes beyond the two schema additions ruled above.
