# Canon and Reference Rules

## Source Priority

When sources conflict, use this order:

1. User's latest explicit instruction
2. Latest approved reference image
3. Latest locked markdown rule
4. Current screenplay
5. Earlier approved board
6. General visual inspiration
7. Model intuition

Model intuition is never allowed to override the first five sources.

---

## Screenplay Authority

The screenplay defines:

- who is present
- where the scene occurs
- time of day
- sequence of actions
- dialogue beats
- vehicle count
- vehicle type
- injuries
- destruction
- direction of travel
- reveal order
- emotional progression
- transitions
- effects explicitly seen

The screenplay does not automatically define every design detail. Unspecified design decisions must still remain inside the locked art direction.

---

## Reference Photo Protocol

When the user supplies a reference image, identify its purpose explicitly.

Examples:

- `GT40_MKII_REAR_GEOMETRY`
- `JOHN_LIKENESS`
- `WORKSHOP_LAYOUT`
- `ONYX_UNIT_PROPORTIONS`
- `WORLD_TEXTURE` (movie parameter — the world's condition)
- `COLOR_PALETTE` (movie parameter — the film's color language)
- `CINEMATOGRAPHY_STYLE` (movie parameter — light behaviour and framing)
- `BOARD_RENDERING_STYLE` (board parameter — presentation medium only)
- `BOARD_LAYOUT_STYLE` (assembly grammar — never in a panel render)
- `LIGHTING_REFERENCE`
- `MATERIAL_REFERENCE`

The reference controls only the category assigned to it unless the user says it controls the entire image.

### Example

A GT40 rear reference controls:

- rear body geometry
- intake locations
- grille layout
- lamp placement
- exhaust relationship
- stance

It does not automatically require:

- a new camera angle
- a close-up reference strip
- a change to the hero composition
- a new paint scheme
- a different environment

---

## Preserve-Unmentioned Rule

During revision:

**Only change what the user mentions.**

Every prompt must include a preservation block:

```text
PRESERVE UNCHANGED:
- overall board composition
- panel count
- vehicle orientation
- camera direction
- approved character placement
- lighting structure
- all approved materials
- all unmentioned design elements
```

The Revision Controller must reject any prompt that introduces unrelated improvements.

---

## No Extrapolation Rule

Do not infer that the user wants:

- more references
- more panels
- more action
- more characters
- more vehicles
- more explosions
- a different angle
- a clearer front view
- a stronger hero pose
- a more attractive composition

These may only change through explicit instruction.

---

## Canon Package for Each Scene

Every scene board receives a compact canon package:

```yaml
scene_id:
screenplay_pages:
scene_start:
scene_end:
characters_present:
characters_absent_but_easy_to_assume:
vehicles:
vehicle_count:
props:
location:
time_of_day:
weather:
major_actions:
visual_effects:
dialogue_to_inform_tone:
forbidden_inventions:
approved_references:
locked_elements_from_previous_board:
```

The field `characters_absent_but_easy_to_assume` is mandatory. It prevents recurring mistakes such as inserting Kyra because she is prominent in adjacent scenes.

---

## Evidence Tags

Every proposed image cell should include an internal evidence tag:

- `SCRIPT_EXPLICIT`
- `SCRIPT_INFERRED`
- `ART_BIBLE`
- `USER_REFERENCE`
- `PRODUCTION_DESIGN_PROPOSAL`

A `PRODUCTION_DESIGN_PROPOSAL` may not alter plot or action.

Example:

```text
Cell: Hidden jump handle
Evidence: SCRIPT_EXPLICIT
```

```text
Cell: Scorched aluminum surface treatment
Evidence: ART_BIBLE + PRODUCTION_DESIGN_PROPOSAL
```

---

## Reference Cell Discipline

Each reference cell must solve a unique production question.

Good:

- bridge structure and failure geometry
- GT40 Mk II rear silhouette
- handwritten hidden-panel label
- GRM hover-jet skin material
- contained-jump edge distortion
- canyon particulate behavior

Bad:

- four nearly identical GT40 angles
- three versions of the same warp flash
- several Charlie portraits
- repeated hover-jet hero views
