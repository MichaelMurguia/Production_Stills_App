# LOCKED_STAGE_PLAN.md — a locked stage is a condition, not a destination

**For the coding agent.** Replaces the current Breakdowns locked-stage screen
and the `Open Production Design` button. Mocks:
`design_mocks/12b-locked-stage.png` (chosen) and
`12c-stage-empty-state.png` (its companion). Read
`app/static/DESIGN_SYSTEM.md` first. One task per commit, L1→L4.

## The problem being fixed

The locked Breakdowns screen ends in an `Open Production Design` button. That
button duplicates navigation that is already on screen — stage 02 sits two
cells to the left in the band, already flagged red, already reading *"no
bible yet."* Worse, it teaches that the band is not how you move. And the
user had to load a dead page to be told to leave it.

## L1 — Locked stages do not open

A stage cell whose gate is unmet is **inert**: no navigation, no view change,
no history entry. This applies to every unmet stage, not just the next one —
today 04 and 05 are equally locked and still look clickable.

Locked cell treatment (mock 12b):
- Background `#17191c` (below `--bg2`), `cursor: not-allowed`, no hover.
- Labels stay `--ink-faint`. **Do not dim below that** — the band is the
  product's map and every stage name must stay readable. `#4a4d52` is
  sanctioned for disabled buttons only.
- A bordered `LOCKED` chip in `--hold` beside the stage name.
- `aria-disabled="true"`; keep it focusable so keyboard users get the same
  explanation.

## L2 — Clicking a locked stage explains, in place

The click opens a **popover anchored under the first unmet stage's cell** —
not under the cell that was clicked. The user stays exactly where they were;
the view behind does not change.

Popover (mock 12b), `--panel2` on a `#3a4048` border, no top border so it
reads as hanging from the band, drop shadow, width spanning roughly two band
cells from the target cell's left edge:

- Header: bordered `--hold` chip naming what is locked (`03 IS LOCKED`) and a
  `×` to dismiss.
- One sentence: *"Breakdowns need the Art Direction Bible. **Four steps here
  first.**"*
- The remaining gate steps, Courier, current step `→` in amber and the rest
  `·` in `--ink-faint`.
- Footer line: `03 UNLOCKS ITSELF THE MOMENT THE BIBLE IS SAVED`.

Dismiss on `×`, Esc, or any click outside. If the first unmet stage is the
one the user is already on, the popover still anchors to it — that is the
correct answer to "why can't I go forward."

## L3 — The gate steps, stated correctly

The Breakdowns gate is **four steps**, all in Production Design:

1. **Run the script scan** — reads the draft for design languages,
   environments, locations and cast
2. **Add style reference** — board layout, cinematography and rendering
   plates, the three anchors
3. **Complete the look interview** — touchstones, medium, palette, and what
   it must never look like
4. **Draft the Art Direction Bible** — everything above becomes the document
   every render obeys

Then Breakdowns unlocks itself; there is no fifth step for the user to take.
Drive the list from real state so completed steps drop off as they are done —
a checklist that doesn't move is a poster.

**Dev note, from the director:** Production Design steps **3 and 4 swap** —
the look interview moves ahead of cast & subjects. Casting belongs after the
bible: a card's photos are reference gathering, not a precondition for
drafting. Renumber the `data-step` attributes when the panels move; they are
static markup, not generated.

## L4 — The reachable-but-empty state (mock 12c)

When the gate is met and Breakdowns has no sheets, the stage opens normally
and shows the checklist pattern instead of an explanation-plus-button:
one bordered list, one row per step, each row carrying its verb, a one-line
subtitle of what it does, and its address (`STAGE 02 ↗`). The current row
gets the amber left border and `--panel2` fill; done rows collapse to a
single `✓` line. **No generic navigation button anywhere on the screen** —
the rows are the navigation.

Use the same component for any stage's empty state; only the rows change.

## Ground rules

Tokens only; no new grey; square corners. Amber appears once — on the current
step's marker and border. Machine values Courier, prose Archivo. Remove
`Open Production Design` and any sibling "go to stage" buttons. Never
`scrollIntoView`. Add to `DESIGN_SYSTEM.md`: the locked-cell treatment and
the anchored-explanation popover under Layout patterns, and the stage
checklist under Components; changelog it. Delete this file when done.
