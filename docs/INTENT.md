# Screenboard Studio — Product Intent & Usage

*Current to 2026-08-04 (release 2026.08.04.43). This is the "why and how"
document; the technical companion is `docs/ARCHITECTURE.md`.*

## What this product is

Screenboard Studio gives a film production its **art department**: it reads
a screenplay, builds an Art Direction Bible with the director, breaks
scenes down element-by-element with cited evidence, renders concept panels
against approved references, and assembles native-4K presentation boards.

It exists to prevent one failure mode above all: **image models
reinterpreting approved work.** Every mechanism in the product — locked
sheets, evidence classes, reference jurisdictions, the no-upscale rule,
hash-pinned approvals — makes drift structurally difficult once a human
has said "this is canon."

The product ships two ways, same code: a **standalone app** (buyer's
machine, buyer's disk, air-gap capable) and a **cloud studio**
(`<name>.screenboardstudio.com`, one isolated service + volume per
subscriber). Both render through the customer's own credentials — pasted
provider keys, or one OpenRouter/fal connection that unlocks a synced
catalog of models. First run states this as a setup form: connect once
and the recommended defaults land automatically (narrative on gpt-5.6,
GPT Image 2 as the starting engine); narrative passes can also run on a
stored Anthropic key.

## The convictions the product is built on

1. **Canon is extracted, never invented.** A breakdown's job is to say
   what the screenplay establishes. "Unknown" is an acceptable answer;
   silent invention is not. Every visible object carries an evidence class
   (`SCRIPT_EXPLICIT` → `PROPOSED_NOT_CANON`) and a citation; unsupported
   objects can never pass, in any mode.
2. **Gates are readable as state, never surprises.** A locked stage says
   it is locked, why, and what unlocks it — before the click, not after.
   The button that can't run is visible, disabled, and explains itself.
3. **The human is the director.** The app proposes (PROPOSED languages,
   HOLD evidence rows, board candidates); only the user confirms, approves
   and locks. Rejections are never lost — their reasons ride into future
   prompts as carried rejections.
4. **Nothing is ever upscaled.** A render smaller than its slot is flagged
   and regenerated larger, never stretched. Boards are true 4K.
5. **Typography is drawn by the app, never the model** — titles are always
   correct and legible at print size.
6. **One production, one world.** Each production keeps its own
   screenplay, bible, references, sheets and boards; nothing crosses
   between productions.

## The pipeline — how a user moves through it

The navigation band IS the pipeline. Stages gate on each other; a stage
whose gate is unmet is inert with a `LOCKED` chip, and clicking it drops
an explanation with the remaining steps anchored where the work is.

**01 Screenplay** — upload the draft (PDF/FDX/Fountain/TXT). The app
extracts text once at import (the model-efficient format), maps every
slugline location with coverage depth, and re-checks cited quotes on
every replacement draft (report-only; broken citations surface as CITE
blockers).

**02 Production Design** — six steps:
1. *Style reference images* — three anchors with narrow jurisdictions:
   board layout, cinematography, board rendering style.
2. *Script Scene Scan* — the research model reads every scene and returns
   design languages (confirm/rename/drop; blanks marked PROPOSED),
   environments, key locations, cast, and open questions.
3. *Interview* (optional, persisted per production) — touchstones, medium,
   palette, never-list. Answers BIND the bible draft.
4. *Cast the film* — subjects (characters/vehicles/props) become cards in
   the reference library; photos are reference gathering, not a
   precondition.
5. *Art Direction Bible* — draft (model), review, edit, save. The single
   source every prompt draws from. There is no template default: every
   production's look comes from its own material.
6. *Model bake-off* — every configured engine renders the same screenplay
   location under the saved bible; pick the default by looking.

**03 Breakdowns** — unlocked by the saved bible. "Create Breakdown" from
any location arrives pre-filled (deduped Spec ID + a brief composed from
the read). The research pass drafts panels, required objects and a cited
evidence ledger; HOLD rows demand a human decision; only a sheet whose
required objects all PASS can be approved & locked. Two modes:
`CANON_EXTRACTION` (≤2 weak inferences, no proposals) and
`DESIGN_EXPLORATION` (≤10 weak inferences, PROPOSED_NOT_CANON allowed).

**04 Panels** — the judging room. Takes render against the locked sheet
(hash-pinned) with style anchors auto-attached and subject references
chosen per generation. Judge full-size, one at a time: approve, reject
(reason recorded and carried), repair a region (masked edit, everything
outside the paint preserved byte-for-byte), re-render at full size
(re-performance, never interpolation), derive lighting studies /
palette / materials. Approved takes can be promoted into the reference
library — the loop that lets later scenes anchor to earlier approvals.

**05 Boards** — readiness AND presentation, one page. The slot map shows
exact geometry and per-slot verdicts BEFORE a render is spent.
**Arrange this board** unfolds the arrange room inline on the scene's own
BOARD sheet (2026-08-12 — the standalone Lookbook tool was rolled back as
too big and too separate from board work); layout is a sheet property
there, recorded on the board and never touching the locked breakdown. Assembling produces a **structural board** — the layout
frames holding the individual panels, each clickable through to its
uncropped take — plus a drawn 4K composite available as "Export board".
Boards are candidates until approved.

**Tools (header):** Status (DO THIS NEXT + blocking + advisory + recent),
Reference (the one library, three shelves: STYLE / SUBJECTS / SCENES),
Productions (the Screenboard Library — cards with reach bands, per-
production next verbs, backup care states), Settings (engines & keys,
install-level).

## Cost posture

Customers bring their own keys, so the app's token habits are their bill:
the screenplay converts to plain text at import and every model call reads
that (PDF-per-page billing avoided; prompt-caching engaged by keeping the
screenplay as the stable prompt prefix); failed generations are surfaced
with their provider reason; engines without a working key are not
selectable anywhere.

## What the app will not do

- Invent canon, silently or otherwise.
- Upscale.
- Bypass a provider's safety system — a content-policy refusal is stated,
  with the craft answer (restage to imply, or a different engine).
- Ship one film's look to another: no template art direction, no
  hardcoded project names anywhere in prompts or records.
