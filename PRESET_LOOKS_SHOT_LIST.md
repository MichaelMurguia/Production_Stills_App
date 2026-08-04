# PRESET_LOOKS_SHOT_LIST.md — the plate library

**For whoever renders the library** (Claude Code drives the generation; the
plates are shipped assets, not runtime output). Ten looks, five plates each,
50 images total. Read alongside `PRODUCTION_DESIGN_V3_PLAN.md` D7.

## What a plate must be

A plate is **evidence of a way of seeing, not a subject**. It teaches the
model light behaviour, lens character and finish — so:

- **No recognisable IP, no real actors, no logos, no legible text.**
- **Generic subjects only** — an unnamed figure, an unbranded vehicle, an
  ordinary room, landscape. The subject must not compete with the look.
- **Neutral genre.** These ship to every production; a plate that reads
  "1960s aerospace" is useless to a rom-com. Keep era cues out unless the
  look is explicitly period.
- **One look per set of five, held rigidly.** The five plates vary subject and
  scale, never the light logic. That consistency is the entire signal.
- 1920px on the long edge, JPEG q85, sRGB. Landscape 16:9 for
  cinematography; the rendering looks may be squarer if the medium implies it.

Per look, the five plates cover: **(1)** a wide establishing frame,
**(2)** a mid on a figure, **(3)** a close detail (texture/material),
**(4)** an interior or shade condition, **(5)** the look's extreme —
its hardest or lowest-light case.

## Cinematography — 5 looks

| slug | name | sets (the two Courier lines) |
|---|---|---|
| `available-light-doc` | Available-Light Doc | SOFT SOURCES · SPHERICAL 35MM · HANDHELD DRIFT / SHADOWS KEEP DETAIL · NO FILL |
| `hard-noon` | Hard Noon | SINGLE HARD SUN · SHORT SHADOWS · HEAT SHIMMER / CRUSHED BLACKS · WIDE HORIZONS |
| `sodium-night-interior` | Sodium Night Interior | PRACTICALS IN FRAME · WARM/COOL SPLIT · LONG LENS / WINDOWS BLOWN · NO MOONLIGHT BLUE |
| `anamorphic-scope` | Anamorphic Scope | 2.39 · OVAL BOKEH · HORIZONTAL FLARE / SHALLOW FOCUS · FACES OFF-CENTRE |
| `deep-focus-formal` | Deep Focus Formal | LOCKED FRAMES · WIDE STOP · EVERYTHING SHARP / SYMMETRY · SOFT TOPLIGHT |

## Board rendering — 5 looks

These teach **medium and finish**, not the world. Same subject discipline;
each plate should look like a *board panel*, including its edge and paper.

| slug | name | sets |
|---|---|---|
| `graphite-storyboard` | Graphite Storyboard | GRAPHITE ON TONED PAPER · VISIBLE HATCHING / VALUE ONLY · NO COLOUR |
| `painterly-concept` | Painterly Concept | OPAQUE BRUSHWORK · EDGES LOST AND FOUND / LOOSE PERIPHERY · FINISHED FOCAL POINT |
| `ink-and-wash` | Ink & Wash | BRUSH-PEN LINE · SINGLE GREY WASH / HIGH CONTRAST · WHITE PAPER HOLDS |
| `marker-comp` | Marker Comp | WARM/COOL MARKER · FLAT PLANES · STREAKING / LIMITED PALETTE · WHITE GAPS LEFT |
| `photoreal-still` | Photoreal Still | PHOTOGRAPHIC FINISH · NO VISIBLE MEDIUM / GRAIN AND FALLOFF · FRAME EDGE ONLY |

## Delivery

```
app/static/look_library/
  looks.json
  available-light-doc/01.jpg … 05.jpg
  …
```

`looks.json` per entry: `{slug, column: "cinematography"|"board_rendering",
name, tags: [...], sets: ["line 1","line 2"], plates: ["01.jpg",…]}`.
Tags drive the browser's filter chips — reuse the chip set in the mock
(NATURAL LIGHT · HARD SUN · NIGHT · INTERIOR PRACTICAL · ANAMORPHIC ·
LONG LENS · HANDHELD for cinematography; medium names for rendering).

When a look is applied, each plate is copied into the production's reference
library as an approved ref with `source: "look:<slug>"` — provenance survives
and the plate is individually removable, per D7 rule 3.

**Before rendering 50 images, render one look (5 plates) and show it.** If the
consistency discipline isn't holding across the five, the other nine will
fail the same way and the cost is 10× to find out.
