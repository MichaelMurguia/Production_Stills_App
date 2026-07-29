# Beltminers Production Art Director v2 — Full Instructions

## 1. What this skill does

This skill creates screenplay-faithful production art for **The Beltminers**.

It does not begin by casually writing an image prompt. It first builds a structured, reviewable production package:

```text
Screenplay and approved references
        ↓
Research and evidence extraction
        ↓
Asset dossiers
        ↓
Evidence ledger
        ↓
Production Generation Specification
        ↓
Specification validation
        ↓
Compiled render prompt
        ↓
Candidate image
        ↓
Image audit
        ↓
User approval or revision
```

The durable creative artifact is the **Production Generation Specification**. The image prompt is only a translation layer used to communicate that specification to the image model.

---

## 2. Installation

### Recommended ChatGPT Project setup

Create a dedicated ChatGPT Project for **The Beltminers Production Art**.

Upload:

1. `beltminers_production_art_director_v2.zip`
2. The latest screenplay, currently referenced as `Beltminer_Summer_25.pdf`
3. Master Board #001
4. Approved character likeness references
5. Approved vehicle references
6. Approved environment and location references
7. Any previously approved production boards

Extract the ZIP if your workspace requires individual files.

Set the included `SKILL.md` as the main project instruction file.

The skill ZIP does **not** contain the screenplay or proprietary reference images. Those must remain alongside the skill.

---

## 3. First command

Start a new project conversation and enter:

```text
Initialize production. Audit all available canon sources, then show project state and missing dependencies.
```

The skill should then:

- locate the current screenplay
- identify Master Board #001
- inventory approved references
- load the approval and rejection history
- identify missing source material
- report which assets already have approved dossiers
- report which boards are approved, provisional, rejected, or absent

Do not begin image generation until initialization is complete.

---

## 4. Source authority

The system resolves conflicts using this order:

1. The user's latest explicit instruction
2. The latest approved reference image for its assigned purpose
3. Locked visual canon and approved asset dossiers
4. The current screenplay
5. Earlier approved boards
6. Clearly identified design exploration
7. Model intuition

Model intuition is never enough to establish canon.

For example, a photograph labeled as controlling **John's likeness** controls John's face, hair, proportions, and recognizable identity. It does not automatically control his costume, lighting, location, or camera angle.

A GT40 rear reference controls rear geometry. It does not automatically authorize a new vehicle panel or a new camera angle.

---

## 5. Production modes

Every board or image request must use one of two modes.

### Canon Extraction

Use:

```text
Mode: CANON_EXTRACTION
```

This is the default.

It allows:

- screenplay-explicit content
- unavoidable necessary inference
- approved visual canon
- the user's explicit direction
- no unsupported invention

Weak inference should normally be zero and may never exceed two items across an entire board.

Use this mode for official production boards, scene boards, asset sheets, and anything intended to become canon.

### Design Exploration

Use:

```text
Mode: DESIGN_EXPLORATION
```

This allows the production designer to propose answers where the screenplay is silent.

Every proposal must be labeled:

```text
PROPOSED — NOT CANON
```

Nothing from an exploration board enters canon unless the user explicitly approves it.

Example:

```text
Create specification: Genetics clothing exploration.
Mode: DESIGN_EXPLORATION.
Explore three clothing directions without inventing vehicles, animals, symbols, weapons, or social rituals.
```

---

## 6. Standard production workflow

### Step 1 — Build an Asset Dossier

Before making a board, create durable definitions for important assets.

Command:

```text
Build asset dossier: The Genetics
```

Other examples:

```text
Build asset dossier: John Stanner
```

```text
Build asset dossier: Ford GT40 Mk II
```

```text
Build asset dossier: Charlie's workshop
```

```text
Build asset dossier: Resistance civilization
```

```text
Build asset dossier: GRM Onyx Unit
```

An Asset Dossier should contain:

