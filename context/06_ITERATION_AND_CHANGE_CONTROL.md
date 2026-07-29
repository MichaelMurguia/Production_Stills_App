# Iteration and Change Control

## Why This Exists

Image models tend to reinterpret the whole image when asked to make a local correction.

This workflow treats every revision like a controlled production change.

---

## Revision Request Parsing

Convert user notes into four categories:

### A. Required Change

What must change.

### B. Preservation Set

What must remain exactly as approved.

### C. Prohibited Side Effects

Changes the model is likely to make but must not.

### D. Validation Criteria

How to decide whether the pass succeeded.

---

## Example

User note:

> Add the cover back on the GT40, show light from workshop cracks from outside, and make the device more oval and round.

Revision specification:

```yaml
required_change:
  - restore cover over GT40
  - exterior workshop lighting cell must show light escaping through cracks
  - device body becomes oval and rounded

preserve:
  - board composition
  - GT40 rear orientation
  - yellow Mk II identity
  - pre-dawn lighting
  - Charlie placement
  - scene cleanliness
  - digital interface

prohibited_side_effects:
  - no new GT40 reference row
  - no front view
  - no extra device panels
  - no additional warp images
  - no analog gauges

validation:
  - covered car remains identifiable as Mk II by tarp silhouette
  - crack light is seen from outside the building
  - device has simpler rounded form
```

---

## Revision Depth Levels

### Level 1 — Local Correction

One detail:

- color
- prop shape
- vehicle variant
- missing cover
- label
- panel content

Composition must remain fixed.

### Level 2 — Cell Replacement

Replace one panel while preserving the rest of the board.

### Level 3 — Board Rebalance

Change hierarchy, panel count, or rhythm.

Requires user instruction.

### Level 4 — Art Direction Revision

Changes global visual language.

Requires update to `01_ART_DIRECTION_BIBLE.md`.

---

## Locking System

Lock elements granularly.

Example:

```yaml
board:
  composition: LOCKED
  typography: APPROVED
  hero_image:
    camera: LOCKED
    lighting: LOCKED
    GT40_orientation: LOCKED
    GT40_variant: LOCKED
    dust_level: PROVISIONAL
  reference_cells:
    bridge_geometry: APPROVED
    materials_strip: PROVISIONAL
```

---

## Regression Check

After every revision, compare against the previous approved image.

Ask:

- Did any unmentioned character appear?
- Did a vehicle rotate?
- Did the model variant change?
- Did the panel count change?
- Did the board add reference emphasis?
- Did approved lighting drift?
- Did clutter increase?
- Did the same image repeat?
- Did the rendering become glossier?
- Did text become less accurate?

Any unrequested change is a regression.

---

## User Feedback Log

Store user feedback verbatim when it defines a durable rule.

Example:

```text
"Only address what I mention. Don't go off on your own."
```

Convert it into a permanent workflow constraint:

```text
Preserve-Unmentioned Rule: enabled.
```

---

## Current-Board Snapshot

Each board iteration should have:

```yaml
board_id:
scene_id:
source_screenplay_version:
source_art_bible_version:
source_references:
generation_id:
approved_elements:
rejected_elements:
open_issues:
next_revision_scope:
```

This makes later reconstruction possible.
