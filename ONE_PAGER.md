# Screenboard Studio

**An art department for a film production.** Screenboard Studio reads your
screenplay, builds an Art Direction Bible with the director, and breaks each
scene down element by element — every required object citing the line of
script it came from. You approve reference images once; from then on they are
jurisdictional, governing exactly the aspect of the render they were approved
for and nothing else. Approved breakdowns lock and are hash-pinned, so every
concept panel is traceable to the document that produced it, and presentation
boards assemble at native 4K. It runs on your own model keys, on your machine
or as a private cloud studio, and the screenplay never leaves either.

> ### The difference
> Every other AI image tool optimises for **generating** pictures; this one
> is built to make it structurally impossible for a model to **reinterpret**
> what a human has already approved.

---

## The pipeline

Strictly sequential, and every stage is gated on the one before it. You cannot
render panels from an unapproved breakdown, and you cannot assemble a board
until every panel is approved.

```
01 Screenplay → 02 Prod. Design → 03 Breakdowns → 04 Panels → 05 Boards
```

Gates are readable as **state**, never as an error after the fact: a control
you cannot use is shown disabled, with the unmet condition beside it and a
link to where it gets resolved.

---

## Key features

### Cited evidence, verified against the screenplay
Every object a panel requires carries an evidence row with a class — from
`SCRIPT_EXPLICIT` down to `UNSUPPORTED` — and a citation. Citations claiming
the screenplay are **checked against the actual text**; one that cannot be
found is demoted and held for your decision rather than passing silently. A
breakdown cannot be approved while any required object lacks passing
evidence, and the weakest class carries a hard budget, so a draft built on
guesswork hits the cap and stops.

### Reference jurisdiction
An approved reference does not govern the whole image. A character-likeness
plate controls the face, build, hair and age — and explicitly *not* the
costume, the lighting or the camera. Each attachment declares its scope in
the render prompt, so a style plate can never quietly dictate composition.

### Never upscaled
If a render is smaller than the slot it has to fill, the app refuses and
flags it for regeneration. It will not enlarge a panel to make a board fit.
This is enforced at the geometry authority, not by convention.

### Locked canon with per-panel granularity
Approving a take freezes exactly what it was approved against — that panel's
fields, its evidence rows, and the board-level direction. Everything else on
the sheet stays editable. An approval can be **withdrawn** without rejecting
the take, because "I want to change the brief" is not "this render was
wrong": a rejection's reason is carried into every future prompt for that
panel, and using it to unlock an edit would poison the work that follows.

### Style libraries you can extend
Cinematography grammars, rendering styles and world textures are authored as
documents, illustrated with your own approved renders. Pick a look and its
full directive rides the prompt. Your own production's house style becomes a
card alongside them, written from your Art Direction Bible's rendering
language and illustrated by your most recent approved panel — so the style
you are working in is described by the document that governs it, not by a
phrase we wrote.

### The prompt is visible, editable, and yours
Every panel shows the exact compiled prompt before you spend anything. Read
it, edit it for one take, or save it to the panel — and when you do, the app
says plainly that the earlier steps no longer write that panel.

### Engines are honest about what they can do
Some image engines receive your reference plates; others only receive a
written description of them. The app says which is which, on the engine list
and again where the money is spent, because a likeness rendered from prose is
not a likeness.

### Ask the screenplay anything
Tell a panel what you want — a question, a correction, how it should feel, a
passage pasted from elsewhere — and its scene is re-read against what you
said. Findings come back quoted, and each states whether the screenplay says
it or you did. Nothing is added until you accept it.

### Your keys, your machine
Connect your own provider keys, or one OpenRouter connection that unlocks a
synced catalogue. Ships as a standalone install (air-gap capable) or a cloud
studio with one isolated service and volume per subscriber. Nothing is
metered, marked up, or routed through us.