- all relevant screenplay evidence
- physical description
- behavior
- scale
- movement
- materials
- anatomy or mechanical construction
- environmental relationships
- approved reference roles
- prohibited interpretations
- unresolved questions
- recommendations clearly separated from canon
- confidence level

The dossier should not silently resolve unknowns.

It should say:

```text
Vehicles: not established
Animals: not established
Faction symbols: not established
Clothing system: unresolved
```

That restraint is intentional.

### Step 2 — Review the dossier

Use:

```text
Review asset dossier: The Genetics
```

Check:

- Does every claim have screenplay or approved-reference support?
- Are recommendations labeled separately?
- Has generic science-fiction imagery slipped in?
- Are unknowns honestly marked?
- Has the dossier inferred culture, rituals, animals, technology, or symbols without proof?
- Does it contradict approved canon?

Then give corrections:

```text
Revise asset dossier: The Genetics.

Remove all claims about rituals, petroglyphs, transport animals, faction symbols, farming, and flying craft. Those are not established.

Preserve the physical evidence showing that Genetics are towering, angular, telekinetic, superhuman, humanoid, and visibly non-human.
```

When satisfied:

```text
Approve asset dossier: The Genetics
```

Approval can be granular:

```text
Approve the Genetics body silhouette and facial anatomy only. Architecture remains provisional.
```

### Step 3 — Create the Production Generation Specification

Command:

```text
Create specification: Genetics faction board.
Mode: CANON_EXTRACTION.
```

The skill should stop after producing the specification. It should not automatically generate the image unless the user explicitly requested an uninterrupted pipeline.

The specification should include the following sections.

#### Request Record

- project
- subject
- board type
- mode
- revision
- production goal

#### Canon Sources

- screenplay version
- exact screenplay passages
- Master Board #001
- approved dossiers
- approved references
- continuity records
- rejected-content history

#### Evidence Summary

Each proposed board element must be classified as one of:

```text
SCRIPT_EXPLICIT
SCRIPT_NECESSARY_INFERENCE
VISUAL_CANON_LOCKED
USER_DIRECTED
WEAK_INFERENCE
PROPOSED_NOT_CANON
UNSUPPORTED
```

Anything marked `UNSUPPORTED` must be removed before generation.

#### World or Scene Definition

Only supported facts:

- location
- characters
- architecture
- vehicles
- props
- technology
- materials
- lighting
- time of day
- action
- scale
- emotional intent

#### Forbidden Elements

For a Genetics board, this might include:

```text
No animals
No flying craft
No petroglyphs
No faction insignia
No DNA symbols
No invented names
No farming terraces
No fantasy ruins
No ceremonial culture
No modern laboratory equipment
No human-looking Genetics
```

The actual list must be derived from the project's known failure history and the current specification.

#### Adaptive Layout

The specification determines the layout from available evidence.

It should not force categories such as Vehicles, Weapons, Symbols, or Daily Life merely because faction boards often include those sections.

Example:

```text
Hero environment: 50%
Genetics anatomy and silhouette: 25%
Architecture details: 15%
Materials and lighting: 10%

Vehicles: omitted
Animals: omitted
Symbols: omitted
Weapons: omitted
```

#### Panel Specifications

Every panel should state:

- panel ID
- purpose
- evidence
- required content
- forbidden content
- scale
- composition role
- reference dependencies
- continuity dependencies

Example:

```text
PANEL 01 — HERO ENVIRONMENT

Purpose:
Establish the scale relationship between the Genetics and their cliff environment.

Evidence:
SCRIPT_EXPLICIT
Approved Genetics Asset Dossier

Required:
Utah-like red sandstone cliffs
Monumental scale
Architecture physically integrated with rock only where supported
Genetics visible for scale
Production-painting treatment

Forbidden:
Flying craft
Animals
Petroglyphs
Faction banners
Road traffic
Invented agricultural terraces
Fantasy temple ornament
```

