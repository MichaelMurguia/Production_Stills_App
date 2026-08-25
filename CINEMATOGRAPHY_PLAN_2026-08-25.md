# Plan — making art direction and cinematography reach the image

**2026-08-25. Status: FOR REVIEW.** Approve, modify or strike by ID.
Consolidates three passes of review into one document; the superseded
drafts are in git history.

Written after two days and ~20 renders testing a per-panel cinematography
axis that was wired correctly end to end and produced almost no visible
effect. Four real bugs found and fixed along the way, none of them the
cause.

---

## What was established

**E1 — A prompt fails when it carries instructions that contradict the
panel.** Length is a symptom of carrying everything, not the disease.

Measured: the app's 19,094-character compile produced no visible style
across four grammars and ~15 renders. A 1,782-character hand-trimmed
prompt landed first try. But the short one did not work *because* it was
short — it worked because everything left in it **agreed with the panel**.
The long one carried `use wide or moderate-wide lenses with deep focus`
against a selective-focus grammar, `low-saturation gray-blue` against a
colour grammar, `readable form over surface` against anything that wants
part of the frame given up.

Nineteen thousand characters of purely supportive art direction would have
rendered correctly. **1,782 was a diagnostic, never a target.**

**E2 — A style's own wording is the strongest single lever.** One word in
`CINEMATOGRAPHY_STYLES.md` — `Use saturation selectively` → `extremely` —
did what four code changes could not.

| style | hedged lines | landed clearly? |
|---|---|---|
| Deep-Space Mise-en-Scène | **0** | **yes, consistently** |
| Classical Adventure | 1 | untested |
| Immersive / Experiential | 1 | untested |
| Expressionist / Noir | 3 | untested |
| Formalist / Architectural | 3 | untested |
| Chromatic / Operatic | 3 | only after the word change |
| Subjective / Poetic | 3 | only in the short prompt |
| Naturalistic / Observational | 4 | untested |

Chromatic carries four restraint cues against one drama cue.
Subjective/Poetic's mechanics end `when emotionally motivated` — not a
hedge but an **opt-out**: the model can decide the moment is not
emotionally motivated and comply by doing nothing.

**E3 — The grammar speaks in adjectives; the recipes speak in cameras.**
*Selective focus, negative space, unusual placement* can all be satisfied
by doing nothing. `85mm, f/2, focus on the eyes, shallow, backed away
enough to preserve facial perspective` cannot. The recipes are also denser
— ~150 words carrying more instruction than the 836-character grammar
block.

**E4 — Single renders are not evidence.** Two runs of one prompt produced
visibly different frames.

**E5 — Nothing showed what a take was rendered from.** `prompt` is the
compile; `render_prompt` is what the model received. Two days of wrong
conclusions came from reading the first. **Fixed — see Done.**

---

## R1 — Intelligent selection from the Bible

**Size: L. The centre of the work.**

`bible.render_context()` already selects by design language and
environment. Two things are missing and the second is the important one:
relevance is matched on names and keywords rather than read, and
**nothing checks for contradiction at all**. Every selected section ships
whole, including the lines that fight the panel's own camera, grammar and
moment.

The selector must read the whole Bible, the screenplay's scene, the style
anchors, the panel's purpose, its required content, its camera recipe and
its cinematography grammar — then apply **two** tests to every element:

- **Does it describe something in this panel?** (relevance — exists today,
  crudely)
- **Does it contradict what this panel is trying to do?** (new, and the
  reason the axis never worked)

**R1.1** — A per-panel decision made by the narrative model at breakdown
time, stored on the panel. Inspectable before the spend, editable,
recorded on the take, paid for once. **M**

**R1.2** — The panel states what it carries AND what it withheld, with
reasons. A selector that silently drops a section takes canon out of a
render and leaves nobody able to see it — the exact failure this week was
made of. **M**

**R1.3** — Where the selector is unsure it FLAGS rather than drops.
Losing canon silently is worse than carrying a line that mildly disagrees.
**S**

