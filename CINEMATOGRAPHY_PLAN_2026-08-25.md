# Plan — making cinematography reach the image, 2026-08-25

**Status: FOR REVIEW. Nothing here is implemented.** Approve, modify or
strike by ID.

Written after two days of testing a per-panel cinematography axis that was
wired correctly end to end and still produced almost no visible effect.
Roughly twenty renders. Four real bugs found and fixed along the way, none
of which was the cause.

---

## What was actually established

Measured, not inferred. Every claim here has a take record or a file
behind it.

**E1 — Prompt length is the constraint.**

| prompt | style block's share | result |
|---|---|---|
| app compile, 19,094 chars | ~4% | no visible effect, four styles, ~15 renders |
| hand-trimmed, 1,782 chars | ~45% | style visibly lands, first try |

The same grammar, the same engine, the same panel. This is the finding the
rest of the plan follows from.

**E2 — The style documents' own wording is the strongest single lever.**
Changing one word in `docs/CINEMATOGRAPHY_STYLES.md` — `Use saturation
selectively` → `extremely` — did what four code changes could not. The
hedging is systematic:

| style | hedged lines | ever landed clearly? |
|---|---|---|
| Deep-Space Mise-en-Scène | **0** | **yes, consistently** |
| Classical Adventure | 1 | untested |
| Immersive / Experiential | 1 | untested |
| Expressionist / Noir | 3 | untested |
| Formalist / Architectural | 3 | untested |
| Chromatic / Operatic | 3 | only after the word change |
| Subjective / Poetic | 3 | only in the short prompt |
| Naturalistic / Observational | 4 | untested |

