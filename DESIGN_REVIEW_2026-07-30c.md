# DESIGN_REVIEW_2026-07-30c.md — five-pattern review

**For the coding agent.** Rulings on all five uncanonized rows. Apply, fold
into DESIGN_SYSTEM.md, clear the table, delete this file and hatch-test
values below become canon.

## 1. Placeholder hatch — HELP WANTED answered (tested visually, 5 variants)

The 1px stripe is the problem: at 1px/9px it aliases into shimmer on
non-integer device pixel ratios. Canon spec — **2px stripe, 11px period,
45°, ink-colored, opacity per surface**:

```css
/* placeholder hatch — canonical. MUST stay last in the cascade:
   background: shorthands reset background-image. */
.hatch          { background-image: repeating-linear-gradient(45deg,
                    rgba(236,238,240,.035) 0 2px, transparent 2px 11px); }
.hatch-deep     { background-image: repeating-linear-gradient(45deg,
                    rgba(236,238,240,.05)  0 2px, transparent 2px 11px); }
```

- `--bg2` surfaces (empty slots, empty rail thumbs) → `.hatch` (3.5%).
- `--field` surfaces (empty stage shot, pending spin area) → `.hatch-deep`
  (5% — the darker ground needs more).
- TOO-SMALL red tint → `.hatch` (3.5%); the white-ink stripe reads correctly
  over `rgba(205,97,85,.07)` — do not switch the stripe to red, the border
  and label already carry the state.
- Never on populated surfaces, never behind body text panels — hatch means
  "an image belongs here and isn't here."

Implementation: replace the guessed values with these two classes; apply by
class, not by copying gradients inline, so the cascade-order footgun lives
in one place. Keep the code comment about `background:` shorthand resets.

## 2. Pending take tile + take state tags — CANONIZED

Right as built. Canonical rule: *in-flight work holds its place — a pending
tile sits in the filmstrip with the spinner vocabulary from `.busy` and
survives closing whatever screen launched it. State reads at a glance in
the strip: approved = `--ok` border + label, promoted = `· REF` suffix on
the tile and a `REFERENCE · REF-xxxx` bordered badge on the stage (status
color border, never filled — same grammar as verdict chips).* One check:
the pending tile's spinner must honor `prefers-reduced-motion` like `.busy`
does.

## 3. Scene browser — CANONIZED as "finder list"

Right call; search + expandable rows is a new need (252 items). Canonical
rule: *finder list = a Courier search field over a `--field` scrollable list
(max-height, global scrollbar), parent rows expand to children, every row
ends in its one verb (Draft a sheet / Open sheet). Row anatomy follows
registry rows: Courier identity left, facts middle, ghost/text action
right. Reuse it for any >30-item findable list; below ~30, the coverage
table pattern is enough.* One check: the search field must not trap focus
or filter on every keystroke below 3 chars if the list re-render is
janky — debounce if needed.

## 4. Lock strip — CANONIZED

Exactly the right instinct: a gate readable as state, not a silent absence.
Canonical rule: *`.gate-strip.lock-strip` = the gate strip vocabulary in
grey (`--line` left border, Courier `--ink-dim` LOCKED label) stating why
editing is off, with the resolving actions inline (Create revision /
Unlock & edit as ghost buttons). Amber gate = "cannot proceed forward";
grey lock = "cannot edit backward." Any state that hides controls must
surface one of the two.*

## 5. Object intake row — MERGED into intake row, not a new pattern

The fix is right; the lesson is general. Add one line to the existing
intake-row canon: *an intake row is always a full-width row of its own —
never placed inside a column of a wider grid, where a sibling's intrinsic
size can starve the input. The text input is the widest element; selects
are capped.* Then delete this table row (it's a bug fix + a sentence, not
a component).

## Presentation rulings from the changelog — reviewed, all approved

Cover-crop with originals a click away, either-dimension TOO SMALL, board
grammars seeding blank sheets, CAPS-as-typed sheet IDs, Read-the-screenplay
in the reading view: all consistent with the system. No changes.

## Doc moves

1. Hatch: add to Layout patterns as above (with the cascade warning);
   patterns 2–4 into Components; pattern 5 folded into the intake-row
   entry. Clear the table.
2. Changelog: `**2026-07-30** — Review c: placeholder hatch specced by eye
   (2px/11px 45°, 3.5% on --bg2 / 5% on --field, class-applied); pending
   tiles, take tags, finder list, lock strip canonized; object intake row
   folded into intake-row rule.`
3. Remove the five `/* UNCANONIZED */` markers.
4. Delete this file.
