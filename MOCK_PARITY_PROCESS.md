# MOCK_PARITY_PROCESS.md — verifying a build against its mock

**For the coding agent.** Two parts: a standing process to append to
`app/static/DESIGN_SYSTEM.md` (part 1), and the targeted discrepancy list
from today's first-run Settings build, which is also the worked example
(part 2). Fix D1–D8, then run the part-1 loop before reporting done.

---

## Part 1 — Append to DESIGN_SYSTEM.md as "Verifying against mocks"

> Every design mock is authored at **1360px content width**. A screen is not
> done until it passes this loop:
>
> 1. **Seed the same data.** Load the app with demo state matching the mock's
>    content. Text/count differences are expected; structural ones are not.
> 2. **Screenshot at the design width.** Headless browser, viewport 1360 wide
>    (plus page chrome), full-page capture.
> 3. **Diff.** `pixelmatch`/`odiff` the capture against the mock. Read the
>    marked-up output image; fix; re-shoot. Iterate until only content-driven
>    regions differ.
> 4. **Assert the tokens mechanically.** Image diff catches layout; computed
>    styles catch the rest. For each new component assert via
>    `getComputedStyle`: font-family, font-size, colors, border, padding,
>    letter-spacing against the mock's stated values. This is more reliable
>    than eyes for hex values and 1px differences.
>
> **What must match exactly:** tokens (hex, sizes, weights, spacing, borders),
> structure (order, alignment, grouping, fixed column widths), and
> **containment** — if the mock draws a bordered panel around a region, the
> region is inside a bordered panel, not floating on the page.
> **What never matches:** the demo content itself.
>
> The most common failure is not a wrong value but a **dropped wrapper**:
> content rendered at full page width because the mock's outer panel, its
> padding, or its internal hairline was skipped. Check containment first.

## Part 2 — Discrepancies in the shipped first-run Settings

D1 — **The outer panel is gone.** The mock wraps the whole tab in a
`#121417` panel with a `#2b3037` border and 30px padding; the build floats
every section on the page background at near-full width. Restore the panel;
everything below sits inside it. (This is the dropped-wrapper failure named
above — it caused half the other drift.)

D2 — **The quick start / notice divider is missing.** The notice column gets
`border-left: 1px solid #23272c` and 34px left padding. Without it the two
columns read as unrelated blocks.

D3 — **The SET DEFAULT MODELS rows lost their geometry.** Mock: each card is
one row — title left, dashed withheld-verb chip right-aligned (`WILL RUN ON
ChatGPT gpt-5.6`), chip sized to its text. Build: the chip became a
full-width dashed box stacked under the title. Restore the single-row layout;
the chip never stretches.

D4 — **The marquee has no edge fade.** Tiles clip hard at both ends. Apply
the mask: `mask-image: linear-gradient(90deg, transparent, #000 8%, #000
92%, transparent)` (and `-webkit-`). The strip should dissolve, not cut.

D5 — **Active-tab marker moved.** Mock: 2px `--accent` **bottom** border on
the active tab, tab background `#121417`. Build: amber left edge. Move it
back — the left-edge accent belongs to list rows, not tabs.

D6 — **`Add model` is set in the wrong voice.** It is an action, so it is
Archivo 12.5px with the underline treatment like every other text act —
the build set it in Courier caps, which is the machine-data voice.

D7 — **The subnav kept the `PRODUCTIONS MOVED` pointer.** The 18a mock drops
it (first-run users have no productions to manage). Render it only in the
configured state.

D8 — **Spacing tightened everywhere by the missing padding.** After D1,
re-check section paddings against the mock: 30px panel padding, 22/30px
section padding, 26px gap between the two hero columns' contents.

Run the part-1 loop after D1–D8; attach the final diff image to the commit.
Changelog `DESIGN_SYSTEM.md` (new Verifying-against-mocks section). Delete
this file when done.
