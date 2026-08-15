# STEP_SEQUENCE_SPEC_2026-08-14.md — PART 4 ONLY

Parts 1, 2 and 3 shipped 2026-08-14 and are folded into
`app/static/DESIGN_SYSTEM.md`; Parts 5 and 6 were already in the tree
before this spec arrived. What remains is stage 02 — and the spec itself
says not to start it until stage 04 has survived a week of real use.
See `docs/RETIRED_PLANS.md` for what shipped and the deviations reported.

Still deferred for want of a recording: the arrange room and the style
picker (SHEET_SYSTEM_PLAN's board-looks parts 3/4/5/6a/7 and all of its
arrange-room physics). They are the top of the next recording walk.

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
