# DESIGN_REVIEW_2026-07-30.md — rulings on FEATURE_INVENTORY.md ⚑ items

**For the coding agent.** Apply Part 1's refinements, then Part 2's doc moves,
then delete this file. Everything here is a ruling — nothing is left open.

## Part 1 — The three uncanonized patterns: canonized, with refinements

### 1a. Compact add-reference row (`.ref-add`) — CANONIZED as "intake row"

The pattern is right: one-line intake at the top of a library, explanations in
tooltips. Two refinements before it enters the doc:

1. The role input is the one field a first-time user can't guess. Give it (and
   only it) a visible ghost label: a Courier `--ink-faint` 10px `ROLE` prefix
   inside the row before the input (the other fields keep placeholder-only).
   If this crowds the row at 1100px, drop the prefix at that breakpoint.
2. `+ Add` is an ordinary ghost button, not primary — an intake row must not
   spend the screen's amber. Confirm this is already true; fix if not.

Canonical rule for the doc: *an intake row is for high-frequency entry into a
list/library directly above it; max 6 fields; placeholders name fields,
tooltips explain them; the submit is ghost; anything needing explanation
beyond a tooltip belongs in a dialog instead.*

### 1b. Custom engine rows (`.eng-row`) — CANONIZED as "registry rows"

Right as shipped: name in sans, facts in Courier ellipsized, actions flush
right. One refinement: the LAST TEST cell should use the same
PASS/FAIL coloring as the engine cards (`--ok` / `--bad` on the verdict word
only, date stays faint) — consistency across the two test surfaces.

Canonical rule: *registry rows list user-registered externals (engines, and
any future integrations): sans name · Courier facts (ellipsize middle) ·
Courier test-state · ghost actions. Rows separated by `--line-soft` top
borders; no cards-within-cards.*

### 1c. Prompt reading view (`promptOverlay()`, `.modal.prompt-full`) —
CANONIZED as the "reading view" variant of the app dialog

Right as shipped: 900px modal, Courier `<pre>` on `--field`, Copy + Close.
Two refinements:

1. Add the prompt's identity line above the `<pre>` in the modal: Courier
   faint `P02 · CAND-0026 · GEMINI 3 PRO · 4K` — a copied prompt loses its
   context otherwise, and a reading view should say what it holds.
2. Copy button gives feedback via the existing toast ("Prompt copied —
   4,812 chars"), not a label swap.

Canonical rule: *reading view = the app dialog at `min(900px, 94vw)` holding
one scrollable Courier document on `--field`, an identity line above it, Copy
+ Close. Use it for any machine document too long for a rail (prompts, logs,
raw JSON) — never for forms.*

## Part 2 — Open questions answered

1. **Pipeline size cap: yes, surface it visibly.** A tooltip is invisible at
   the moment of choice. When MODEL = PIPELINE, render under the Size select
   one Courier `--accent` 10.5px line: `PIPELINE CAP — RENDERS AT ≈1.5K
   PRESET`. Reuse the `.eng-note.warn` vocabulary. Additionally, if the user
   has SIZE = 4K selected when switching to PIPELINE, the note is the only
   signal they'll silently get a smaller file — that state alone justifies
   the visible line. No dialog, no toast; a quiet standing fact.
2. **Custom engines excluded from repair: correct, keep it.** Repair
   promises mask fidelity the OpenAI-images contract doesn't guarantee
   across arbitrary servers; a broken repair looks like the app's fault. No
   opt-in flag until a real user asks with a real server — then it's a
   checkbox on the add-engine dialog ("supports mask edits"), default off.
3. **Wizard left-rail spine stays Phase 2.** Unchanged.

## Part 3 — Doc moves

1. In `DESIGN_SYSTEM.md`: move the three patterns from the uncanonized table
   into `## Components` using the canonical rules above (intake row, registry
   rows, reading view). Clear their table rows.
2. Changelog line: `**2026-07-30** — Design review: intake row, registry
   rows, and reading view canonized (with role prefix, test-state coloring,
   identity line); pipeline size cap surfaced on the Size select; custom
   engines stay out of repair by ruling.`
3. Remove the `/* UNCANONIZED */` markers from the two styles.css blocks
   (and the prompt-full block if marked) — they are canon now.
4. Delete this file.
