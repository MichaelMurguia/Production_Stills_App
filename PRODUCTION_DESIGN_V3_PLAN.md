# PRODUCTION_DESIGN_V3_PLAN.md — remaining: D7 preset looks

**D1–D6, D8, D9 shipped 2026-08-06 (releases .64; see
docs/RETIRED_PLANS.md). This file keeps only D7, which waits on the
plate library — build it with PRESET_LOOKS_SHOT_LIST.md.**

## D7 — Preset looks — NEEDS THE PLATE LIBRARY

In the two board-facing columns only (Cinematography, Board Rendering), above
the upload control:

- Label `PRESET LOOKS (OPTIONAL)` + `Browse 5`.
- Two preset rows visible: name, `5 IMG`, and a five-frame contact strip at
  22px tall. The in-use preset carries a `--line`-lifted border on `--panel`.
- `Browse 5` opens the look browser (mock `pd3-look-browser.png`): filter
  chips, a 3-up grid, each card a 5-plate mosaic (one large + two stacked +
  two wide) with name, a two-line Courier description of what the look sets,
  and `Use this look` / `See all 5 plates`. The in-use card reads `IN USE`
  and its verb becomes `Replace column`.

**Three rules:**

1. **A look is five pre-rendered plates we ship — never a text prompt.**
   Selecting one adds real reference images, so the Bible ends up citing
   images rather than adjectives. This is the whole reason the feature exists.
2. **Looks filter to the column that opened the browser.** A cinematography
   look can never land in board rendering; the jurisdiction rule holds.
3. **Selecting never destroys user uploads.** Plates are added as approved
   refs alongside them, individually removable. Footer states this verbatim:
   `A LOOK ADDS 5 PLATES AS APPROVED REFERENCES · REMOVE ANY ROW AFTERWARDS · YOUR OWN UPLOADS ARE NEVER REPLACED`.

Plates live in `app/static/look_library/<slug>/01..05.jpg` with a
`looks.json` manifest (`slug, column, name, tags[], sets[2 lines]`). They
enter the project's reference library as approved refs with
`source: "look:<slug>"` so provenance survives. **Five looks per column at
launch** — shot list in `PRESET_LOOKS_SHOT_LIST.md`.

