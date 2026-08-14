# STEP_SEQUENCE_SPEC_2026-08-14.md — PARTIALLY IMPLEMENTED, TRIMMED

**Part 1 (the vocabulary) and Part 2 (stage 04) shipped 2026-08-14** and
are folded into `app/static/DESIGN_SYSTEM.md`; Parts 5 and 6 were already
in the tree before this spec arrived. What remains below is the un-built
work, kept verbatim. See `docs/RETIRED_PLANS.md` for what shipped, the
four reported deviations, and the user's rulings on the stage-03
questions.

Mock `design_mocks/hier-5a-breakdown.png` specs Part 3.

**User rulings carried into the stage-03 pass (2026-08-14):**

- The evidence ledger is a HYBRID: the selects the user directed on
  2026-08-13 stay while a sheet is drafting; a confirmed or locked ledger
  reads as the stated table §3.35 asks for, with editing behind the row.
  §3.35's "always a table" reading is declined.
- §3.15 (the breakdown opens on its panels' takes) is APPROVED.
- §3.3 (creation cards collapse into one `New breakdown` verb) is
  DECLINED — the creation cards stay as they are.
- The duplicate forbidden entries are DECLINED as a data change; the
  board's "unsupported animals" and the panel's "unsupported pets or
  animals" both keep riding the prompt.

---

# Part 3 — Stage 03, Breakdowns · `hier-5a-breakdown.png`

Measured today: the editor opens at **y=1452**, below the entire "create a
different one" form. Creation is the rarest act on the page and it is first and
largest.

## 3.1 The sequence — **seven sections, not six**

```
01  IDENTITY         mode, board type, canvas, slugline fields
02  DIRECTION        the scene, render intent, forbidden lines, budget
03  OPEN QUESTIONS   0 of 12 answered
04  SCOPE            design languages, environment, scene lessons
05  PANELS           2 · allocation 100%
06  EVIDENCE         21 rows · every object has a PASS row
07  APPROVE & LOCK   the act
```

My first pass guessed six and dropped IDENTITY (`Mode` CANON_EXTRACTION,
`Board type` LOCATION, `Canvas`) and the slugline fields (`INT/EXT`,
`Location`, `Atmosphere`) entirely. They are real, they are the first thing on
the page, and a spec that omits them would have deleted working controls.

## 3.15 The breakdown opens on what it has made

The shipped page has **no imagery at all**, on a surface whose entire job is
describing two pictures. Reviewing a specification without seeing what it
produced is reviewing it blind.

Open on a two-up of the board's panels at 21:9, above step 01:

- **P01** — its approved take, tagged `P01 · CAND-0046` and
  `APPROVED · 3136 × 1344` in `--good`.
- **P02** — an **empty frame** (`--panel` ground, `--line` border) stating
  `NO TAKE YET`, with `SIZE — CANVAS TOO SMALL FOR 2 HERO PANELS` in `--bad`
  on the frame itself.
- Beside them, the stake in one line: *One panel approved of two. The board
  cannot be assembled until P02 has an approved take.*

The empty frame is the more valuable of the two: it is the only place `SIZE`
reads as a **consequence** — the picture that does not exist because of it —
rather than as a red tag in a rail. This is the sanctioned exception to *never
reserve the shape of the missing thing*: the shape is the subject's own aspect
ratio and the frame states its blocker, so it is a report, not a placeholder.

## 3.2 The two findings this exposed

**Open questions are step 02, not a bullet under the header.** They are the
highest-leverage thing on the page: each answer becomes canon for every future
render, and each blank one is a licence for the model to invent. State the
consequence in the step —
`ANSWER ONE AND IT BECOMES CANON · LEAVE IT OPEN AND THE RENDER IS TOLD NOT TO
INVENT ONE`.

**Approve states its gate.** A draft with twelve open questions can be
approved, so say `12 QUESTIONS UNANSWERED — YOU CAN STILL APPROVE`.

## 3.3 Creation and the switcher

The two creation cards become **one `New breakdown` verb at the end of the
switcher row**. The breakdowns table becomes that switcher: three ids you move
between without leaving the editor. Rarest act, smallest footprint, still one
click.

## 3.35 The evidence ledger is the best content in the app

Every row cites a real slugline:
`INT. SHACK CONTINUOUS: "Animal hides dry near a cast-iron stove."`

The shipped page renders each row as **five selects** — panel, object, source,
citation, state — so twenty-one rows are 105 controls. It is a provenance
record being displayed as a data-entry form.

Ruled: **a confirmed ledger reads as a table of stated facts** — Courier ID,
object, source enum, citation, one `PASS` in `--good` — with editing behind the
row. Sources are `SCRIPT_EXPLICIT`, `SCRIPT_NECESSARY_INFERENCE`,
`VISUAL_CANON_LOCKED`, `USER_DIRECTED`; states are `PASS` / `HOLD` / `REMOVE`.
Do not truncate the object column — the longest real object string
(`worktable with handmade metal part and mold`) needs 330px.

## 3.4 The right rail is provenance, not settings

Who drafted this (`gpt-5.6`, from `INT. SHACK · 6 SCENES`), what the prompt will
carry, and **what already depends on it** (2 takes rendered, 1 of 2 panels
approved, no boards built). That is the question you actually have when
deciding whether to approve.

Locked, so the rail reads as a document, not a greyed-out form.

## 3.5 The transfer finding

**A panel is a rail item where you pick it and a full-width row where you edit
it.** Same data, opposite verb — the same object legitimately takes two shapes
across surfaces. Do not try to share one component.

---

# Part 4 — Stage 02, Production Design

**8901px, 370 uppercase labels, six-step rail that scrolls away after 200px.**
The largest job in the app, and deliberately not mocked — prove the vocabulary
on stages 03 and 04 first, then bring it here.

What is already decided:

1. **The step rail sticks.** For 8700px there is currently no indication of
   which step you are in. At these lengths position is information and the app
   discards it.
2. **Each of the six steps is a step in the Part 1 sense** — a number, a state,
   one verb. The wizard already is a sequence; it just does not look like one.
3. **The 370 labels resolve by tier**, mostly by asking whether the row is a
   choice or a report. `read-lab` and `step-cond` are reports.
4. **The camera row keeps its full controls here** (Look Interview and the
   breakdown editor author these values), and wraps **3 + 2, never 4 + 1** —
   five peers must not split one-off.

Do not start this until 4a ships and survives a week of use.

---

# Part 5 — Reference

From the canonization pass, unchanged and still pending:

- **Unanchored locations are a register, not uncast cards.** A place with no
  reference has nothing to judge; an image-sized empty well reserves the shape
  of the missing thing. Labelled table under the SCENES shelf, one act per row.
  No own shelf.
- **The ramps are the STYLE shelf.** Nineteen swatch cards restating three ramps
  is the wall the ramps were added to fix. Plates live behind the group viewer.
  Quarantined swatches keep their cards.

Apply Part 1's type scale and verb treatment when you touch it; the shelves
themselves do not become a step sequence — Reference is a library, not a
sequence, and forcing steps on it would be the same category error as putting a
card on a place with no picture.

---

# Part 6 — Status

- **The lead promotes, it does not copy.** The `.panel-lead` next-row and the
  first `.block-row` carry the identical 22-word sentence with two identical
  buttons — verified, the string occurs exactly twice. A row promoted into the
  lead is **removed** from the list below and the count excludes it.
- **Delete `.stor-bar`.** The coverage meter is the only meter vocabulary.
  Storage is a Courier line, `FREE 214 GB OF 500 GB · 57% USED`, whose colour
  carries its state.

---

# Part 7 — Canon to add

Into **Layout patterns**, first and outranking the rest:

0. **The image is the hero.** This app makes movies. On any surface that has a
   picture, the picture is the largest element on it, at the subject's own
   aspect ratio; alternates are a filmstrip beneath it; the specification sits
   below the image, never above it. Facts about an image ride on it. A rail holds
   only what has no picture. **A surface that could show imagery and does not is
   a defect.**

1. **Three type sizes per surface, and the largest anchors the rest.** 24 / 15 /
   11.5. Two roles may share 15px separated by weight only because 24px exists
   above them. At 11.5px the font family carries the meaning: Courier is a
   machine fact, Archivo is a verb.
2. **Fill classifies; border does not.** Accent fill is the primary act, panel
   fill plus a hairline is a set member, no fill plus a hairline is a secondary
   control. A set-member tile always sits one value above its ground.
3. **A verb is full ink and underlined, and every verb on a surface aligns to
   one right edge.** Colour alone cannot separate an 11.5px verb from an 11.5px
   fact.
4. **A surface whose job is a sequence numbers its steps**, and the number — not
   a label gutter — is the spine. Two states only: needs you, or confirmed. A
   confirmed step dims and stays legible.
5. **A gate states its condition and does not lie.** If unconfirmed steps do not
   block the act, say so rather than disabling the button.
6. **The gutter is for rows, not blocks.** A label with a grid under it sits
   above its content.
7. **Cap prose measures independent of surface width.** 720px body, 900px
   Courier. Extra width goes to rails and grid columns, never line length.

Into **Do not**:

8. **Do not truncate a title.** Two panel titles that differ only in their last
   word are the same string once cut. Wrap it, on its own row if the column is
   narrow.
9. **Do not state a count without making it provable.** `2 WITH A REFERENCE`
   requires a mark on those two. Never mix an image count against a group
   denominator.
10. **Do not use two words for one state.** `REVIEWED` and `CONFIRMED` on one
    surface is a third state the head then miscounts.

---

# Order of work

0. **The hero take and filmstrip on stage 04** (§2.15). Smallest change with the
   largest effect, and it is independent of the step sequence — ship it first
   even if the rest slips.

1. **4a, stage 04** — the reference implementation. Everything else depends on
   the vocabulary being right here.
2. **5a, stage 03** — proves the transfer costs nothing.
3. Status (Part 6) — two small, self-contained fixes.
4. Reference (Part 5) — the two shelf rulings.
5. **Stage 02 last**, and only after 4a has survived real use.

# Still needed from a recording

The arrange room and style picker are absent from the bundle and are the newest,
densest surfaces in the app. They are the top of the next recording walk — if
they are as dense as the workbench they belong in this vocabulary, not
retrofitted after it.
