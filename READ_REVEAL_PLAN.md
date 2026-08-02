# READ_REVEAL_PLAN.md — Production Design step 2: the reveal (items 1–4)

**For the coding agent.** Presentation only — NO extraction/prompt changes in
this plan (the faction self-check and environments axis are a separate round).
Read `app/static/DESIGN_SYSTEM.md` first. One task per commit, R1→R4.

Mocks: design_mocks/6a-read-reveal.png (reveal strip, PROPOSED language chip,
environment cards, grouped location finder, questions-as-interview),
6b-uncast-triage.png, 6c-scope-language-environment.png. 6a/6c show the
POST-EXTRACTION state (environments, prominence counts, PROPOSED chips) —
build R1–R4 against current data now; those elements light up when
EXTRACTION_GAPS.md lands. Layout positions for them are already in the mocks.

Data note: everything below renders from the existing `wizAnalysis` payload.
Where a field doesn't exist (scene-mention counts for ranking), the plan says
what to do instead — do not invent data or add endpoints in this round.

## R1 — The reveal strip

After a successful read, the analysis section opens with a summary strip
(before the logline), replacing nothing:

```
THE READ FOUND
5 DESIGN LANGUAGES · 26 LOCATIONS · 55 SUBJECTS · 14 OPEN QUESTIONS
```

- Counts computed from the payload (languages, key_locations, subject
  recommendations, open questions — see R3 for splitting questions).
- Courier, `--ink`; each count is a text link that scrolls to its section
  within step 2/3 (window.scrollTo recipe — never scrollIntoView).
- The strip is the panel-lead treatment INSIDE the step (amber left border,
  `--panel2`) — the one lead of the wizard view while unreviewed. Logline
  renders directly beneath it, then the language chips.

## R2 — Locations become a finder list

Replace the `Recurring locations:` prose blob with the finder-list component
(canonized 2026-07-30) fed by `key_locations`:

- One row per location: Courier name · sheet-match state (same fuzzy match as
  the screenplay stage's coverage table) · one verb: `Open sheet` when matched,
  `Draft a sheet` (prefills `#spec-auto-prompt`) when not.
- Search field above; max-height ~340px, global scrollbar.
- No grouping headers yet (environments come in the next round). Flat list,
  screenplay order.
- The screenplay stage's coverage table and this list must render from the
  same code path — extract a shared builder, don't fork a second one.

## R3 — Open questions become the interview

Replace the `Open visual questions:` paragraph with one row per question:

- Split the existing dot-separated string into items (split on `" · "`; if the
  payload already carries an array, use it — check first).
- Row anatomy: Courier `Q01`-style index · question text (sans, `--ink-dim`,
  74ch) · a compact answer affordance: an inline text input revealed by an
  `Answer` ghost button, plus a `Decide later` text button that dims the row
  (state in the analysis JSON, persisted via the existing analysis-save path
  if one exists; otherwise localStorage keyed by spec-safe hash of the
  question text — note which you used).
- Answered rows: `--ok` left border (2px, ledger vocabulary), the answer shown
  in Courier under the question.
- Header: `OPEN QUESTIONS — n ANSWERED OF m` and one line of copy: "The read
  couldn't settle these. Answers are appended to the interview and honored by
  the Bible draft."
- Wiring: on Draft (step 5), append answered pairs to the interview payload as
  `Q: … / A: …` lines in the notes field the drafter already reads. No new
  endpoint.
- Step 4's intro gains one line: "Questions you answered in step 2 are already
  included."

## R4 — Uncast triage

The uncast block currently renders 47 chips as an undifferentiated wall.
Without mention-count data this round, triage by what exists:

- Keep the CHARACTERS / VEHICLES / PROPS rows, but cap each row's initial
  render: first 8 chips + `+ n more` expander chip (ghost, dashed) per row.
- Order within a row: payload order (extraction lists principals first in
  practice; do not re-sort alphabetically).
- Add one bulk action per row header, right-aligned: `Cast first 8` (ghost).
  Bulk-cast calls the same single-cast path in sequence; toast the result
  (`8 cast — 3 already existed`).
- The step badge (`8 CAST · 47 UNCAST`) is unchanged.
- When mention counts arrive in a later extraction round, the cap upgrades to
  a real PRINCIPALS/SUPPORTING split — leave a `TODO(prominence)` comment at
  the sort site.

## Ground rules

Tokens only; the reveal strip is the wizard's one lead — if the step-1 panel
currently carries `panel-lead`, demote it while an unreviewed analysis exists.
Amber budget: strip border + one primary per step, unchanged elsewhere. All
new patterns reuse existing vocabularies (lead, finder list, ledger border,
chips) — nothing here should need an UNCANONIZED marker. Update
DESIGN_SYSTEM.md changelog with one line; delete this file after applying.