**R1.4** — References are unaffected. They attach by role and
jurisdiction, they are images not prose, and nothing here touches them.
**XS**

**R1.5** — Instrument first: a per-block byte and provenance breakdown of
a compiled prompt, beside the prompt preview. Evidence for the selector,
not a prelude to cutting. **S**

---

## R2 — A self-consistency pass when the Bible is written

**Size: M.** Selection is repair work; a Bible that does not contradict
itself needs less of it.

At draft time the whole Bible is wanted — that is what the document is
for. But nothing has ever read it back to ask whether its sections agree.
Ada's carried `use wide or moderate-wide lenses with deep focus` in
Lighting Language while Rendering Language demanded `readable form over
surface` and Composition Rules asked for legibility everywhere: three
sections independently ruling out selective focus, none aware of the
others.

**R2.1** — After a Bible is drafted or saved, a pass reads it against
itself and reports conflicts. Advisory; it never edits the document. **M**

**R2.2** — It must distinguish **designed contrast** from
**contradiction**. `Weathered Present / Pristine Future` is the spine of
Ada's production, not an error — two rules scoped to different subjects,
deliberately opposed. A contradiction is two rules that cannot both hold
*for the same subject in the same frame*. A checker that cannot tell them
apart gets switched off within a day. **M**

**R2.3** — Report where it lands, in the Bible's own sections, so the fix
is one edit from the reading. **S**

---

## A1 — Camera recipes as their own document

**Size: S.** `docs/Cinematography/CINEMATIC_LENS_AND_FRAMING_RECIPES.md`
holds 20 base framings and 13 modifier axes. They belong in a parsed
library, separate from the grammar.

| document | holds | edit cadence |
|---|---|---|
| `CINEMATOGRAPHY_STYLES.md` *(exists)* | what a style is FOR | rarely; creative doctrine |
| `CAMERA_RECIPES.md` *(new)* | the 20 framings, the 13 modifiers | whenever calibrated against renders |
| `camera_defaults.json` *(exists)* | silent fallback only | never, once styles own the camera |

Separate because they change on different schedules, because it makes
pulling ONE row natural rather than a whole style entry, and because
tuning f-stops is not the job of writing what a style means.

**A1.1** — Move sections 2 and 3 into `docs/CAMERA_RECIPES.md` with a
stable slug per row. **S**
**A1.2** — Parse it in `style_docs` as a fourth library. **S**
**A1.3** — Section 2 reads as 20 rows, not 21. Confirm whether one was
dropped in authoring. **XS**

---

## A2 — The recipe is a panel field, chosen at breakdown time

**Size: M.** Not at compile time. The research pass already writes each
panel's purpose and required objects; it should also name the framing —
which makes the choice inspectable before the spend, editable from a
picker of 20, recorded on the take, and paid for once.

Deciding it at compile time would repeat this week's central failure: a
decision the app makes invisibly, inferable only from the picture.

**A2.1** — `camera_recipe` on the panel, with modifier deltas beside it.
**A2.2** — Picker in the breakdown row and the panel workbench.
**A2.3** — The take records the recipe it rode.

---

## A3 — Teaching the narrative model to choose

**Size: M.** A lookup keyed on intent cannot work: a surfer at 400mm and a
race car at 24mm are both "action" and land on opposite rows.

The same breakdown-time pass that does R1 also picks the recipe. What it
reasons about, in order:

1. **What is this panel FOR** — the question its purpose answers.
2. **Where does the weight sit** — one face, a relationship, an object, a
   place, an event?
3. **What must stay readable**, and what may be given up. The choice the
   adjectives never forced anyone to make.
4. **What does the STYLE allow** — the grammar constrains the family
   without determining the row.
5. **Then modifiers**, only where the shot departs from the row's
   baseline, so the prompt carries deltas.

**A3.1** — Array and method into `autofill._instructions`.
**A3.2** — One line of justification the director can argue with.
**A3.3** — A recipe that fights its own style is stated, not silently
resolved.

