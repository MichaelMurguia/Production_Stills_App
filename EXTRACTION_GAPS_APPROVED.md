# EXTRACTION_GAPS_APPROVED.md — design rulings on the response, build go-ahead

**For the coding agent.** All findings in `EXTRACTION_GAPS_RESPONSE.md` are
accepted: confirmed/proposed state + merge-on-rerun (Correction 1),
environments on the level-3 Bible mechanism (Correction 2), and slugline-
constrained environment locations (the matching risk — your recommendation is
adopted verbatim: assignment, not generation). Build Gap 5 then Gap 6.
Rulings on the three points that needed design decisions:

## 1. Chip state vocabulary (Gap 5)

- CONFIRMED world chip: exactly the current chip (solid `--line` border,
  `--ink`). Confirmation is the default state, not a badge — no ✓, no color.
- PROPOSED chip: dashed `--hold` border, `--hold` text, suffixed
  `· PROPOSED — CONFIRM / DROP` per mock 6a. Confirm flips it to a plain
  chip in place; Drop removes it with a toast (undo via re-run).
- Editing-and-saving a proposed world = implicit confirm (as you proposed) —
  but still flip the visual immediately on save.
- The reveal strip counts them separately: `6 DESIGN LANGUAGES · 1 PROPOSED`.

## 2. Unlock & re-run dialog copy (replaces the "replaces everything" warning)

> Re-running the read keeps everything you've confirmed — design languages,
> environments, and their location assignments survive by name. New finds
> arrive as PROPOSED for your review. Answered questions and cast subjects
> are never touched.

Use the app dialog, not `confirm()`, if Task 7 (dialog replacement) has
landed; otherwise keep `confirm()` with this text and leave a TODO.

## 3. Environment vs. per-sheet atmosphere (the double-steer)

- Injection order as you recommended: environment block before SETTING lines;
  sheet atmosphere wins ties.
- UI copy, one line under the environment selector (mock 6c position):
  "Environment sets the biome's palette and light. ATMOSPHERE below is this
  sheet's weather and mood — it wins where they overlap."
- The `PROMPT WILL CARRY` line (mock 6c) lists `ENV: <NAME>` between
  languages and lessons, matching injection order.

## 4. Older payloads (Gap 6 implication 1)

Approved as proposed, with the empty state written as a quiet standing line
in the ENVIRONMENTS block position, Courier `--ink-faint`:
`NO ENVIRONMENTS IN THIS READ — RE-RUN TO EXTRACT THEM` (the Unlock &
re-run button is already adjacent; don't add a second button).

## Done criteria

- Gap 5: re-run a project with confirmed worlds → all survive, Resistance
  arrives PROPOSED on the Beltminers data, self-check failure degrades
  silently to the main result.
- Gap 6: environment cards + grouped finder light up in step 2 (mock 6a),
  selector + carry-line in the spec editor (mock 6c), R2's flat list flips
  to grouped, coverage table inherits the same grouping with zero fuzzy
  matching.
- DESIGN_SYSTEM.md: changelog lines; PROPOSED chip state documented beside
  the vocabulary-picker entry (it is the same family: dashed = not yet real).
- Delete this file, EXTRACTION_GAPS.md, and EXTRACTION_GAPS_RESPONSE.md
  after the Gap 6 commit lands.