#### Object-Level Evidence Ledger

Not only panels, but each intended visible object should be justified.

Example:

```text
Object: red sandstone cliff
Evidence: USER_DIRECTED + approved environment direction
Status: ALLOWED

Object: towering Genetic
Evidence: SCRIPT_EXPLICIT
Status: ALLOWED

Object: flying transport
Evidence: none
Status: REMOVE

Object: carved spiral symbol
Evidence: none
Status: REMOVE
```

#### Canon Budget

For a Canon Extraction board:

```text
Explicit canon: unlimited
Necessary inference: unlimited
Approved canon: unlimited
User-directed: unlimited
Weak inference: preferably 0, maximum 2
Unsupported: 0
```

#### Continuity Check

The specification should confirm that it does not conflict with:

- approved likenesses
- approved silhouettes
- approved faction materials
- approved vehicle geometry
- Master Board #001 presentation language
- prior rejections
- visual ownership rules

### Step 4 — Review the specification

Command:

```text
Review specification.
```

The review should behave like a hostile production audit, not a supportive brainstorming pass.

It should ask:

- Can every visible object be proven?
- Is any category present only because a generic faction board usually has it?
- Did the system invent daily life?
- Did it invent culture?
- Did it invent tools, vehicles, fauna, symbols, clothing, weapons, or rituals?
- Did it mistake a recommendation for canon?
- Did it omit major screenplay evidence?
- Did it overfill the board?
- Does every panel answer a distinct production question?
- Is the board more like a production wall than a wiki page?
- Has Master Board #001 been used only for presentation language rather than faction content?

A useful command is:

```text
Prosecute this specification. Attempt to disprove every panel and every visible object. Remove anything that cannot survive the evidence test.
```

### Step 5 — Approve the specification

When satisfied:

```text
Approve specification.
```

This approval means the creative decisions may now be translated into render instructions.

It does **not** mean the resulting image is automatically approved.

### Step 6 — Compile the render prompt

Command:

```text
Compile render prompt.
```

The compiler should be mechanical.

It may:

- reorder information for the image model
- translate structured requirements into render language
- restate negative constraints
- attach approved reference roles
- describe the layout precisely

It may not:

- add a more cinematic vehicle
- invent more interesting characters
- add symbols
- add props
- add animals
- enrich the culture
- fill blank areas
- make the design more epic
- reinterpret the specification

The output is `RENDER_PROMPT.txt`.

The prompt is disposable. The approved specification remains the durable asset.

### Step 7 — Generate the candidate image

Command:

```text
Generate candidate image from the approved specification.
```

Or, for an uninterrupted pass after the specification has already been approved:

```text
Compile the render prompt and generate the candidate image. Do not change the approved specification.
```

Every result must be labeled:

```text
CANDIDATE — UNAPPROVED
```

A generated image never becomes canon by default.

### Step 8 — Audit the generated image

Command:

```text
Audit image against the approved specification.
```

The auditor should inspect the actual visible image and produce `IMAGE_AUDIT.md`.

The audit should include:

#### Required Element Check

- present
- missing
- incorrect
- ambiguous

#### Unsupported Object Inventory

Inventory all visible content, including:

- people
- animals
- aircraft
- ground vehicles
- symbols
- signs
- weapons
- tools
- architecture
- furniture
- containers
- vegetation
- clothing
- markings
- technology
- decorative motifs

Each item must map back to the evidence ledger.

#### Canon Accuracy

- character identity
- species anatomy
- vehicle model and variant
- location
- scale
- action
- materials
- damage
- technology
- effects

#### Presentation Accuracy

- visual grammar
- image hierarchy
- whitespace
- typography
- panel count
- repetition
- production-wall readability

#### Continuity

- asset drift
- faction drift
- material drift
- scale drift
- lighting drift
- geometry drift
- reference-role violations

#### Release Decision

One of:

```text
PASS — READY FOR USER REVIEW
```