Chromatic carries four restraint cues (`controlled` secondary colour,
`selectively`, `controlled saturation`, `maintain strong value structure`)
against one drama cue. Subjective/Poetic's mechanics line ends `when
emotionally motivated` — not a hedge but an **opt-out**: the model can
decide the moment is not emotionally motivated and comply by doing nothing.

**E3 — A positive permission grant beats a defensive precedence clause.**
The calibration prompts that work all carry `CALIBRATION CONTINUITY` near
the top, naming what the style MAY change. The app instead states that the
art direction rules everything, then carves out exceptions ~13,000
characters later.

**E4 — A panel's brief can be structurally incompatible with its style.**
`SHIP_DESCENDS_V1 / P01` has a purpose beginning *"Establish"* and five
required objects. That is an establishing shot. Subjective/Poetic requires
the frame to give things up. No precedence rule reconciles those two.

**E5 — Single renders are not evidence.** Two runs of an identical prompt
produced visibly different frames. Most mid-session readings — mine and
yours — were one-sample and several were wrong.

**E6 — The take card shows the wrong prompt.** `prompt` is the governance
compile; `render_prompt` is what the model received. Two days of wrong
conclusions came from reading the first.

---

## Part 1 — The structural change

### C1 — A prompt budget *(the one that matters)*

**Size: L. Recommend doing, and doing carefully.**

The compiler emits everything it knows on every render. A panel needing
five objects and one grammar receives 19,000 characters, of which the
grammar is 800. Nothing downstream can fix a ratio like that, and
everything I tried was a way of arguing with it.

This is design work, not a patch. The questions it has to answer:

- What does a panel actually *need*, versus what does it inherit because
  the production has it?
- Does the Bible need to arrive whole on every panel, or only the sections
  a panel's design languages and environment call for? (`bible.py` already
  does selective injection — the selection may simply be too generous.)
- Should the style's share of the prompt be a stated proportion rather
  than an accident of how much art direction exists?

**Do not start by cutting text.** Start by instrumenting: log the compiled
prompt's composition per block, per render, and look at real productions.
The 4% figure is from one panel of one production.

**C1.1** — Instrument first: a per-block byte breakdown of a compiled
prompt, visible in the app beside the prompt preview. **S**
**C1.2** — Tighten the Bible's selective injection against that data. **M**
**C1.3** — A stated floor for the style block's share, and a warning when
a panel's prompt falls below it. **M**

### C2 — A permission grant, early

**Size: S. Recommend.**

Replace `_grammar_precedence`'s defensive clause with a positive grant
near the top of the prompt, in the calibration's own terms: the
cinematography grammar MAY change camera position, lens behaviour,
framing, depth, lighting, exposure, colour strategy, focus and visual
rhythm; it may NOT redesign story, characters, costumes, props, materials
or world.

Keep the `WHERE THEY DISAGREE` clause or drop it — but it cannot be the
only place authority is stated, and 79% depth is not where a permission
gets read.

### C3 — A hedge lint for the style documents

**Size: S. Recommend.**

The style libraries are user-maintained prose and their wording decides
whether a style works at all. Nothing checks them. `style_docs` parses
each document already; it can flag hedges in the same pass — `selectively`,
`controlled`, `restrained`, `subtle`, `when appropriate`, `when emotionally
motivated`, `rather than becoming` — and surface the count in the picker
and the style reader.

Not an error. A style may want restraint; Naturalistic/Observational
legitimately does. The point is that four hedges in a style built on
excess is a fact the author should see.

---

## Part 2 — Telling the truth about a render

### C4 — Show what was actually sent

**Size: S. Recommend — this one cost two days.**

The take's prompt reader shows `prompt`, the governance compile. When a
take rode an override — a saved prompt, a one-take edit — the model saw
`render_prompt` instead, and nothing on screen says so or shows it.

Show `render_prompt` when it exists, labelled as what the model received,
with the compile available beside it as the governance record.

### C5 — State a conflict before the spend

**Size: M.**

When a panel's purpose and required content structurally oppose its
grammar, say so where the render is triggered. A purpose beginning
"Establish" with five required objects, under a grammar whose Avoid list
names "objective establishing-shot composition", is knowable before
paying.

Advisory, never blocking — the director may want exactly that fight.

### C6 — A two-render rule for style evaluation

**Size: S.**

Run-to-run variance is large enough that one take proves nothing about a
style. Where the app invites a comparison — the model test, any future
style probe — it should render two and show them together.

---

## Part 3 — Yours, not the app's

### C7 — Rewrite the hedged styles

**Not code. Your document, your creative call.** `docs/CINEMATOGRAPHY_STYLES.md`
is read live, so an edit updates the picker, the prompt and the reader
together.

A suggested shape for Chromatic, keeping discipline where it earns its
place:

- `Use saturation selectively` → **`Push saturation hard where colour
  carries meaning, and let the rest fall away`**
- `controlled saturation` → **`decisive saturation`**
- keep `a controlled secondary or opposing color` — that is palette
  discipline and it is doing real work
- keep the value-structure line — it is what stopped `extremely` from
  working properly

For Subjective/Poetic, the opt-out is the thing to remove: `when
emotionally motivated` lets the model decline. `where the moment carries
feeling` states the same intent without offering a way out.

**C7.1** — Chromatic / Operatic
**C7.2** — Subjective / Poetic
**C7.3** — The remaining five, reviewed against E2's table

### C8 — Engine per look *(untested)*

Your calibration images were rendered in ChatGPT directly. Every app
render in this investigation was `gpt-image-2`. We never tried Gemini on
the same panel and prompt.

Worth one controlled pair before assuming anything. If engines differ
markedly on style adherence, that is a product fact worth surfacing —
"this look renders better on X" — and it is cheaper than any of the above.

---

## What NOT to do

- **Do not add more precedence text.** Four attempts, each defensible,
  none sufficient. The clause is now correct and it is not the lever.
- **Do not reorder the prompt as a fix on its own.** I proposed it and
  built the variant; the short-prompt result superseded it before it was
  tested. Reordering a 19,000-character prompt moves the style from 15% to
  87% of the way through, and it is still 4% of the text.
- **Do not rewrite the Bible drafter again.** The 2026-08-24 fix was
  correct — cinematography doctrine no longer lands in Lighting Language —
  and going further would start deleting art direction the production
  needs.
- **Do not treat a single render as a result**, including a good one.

---

## Already fixed, and worth keeping

Four real bugs, found while looking for the wrong thing. All committed,
all local, none of them the cause:

| | |
|---|---|
| The grammar was scoped to LIGHT AND COLOUR only, so a framing style had no authority over framing | `generate._grammar_precedence` |
| The Bible drafter wrote lens and focus doctrine into Lighting Language, where it outranked the per-panel axis | `wizard.style_depth`, `_ANCHOR_LIBRARY` |
| A panel never said whether its grammar was its own or inherited — cost three renders | `app.js`, take tag and step 03 |
| There was no way to send a panel no colour reference at all | `-COLOR_PALETTE` suppression |

Plus Stops 1–4 of the first-user-test plan. 1,939 tests, both suites
green, thirteen commits unpushed.

---

## Suggested order

1. **C4** — show what was actually sent. Small, and it makes every later
   experiment trustworthy.
2. **C7** — the document rewrites. Free, immediate, and by E2 the largest
   effect available.
3. **C1.1** — instrument the prompt's composition. Cheap, and it turns C1
   from a hunch into a measurement.
4. **C8** — one controlled engine pair.
5. **C2**, **C3**, **C6** — small and independent.
6. **C1.2 / C1.3** — the real work, once there is data to aim it.

The first three cost almost nothing and would have saved most of the
twenty renders this took.

---

# Addendum — camera recipes (2026-08-25, after review)

This supersedes parts of the plan above. Read it before C1, C2 and C5.

## A correction first

The plan claims (E4) that a panel's required content can be structurally
incompatible with a style — that five required objects cannot appear in a
subjective frame. **That is wrong**, and wrong in the way that matters: it
reasoned about content lists instead of about optics.

Avrel at 1.5m on a 24mm wide open puts the hull, the pan, the ramp and the
six figures behind her in the same frame. All present. Not all sharp. The
recipes document says it outright — *"secondary characters remain present
but substantially softer"*. **Strike E4 and C5.** There is no conflict to
warn about; there is a camera to choose.

## What the grammar was missing

The styles speak in adjectives — *selective focus, negative space, unusual
placement, when emotionally motivated*. An image model satisfies every one
of those by doing nothing. `docs/Cinematography/CINEMATIC_LENS_AND_FRAMING_RECIPES.md`
speaks in camera settings — `85mm, f/2, focus on the eyes, shallow, backed
away enough to preserve facial perspective`. There is no reading of that
which returns an everything-sharp frame.

It is also **denser**: ~150 words carrying more instruction than the
836-character grammar block. It helps E1 rather than fighting it.

## A1 — Three documents, one job each

| document | holds | edit cadence |
|---|---|---|
| `CINEMATOGRAPHY_STYLES.md` *(exists)* | what a style is FOR — principle, mechanics, avoid | rarely; creative doctrine |
| `CAMERA_RECIPES.md` *(new)* | the 20 base framings and 13 modifier axes, lifted from `docs/Cinematography/` | whenever calibrated against renders |
| `camera_defaults.json` *(exists)* | silent fallback only | never, once styles own the camera |

Separate rather than folded together, for three reasons: they change on
different schedules; a separate document makes it natural for the compiler
to pull exactly ONE row instead of a whole style entry; and the person
tuning f-stops is not the person writing what a style is for.

Both markdown documents stay live-read, so an edit updates the picker, the
prompt and the reader together — the property that let one word fix
Chromatic.

**A1.1** — Move section 2 (framings) and section 3 (modifiers) into
`docs/CAMERA_RECIPES.md`, with a stable slug per row. **S**
**A1.2** — Parse it in `style_docs` as a fourth library. **S**
**A1.3** — Count check: section 2 reads as 20 rows, not 21. Confirm
whether one was dropped in authoring. **XS**

## A2 — The recipe is a PANEL FIELD, chosen at breakdown time

Not at compile time, and this is the part to hold onto.

The research pass already reads the screenplay and writes each panel's
purpose and required objects. It should also name the framing. That makes
the choice:

- **inspectable before the spend** — the panel reads
  `Extreme emotional isolation · 85–135mm · f/1.4–2`, and can be argued
  with before paying
- **editable** — a picker over 20 named framings, not free text
- **recorded** — a take knows which framing it rode
- **paid for once** — one call at breakdown, not one per render

Deciding it at compile time would repeat this week's central failure: a
decision the app makes invisibly, inferable only from the picture.

**A2.1** — `camera_recipe` on the panel, with modifier deltas beside it. **M**
**A2.2** — Picker in the breakdown row and the panel workbench. **M**
**A2.3** — The take records the recipe it rode, beside the cinematography
stamp. **S**

## A3 — Teaching the narrative model to choose

The heart of it. A lookup keyed on intent cannot work: a surfer at 400mm
and a race car at 24mm are both "action" and land on opposite rows
(`Compressed crowd / city / pursuit` versus `Threatening / confrontational
proximity`). Selection needs judgement about the shot.

The research pass's instructions gain the recipe array and a selection
method. What it must reason about, in order:

1. **What is this panel FOR** — the question its purpose answers.
2. **Where does the weight sit** — one face, a relationship, an object, a
   place, an event?
3. **What must stay readable**, and what may be given up. This is the
   choice the adjectives never forced anyone to make.
4. **What does the STYLE allow** — the grammar constrains the family
   without determining the row. Subjective/Poetic on an action beat is
   `Subjective / poetic character` or `Immersive / inside the action`
   opened up; never `Epic environmental wide`.
5. **Then modifiers**, and only where the shot departs from the row's
   baseline, so the prompt carries deltas rather than a restatement.

**A3.1** — Add the array and the method to `autofill._instructions`. **M**
**A3.2** — The chosen row carries one line of justification the director
can read and argue with. **S**
**A3.3** — A panel whose recipe fights its own style is a fact worth
stating, not silently resolving. **S**

## A4 — Retire the Production Design camera card

`#cam-default-row` sets a production-wide `Eye level · 24mm · Level ·
Wide`. Nobody chose that; it is a value the app needed. Once a style
carries recipes it is superseded.

**A4.1** — Remove the card. **S**
**A4.2** — Keep `camera_defaults.json` as the silent fallback answering
the panel editor's `— production default —`. **XS**
**A4.3** — The panel's manual camera override stays. It is the director
disagreeing with the recipe on one shot, which is the point. **XS**

## A5 — Struck: the slider

Proposed, reframed three times, and cut.

It began as screenplay-description ↔ cinematography, which was a real
observation about P01. But each attempt to say what it would actually
CHANGE produced something narrower than the last: first a weighting of
prose, then aperture and depth of field written out four ways, then a
legibility budget. Only the third was a real variable, and by then it had
stopped being a slider and become a fact about the panel.

Two reasons it does not survive.

The array does not sort along one line. `Distant observational` is
detached — coverage and feeling at once. `Flat graphic composition` is
highly expressive and not remotely intimate. A one-dimensional control
over twenty recipes implies an ordering that is not there, and would push
the selector toward the wrong row precisely where the choice is
interesting.

And the recipe selection already answers it. A2 and A3 have the narrative
model read the panel and name a framing, with a line of justification and
a picker to override it. That IS the control — twenty named choices a
director can read and argue with, rather than a number that stands for
something nobody can state plainly.

If the panel's accountability turns out to need saying out loud — how many
required objects the frame must make legible — it belongs as a stated
field beside the recipe, not as a dial.

## What survives from the original plan

Unchanged and still wanted: **C3** (hedge lint), **C4** (show
`render_prompt`), **C6** (two-render rule), **C7** (rewrite the hedged
styles), **C8** (engine comparison).

Superseded by A1–A4: **C1** (the budget becomes a consequence of
shipping one recipe row instead of everything) and **C2** (the
permission grant becomes the recipe's own authority).

Struck: **E4**, **C5**, **A5**.