---

## A4 — Retire the Production Design camera card

**Size: S.** `#cam-default-row` sets a production-wide `Eye level · 24mm ·
Level · Wide`. Nobody chose that; it is a value the app needed. Once a
style carries recipes it is superseded.

**A4.1** — Remove the card.
**A4.2** — Keep `camera_defaults.json` as the silent fallback answering
`— production default —`. **XS**
**A4.3** — The panel's manual camera override stays: the director
disagreeing with the recipe on one shot is the point. **XS**

---

## C3 — A hedge lint for the style documents

**Size: S.** The style libraries are user-maintained prose whose wording
decides whether a style works, and nothing checks them. `style_docs`
parses each document already; it can flag hedges in the same pass and
surface the count in the picker and the reader.

Not an error — Naturalistic/Observational legitimately wants restraint.
The point is that four hedges in a style built on excess is a fact the
author should see.

## C6 — A two-render rule for style evaluation

**Size: S.** Run-to-run variance is large enough that one take proves
nothing. Where the app invites a comparison, it should render two and show
them together.

## C7 — Rewrite the hedged styles *(yours, not the app's)*

`docs/CINEMATOGRAPHY_STYLES.md` is read live, so an edit updates picker,
prompt and reader together.

- `Use saturation selectively` → **`Push saturation hard where colour
  carries meaning, and let the rest fall away`**
- `controlled saturation` → **`decisive saturation`**
- keep `a controlled secondary or opposing color` — palette discipline,
  doing real work
- keep the value-structure line — it is what `extremely` steamrollered
- Subjective/Poetic: remove the opt-out. `when emotionally motivated` →
  `where the moment carries feeling`

**C7.1** Chromatic · **C7.2** Subjective/Poetic · **C7.3** the remaining
five against E2's table

## C8 — Engine per look *(untested)*

Every render in this investigation was `gpt-image-2`; the calibration
images were made in ChatGPT directly. One controlled pair against Gemini,
before assuming anything. If engines differ markedly on style adherence
that is a product fact worth surfacing.

---

## Tried and struck

- **A prompt-length budget.** Replaced by R1. Cutting to a character
  target would throw away canon the panel needs.
- **More precedence text.** Four attempts, each defensible, none
  sufficient. The clause is now correct and it is not the lever.
- **Reordering the prompt.** Moves the style from 15% to 87% of the way
  through and it is still 4% of the text.
- **A screenplay↔cinematography slider.** Proposed, reframed three times,
  cut: the 20 recipes do not sort along one line, and A2/A3 already give
  the director twenty named choices to argue with.
- **A structural-conflict warning.** Struck — it rested on the claim that
  five required objects cannot appear in a subjective frame. They can.
  Avrel at 1.5m on a 24mm wide open holds the hull, the ramp and the six
  figures behind her. All present, not all sharp.

---

## Done

**C4 — a take says what it was rendered from.** `SENT — HAND-EDITED` /
`SENT — THE COMPILE`, leading with the text the model received, both
character counts stated, the compile shown beneath and labelled as not
sent.

Four bugs fixed while looking for the wrong thing, all real, none the
cause: the grammar was scoped to light-and-colour-only; the Bible drafter
wrote lens doctrine into art direction; a panel never said whether its
grammar was its own; a panel could not send no colour reference.

---

## Suggested order

1. **C7** — free, immediate, and by E2 the largest effect available.
2. **R1.5** — instrument. Evidence before design.
3. **A1** — the recipes into a parsed library.
4. **R2** — stop the Bible contradicting itself, before building a
   selector to work around it.
5. **A2 / A3** — the recipe as a panel field, chosen intelligently.
6. **R1.1–R1.4** — the selector, with recipes and a clean Bible to reason
   about.
7. **A4**, **C3**, **C6**, **C8** — small and independent.

R2 before R1 is deliberate: repairing contradictions at the source is
cheaper than teaching a selector to route around them.