```text
PASS WITH MINOR ISSUES — DO NOT LOCK
```

```text
FAIL — REGENERATE
```

The auditor should not call a failed image successful merely because it looks attractive.

---

## 7. Revision workflow

For any correction, specify exactly what changes and what must remain fixed.

Example:

```text
Revise board:

Required change:
Remove the flying ship, animal, and petroglyphs.

Restore:
The missing full-body Genetics scale study from the approved specification.

Preserve exactly:
The hero cliff composition
The red sandstone palette
The Genetics facial direction
The architecture panel
The current board hierarchy
The painterly looseness
The typography and whitespace

Do not add:
New vehicles
New symbols
New tools
New culture panels
New characters
New technology
```

The skill should convert this into a revision delta containing:

```text
REQUIRED CHANGES
PRESERVE EXACTLY
DO NOT ADD
VALIDATION CRITERIA
RISK OF UNINTENDED CHANGE
REFERENCE ROLES
```

Then use:

```text
Compile revision prompt and regenerate only the requested changes.
```

Afterward:

```text
Run regression audit against the previous candidate and the approved specification.
```

Any unrelated change is a regression.

---

## 8. Approval commands

### Approve the entire board

```text
Approve board.
```

This should record:

- board ID
- approved image
- specification version
- approved layout
- approved panels
- approved assets
- locked constraints
- unresolved details
- approval date
- the user's exact approval language when significant

### Approve only part of a board

```text
Approve the hero environment only. Do not approve the character designs.
```

```text
Approve the board layout and material palette. Everything else remains provisional.
```

```text
Approve the Genetics silhouette, proportions, and face structure as canonical.
```

### Reject a board

```text
Reject board.

Record these as prohibited inventions:
animals, flying ships, petroglyphs, faction symbols, DNA imagery, invented named citizens, and unsupported cultural rituals.
```

Rejected content must not be used as future reference.

---

## 9. Project-state commands

Use:

```text
Show project state.
```

The response should report:

- current screenplay version
- Master Board #001 status
- approved boards
- candidate boards
- rejected boards
- approved assets
- provisional assets
- missing dossiers
- unresolved canon questions
- active specification
- active render
- continuity risks
- recorded prohibited inventions

Other commands:

```text
Show approval log.
```

```text
Show rejection history.
```

```text
Show all approved Genetics canon.
```

```text
Show unresolved Genetics design questions.
```

---

## 10. Recommended production-library order

Do not try to define everything at once. Build foundational assets first.

A good sequence is:

```text
Build asset dossier: Master Board #001 visual grammar
```

```text
Build asset dossier: The Genetics
```

```text
Build asset dossier: Genetics stronghold and associated screenplay locations
```

```text
Build asset dossier: Resistance civilization
```

```text
Build asset dossier: GRM civilization
```

```text
Build asset dossier: John Stanner
```

```text
Build asset dossier: Charlie Stanner
```

```text
Build asset dossier: Kyra
```

```text
Build asset dossier: Ford GT40 Mk II
```

```text
Build asset dossier: Prospector
```

```text
Build asset dossier: Onyx Unit
```

```text
Build asset dossier: Terra Nova station
```

Character, vehicle, and location dossiers can then be reused across faction boards, scene boards, storyboards, and key art.

---

## 11. Full automatic run

Once the foundational dossiers are approved, request a complete process:

```text
Create a Genetics faction board in CANON_EXTRACTION mode.

Run the full pipeline:
1. Research the complete screenplay.
2. Load all approved Genetics dossiers and references.
3. Build the evidence ledger.
4. Apply the canon budget.
5. Create an adaptive production-board layout.
6. Prosecute the specification for unsupported content.
7. Remove all failed content.
8. Validate the specification.
9. Compile the render prompt.
10. Generate the candidate image.
11. Audit every visible object against the specification.
12. Regenerate automatically if the audit fails.
13. Stop when a compliant candidate is ready for my review.

Do not add the result to canon.
```

