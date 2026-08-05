# SWATCH_GENERATE_RULING.md — the act goes where its condition is met

**For the coding agent.** Rules the single open row in the Uncanonized table
(2026-08-06, swatch-generate flow inversion). No mock needed — this moves one
control and adds one line. Read `app/static/DESIGN_SYSTEM.md` first.

## The defect

`Generate swatches` sits in step 1's Color Palette column but cannot run
until step 5's Bible is saved. The user meets the verb four steps before it
can work, and satisfying it means walking down the page and back up. Arming
the gate on save fixed the lie; it did not fix the walk.

## The ruling — split the verb from the result

**The act moves to step 5, beside the saved Bible. The swatches stay in step
1's column.**

This is the L2 popover rule inverted, and it should be canonized as its pair:

> **An act lives where its precondition is met; its result lives where it
> belongs.** When those are different places, the act states where its output
> landed and links there. Never place a verb next to its result if the verb
> cannot run there.

Concretely:

1. **Step 1, Color Palette column** — remove the `Generate swatches` control
   and its `NEEDS A SAVED BIBLE` tag. The column keeps: manual hex add, the
   swatch rows, and (when swatches exist) its normal count chip. Nothing in
   the column explains where they came from beyond each row's existing
   `source` provenance.
2. **Step 5, under the saved Bible** — after a successful save, a bordered
   ghost row appears: `Generate palette swatches` with the Courier line
   `FROM THE SAVED BIBLE · LANDS IN STEP 1 / COLOR PALETTE`. Ghost, not
   amber: `Draft Art Direction Bible` owns this page's amber, and generating
   swatches is a follow-on, not the page's primary act.
3. **On completion** — a stated result line beside the control:
   `N SWATCHES PROPOSED IN COLOR PALETTE` with a link that scrolls to step 1
   (offset math, never `scrollIntoView`).
4. Before a save exists, the row does not render at all. A withheld-verb tag
   would be correct grammar but wrong judgement here: step 5's own gate
   already explains the situation two lines above, and stating it twice on
   one screen is the verbosity D1 just cut.

## What is not changing

- Proposals still persist as **PROVISIONAL refs** (D8's correction stands) —
  the approval log must record what was rejected.
- The approve/reject controls stay in the column, on the rows themselves.
  Judging a swatch happens where the swatch is.
- Re-drafting the Bible after approving swatches is the user's call; do not
  prompt for it. The Bible already states its own staleness.

## Canon

Add the paired rule (above, in blockquote) to Layout patterns, directly under
the L2 anchored-explanation entry — they are the same principle facing
opposite directions, and reading them together is what makes either
memorable. Delete the Uncanonized row. Changelog:
`**2026-08-06** — Swatch generation moved to step 5 beside the saved Bible;
act-where-condition-is-met canonized as the pair to anchored explanation.`

Delete this file when shipped.
