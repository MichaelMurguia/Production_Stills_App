# STORE_PIPELINE_PLAN.md — build `/pipeline`

**For the coding agent.** New page at `/pipeline`, linked from the homepage
hero's "See the pipeline" and the header. Mock:
`design_mocks/store-pipeline.png` (1180px design width). Read
`STORE_DESIGN_SYSTEM.md` first — especially §8 on amber's four roles; this
page uses all four and that is correct.

New route, new template (`storefront/app/templates/pipeline.html`), no data
dependencies — it is a static marketing page. Add it to the CI route check.

## Page order

1. Header (`The pipeline` is the active tool)
2. Hero — `THE METHOD` / "How a screenplay becomes a board." / four Courier
   production figures right-aligned
3. **The long walk** — sticky rail + five stage sections
4. **The case file** — five rows on a darker ground
5. Closing CTA band, footer

## P1 — The long walk

A two-column flex: a `196px` rail on `--bg2`-dark (`#0d0f12`) with
`position: sticky; top: 20px` inside it, and the stage column beside it.
Rail lists the five stages plus a `CASE FILE` entry under a divider; the
active entry gets the amber left border, amber Courier text and a
`#15181b` fill. Wire active state to scroll position with
`IntersectionObserver` (no library); if that's fussy, ship it static on
`01` and note it — the page is readable either way.

Each stage section is the same shape, which is the point — the reader
learns the rhythm once:

```
[ 34px Courier stage number, --line ]  [ h2 + one paragraph, max 62ch ]
[ the artifact, full width, bordered ]
[ two footnote columns, 2px left borders ]
```

**The artifacts** — all real, from `storefront/app/static/img/`:

1. **Screenplay** — the formatted page (Courier, `white-space: pre`) beside
   an amber-bordered `THE READ FOUND` panel listing the counts. Keep the
   screenplay indentation exact.
2. **Production design** — the Cinematography lookbook card (CONTROLS in
   `--ok`, NEVER in `--bad`, three plates with `IN USE` badges) plus the
   design-language chip row, with `RESISTANCE · PROPOSED` as a dashed
   `--hold` chip.
3. **Breakdown** — the script excerpt with extracted phrases highlighted,
   beside the full six-row element table, FORBIDDEN line beneath.
4. **Panels** — the staged panel with its facts bar, a takes strip below
   (rejected takes at `opacity:.45`, the approved one bordered `--ok`), and
   a `262px` provenance rail: ANCHORED TO, SCOPE, CARRIED REJECTIONS.
5. **Board** — the finished board with its facts bar.

**The footnotes are the argument of the page.** Every stage ends with two:
one `THE GATE` in `--ok` stating the rule that closes the stage, and one
concept note in `--accent` or `--hold` explaining the idea a buyer won't
already know (`WHAT PROPOSED MEANS`, `WHY JURISDICTIONS`, `WHAT HOLD
MEANS`, `NATIVE RESOLUTION`, `THE LOOP CLOSES`). Do not drop these to save
space — without them the page is a feature list.

## P2 — The case file

Same five beats, one scene, on `#0d0f12` so it reads as a separate chapter.
Five rows, each `240px` label column + artifact. Copy is past-tense and
specific ("Nine takes. Take six carried the cabin but lost the asteroid
field; take nine held both.") — this section earns trust by being concrete,
so keep the numbers and don't genericize them.

## P3 — Performance

The board and panel PNGs are 3–4K source files. `loading="lazy"` on
everything below the hero (already in the mock), and generate downscaled
web copies at ~1.5× their rendered size — do not ship 3840px files to
render at 640px. Keep the originals for the gallery page.

## Ground rules

Tokens only; square corners; Archivo for hierarchy, Courier for machine
data. Amber per §8: one fill (`See pricing`), one kicker per section,
highlights only in the breakdown excerpt, one active rail item. Status
colors carry the footnote labels. No frameworks, no new fonts, no emoji.
Keep `/pipeline` serving 200 for CI.