This is the most useful “do not stop” command, but the skill must still stop if it encounters a real unresolved conflict that cannot be safely answered.

Examples:

- two screenplay passages conflict
- an important likeness reference is missing
- the requested vehicle variant is uncertain
- the request contradicts approved canon
- the board requires a major design choice not established by the screenplay

In those cases, inventing an answer would violate the purpose of the skill.

---

## 12. Example: Genetics faction board

Use this sequence.

### A. Initialize

```text
Initialize production. Audit all available canon sources, then show project state and missing dependencies.
```

### B. Research and dossier

```text
Build asset dossier: The Genetics.

Search the entire screenplay, not only scenes containing the word Genetics. Include physical descriptions, actions that imply anatomy or strength, telekinetic behavior, environmental context, dialogue about their origin and nature, and all locations they occupy.

Separate:
- explicit canon
- unavoidable inference
- recommendation
- unknown

Do not propose vehicles, animals, symbols, rituals, petroglyphs, agriculture, clothing systems, or named citizens.
```

### C. Audit dossier

```text
Prosecute the Genetics dossier. Remove every claim that cannot be supported by the screenplay, an approved reference, or an unavoidable physical inference.
```

### D. Approve dossier

```text
Approve the Genetics dossier sections covering anatomy, scale, movement, telekinesis, and non-human appearance. Keep architecture provisional.
```

### E. Create specification

```text
Create specification: Genetics faction board.
Mode: CANON_EXTRACTION.

Use Master Board #001 only for board grammar and presentation.

Do not use rejected Genetics boards as design references.

The layout must be driven by available evidence. Omit unsupported categories rather than filling them.
```

### F. Challenge it

```text
Review and prosecute the specification object by object.

Specifically search for:
animals
flying craft
petroglyphs
symbols
DNA motifs
invented technology
invented names
invented daily life
invented clothing
invented tools
invented cultural practices

Remove every unsupported item.
Also identify major screenplay-supported material that the proposed board failed to include.
```

### G. Approve and render

```text
Approve specification. Compile the render prompt and generate a candidate image without changing the specification.
```

### H. Audit

```text
Audit the image against the approved specification. Inventory every visible object and report missing required content, unsupported additions, anatomy drift, visual-language drift, and continuity violations.
```

---

## 13. Exporting the production package

Use:

```text
Export production package.
```

The export should include:

```text
SKILL.md
Approved asset dossiers
Active and approved specifications
Evidence ledgers
Compiled render prompts
Image audit reports
Continuity database
Approval log
Rejection history
Reference manifest
Project-state record
```

This makes the creative decisions portable to another model or production tool.

---

## 14. Local validation scripts

The ZIP may include deterministic scripts. From the extracted skill folder, use the scripts documented in the package, for example:

```bash
python scripts/validate_spec.py examples/minimal_valid_spec.json
```

A valid specification should produce:

```text
SPEC_PASS
```

Compile a test prompt with:

```bash
python scripts/compile_prompt.py examples/minimal_valid_spec.json
```

These scripts are safeguards. They cannot judge artistic quality, but they can detect missing required fields and prevent an incomplete specification from entering the render pipeline.

---

## 15. Rules to hold the skill accountable

Use these statements whenever it begins drifting:

```text
Do not complete the world. Prove the world.
```

```text
Unknown is an acceptable result.
```

```text
Empty space is preferable to invented content.
```

```text
A visually attractive unsupported object is still a failure.
```

```text
Master Board #001 defines presentation grammar, not faction content.
```

```text
Generated does not mean approved.
```

```text
Recommendations are not canon.
```

```text
The board assembles supported assets. It does not invent assets.
```

```text
The image model is the illustrator, not the production designer.
```

---

## Recommended next command

```text
Initialize production. Then build the full Genetics asset dossier using the complete screenplay and all approved project references. Do not generate an image yet.
```
