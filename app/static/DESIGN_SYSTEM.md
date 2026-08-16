# Screenboard Studio — design system

**For the agent working on this codebase: read this before writing any UI.**
Add to `CLAUDE.md`: `UI work must follow app/static/DESIGN_SYSTEM.md.`

This file is the contract. The app was redesigned in July 2026; markup written
against the old conventions will look wrong even if it "works". If a rule here
conflicts with surrounding code you find, this file wins — that code is v1
residue and should be brought forward.

---

## The two rules everything derives from

**1. Amber is a signal, not a decoration.** `--accent` marks exactly three
things: the current pipeline stage, the one primary action in view, and focus.
Nothing else. Not section titles, not IDs, not badges, not borders for emphasis.
The v1 failure was amber on every `h2`, every ID, and both borders and buttons —
used everywhere it pointed nowhere, and the one live action became unfindable.
Before you add amber, name which of the three things it is. If it isn't one of
them, use `--ink` or `--ink-dim`.

**Status owns colour; selection owns an outline** (2026-08-16, user-caught).
`--ok` means APPROVED and `--bad` means REJECTED, on every surface. Which item
you are currently LOOKING at is a different fact and takes an ink outline
(`outline: 2px solid var(--ink)`, offset so it draws outside the frame) — never
a status colour. Sharing one encoding made a merely-selected take read as
canon, and made an approved take you were viewing unable to say so. Two facts,
two encodings, both true at once.

**Stacking order, stated once so it stops drifting** (2026-08-16, user-caught:
a lightbox opened from a modal rendered behind it). Page chrome `< 100` ·
`.modal-scrim` 400 · `.cropper` 480 · `.lightbox` 500. **A viewer opened FROM
a surface must sit above it** — the lightbox is the topmost thing in the app,
because nothing opens on top of a picture at full size.

**2. Courier carries machine data.** Screenplays are typed in Courier, so the
app speaks the same hand. Spec IDs, statuses, counts, timestamps, roles, hashes,
sizes, file names, column headers → `var(--mono)`. Headings, labels, prose,
buttons → `var(--sans)` (Archivo). A reader should be able to tell data from
voice without reading a word. Never set body prose in Courier; never set an ID
in Archivo.

---

## Tokens

Use variables. Never hardcode a hex in new CSS.

```
surfaces   --bg #121417  --bg2 #15181b  --panel #1a1d21  --panel2 #21252a
           --field #0f1114   (inputs sit INSET, darker than everything)
           --band #131619    (step-sequence alternating ground, 2026-08-14)
           --tile #181b1f    (a set member, one value ABOVE its ground)
lines      --line #2b3037    --line-soft #23272c
           --hairline #1e2226 (section separation inside a sequence)
ink        --ink #eceef0     --ink-dim #9aa1a8    --ink-faint #6b7278
accent     --accent #e0a33f  --accent-ink #0b0c0e (text on amber)
status     --ok #6fae7a  --bad #cd6155  --hold #7d8fd0   (--warn deleted R3:
           it aliased the accent; --hold IS the warning color, hotter = --bad)
type       --sans Archivo    --mono "Courier New"
radius     --radius 0px      (square. do not add rounding)
```

Surfaces layer `--field` < `--bg` < `--band` < `--bg2` < `--tile` < `--panel`
< `--panel2`. Going deeper means "more active/selected", never "more
important". `--band` and `--tile` (STEP_SEQUENCE_SPEC §1.5, 2026-08-14) slot
INTO that ladder rather than beside it: a band sits one step below its
surface's ground and a set-member tile one step above, so a tile never falls
back to its border. `#111316` was tried for the band and measured 1.016:1 —
below perception, spending fill for nothing.

Amber has exactly two values: `--accent` at rest, `--accent-hover` under
the pointer — no third tint may be created (R1). Translucent amber is
`--accent-soft`; bordered amber regions use `--accent-line`; no raw
rgba(224,163,63,·) may appear in a rule (R2).

Status colors report state only. `--ok` is not a "success accent" for
decoration; `--bad` is not a red you reach for because something is loud.

### Three ink tiers, and only three
`--ink` for primary content, `--ink-dim` for supporting, `--ink-faint` for
labels and metadata. Do not invent a fourth grey — a mid-tone between
`--ink-faint` and the surface will fail contrast on `--bg`. (This happened once
already with `#4f5459`.) The single exception is `#4a4d52` on disabled buttons,
where low contrast is the signal.

---

## Layout patterns

**The image is the hero** (STEP_SEQUENCE_SPEC §1.0, ruled 2026-08-14 —
this outranks the rest of this section where they conflict). **This app
makes movies.** Every surface exists to produce, judge or assemble a
picture, so on any surface that has one the picture is the largest element
on it, at the subject's own declared aspect ratio (`aspect-ratio`, never a
fixed height that letterboxes or drifts). Alternates are a filmstrip
directly beneath it at the same ratio, the shown one outlined; a rejected
take stays in the strip as a record. **Specification follows the image,
never precedes it** — the confirmation steps are what the picture was told
to be, and a form above an image inverts the reason the screen exists.
Facts about an image ride on it (id, take number, state, pixel size). A
rail holds only what has **no** picture. **A surface that could show
imagery and does not is a defect**, not a layout to preserve.

**Three type sizes per surface, and the largest anchors the rest**
(§1.2). `24px/600/-.015em` the subject, exactly one per surface · `15px`
headings (600, `--ink`) and body (400, `--ink-dim`) · `11.5px` everything
else. Two roles may share 15px separated by weight ONLY because 24px
exists above them. At 11.5px the family carries the meaning: Courier is a
machine fact, Archivo is a verb. The measured fault this replaced was nine
sizes between 9.5px and 15px — nine steps inside five and a half pixels,
which is not a weak hierarchy but a continuum, and a continuum reads as
one size with noise. Gradations are not contrast.

**One 24px element per surface, per VOICE** (§1.2, amended by A5,
2026-08-16). The subject is Archivo 600; a step spine is Courier, and the two
never compete because §1.3 already makes the family carry the meaning at
11.5px — it carries it at 24px too. A surface whose job is a sequence may set
its step numbers at 24px in Courier beside its 24px Archivo subject; it may
not set two Archivo elements there. A surface with no sequence has no second
24px element.

**Promote by ink tier and position before size** (§1.2, A6, 2026-08-16). A
thing that reads too quietly is usually dim, or filed in a row beside a label,
or both — change those first. The scale gains a step only when a genuinely new
structural role appears, and three sizes have never yet failed to carry one. A
fourth size chosen because 15px "did not separate enough" is the first step
back toward the nine-sizes-in-five-pixels continuum this rule was written to
kill.

**Fill classifies; border does not** (§1.3). A border cannot classify
because a tag and a button both carry one. `--accent` fill is the primary
act (already canon); `--tile` + a `--line` stroke is a set member; no fill
+ a stroke is a secondary control. A set-member tile always sits one value
above its ground. Alternating `--band` grounds are the one sanctioned
exception — a ground is not a tile.

**A verb is full ink and underlined, and every verb on a surface aligns to
one right edge** (§1.4). At 11.5px colour alone fails: an `--ink-dim` verb
sits at the same value as the fact beside it, so `Change camera` read as
part of the camera string. `color: var(--ink)`, `text-decoration:
underline`, `text-decoration-color: var(--ink-dim)`,
`text-underline-offset: 3px`, `white-space: nowrap`; hover raises the
underline to `--ink`. Not each row's own right edge — ONE shared vertical
line, so the eye finds actions by running down a single column.

**Verb or tool — the test is whether ONE object is visible beside it** (§1.4,
A7, 2026-08-16). A **verb** sits inline beside the single object it acts on:
`--ink`, underlined, no box, on the surface's one right edge. A **tool** sits
in a bar of peer tools acting on the REGION rather than on a row: `--line`
border, 13.5px/600, no underline. A bar of underlined 11.5px verbs reads as a
row of footnotes — the measured fault that produced this rule. Facts about a
picture ride on the picture, never in the bar beside it.

**A surface whose job is a sequence numbers its steps** (§1.6/§1.7), and
the number — not a label gutter — is the spine. **The vocabulary is scoped
to `.steps`** — every `.step*` declaration lives under that container and
none is written bare. `.panel.step` is the production-design wizard's own,
older pattern (a numbered PANEL, its number drawn in a 46px `::before`
gutter) and shares nothing but the word: an unscoped `.step { display:
flex }` captured every wizard panel and scattered its contents into
columns (user-caught 2026-08-16). A shared class name is not a shared
component. Within that scope: a label says what KIND of
thing a row is, a number says where you are in the work. Three states, and
the third is not a fourth tick (A8, 2026-08-16). `NEEDS YOU` — number
`--ink`, its own verb. `✓ CONFIRMED` — **you** ruled it; number `--ok`,
label `--ink-dim`, and it offers `Unconfirm`. `✓ SETTLED` — the **work**
ruled it: an approved take settled the step and the user never ruled
anything, so it carries no verb, its title names what settled it
(`SETTLED BY TAKE 03`) and says withdrawing the approval is the way back.
Number stays `--ok` in both confirmed states.

**A tick you made and a fact that settled it must not look identical.**
Rendering both as `✓ CONFIRMED` claims an action the user did not take,
and the count in the head is what makes it matter: `5 OF 5 STEPS
CONFIRMED` on a panel nobody confirmed anything on is a false report. The
head counts them separately or generically — `n OF n STEPS SETTLED` when
every remaining one is frozen, never `CONFIRMED`.

A confirmed step dims but stays fully legible — it is evidence you already
ruled, not clutter to be hidden. Do not collapse it.

**A gate states its condition and does not lie** (§2.4). A reserved shape is
still forbidden — **except** a frame that earns it by STATING THE BLOCKER
that keeps it empty (C2, 2026-08-16). The exception is the sentence, not
the shape: a dashed cell that says nothing remains forbidden. That extends to
the CURSOR: `not-allowed` may only mark something that genuinely does
nothing. A control that explains itself on click takes `help`; one that
navigates takes `pointer` (2026-08-16). If unconfirmed
steps do not block the act, say so — `3 STEPS UNCONFIRMED — YOU CAN STILL
RENDER` — rather than disabling the button. A render is the end of a
sequence, not a reward for finishing one.

**The gutter is for rows, not blocks** (§1.8). A label with a one-line
value earns an aligned gutter; a label with a grid under it does not —
reserving a label column plus a verb column squeezed a twelve-tile grid
into two wrapped columns. A block label sits above its content and the
content takes the full column.

**Cap prose measures independent of surface width** (§1.9). 15px body
across a 1200px column runs to ~140 characters a line: cap prose at
`max-width: 720px` and Courier annotation at `900px` whatever the surface
is. Extra width goes to rails and grid columns, never to line length.

**Pipeline band.** `nav#nav` is the product's spine: numbered stages 01–04 in
work order, then `.nav-gap`, then off-pipeline tools (Reference, Settings). A new
*stage* gets a number and joins the band in sequence. A new *tool* goes right of
the gap. Stage cells use `minmax(0,1fr)` tracks and their labels are
`white-space: nowrap` — a long label must be shortened, never allowed to inflate
its track.

**One lead per screen.** At most one `.panel.panel-lead` (amber left border,
`--panel2`) per view, and it holds the thing blocking the user. Everything else
is a plain `.panel`. Two leads = no lead.

**An empty state never reserves the shape of the missing thing.** (PANEL_CARD
ruling, 2026-08-03.) No hatched rectangles, no dashed image-sized wells whose
only message is *there is nothing here*. Show what the user has, and make the
act that fills the gap the primary action. A component with an empty life and
a filled life ships as one component with two states — the empty state is a
different layout, not the filled layout minus its content.

**The control panel states, it never explains** (SETTINGS_CONTROL_PANEL
P1/P4, designer-ruled 2026-08-05): once a surface's setup life has done
the persuading, its configured life carries required information only —
machine facts in Courier, at most one Courier footnote per section, zero
paragraphs. Explanation lives in first run and in the modal a row opens.
Worked example: the configured AI & engines tab — two role cards with
live selectors (`EACH PANEL KEEPS ITS OWN PICKER`), one equal-row
credential list (`BILLED PER RENDER — REJECTED TAKES COST THE SAME`),
and a one-line MODELS summary (`N ENABLED · N IN CATALOG · SYNCED
<AGE>`). A row that isn't connected shows a name and Authenticate —
never a status chip for something that hasn't happened. Failing states
(`401 — REJECTED`, `NO NETWORK`, `KEY FAILED`) are machine facts and
always stay.

**A step states what it does to the movie, never what it is**
(PRODUCTION_DESIGN_V3, designer-ruled 2026-08-06, app-wide): prose that
explains the app's own architecture to the user is cut; prose that tells
the user what a control will do to their film stays. When a sentence can
become a section label, it becomes the label. Courier condition lines on
step headings carry the surviving conditions; jurisdiction pairs read
`SETS … / NOT …`.

**Two doors, one section** (B1, ruled 2026-08-06). When two controls
perform the same act by different means, they sit **side by side in one
section** — never one at the top of the page and the other hidden under
a table. Amber marks the recommended door only (`--accent` top border,
`--accent-line` frame); the alternative is a plain `--line` card with a
ghost submit. Each door states its nature once, in Courier, beside its
name (`READS THE WHOLE SCREENPLAY` / `YOU FILL EVERYTHING`). Worked
example: Breakdowns' auto-breakdown and blank-sheet doors.

**A table holds data; a create form never renders as its last rows**
(B4). A form living inside a table's panel reads as another row and is
found by nobody looking for it. Move it to the section that owns the
act; the table keeps its heading, its count, and its rows.

**Tags ride the image; verbs sit beneath it** (T1, ruled 2026-08-06).
Where a picture is the evidence, its state and identity overlay the
picture — state chip top-left, identity bottom-right, each on
`rgba(11,12,14,.82)` with a `--line` border so they read on any render —
and the row below carries verbs only. **Horizontal scroll on navigation
is never acceptable**: an action that scrolls out of view is an action
the user cannot find, so a row of verbs wraps to a second line and never
scrolls. A chip swallows its own click; the picture opens the lightbox.

**The labelled table** (D4, canon): a data table gets a Courier header
row on the same fixed grid tracks as its rows (worked example: the
locations table, `minmax(0,1fr) 240px 120px 190px`), group headers on
`--field`, and it never scrolls inside a fixed-height box — the page
scrolls, the table does not.

**The verb is the form** (R8, canon with its boundary): a lead may carry
the unblocking form itself only when ONE input satisfies the blocker.
Two fields or more is a task, and tasks live in their stage — the lead
then links, stated, to the stage.

**One surface per document** (R11, canon): the Art Direction Bible has
one editor; Draft is primary amber (it creates the thing the gate
needs), Save is ghost bookkeeping, and the overwrite confirm protecting
unsaved text is mandatory.

**Sticky chrome & the z-ladder** (R13, canon): the pipeline band is the
literal ceiling. Ladder: sticky band 44 · header 45 · toast 50 · popover
55 · menus 60 · lightbox 100 · modal 400. New floating surfaces slot in;
no new z-index value may be coined without a row here.

**The two-mode band** (BAND_CONDENSE ruling, 2026-08-05): tools are not
stages. While a tool view (Status / Reference / Productions /
Settings) is open the band condenses to half height — sublines and the HERE chip
leave, cells drop to one row (7/8px padding), backgrounds recede
`--bg2` → `--bg`, labels fall to `--ink-faint` (dimmer, never
unreadable). Progress top borders survive — the map keeps reporting —
and no cell reads "current" in tool mode; that absence IS the signal you
are outside the pipeline. Sticky position and z-order untouched; the
condensed band stays fully clickable (it is the way back) and hover
still lifts a cell to `--panel` + `--ink`. 150ms ease-out; snaps under
reduced motion. Keyed on `body.tool-mode`, toggled at the router
chokepoint so boot-restored views wake correct.

**Main/side split.** Work goes left in `.dash-main` at generous width; counts,
standing rules, and history recede into `.dash-side`. Counts are not the point
of a screen — the next action is.

**Wizard steps.** `.panel.step[data-step="N"]` renders its number in the gutter
with a connecting rule. If you add or reorder steps, renumber `data-step` — it
is static markup, not generated.

**Ledger rows.** `.ledger-row` — every row *including the header* carries
`border-left: 2px solid transparent`. A state marker colors that border in. Never
add the border only to marked rows; it shifts columns 2px and destroys vertical
scanning. Non-PASS rows tint `--panel` (inline style beats the zebra rule).

**Pipeline band (v3).** Five stage cells in `minmax(0,1fr)` tracks, each with
number, label, a live Courier subline from `stage_summary`, and a top border
stating progress: `--ok` complete, `--accent` current (the viewed stage, else
the work frontier — exactly one amber in the chrome), `--bad` blocked,
`--line` unreached. `HERE` chip marks the viewed stage only. Tools (Status ·
Reference · Productions · Settings) live in the header with the
engine credential dots.

**Cursor band vs reach band — both are canon; do not "fix" one into the
other** (PRODUCTIONS_PLAN A7). The nav band is a *cursor*: where the user
is standing right now. A production card's band (`.prod-band`) is a
*reach* indicator: what this production has ever achieved. Same four
colors, different mapping:

| | Nav band (cursor) | Card band (reach) |
|---|---|---|
| `--ok` | stage complete | production has **ever** completed this stage |
| `--accent` | the stage you are on | *not used — a card has no cursor* |
| `--bad` | stage carries a blocker | any of this production's sheets is blocked here |
| `--line` | not reached | never reached |

A production may legally read green through 05 with 03 in red — it has
boarded work and one blocked breakdown right now.

**Judging room** (`.board-room` = `.board-rail` 230px · `.board-stage` ·
`.board-side` 300px). Rail: sheet block, panel list with latest-take thumbs
and readiness marks, derived entry, assembly pointer. Stage: panel strip, one
big staged render on `--field`, status chip left / actions right (Approve
panel is the screen's only amber; → Reference disabled until approved), ghost
secondary row (Repair region · Crop → reference · → Light study · Delete
forever on rejected takes only), takes filmstrip (rejected dims the image
only), then the generation bench — whose Generate button is deliberately not
amber. Side: THIS RENDER facts, ANCHORED TO, COMPILED PROMPT with Full
toggle, CARRIED REJECTIONS.

**Blocking rows + DO-THIS-NEXT.** Row grid `badge · text · action`: kind
badge fixed 52px Courier 10px bordered in its status color (never filled),
rows split by `--line-soft` top borders, action is an amber text link-button
(`.block-act`), not a bordered button. The DO-THIS-NEXT lead is blocking[0]
promoted into `.panel-lead` — Courier amber kicker, one-line verb headline
(Archivo 600 21px), one supporting sentence max, primary button right. It is
a presentation of the first blocker, never a second list. Blocking rows
report what stops the next render. Advisory rows (care of existing work,
kind `CARE`) render below an `ADVISORY` divider with a faint kind badge
(`--ink-faint`, never `--warn`), are never counted as blockers, and are
never promoted to the lead (review 2026-08-01 §9).

**Stated-path empty states** (PRODUCTIONS_PLAN M6, superseded in part by
LOCKED_STAGE_PLAN L4). A dead end states the path to the outcome the user
came for — as the **stage checklist** (see Components), never as an
explanation box plus a go-to-stage button. The *middle* state (locked
sheets, no boards yet) still gets exactly one Courier `--ink-faint` line
above the bench — `NO BOARDS YET — APPROVE EVERY PANEL IN A SHEET, THEN
ASSEMBLE` (ratified C2) — because the picker and bench already state the
path by being present. First run (no productions, empty root) is the same
idea at app scale: one centered panel, "Name the show you're working
on.", create + restore, the pipeline band hidden until there is a
production to stand in.

**Locked stage cells** (LOCKED_STAGE_PLAN L1, mock 12b). A stage whose
gate is unmet is a condition, not a destination: its band cell is inert —
no navigation, no view change, no history entry — on the sanctioned
`#17191c` ground with `cursor: not-allowed` and a bordered `--hold`
`LOCKED` chip beside the name. Labels stay `--ink-faint`; never dimmer —
the band is the product's map and every stage name must stay readable
(`#4a4d52` is for disabled buttons only). Cells stay focusable with
`aria-disabled` so keyboard users get the same explanation. Every unmet
stage locks, not just the next one.

**Anchored lock explanation** (LOCKED_STAGE_PLAN L2, mock 12b). Clicking
a locked cell explains in place: a popover on `--panel2` with a `#3a4048`
border and no top border (it hangs from the band), anchored under the
**first unmet stage's cell** — the cell the user actually needs — roughly
two cells wide. Header: bordered `--hold` chip (`03 IS LOCKED`) and `×`.
One sentence stating the gate with the live remaining count; the
remaining steps in Courier, current `→` amber, rest `·` faint; footer
`03 UNLOCKS ITSELF THE MOMENT …`. Dismiss on ×, Esc, outside click. The
view behind never changes.

**An act lives where its precondition is met; its result lives where it
belongs** (SWATCH_GENERATE_RULING, ruled 2026-08-06 — the pair to the
anchored explanation above, and reading them together is what makes
either memorable). When those are different places, the act states where
its output landed and links there. **Never place a verb next to its
result if the verb cannot run there.** Worked example: `Generate palette
swatches` reads the SAVED Bible, so it stands under the Bible in step 5
as a bordered ghost row (Draft owns that page's amber; generation is a
follow-on) with the Courier line `FROM THE SAVED BIBLE · LANDS IN STEP
1 / COLOR PALETTE`; on completion it states `N SWATCHES PROPOSED IN
COLOR PALETTE` with a link that scrolls there. The swatches themselves —
and their approve/reject controls — stay in the Color Palette column,
because judging a swatch happens where the swatch is. Before the
precondition exists the row does not render at all: the stage's own gate
already explains the situation, and stating it twice on one screen is
verbosity.

**A verb sits with the thing it acts on, and never in the row of verbs
that judge it** (NON_CANON_REVIEW_2026-08-07 — the pair to
*act-where-condition-is-met* above; that one says a verb waits for its
precondition, this one says it stands next to its object). Making,
reading and judging are three different acts, and a bar that mixes them
makes the user read every button before pressing any. **Generation lives
in the header of what it regenerates** — `Rescan this language` sits in
the swatch viewer's header, not its footer, because the footer is the
verdict bar. **Verdicts live in the footer.** **Destruction lives wherever
it can be read in full**, which is never a 44px row.

Three consequences, all canon:

- **A destructive act is only offered where its object can be read in
  full.** Not in a row, not in a strip — in the view that shows what will
  be lost. The approved ramp row carries no `×`; `Remove group` is a
  right-aligned `.text-act` in the viewer's footer, confirming with the
  count, because by then the user can see all eight swatches.
- **A bulk verdict is withheld until everything it judges has been seen.**
  State the condition beside the withheld verb; never state it and then
  permit the act anyway. `Approve all 19` is disabled while any language
  is unopened, with `2 OF 5 LANGUAGES UNOPENED` as its explanation.
  `Discard the rest` is NOT withheld — rejecting unread proposals is
  legitimate and every rejection is logged.
- **Amber marks what blocks. A report has no amber**, however urgent it
  reads. If a surface only tells you something, its verbs are
  `.text-act`. The breakdown's design-questions block is the case: nothing
  is blocked by an unanswered question, so its verb is not amber and its
  count (`4 OF 7 ANSWERED`) is a fact in Courier `--ink-faint`.

**A resolved item fades its label and keeps its answer.** An answered
design question stays inline — collapsing it would hide the answer, and
the answer is the only part worth re-reading; the question is just its
label. Question to `--ink-faint`, answer below it in `--ink`.

**A card is for a thing with a picture** (canon pass R4, 2026-08-10, mock
au-ref-register). Where a record has no image to judge, it is a row in a
labelled table, not a card with an empty well — an uncast-style card is an
image-sized well whose only message is that there is no image, and it
invites a judgement that cannot be made. A register of such rows belongs
under the shelf that would hold its answers, never beside it as a peer.
Worked example: unanchored screenplay locations — a labelled table
(`.loc-register`, tracks `minmax(0,1fr) 130px 210px 170px`) beneath the
SCENES card grid, section label `UNANCHORED · FROM THE SCREENPLAY'S
SLUGLINES`, one `Add reference` text act per row prefilling
`LOCATION_GEOMETRY — <NAME>`, footer stating `CASTING STAYS
SUBJECTS-ONLY`. The shelf count states the finding factually — never an
apology.

**A room is owed when other records inherit the prose** (canon pass R3 —
the discriminator on *edit a paragraph in a room, not in a cell*). Prose
only its own record reads is edited in place; the room exists so a save
can state its blast radius, and a record with no inheritors has none. The
discriminator is inheritance, not length. Worked example: the panel brief
edits in place (`.brief-row`), its Courier line stating `JOURNALED · NEXT
TAKE PAINTS FROM THE NEW BRIEF · NOTHING ELSE INHERITS IT`; the
environment editor keeps its room because sheets inherit it.

**One control, two presentations** (canon pass R7, mock au-wb-camera). A
setting authored on one surface and merely in force on another shows its
full controls where it is authored and a single stated Courier line where
it is inherited — with the verb beside the line. A summary always states
the value, never the word "Custom". Worked example: the camera axes —
full `.cam-row` on the Look Interview and the breakdown editor (authoring
surfaces); on the panels workbench one line, `EYE LEVEL · 24MM · LEVEL ·
WIDE — PRODUCTION DEFAULT` / `Change camera`, opening the four selects on ask
with `Save camera` / `Cancel`; an approved take freezes the act in place
with the condition in its `title`. Provenance suffixes `— PRODUCTION
DEFAULT` / `— THIS PANEL` answer "why does this say 24mm" without a
sentence. The first read `— FROM BIBLE` until 2026-08-16 and named the
wrong document: the default lives in `data/camera_defaults.json`, set on
the Cinematography anchor, and the Art Direction Bible has never held it.
A provenance label that points at the wrong place is worse than none.

**Geometry is computed once and declared** (canon pass R2). When one
component draws and another must aim at what was drawn, the drawer emits
its rects and the aimer consumes them. Two implementations of one
geometry is a drift bug with a permanent maintenance cost, not a
tolerance to tune. Worked example: `render_sheet` returns a geometry
manifest (block outer, image band, slot rects) riding the preview
response as `X-Sheet-Geometry`; the composer overlay positions from it
and measures nothing.

**A set that means something as a set renders as one object**
(PALETTE_GROUPS_PLAN, ruled 2026-08-06) — the members live inside it, one
click away, not spread beside it. Grids are for things that merely share a
type; a ramp, a rig, a call sheet are single objects with an inside. A
palette is the case that names the rule: the ramp IS the swatch, the
colours are its inside.

Worked example, and the shape to copy. A design language renders as one
contiguous `.sw-ramp` — hero band leftmost at `flex:2`, the rest ordered
light → dark by relative luminance (`0.2126R + 0.7152G + 0.0722B`, ties
broken on the hex so the order never reshuffles), bands touching: no gap,
no radius, an `outline` rather than a border so nothing insets them. A
value-key pair is ONE swatch, so it takes one band split top/bottom. Under
it, a Courier label — language, count, and either `HERO #4F766C` or
`OPEN` in amber where no hero is set. Clicking anywhere opens the **swatch
viewer**, which holds every per-colour fact and verb: the ramp again at
92px where clicking a band sets the hero, one row per colour (chip, name,
hex, citation, and `Recolor · Approve · Reject` as text acts), and a
footer running the same per-reference status records the group bar runs.
Amber does three jobs here and only these: the hero band's inset outline,
the `HERO` chip, and `OPEN` on a group still asking for one — a hero is
the single thing the page asks a designer to decide.

Two consequences worth stating because they are easy to get wrong. **A
rejected hero leaves the group `OPEN`** — the user chooses a hero, the app
never guesses one after the fact. And the members are still individually
governed: every approve and reject remains its own reference status record
with a reason (D8), and removing a grouped row deletes each reference
through the normal path so the log records every one. Grouping is a way of
SEEING, never a way of acting on many things as if they were one.

**A long list shows its head and states its tail**
(SCAN_CONSOLIDATION, ruled 2026-08-07). Five rows per group, then one row
that says how many more — `Expand — 35 more` with the group's name in
Courier beside it, swapping to `Collapse` when open. Groups of five or
fewer render no expand row at all, and a collapsed group states `SHOWING
5` beside its count. **Search always ignores the cap:** while the finder
has a needle every match renders, in every group, and the cap returns when
the field clears. A list that hides matches behind an expand is a list
that lies. Expansion is per group and lives outside the render, so a
re-draw does not forget what the user opened. One helper (`capList` /
`capRow`) serves every capped list, so two of them cannot drift apart.

**Edit a paragraph in a room, not in a cell** (same ruling). When the
thing being edited is prose that other records INHERIT, it opens a modal
that shows both the prose and what inherits it, and states the blast
radius before the save. The environment editor is the case that names the
rule: `.envm` at 960px on the `modal({custom})` shell — a 150px textarea
for the rules, the optional LIGHT and MATERIAL facts a designer always
separates from the prose, the design language's palette ramp read-only at
22px, and a right column listing the inheriting locations (capped by the
rule above) over the Courier line `EDITING THE RULES REPAINTS ALL N SHEETS
THAT HAVE NOT BEEN OVERRIDDEN`. The room's own primary act carries amber;
a verdict on a PROPOSED record stays on the card, because a verdict
happens where the proposal is.

**Recent feed.** `.recent-row` — timestamp column flex-none Courier
`--ink-faint`, text Archivo 13px `--ink-dim`, machine IDs inside the text in
Courier `--ink` (`monoIds()`). No icons, no dots — the timestamp column is
the rhythm.

**Coverage meter.** `.loc-meter` — 4 segments 11×4px, 3px gap; filled =
`--ok`; a single amber first segment means "thin — inference will be spent
here"; empty = `--line-soft`. This is the project's only meter vocabulary —
reuse it anywhere "how much support exists" appears (canon budget included);
never invent another bar.

**Slot map.** `.slotmap` — exact assembler geometry as absolutely-positioned
`.slot` cells on `--bg2` in a `--line` frame; panel ID chip top-left, verdict
chip bottom-right (status-color border, never filled); TOO-SMALL tints
border + id `--bad`; app-drawn title/canon blocks are labeled `APP-DRAWN`.
The map is read-only geometry — actions live outside it.

**CANNOT-LOCK gate strip.** `.gate-strip` — amber left border, Courier amber
label, one line per failing validate condition (the *server's* rules: PASS
gaps, allocation, citations, weak budget), "Jump to first ↓" as a text
action. Approve & lock disabled while it shows.

**Lock strip** (`.gate-strip.lock-strip`). The gate strip vocabulary in grey
(`--line` left border, Courier `--ink-dim` LOCKED label) stating why editing
is off, with the resolving actions inline (Create revision / Unlock & edit).
Amber gate = "cannot proceed forward"; grey lock = "cannot edit backward."
Any state that hides controls must surface one of the two.

**Placeholder bands** (`.hatch` / `.hatch-fine` / `.hatch-bad`). Opaque
two-tone 135° bands — the Board Assembly stripe everywhere; no thin lines,
no translucent ink. `.hatch` 7/14px for blocks ≥ 60px tall; `.hatch-fine`
5/10px for smaller thumbs; `.hatch-bad` the red-shifted pair for TOO-SMALL
and error surfaces (with the `--bad` border — border and label carry the
state). Band tones are deliberate near-surface pairs, not new greys. Hatch
means "an image belongs here and isn't here" — never on populated surfaces,
never behind body text. Applied by class only; the rules stay LAST in the
component cascade — `background:` shorthands reset the image.

**Finder list** (`.loc-search/.loc-scroll/.scene-row`). A Courier search
field over a `--field` scrollable list (max-height, global scrollbar);
parent rows expand to children; every row ends in its one verb (Create
Breakdown / Open Breakdown — the product's own vocabulary, ruled
2026-08-01). Row anatomy follows registry rows: Courier identity
left, facts middle, ghost/text action right. Reuse for any >30-item
findable list; below ~30, the coverage-table pattern is enough.

**One reference library** (`.shelf`, the Reference view). There is ONE
library ("Research" was renamed REFERENCE), on three shelf sections
ordered by *when an image rides along*, not how it arrived: STYLE (every
render, automatically) · SUBJECTS (when its subject appears on a panel —
subject cards ARE this shelf) · SCENES (when a board covers its scene).
**The ramps ARE the STYLE shelf** (canon pass R5, 2026-08-10, mock
au-ref-style-shelf): one 34px ramp per design language — name and count
above, `Open group` beneath — with individual plates behind the group
viewer each ramp already opens; no plate grid on the shelf. Quarantined
swatches keep their cards below, under `QUARANTINED · AWAITING A
VERDICT` (*a verdict happens where the proposal is*), and a mixed
group's count reads `N PROVISIONAL` in `--bad`. The shelf count states
`N GROUPS · M SWATCHES`.
Shelf header (`.shelf-head`): Courier bold shelf name · faint Courier
ride-along line (`RIDES ALONG — …`) · right-aligned Courier counts
(`.shelf-count`). Intake lives behind `+ Add reference` (the role
dialog); the search field uses the finder-list vocabulary and filters
every shelf. Production Design step 4 ("Cast the film", `.uncast-block`)
is a *door* into SUBJECTS: extraction proposals grouped CHARACTERS /
VEHICLES / PROPS under Courier faint fixed-width row labels; casting a
chip creates the card in the library. The wizard owns the moment and the
gate (step badge `n CAST · m UNCAST`, `--hold` while uncast > 0); the
library owns the data.

**The read reveal** (`.reveal-strip` + step-2 order, mock 6a). A completed
screenplay read presents as a summary, not a wall. The strip is the lead
treatment inside the step (amber left border, `--panel2`, Courier amber
kicker `THE READ FOUND`): Courier counts that link to their sections
(segments render only when their data exists — never `0 ENVIRONMENTS`),
logline beneath. Then in order: language chips, environment cards, the
locations finder (grouped under `.loc-group` headers by the read's verbatim
environment assignments when they exist, flat otherwise — the coverage
table and the wizard list share one `buildLocFinder` code path), and open
questions as answerable rows (`.q-row` — ledger border box, `--ok` left
border when answered, deferred rows dim their text only). Answers persist
in the analysis payload and append to the interview at draft time.

**Scope inheritance** (spec editor panels — review 2026-08-01 §3+4). Sheet
scope is the board's baseline and applies to every panel. A panel may
declare an exception for design languages and environment — opt-in, visible,
reversible. Inheriting panels state it in one quiet Courier `.pscope-line`
(`SCOPE — INHERITS BOARD · …`, live against the board's scope) with a ghost
`Override` text action — never an empty control that looks unset. Overriding
reveals the facet chips and environment select in place with `Revert to
board`; the panel head gains a Courier `--hold` bordered `SCOPE OVERRIDE`
chip (proposed-state family). The `.scope-carry` receipt splits when any
panel overrides: `BOARD CARRIES — …` plus one `Pnn OVERRIDES — …` line per
diverging panel (`.carry-ovr`, `--ink-dim`); unchanged otherwise. A panel's
environment is exactly one (the sheet's is one-per-board); languages stay
multi-select. Locking freezes overrides with the rest of the scope.

**Gallery drill-in** (Board assembly — review 2026-08-01 §5). A stage that
holds many finished artifacts opens on a grid of them; selecting one
replaces the grid with a single contained full-width card carrying that
artifact's judge actions, and a `← All boards` text action returns. The
contained image never crops — finished work is judged whole, unlike takes,
which cover-crop into slots. The bench/picker above the grid persists in
both states, so producing more never requires leaving the drill-in. Same
shape as the judging room (many small, one big) — keep the two consistent.

**Entry gate** (`.gate-page` — review 2026-08-01 §6). A standalone centered
`.panel` (~380px) on `--bg` holding the wordmark, one field, one `.primary`,
and at most one line of `.hint`. No nav band, no header tools, no brand-sub
project name — there is no project context before auth. Errors render as
the field's own state (`input.bad`) plus one `--bad` line, never a toast.
The gate is the only screen allowed to be vertically centered; the
centering lives in `.gate-page`, never inline.

**An in-card wait states its phase in sentence case and its progress in
Courier beneath** (ruled 2026-08-07). Two facts, two voices — never one
sentence carrying both. `Packing the production…` on `.busy-label`, then
`12.4 MB OF 88.1 MB` on `.busy-prog` in `--ink-faint`. The strip belongs
to the card it describes, at its foot, collapsed when idle: the wait
belongs to one production and the shelf shows several.

**Pending take tile + take state tags** (`.take.pending/.take-spin`).
In-flight work holds its place: a pending tile sits in the filmstrip with
the `.busy` spinner vocabulary (honoring `prefers-reduced-motion`) and
survives closing whatever screen launched it. State reads at a glance in
the strip: approved = `--ok` border + label; promoted = `· REF` suffix on
the tile and a `REFERENCE · REF-xxxx` bordered badge on the stage (status
color border, never filled — the verdict-chip grammar).

**Three-question Settings order** (CONNECTORS_UI_PLAN, ruled 2026-08-03;
headers renamed by SETTINGS_FIRST_RUN_PLAN F7). The AI & engines tab
answers exactly three questions, in order, never mixed: SET DEFAULT
MODELS (the two AI roles and their selection) · WHAT PAYS FOR IT (every
credential — built-in keys and connectors in ONE list; splitting them
would imply a hierarchy that does not exist) · WHAT ELSE IS REACHABLE
(the synced catalogs and the enabled set). The numeric 01/02/03 prefixes
retired with the rename — the order carries the meaning.

**Capability before vendor** (ruled 2026-08-03). Wherever models list —
the catalog browser, every Model dropdown, the engine picker — they group
by what they can do (`ANCHORS REFERENCES` first, `STYLE STUDIES ONLY`
second), never by who sells them. At the point of choice the question is
whether this model can hold a subject, not who bills for it.

**The two lives** (SETTINGS_FIRST_RUN_PLAN, ruled 2026-08-03). Before a
credential exists the AI & engines page is a SETUP FORM (quick-start hero,
account list, withheld-verb role tags); after one exists it is a CONTROL
PANEL (the standing layout). A dropdown is never an error message, and a
control that cannot act does not render as a control — an unmet role
renders the dashed withheld-verb tag (`NEEDS THE OPENAI KEY`), never a
disabled dropdown. First run carries required information only: no
footnotes, no rationale cards, no zero-count stat tiles.

**A record has no status colour** (HARNESS_AUDIT U1, ruled 2026-08-14).
Status colour marks live state — what blocks, what needs attention. A
resolved judgement, an applied delta, a past rejection is history:
`--ink` and `--ink-dim`. The mirror of *a report has no amber*. Worked
example: the carried-notes rail — the `SIZE` tag on Status earns `--bad`;
a note riding the next take does not.

**A person's sentence is never Courier** (HARNESS_AUDIT U1, ruled
2026-08-14). Courier is for ids, sizes, counts and statuses.
User-authored prose is Archivo in the case it was typed, even when it
sits in a rail full of machine facts.

**The lead promotes, it does not copy** (HARNESS_AUDIT U2, ruled
2026-08-14). A row promoted into `.panel-lead` is removed from the list
it came from, and that list's count excludes it (`Blocking — 1 more`;
the section is omitted at zero). One fact, one place, one act.

**A stage that knows what you were doing must not ask** (HARNESS_AUDIT
U3, ruled 2026-08-14). A surface with a remembered or single-valued
selection opens on the work; the selector remains as a switcher above
it, never as the whole screen. At genuinely zero, one stated line points
at the stage that resolves it — never an empty select as the screen.

**A locked surface reads as a document, not a disabled form**
(HARNESS_AUDIT R10, promoted 2026-08-14 from the evidence ledger).
Controls drop their affordance and read as values (`:disabled` with
transparent chrome). Applies to every locked surface, not just the
ledger.

**Sheet-render typography is the artifact's; app chrome is the
system's** (HARNESS_AUDIT R4.6b, ruled 2026-08-14). A render may bundle
a face the chrome may not use — the same separation as sheet ink not
being a design token. The font ban in this file governs chrome.

---

## Copy

**A name a human wrote is Archivo, even in a list shaped like data** (B5,
2026-08-16). Courier is machine data — ids, counts, hashes, states. Film
titles, people's names and place names are proper nouns somebody chose,
and setting them in Courier claims they were emitted by something.

**An axis the app has never taught is stated by what it is NOT, before its
options appear** (B8, 2026-08-16). `not mood, not light, not
cinematography` does more work than a paragraph of definition. A field
whose answer comes from a known vocabulary shows what was CHOSEN — the
name — not the directive that choice writes.

**A label names its effect on the work, not its destination in the data
model** (A1, ruled 2026-08-16). `EACH BECOMES A BIBLE SECTION` describes our
filing; the user is asking what changes in the picture. If a label can be
answered with "so what?", it is naming a destination. Where a label genuinely
has no effect on the render, say THAT — `SPEC ID — JUST A NAME` — leading with
the reassurance. Every Courier caps label in stages 02-05 is audited against
this: one naming a store, a file, a section, a record or a table is wrong. A
`?` card alongside is the right home for an asymmetry the label cannot carry
(design languages fall back to keyword inference; environments never infer).

**A reassurance precedes its consequence** (B3, ruled 2026-08-06). When a
field is bookkeeping, say so *before* stating what is permanent about it.
Worked example: the Spec ID help opens `Just a name. Does not affect
generation.` and only then names the permanence. The previous copy led
with "used in filenames, prompts, and the audit trail", which reads as
*this steers the render* — and users stalled on a field that decides
nothing. A help affordance is the canonical `?` beside the label, never a
bare `title`: a tooltip nobody knows exists is not documentation.


Prose was ~3:1 over interface by area in v1. Rules:

- One `p.hint` per panel, max. It is capped at `74ch` — respect that.
- A control's explanation goes in its `title` tooltip, not beside it. Never both.
- Constraints render as structure, not sentences. `CONTROLS face · hair · build`
  / `NOT costume · light · lens` in Courier beats a four-line paragraph.
- Every step or blocking state ends with the single next verb. If a screen has no
  verb, it isn't finished.
- Sentence case in prose; uppercase only for Courier labels and badges.

---

## Components

**A card has an empty life and a filled life, and they are ONE component**
(B1, 2026-08-16). Empty: the head, its SETS/NOT line, one button — nothing
reserved, no dashed well, an honest empty state rather than the filled
layout minus its content. Filled: **the picture is the largest element, at
its own ratio, first** — then the name, then the words, then a Courier
provenance line where one exists — and clicking anywhere on it reopens
whatever sets it, because the thing you are looking at is the thing you
would change. Both lives and the catalogue cell render from **one
function** at two scales: if the catalogue gains a field, the card gains
it or deliberately drops it in one place. Two drawings of one thing always
drift.

**Never pad to three** (B3, 2026-08-16). Where a set has fewer members
than its layout expects, show the members that exist and state the absence
in one Courier line — `REFERENCE FRAMES — NOT YET IN THE LIBRARY`. Empty
cells are reserving the shape of the missing thing, and the sanctioned
exception earns itself by naming the blocker; a dashed cell names nothing.

**Four text roles on a card, not seven** (B4, 2026-08-16). Canon's cards
carry two or three. Seven is a document rendered as a cell — it is what
makes a description wrap to a column an inch wide. Anything that rewards
reading goes behind one door, in a reading view with `Copy`, because
nobody reads an essay inside a grid.

**A placeholder says it is one, once per surface** (B2, 2026-08-16). A
diagram teaches an axis; a picker has to sell a look; those are different
jobs. A stand-in is allowed while the real thing is missing, disclosed in
**one line at the head of the panel** — never a mark on every card, which
is nine statements where one is honest. Where real imagery already exists,
the placeholder is not permitted at all.

**A generated entry and an authored one must not look identical** (B6,
2026-08-16). Where the app captures something from the user's own work and
places it beside things we wrote, the captured entry leads with a Courier
provenance line and a hairline under it. Position alone does not disclose.

**An escape hatch is not a member of the set it escapes** (B7,
2026-08-16). It sits below the set, after a hairline, full width, as a
labelled row — never as the last cell of the grid, because a set-member
tile classifies by fill (§1.3) and an escape hatch is not a member. And it
appears **once**: the same control drawn in two places is the fault
`one-control-two-presentations` already names.

**A confirmation never changes what a control can do** (C3, 2026-08-16).
Confirmations are advisory (§2.4), so a control that loses its affordance
when a step is confirmed is a confirmation that gated something — and two
rules cannot both be true. The evidence ledger reads as a document **when
the sheet locks**, never when step 06 is ticked; editing after the lock
goes through the withdraw path.

**A film roll may hide its scrollbar, on one condition** (C4, 2026-08-16):
drag and wheel both work, the contents are visible at rest, and **arrow
keys step it when it has focus**. A bar drawn across a piece of film is
chrome, but removing a standard control without replacing it is not a
trade — the keys are what close the gap. Frames load the `thumb` tier and
the full image only on click, and a drag swallows exactly one click so
ending a swipe never opens the lightbox.

**A report may be a control when it has nothing to show** (C5,
2026-08-16). Two frames side by side may do materially different things on
click — zoom versus navigate — because the difference *is* the only thing
distinguishing them and it is visible: a filled frame has a picture, an
empty one has none, so its click becomes the act that resolves the
consequence it states. Where a report has something to show, showing it is
the act.

**A stale tab says so, and cannot be dismissed** (C7, 2026-08-16). When
the running build no longer matches the server's `app_sha`, a persistent
bar states it and offers the reload. It is not dismissable because
dismissing it leaves someone working confidently inside a build that no
longer exists. It re-checks every 60s and on `visibilitychange` — a
navigation-only check never notices, which was the original bug.

**An act that calls a third party reports on itself where it was fired**
(A3, ruled 2026-08-16). It names the half it is on, disables so it cannot fire
twice, and after **three seconds** states elapsed whole seconds in Courier —
an eight-second call and a hung one are indistinguishable without them. Its
failure lands in the same place, in `--bad`; a toast may repeat it, never
replace it. Any control that aborts the act stays live throughout. This is
`.busy.busy-inline`, not a second vocabulary: `.busy` replaces a region's
contents, which a modal cannot do to its own form, and that is a difference
of PLACEMENT, not of voice.

| Need | Use | Not |
|---|---|---|
| Primary action | `button.primary` (one per region) | amber on multiple buttons |
| Secondary | `button.ghost` | a second `.primary` |
| Destructive | `button.danger` | red fill |
| State | `.badge.APPROVED / .DRAFT / .REJECTED / .LOCKED` | colored text alone |
| Machine value | `<span class="mini">` + Courier child | Archivo |
| Section title | `.panel h2` (quiet Courier label) | amber headline |

`.badge.LOCKED` is deliberately grey: locked is a fact, not an action.

**Panel card, two lives** (PANEL_CARD ruling, 2026-08-03 — mocks
13a/13b). Before its first take the card is a **work order**: the spec is
the content — required objects as a numbered two-column table
(`.req-table`, Courier ordinal + per-row `✓ REF`/`HOLD` marks driven
from real state), forbidden as dashed chips with provenance stated in the
header, a Courier SCOPE line, and the single amber `Generate first take`.
After a take it is a **light table**: the image leads, the spec collapses
to chips, and generate is a ghost. Keyed on `candidates.length === 0`.

**Summarised auto-attachment** (`.anchor-sum`, from P4). Anything
attached automatically and un-uncheckable is summarised — one row per
role with a count, a bordered `ALWAYS ON` chip in `--ok` stating the
mandatory part out loud, and the full ID list behind a `SHOW IDS` text
act. Full-size badge walls are for things the user can act on.

**The stated zero state** (`.nomatch`, from P5/P8). When the app decided
and the answer was *nothing* — no reference group matched, no subject
anchors on a render — that is a finding, not a null: a bordered `--bad`
notice naming the state and its consequence ("it will render from text
and style alone"). Zeros the user should act on are never blank space or
an unexplained `0`.

**One-bar action grouping** (`.act-bar`, from P7). A thing being judged
gets exactly one bordered action bar: its status fenced left, *use this
thing* and *derive from it* split by an internal rule, and the
destructive act fenced right — never adjacent to a promotion. Buttons
inside the bar are borderless text; the bar never wraps.

**The withheld verb** (R9, canon): where an action would appear but its
gate is unmet, a dashed `--ink-faint` bordered tag states the gate in
Courier (`.wv-tag`, `.pd-lock`). It is never a disabled button, never
clickable, and its copy names the act that unlocks it. Worked
example (D4): the locations table once showed a per-row COMPLETE
PRODUCTION DESIGN button — a gate wearing a verb. It is the tag `NEEDS
THE BIBLE` until the Bible exists; only then does the cell hold the real
verb (`Make sheet` / `Open sheet`). A disabled control may also carry
the tag beside it (the Bible editor's Save + `NOTHING TO SAVE UNTIL A
DRAFT EXISTS`).

**The credential modal** (R6, canon): a provider that offers true OAuth
(OpenRouter) gets the one-click connect; a provider that doesn't gets the
Courier step chain (`OPEN THE KEY PAGE → SIGN IN & CREATE A KEY → PASTE
IT HERE`) with the console opening only on an explicit ghost click —
never a connect-styled button over a paste flow.

**Notification marks** (R7, canon): one filled square dot in the severity
color after the tool label — `--bad` for errors, `--hold` for holds. No
counts, no chips, no badges, anywhere, ever: a count is a queue and this
product's queues live in the views; the dot points, the view states. Two
conditions never stack — the worse one wins.

**The stated refusal** (R14, canon): an engine's content-policy refusal
is a third kind of stop — not an error (nothing broke), not a gate
(nothing unlocks it): `--hold` border, stated meaning, the craft answer,
the provider's own words in Courier. Refusal copy never speculates about
why beyond the provider's words.

**The mode chip** (R17, canon — binds all future modes): a mode that
changes what clicks do MUST show a fixed bottom-left Courier chip with an
amber left border (sanctioned — an armed mode is a primary state),
stating the mode and its exit. One mode at a time; entering a second
exits the first.

**Debug quarantine** (R16, canon): a debug tool may be reachable but may
never look like a peer of a paid feature — in dropdowns it renders last,
after a disabled Courier `— DEBUG —` divider, in `--ink-faint`.

**The structural board** (R12, canon): an assembled board renders as its
layout frames (1px `--line` chrome — containment, not content) holding
the real panels, click-through to the uncropped take, the composite
demoted to "Export board". The click-through affordance is stated once
per view in Courier `--ink-faint` (`CLICK ANY FRAME FOR THE FULL TAKE`).
Content exemption: panel imagery and the drawn title block follow the
production's own art, not the app tokens.

**Wizard group labels** (R18, canon): Courier group labels inside one
step (`.wiz-group-label`, THE MOVIE / THE BOARDS) — capability-before-
vendor applied to parameters.

**The sheet grammar** (SHEET_SYSTEM_PLAN §13, canonized 2026-08-10 with
the plan's implementation; **the Lookbook surface was rolled back by the
user 2026-08-12** — the sheet model stays as the boards' engine, and the
composer survives only as the arrange room opened inline on stage 05):

1. **A tool is not a stage.** The band is the pipeline. A surface that
   spans the production rather than advancing it goes in the header
   beside Reference. (The Lookbook was the case; it is gone — the rule
   stands for future tools.)
2. **One grammar per artifact class.** Two surfaces that both arrange
   approved images onto a canvas are one mechanism with two archetypes.
   Before adding a layout engine, name what the existing one cannot
   express.
3. **A style declares surface, edge and voice — never layout, size or
   content.** And a style may not be named after the feature that uses
   it (`PLATE`, not `LOOKBOOK`).
4. **Derived sizes are recommended, never imposed** — and the cost of
   moving is named in the unit the medium is read in, points or pixels,
   not adjectives.
5. **One failure vocabulary per surface.** Two ways of being unready are
   two entries in one list, not two mechanisms. (Stage 05 keeps its
   `slot_map` shape; the sheet speaks `TYPE_FLOOR` / `SLOT_PIXELS`;
   `TOO_SMALL` maps across at the boundary only.)
6. **Never auto-adopt an upstream change into approved work.** Report
   the drift (`SOURCE MOVED`), offer take-it or freeze-it, let the user
   rule.
7. **Composer overlays are app chrome and never enter the artifact.**
   Anything drawn to help the user aim lives in the DOM; the sheet
   carries only its ink — namespaced under `.sheet[data-style]`, never
   `:root`.
8. **A rule applies to shipped output too.** When unification changes
   what already ships — type sizes, a ground colour, a default — change
   the output. Do not exempt it, and do not fork a style to preserve
   the old look. (Boards moved to the `INK` ground and the type floor.)
9. **Type that owns a column reflows; type in a rect does not.** Prose
   grows to the legibility floor and takes the room; a caption under an
   image cannot, so it is what decides the size. Nothing is ever exempt
   from being legible.
10. **One word, one meaning.** Two artifacts sharing a name is not fixed
    by copy discipline. Rename one — stage 03's artifact is a
    *breakdown*; "sheet" names the presentation artifact alone.

**Preset looks** (D7, canon ahead of its library): a look is five
pre-rendered plates the product ships — never a text prompt. Three
rules: (1) selecting a look adds real reference images, so the Bible
cites images rather than adjectives; (2) looks filter to the column that
opened the browser — a cinematography look can never land in board
rendering; (3) selecting never destroys user uploads — plates land as
approved refs alongside them, individually removable, and the footer
states it verbatim. Plates live in `app/static/look_library/<slug>/`
with a `looks.json` manifest and enter the library with
`source: "look:<slug>"` so provenance survives.

**The code is not the authority on hierarchy — the decision is**
(17a, ruled 2026-08-08, superseding T2's one-grammar clause). T2 reasoned
from the source: *they are all `mk(…, "ghost")`, so they are all ghost
buttons.* That inverted the direction of authority — a shared constructor
is an implementation fact, never a design argument. When the source
renders as peers things the user does not experience as peers, the source
is what changes.

The take bar is the worked example: **one verdict and two lists.** The
filled-amber `Approve panel` (this screen's only amber, as canon already
said — `--ok` is the *state* colour of an approved panel, not the colour
of the act that approves it); `USE` and `DERIVE` as Courier-kickered
lists of text acts, DERIVE dimmed because nothing in it advances this
panel toward approval; `Reject` fenced right, `--bad` on hover only.
Arrows come off the labels — one arrow marks a promotion, six mark
nothing. T2's *wraps, never scrolls* holds and is strengthened: **a group
collapses to `⋯` before the row wraps** — a group folding is legible; a
row breaking mid-list is not. Measured with a `ResizeObserver` on the bar
itself, because the rail and side panel change the stage's width without
changing the viewport's.

**The hatch is the only empty-image surface** (HATCH_RULE, ruled
2026-08-06). Wherever an image is expected and absent — panel slots, take
thumbs, board frames, reference rows, the storefront's workspace-door
preview — the surface is one of three canonical classes, never an inline
gradient:

| class | pattern | use |
|---|---|---|
| `.hatch` | `repeating-linear-gradient(135deg, #21252a 0 7px, #1c1f23 7px 14px)` | blocks ≥ 60px |
| `.hatch-fine` | same at 5px/10px | thumbs < 60px |
| `.hatch-bad` | `#211b1b`/`#1b1717` at 7px | TOO-SMALL and error surfaces |

Always **135°**, always two near-equal thick bands — not hairlines, not
45°. Re-declaring the gradient inline is a conformance failure even when
the values match, because the next hand-copy is where they stop matching.
A hatch block states its condition in a bordered Courier chip on
`--panel` in `--ink-dim` (`NO RENDERS YET — THE FIRST APPROVED PANEL
LANDS HERE`); it never renders bare and never shows a broken-image glyph.
`storefront/` mirrors the three definitions with identical values
(H3) — `storefront/tests/test_store_tokens.py` compares them to this
stylesheet's and fails the build if they diverge.

**Intake row** (`.ref-add`, `.chip-add`). High-frequency entry into the
list/library directly above it. Max 6 fields; placeholders name fields,
tooltips explain them; only the one field a first-timer can't guess gets a
Courier `--ink-faint` ghost prefix (dropped under 1100px). The submit is
ghost — an intake row never spends the screen's amber. An intake row is
always a full-width row of its own — never placed inside a column of a
wider grid, where a sibling's intrinsic size can starve the input; the text
input is the widest element, selects are capped. Anything needing
explanation beyond a tooltip belongs in a dialog instead.

**Subject card** (`.subj-card`, built once by `buildSubjectCard` — one
component, two hosts: the SUBJECTS shelf and wizard step 4). Anatomy:
Courier bold name · bordered grey kind badge (`.kind-badge`) ·
CAST/UNCAST badge (`.cast-badge`, `--ok`/`--hold` border, never filled)
· editable identity text (sans 12px `--ink-dim`; click to edit — it
rides in every prompt the subject appears in) · photo mosaic with a `+`
drop slot (`.subj-slot`) · Courier facts line (`n PHOTOS · ROLE — NAME ·
USED IN n RENDERS`, `.subj-facts`). Uncast recommendations are
dashed-border cards with a `Cast this subject` ghost button. In the
wizard the facts line ends with a `VIEW IN REFERENCE` text link
(`.text-act` — Courier bold, ink, never amber).

**Environment card** (`.env-card`, wizard step 3 — mock 6a). Registry-card
family: Courier bold name · sans notes (palette / light / atmosphere) ·
Courier facts line (`n LOCATIONS`). While proposed: dashed `--hold` border
and a `· PROPOSED — CONFIRM / DROP` facts line; edit-and-save is an
implicit confirm. Environments live in the Bible as `###` entries under
the `## Environments` container (the level-3 mechanism, like materials and
lessons) — never as top-level sections, which the parser reads as design
languages. A sheet carries at most one; a panel may override it with exactly one of
its own (scope inheritance, review 2026-08-01). Its block injects between
languages and lessons, and the sheet's own atmosphere wins overlaps.

**Scope carry line** (`.scope-carry`, spec editor — mock 6c). The scope
block's live receipt: quiet Courier on `--field` stating what the prompt
will carry, in injection order (`RENDERING LANGUAGE (ALWAYS) · <languages>
· ENV: <NAME> · n SCENE LESSONS`). A receipt, never an action — no amber.

**Registry rows** (`.eng-row`). User-registered externals (engines, any
future integrations): sans name · Courier facts (ellipsize the middle) ·
Courier test-state (verdict word in `--ok`/`--bad`, date stays faint) ·
ghost actions. Rows separated by `--line-soft` top borders; no
cards-within-cards. A registry row's Courier facts may carry a care state
(`BACKED UP <date>` / `NEVER BACKED UP`) — faint, never a badge; not-yet-done
is not a failure (review 2026-08-01 §8). Care escalates by age but never
blocks (PRODUCTIONS_PLAN A4): under 14 days `--ink-faint`; 14–29 days the
same text in `--hold`; at 30+ days the text goes `--bad` and the row's
first action becomes `Back up now` with a `--bad-line` border; `NEVER
BACKED UP` stays faint. Backup age never enters the blocking list and is
never eligible for DO-THIS-NEXT; the Status view's ADVISORY divider may
carry one row for the active production only, at 30+ days.

**Inline rename** (PRODUCTIONS_PLAN A5, canonical — `inlineRename()` in
app.js, `.inline-rename` input). A label the user owns is renamed in
place: the label becomes an input at the same position and type size,
pre-filled and selected; Enter commits, Esc reverts, blur commits. Never
a dialog, never a separate edit screen. The affordance is a `✎` that
appears on hover of the label — always present for keyboard/touch (do
not gate it on hover alone in the accessibility tree). One helper serves
every host: the header production name and the library cards.

**Production card** (`.prod-card`, the Screenboard Library). Anatomy, top
to bottom: sans-bold name + Courier amber `OPEN` marker on the open card
(3px `--accent` left border, `--panel2` fill — never a badge; open is
navigation state, not approval) + Courier slug right · 5-cell reach band
(see Layout patterns) · Courier counts row (`n SCENES · n PANELS · n
BOARDS · n REFS`, or `NO SCREENPLAY YET`) · `DO THIS NEXT` block (Courier
amber kicker + one sentence, computed per production by the same rule as
the Status blocking list; `ALL STAGES CLEAR` in `--ink-faint` when
nothing waits — no verb, no amber; its line reads `NOTHING WAITING ·
LAST ACTIVITY <d MMM>` in Courier `--ink-faint` — never "Wrapped", which
asserts a production state the app cannot know (ratified 2026-08-01; the
switcher's all-clear preview is `CLEAR · n BOARDS` for the same reason)) · footer: care line left (escalation
per Registry rows), ghost actions right (`Back up`/`Back up now` ·
`Open` · `Rename` · `⋯` menu holding Duplicate and typed-name-confirmed
Delete via the app modal).

**Stage checklist** (`stageChecklist()` / `.stage-check`,
LOCKED_STAGE_PLAN L4, mock 12c). One bordered list for any stage's
reachable-but-empty state: kicker (`NO BOARDS YET — N STEPS LEFT`),
headline, one row per gate step. Each unfinished row IS the link — verb
(sans 600), one-line subtitle, Courier address (`STAGE 02 ↗`); the
current row wears the amber left border and `--panel2` fill; done rows
collapse to a single `✓` line; a terminal info row reads `NO ACTION
NEEDED`. No generic navigation button anywhere on the screen. Rows come
from `gateChain()` — real state, so completed steps drop off as they are
done; a checklist that doesn't move is a poster. Optional steps (the look
interview — blanks come back PROPOSED) list plainly with an `OPTIONAL`
suffix but never hold the `→` pointer and never count toward "N steps
left" — a gate must never claim a step the product does not require
(user-caught 2026-08-01).

**Derive affordance** (review 2026-08-01 §2). A ghost button at the field's
label row that deterministically fills an editable field from data the app
already has ("Derive from screenplay"). Never amber (not the region's
primary action), never a spinner — it must be instant; if it can't be, it
is a generation and belongs on a primary button with the `.busy`
vocabulary. Disabled with the reason stated when its source is missing.
The filled value is ordinary editable content; the button carries no state
and does not mark the field as derived.

**Project switcher** (`.brand-switch` / `.proj-menu` — review 2026-08-01
§7). Switching projects is navigation and lives on the header project name:
same Courier treatment plus a `▾` and hover border, opening a compact menu
of Courier project names (active marked with the `.cast-badge` grammar —
bordered `--ok`, never filled) ending in one `Manage projects…` text action
to Settings. Settings keeps the registry (rows + intake + backup), titled
`Projects — this install` — projects are per-install content while
engines/keys are install-level configuration.

**Vocabulary picker** (`roleDialog()`, `.role-suggest/.role-preview`). For
finite, load-bearing vocabularies (roles, and any future controlled names).
Suggestion chips above the field harvest existing app values — clicking
fills the field and the chip never stays selected; free text remains
possible but reuse is the easy path. Multi-select facet chips use
`.vchip.set` (ink on `--panel2`), never amber — amber selection fill is
reserved for single-choice chips (variant, filter). A passive Courier
`WILL BE STORED AS` preview (label faint, value dim, no field chrome) shows
the normalized value only when it differs from the input. Notes and other
provenance prose stay free text. Suggestion chips can be *grouped by
provenance* (`.obj-suggest`, object intake): groups under Courier faint
labels naming what picking one means — solid `.vchip` = harvested from
the library, the exact title guarantees the match (faint `· SCENE` /
`· GEOMETRY` suffixes); dashed `.vchip.loose` = a scene-paragraph noun
that will need evidence like any free-typed value. The same dashed = not-yet-real
grammar carries the governed-vocabulary **PROPOSED state** (`.chip.proposed`,
design languages and environments): dashed `--hold` border and text, suffixed
`· PROPOSED — CONFIRM / DROP` acting in place. Confirmation is the default
state — a confirmed entry is the plain chip/card, no badge, no color.

**Reading view** (`.modal.prompt-full`). The app dialog at
`min(900px, 94vw)` holding one scrollable Courier document on `--field`,
an identity line above it (Courier faint — what the document is), Copy +
Close. Copy feedback via toast with the character count. Use it for any
machine document too long for a rail — prompts, logs, raw JSON. Never for
forms.

**Recommendation** (`.rec-chip` + `.rec-reason`, ruled 2026-08-03). A
bordered `--ink-dim` Courier chip reading `RECOMMENDED`, always followed
by ONE sentence of reason on the same line. Never amber (a recommendation
is not the current stage, the primary action, or focus — it is a stated
fact), never ordering alone, never unexplained: a recommendation without
a stated reason is an advertisement. With no key behind it, it renders as
the gate grammar, never a preselected broken default.

**Credential row** (`.cred-row`, ruled 2026-08-03). One row per provider
in the §02 list: 36px Courier initials tile on `--field` · name + Courier
powers-and-limits meta (flex) · state · identity · actions, fixed column
widths so every action sits on a shared baseline. Connector states are
exactly four: `NOT CONNECTED` (hollow mark — the only disconnected term),
`SYNCED` (`--ok`), `401 — REJECTED <stamp>` (`--bad`; the cached catalog
stays visible with its age stated, enabled models stay listed and fail
loudly at render — never a silent substitution), `NO NETWORK` (`--hold`;
everything but Refresh and rendering works air-gapped). Rows expand in
place for auth — no modal — and the two auth kinds read differently:
one-click Connect only where the provider offers OAuth; a paste field
never dresses as a connect button.

**Capability badges** (`.cbadge`, ruled 2026-08-03). Courier, bordered in
their meaning's color, never filled: `REFS ≤N` `--ok` · `NO REFERENCES`
`--hold` · `4K NATIVE` `--ink-dim` · `2K MAX` **`--accent`** (the one
amber badge — a ceiling below the board bar is the fact that disappoints
after the money is spent, so it bites at the point of choice) · `$X/IMG`
`--ink-dim` · `NO PRICE` dashed `--line` (never invented) · `DEPRECATED
UPSTREAM` `--bad` (deprecated-but-enabled keeps a `--bad` left border and
STAYS enabled — we report upstream, we do not overrule the user) ·
`UNSUPPORTED SHAPE` dashed `--hold` (dimmed row, reason line never dimmer
than the name it explains).

**`modal()` field kinds.** Text, `textarea`, and **colour** (`.mf-color`,
ruled 2026-08-07): a Courier hex beside a native `<input type="color">`
stripped of its OS chrome and given the field's border — square at the
field's own height, so the pair reads as one control rather than a
control and an ornament. The hex remains the value of record; the picker
is a second view of it. A colour is the one value no amount of type can
show, which is why the native control is admissible in a system this
typographic. An empty one wears `.hatch-fine` — the pattern for any field
whose real value is a rendered thing, not text. A free-text field may
also carry **recall**: the last three values as `.text-act` beneath it,
filling the field when clicked. Recall, never constraint — a chip list
cannot express "no Onyx Unit black, and no reds".

**Card menus read top to bottom in increasing consequence** (ruled
2026-08-07). Duplicate, then Import backup, then Delete — terminal and
last, separated from what precedes it by the menu's own rule.

**The dropdown panel** (HARNESS_AUDIT R15, ruled 2026-08-14; first use:
the workbench palette selector). A ghost summary states the live outcome
(`AUTO · 2 NEWEST OF 19`) and opens a floating panel: `--panel` ground,
`--line` border, no shadow, no radius, no animation, never taller than
60vh, below-left of its summary unless clipped, closes on Escape and on
outside click. One pattern — the next dropdown is a reuse, not a
reinvention.

## Scrollbars

Scrollbars are chrome, not content. The global rules in `styles.css` cover
every scroll container — never restyle one locally.

- Thin (10px), square, thumb inset 2px so it reads as a 6px bar.
- Track invisible; the thumb is `--line`, `--ink-faint` on hover. No amber,
  no status colors — a scrollbar is never a signal.
- Overlays (`.lightbox`, `.cropper`) use `--line-soft` so the thumb doesn't
  glow against near-black.
- New scroll containers (rails, filmstrips, code blocks) inherit this
  automatically. If a thumb is invisible against a custom surface, fix the
  surface color, not the scrollbar.
- `overflow: auto`, not `scroll` — no dead tracks on content that fits.

Rejected reference cards dim the **image only** (`.ref-card.REJECTED img`). Never
dim the card — the rejection reason is the entire payload of a rejected card.

---

## Verifying against mocks

Every design mock is authored at **1360px content width**. A screen is not
done until it passes this loop:

1. **Seed the same data.** Load the app with demo state matching the mock's
   content. Text/count differences are expected; structural ones are not.
2. **Screenshot at the design width.** Headless browser, viewport 1360 wide
   (plus page chrome), full-page capture.
3. **Diff.** `pixelmatch`/`odiff` the capture against the mock. Read the
   marked-up output image; fix; re-shoot. Iterate until only content-driven
   regions differ.
4. **Assert the tokens mechanically.** Image diff catches layout; computed
   styles catch the rest. For each new component assert via
   `getComputedStyle`: font-family, font-size, colors, border, padding,
   letter-spacing against the mock's stated values. This is more reliable
   than eyes for hex values and 1px differences.

**What must match exactly:** tokens (hex, sizes, weights, spacing, borders),
structure (order, alignment, grouping, fixed column widths), and
**containment** — if the mock draws a bordered panel around a region, the
region is inside a bordered panel, not floating on the page.
**What never matches:** the demo content itself.

**The truthful deviation** (R19): the one sanctioned reason to diverge
from a mock without a designer round-trip is when the mock states a
falsehood about the system (mock 16b's "NO KEY HELD" vs the PKCE key
that really lives on this machine). The true statement ships; the
deviation is reported. Worked example: the OpenRouter credential row.

The most common failure is not a wrong value but a **dropped wrapper**:
content rendered at full page width because the mock's outer panel, its
padding, or its internal hairline was skipped. Check containment first.

---

## Sequence and gates

**Facts about an image ride ON it** (B10, 2026-08-16). An experiment that
changes output must be legible in its output: a take that rendered under a
cinematography grammar carries `GRAMMAR — <NAME>` in Courier on the hero
and in the lightbox, and a take that did not carries nothing. A fact that
is sometimes true is only readable if its absence is also a fact.

**A manifest belongs with the thing it becomes** (C6, 2026-08-16). What
is attached is counted where it is chosen — by role, `SUBJECT + PALETTE +
STYLE` — and listed in full beside the prompt it rides in, not beside the
picker. A palette composites to ONE plate and costs one of the fourteen
reference slots however many colours it holds.

**A migration has no surface** (A2, ruled 2026-08-16). §2.4's "a gate must be
readable as state before it is hit" governs **decisions the user still has**.
Legacy data we should already have migrated is not a decision — a screen
offering the choice is us asking the user to do our work. A migration runs at
boot, under three conditions: the change is **recorded** in the production's
own journal, the prior state is **recoverable** from an on-disk backup, and it
is **not a preference in disguise** (if two users could reasonably want
different outcomes, it is a decision and §2.4 applies in full). What §2.4
forbids is *unrecorded* mutation, not automatic mutation.

**A confirm guards the irreversible direction only** (A4, ruled 2026-08-16). A
confirm is friction spent on consequence: spend it entering a state that
changes output or destroys work, and spend nothing leaving one when leaving
restores what was there before. **An asymmetric confirm is correct, not an
oversight** — a confirm on the way out is friction on the act that makes an
experiment safe to run. Governs every toggle whose ON state changes what comes
out and whose OFF state restores byte-identical prior behaviour.

The product is strictly sequential: screenplay → bible → breakdown → lock →
panels → board. Gates must be **readable as state before they are hit**, never
discovered as an error toast. When you add a gated action:

1. Show the disabled control with `:disabled` styling (visible, not hidden).
2. State the unmet condition next to it, in Courier if it's a count.
3. Link to where it gets resolved.

"Only locked sheets generate" should be visible on the sheet, not a surprise on
the button.

---

## Adding a feature — checklist

- [ ] Does it belong to a stage, or is it a tool? That decides where it lives.
- [ ] Reused an existing class before writing a new one?
- [ ] Tokens only — no new hex, no new grey, no border-radius.
- [ ] Amber used zero or one time, and it's the primary action?
- [ ] Machine values in Courier, prose in Archivo?
- [ ] One `p.hint`; longer explanation moved to `title`?
- [ ] Screen still has exactly one obvious next verb?
- [ ] New grid tracks use `minmax(0,1fr)`?

**Precedence: written rule > mock.** When a plan's prose and its mock
disagree, the prose wins and the deviation is reported in the response
document — never silently reconciled either way. Worked example (ratified
2026-08-01): mock 10a filled two buttons amber; the "one primary action"
rule held, `Open` shipped ghost, and the ruling confirmed the mock was
wrong.

---

## Brand

**The mark ("15d2, three and larger").** A near-black `--field` tile, three
perforations per side in `--ink-dim`, two frames between them: the top one
`--accent`, the lower one `--ink`. It says what the interface says — one
thing leads, the rest support. Amber appears once and carries meaning.

**Two masters, not one.** `icon.svg` (3 perfs/side) renders everything 48px
and above; `icon-small.svg` (2 larger perfs) exists solely for 16px and
32px, where six tiny perforations would smear. It is the only sanctioned
deviation — never generate 16px assets from the 3-perf master. Masters and
the full raster set live in `brand/icons/` and are copied (not linked) into
`app/static/icons/` and `storefront/app/static/icons/`, served at
`/icons/` on both surfaces.

**Placement.** The icon may appear in-product — an About dialog, the
standalone build's splash, the storefront header — because it is the app's
own field colour spending amber the way the interface does. It must never
sit inside a working view where it competes with the stage band. No
inverted or light variant exists or is needed; never re-colour it, add a
gradient, round its corners (platforms apply their own masks), set it on a
busy photograph, or render it below 16px. The PNGs are full-bleed;
`maskable-512.png` alone carries a safe zone (art at 80%) and is used only
for the manifest's maskable purpose.

## Icons

- **Header marks: one square per AI role** (ruled 2026-08-03) — NARRATIVE
  and IMAGE, filled squares (never circles), Courier-labelled, carrying
  the worst state among everything that role needs: green ok · amber
  degraded-still-runs · red blocked · hollow not configured. The count is
  fixed at two forever, however many connectors exist.
- **Third-party marks ride transparent icons — app-wide** (SETTINGS_
  CONTROL_PANEL P3, designer-ruled 2026-08-05, extending F4): wherever a
  third-party service appears in the product — credential rows, model
  pickers, the marquee, connector modals, activity lines that name a
  provider — it is represented by its real brand icon: the LobeHub
  static set, dark variants, transparent PNG, served locally from
  `app/static/provider-icons/`, set on a `--field` tile with a `--line`
  border (36px in lists, 22px inline). Never favicons, never recolored,
  never on a light backing, never hotlinked. The Courier initials tile
  (`OAI`, `ORT`…) is the stated fallback when no icon exists in the set —
  and the only place initials may appear once an icon does exist is the
  OpenRouter tile, which has no dark mark (`ORT` stands). The marquee
  stays a masked, duplicated, ~36s auto-scrolling strip, still under
  `prefers-reduced-motion`.
- **Model imagery is the typographic tile plus the witnessed frame**
  (ruled 2026-08-03; developer mark upgraded by P3): a model tile's
  developer mark rides the brand icon where the set has one, Courier
  initials on `--field` otherwise (`BFL`, `IDG`…). No vendor thumbnails
  ever — a grid of third-party marketing samples is a slot machine and
  other people's marketing presented as our evidence. The only image a
  model may wear is a **witnessed test frame**: one standardised
  in-house prompt rendered through the user's own key (cost stated
  before the click), cached to disk, served from disk. Empty state is a
  stated `NO PREVIEW`, never a broken image.

## Do not

- **No italic.** The system has two voices and they are families, not
  slants; adding italic for emphasis is how a third voice starts. Emphasis
  is ink tier, weight, or position (B5, 2026-08-16).

- Add a CSS framework, or Inter/Roboto.
- Add gradients, rounded cards, drop shadows for decoration, or emoji.
- Introduce a new accent color, or use a status color decoratively.
- Wrap content in more nested panels — depth was the v1 clutter mechanism.
- Rename existing CSS classes. `app.js` generates markup against these names;
  the stylesheet was written to preserve every one of them.
- **Grant a feature an exemption from the two rules** (canon pass R1). A
  plan may not authorise amber outside its three roles; if a mark is not
  stage, primary act or focus, it is `--ink` or Courier. The composer is
  the worked refusal: five requested spends ruled down to two — the
  selection outline (focus) and Export-when-ready (primary act); the
  block chip became the tags-ride-the-image label, `AUTHORED` a plain
  Courier fact (amber marks what blocks, and an authored caption blocks
  nothing), and the stale acts equal ghosts.
- **Truncate a title** (STEP_SEQUENCE_SPEC §1.10, 2026-08-14).
  `Residence and Workshop Interior` and `Residence and Workshop Exterior`
  are the same string once cut. In a narrow rail the title takes its own
  row and wraps in full — height is the cheap axis there.
- **State a count without making it provable** (§9). `2 WITH A REFERENCE`
  requires a mark on those two. Never mix an image count against a group
  denominator — `12 OF 19 ATTACHED` claimed most references were attached
  when one group was selected.
- **Use two words for one state** (§10). `✓ REVIEWED` and `✓ CONFIRMED`
  on one surface invents a third state the head then miscounts.
- **Add a second bar** (canon pass R6). The coverage meter is the only
  meter. A capacity is a Courier number line whose colour carries its
  state — `FREE 214 GB OF 500 GB · 57% USED`, uncoloured while healthy,
  `--hold` when tight, `--bad` once a render would be refused.
- **Put a verb where it must wrap** (HARNESS_AUDIT U4, ruled 2026-08-14).
  `.ghost` and `.text-act` carry `white-space: nowrap`; if the label
  cannot fit, the container is wrong, not the label.
- **Offer two verbs for one outcome** (HARNESS_AUDIT R17, ruled
  2026-08-14). `Retire` and `Delete` both stopped a note carrying; one
  reversible act plus a stated state (`NOT CARRIED`) replaces both, and
  the destructive door moves out of pointer range (into the Edit modal,
  confirmed).
- **Dress dev tooling in product signals** (HARNESS_AUDIT R16, ruled
  2026-08-14). Tooling outside the product (the recorder chip, the
  harness chrome) is exempt from this system, but may not borrow its
  colours — a status colour on a non-product surface teaches the wrong
  lesson to the next reader. The recorder chip is `--hold`
  (attention-not-blocking); the harness staleness banner is `--bad`
  precisely because a stale harness does block trustworthy review.

---

## Uncanonized patterns

**Every new feature lands here until Claude Design reviews it** (rule of
2026-07-31) — genuinely new patterns AND pure-reuse features alike; the
latter noted "built from canon — review placement/copy only". New patterns
are additionally built with existing tokens and marked
`/* UNCANONIZED — date — feature */` in the CSS.

This table is a to-do list, not a home. At ~4 rows, tell the user the UI has
accumulated patterns worth a design review — they open their design-review
Claude chat (the one with this folder connected, which delivers `*_PLAN.md`
files), re-sync the folder so it sees current files, and ask it to review this
table. The resulting plan folds patterns into the sections above, and the rows
are then deleted.

**The store keeps its own queue.** This table covers the product app only.
Storefront work lands in `STORE_DESIGN_SYSTEM.md` → `## Non-canon —
awaiting review`, and is reviewed against that file's rules (its amber has
four sanctioned roles; this file's scarcity rule does not apply there). A
review pass should read both tables — they are different systems with
different vocabularies, and a ruling for one is not a ruling for the other.

| Date | Pattern | Used in | Why nothing existing worked |
|---|---|---|---|
| 2026-08-16 | **Choose an existing plate for a required object** (user: "in this dialogue I need to be able to select existing ref"): `+ REF` now asks first — a grid of approved plates at library-card anatomy (picture largest, then id and role in Courier), near-misses ordered first, with `Upload a new image instead` as the second door. Choosing ticks that plate's group in step 04 and scrolls to it, which is the same mechanism an auto-matched group uses | Panels workbench, step 02 | Review (1) a picker that RESOLVES to one of two different dialogs; (2) whether the grid should exclude style/palette anchors, which are selectable today and are never a sensible answer for a prop; (3) that the tick is per-render memory, not a durable object→plate link — it survives only by riding a take |
| 2026-08-16 | **Withdraw approval** (user): an approved panel goes back to draft without being rejected. Offered on the workbench beside `Approve panel` and in the take gallery, as a plain `text-act` — deliberately NOT a danger act, because nothing is lost and dressing it as one pushes people back to `Reject`. Both copies state the difference that matters: Reject's reason rides every future prompt for the panel as a DIRECTOR'S CORRECTION, withdrawing carries nothing. The store verb and endpoint already existed and had no caller | Panels workbench + take gallery | Built from canon (existing act rows, text-act) — review (1) whether an UNDO belongs beside the act it undoes or somewhere quieter; (2) that it only appears when the STAGED take is the approved one, so a user whose newest take is a candidate must first click the approved take in the strip to find it |
| 2026-08-16 | **The compiled prompt is editable** (user-caught bug): step 05's verb read `Read & edit` and the body was a read-only `<pre>` — the override existed end-to-end (`render_prompt` → `prompt_source: "edited"`, read back on the take) but only `Draft prose` ever fed it, so the one text an image model actually receives was the one text you could not correct. Now a textarea with `Generate from this prompt` · `Revert to compiled` and a Courier state line that flips to amber while it differs, because at that moment the panel below is no longer what gets sent. Unedited text is NOT sent as an override. Copy and Download take what is on screen | Panels workbench, step 05 | Built from canon (report host, prose editor's textarea, gate-readable-as-state) — review (1) amber on a transient text-diff state, which is a narrower use than "the current pipeline stage"; (2) a one-take escape hatch from the compile, sitting inside the step that IS the compile; (3) whether an edit this load-bearing should be able to persist to the panel |
| 2026-08-16 | **A prompt can be saved onto the panel** (user): the one-take edit above grew an explicit `Save prompt to this panel` · `Clear saved prompt`, beside `Revert to compiled` which restores the COMPILE in the box without touching the save. While one is saved, steps 01–04 no longer write that panel's text — so step 05's head reads `SAVED PROMPT — STEPS 01–04 DO NOT WRITE THIS PANEL` and step 06 repeats it where the spend happens, both amber. Journaled, lock re-stamped, refused on an approved take. Saving patches those two heads in place rather than redrawing the card, which would close the editor you saved from | Panels workbench, steps 05 and 06 | Review (1) a step that declares the steps ABOVE it inert — the sequence has never had one, and this is the first control that can switch off part of the pipeline; (2) amber in two places on one card for one fact; (3) whether an override this sharp should be visible from the panel list, not only inside the open card |
| 2026-08-16 | **A frozen panel states its refusal in place** (user-caught): Save was greyed by an approved take with the reason ONLY in a hover tooltip, while the help line below still said "Save prompt to this panel to make them stick" — a dead button being advertised. The state line now leads with the gate (`AN APPROVED TAKE FREEZES THIS PANEL · NO PROMPT CAN BE SAVED TO IT`), the help names the take that settled it and where the approval is withdrawn, and says the one-take `Generate from this prompt` path is still open. Frozen is `--ok`, not amber — canon already paints a settled step that way and the accent belongs to what a render is about to do | Panels workbench, step 05 | Built from canon (gate-readable-as-state, `.step-confirmed`'s settled green) — review whether a REFUSAL should share the settled colour with a CONFIRMATION, since one is an achievement and the other is a wall |
| 2026-08-16 | **The breakdown door asks three things** (user, AFTER the rule pass — unreviewed): `What should I get?` reads the screenplay for you · `Or paste a screenplay section`, which WINS over the screenplay and carries `Open the screenplay ↗` · `What panels should it include?`, typed one per line or left to `Auto-generate`. Each field states what it does to the work rather than what it is filed as, per A1, and the Spec ID leads with its reassurance. An empty door still makes a genuinely empty sheet | Stage 03, the second door | Review (1) two doors on one page that now overlap — `Auto breakdown` reads the whole screenplay, this one reads it for a brief; (2) `Auto-generate` as a button that CLEARS a field rather than setting one, which is honest about the server contract but unusual; (3) the three Courier notes under the fields, which is a new density for a form |
| 2026-08-16 | **The location list reads in acts** (user, AFTER the rule pass was written — unreviewed): grouped into three acts, chronological by first appearance rather than by scene count. A screenplay that MARKS its acts supplies its own divisions and titles; one that does not gets the standard 25/50/25 split and its NAMES from the scene scan, which is a reading of the story rather than a parse. The head states which half came from where. Five per act behind the app's one `Expand`; a location the slugline parse never saw has no act and says so | Stage 02, the read strip | Review (1) acts as the primary grouping where environment used to be; (2) an act heading the app INFERRED — the first place it shows a structure it read rather than parsed — and whether `Name the acts` belongs in the strip or with the scan |
| 2026-08-16 | **Casting opens a modal** (user, AFTER the rule pass — unreviewed): `Cast` used to write the card immediately, and a cast card's `+` tile was a bare file input, so the OS picker arrived over the app with nothing confirmed. One modal carries what the read proposed — kind, identity, traits, editable — and a tray where photos are CHOSEN and shown as thumbnails; nothing is written until `Cast`. One `photoTray()` serves both casting and an existing card | Reference, subject cards | Review (1) an intake modal that both EDITS a proposal and STAGES an upload, where canon's dialogs do one or the other; (2) whether casting should be identity-only and photos stay the card's job |
| 2026-08-12 | **Arrange room physics** (`.arr-*`, user-directed, prototyped in the Reflow Lab artifact): tiles are the real takes GHOSTED (field scrim, lifts on hover); linked-edge/corner resize with proportional renegotiation and 24×12 grid + film-ratio snap (Alt = free); drag-middle moves with a dashed-amber ghost previewing the exact landing; drop-on-a-tile splits it (sides beside, top/bottom stacks); EDGE-MIDPOINT CLAIM ARROWS (hover hints the territory, click claims to the canvas; displaced panels re-home to nearest neighbor); per-tile icon chips trash (bench) / + (dock nearby) / crop; corner + returns benched panels; live SHORT hatch + hud line. Commits PUT the rows/cols/cells structure; the server maps it to slot geometry | Stage 05 assembly page, inline under the slot map | Entirely new interaction vocabulary. Ruling wanted on: icon-chip shape (the user tuned ROUND buttons in the lab; canon forbids rounded corners so they ship square), chip sizes (40px tile verbs / 20px arrows / 48px corner), ghost-scrim strength, snap values, and the amended R2 reading (client owns arrangement STRUCTURE; server owns geometry)  **DEFERRED by HARNESS_AUDIT R2 (2026-08-14)** — the room was not in the recorded bundle and the designer will not rule it from a description; top item of the next recording walk. Already ruled: square chips stand (canon forbids rounding) and the amended R2 reading (client owns arrangement STRUCTURE, server owns GEOMETRY). Remaining: chip sizes, ghost-scrim strength, snap values, claim arrows |
| 2026-08-13 | **Board looks** (`.arr-style-*`, user-directed): a `Style…` verb in the arrange room opens a picker whose cards are REAL small-scale renders of this board (INK — none, Art Board, Tech Design), with per-look option checkboxes; the chosen look dresses previews/export/assembly only — the room always works in INK. Renderer-side: two new sheet ink styles (`ART_BOARD` parchment/serif/hand-annotations, `TECH_DESIGN` near-black/mono/keylines+ticks), a `dress` element channel (swatch strip, material chips, spec table, atmosphere strip, profile prose) derived from canon at render time, and bundled OFL render faces incl. a new `hand` voice (Caveat) | Arrange room (stage 05) + board export/assembly | Open questions for the ruling: (1) the `dress` channel as a parallel grammar beside the closed twelve block types; (2) md-tier sources feeding preview-scale renders (scoped exception to "display tiers never feed a render"); (3) which palette languages a board's strip draws (ships: all live); (4) Art Board per-panel taglines vs. atmosphere-strip-only; (5) Tech Design comparison block, ortho-tick styling, and both styles' exact ink values; (6) hand-annotation collision rules, Caveat minimum size, and a ruling distinguishing sheet-render typography from app chrome (canon forbids new fonts in chrome); (7) whether the room's advisory SHORT readouts should read dressed geometry (the gate already does)  **PARTLY RULED by HARNESS_AUDIT R4 (2026-08-14)** — shipped: dress is a selector over the closed block set (PALETTE / MATERIAL / STRIP / SPEC / PRINCIPLES); md-tier feeds previews only, enforced in sheet_render; the chrome/artifact typography split is Layout canon. Still open, needing a rendered sheet: (3) which palette languages a strip draws, (4) Art Board taglines, (5) exact ink values + Tech Design comparison block, (6a) hand-annotation collision + Caveat minimum size, (7) dressed geometry in advisory readouts |
| 2026-08-14 | **Add reference in place + View** (user-directed): a required object without a matching reference offers `+ REF` right in the workbench card (the work-order TABLE that carried the long-form `Add reference` was replaced by step 02's tile grid, 2026-08-14) — opens the existing add-reference dialog prefilled with the object; the reference enters the library APPROVED (supplying it deliberately is the review; Reject in Reference remains the recourse) and the card re-renders so the group attaches immediately. An object WITH a reference is marked `REF` on its tile, and that marker opens — a modal reference widget (library card anatomy: badge · id · role · CONTROLS/NOT · notes per matching plate), a Courier fact line "N PLATES MATCH · ALL ATTACH · THE RENDER WORKS FROM EXACTLY WHAT IS BELOW", a stated thin-anchor warning at one plate, thumbs opening the lightbox, and `Add another plate` prefilled to the same group | Panels workbench card | Built from canon (roleDialog, ref-card anatomy, lightbox, act-where-condition-is-met) — review the auto-approve rule, the `+ REF` chip density, and the thin-anchor warning copy |

---

## Changelog

Newest first. One line per change, dated. Amend the relevant section above as
well — this log records what changed, it does not replace the rules.

- **2026-08-16** — **One rule for "does this phrase name that thing"** (user: a
  panel with "Sal's eyes" showed `+ REF` — "it should find that ref because I
  have Sal Ref"). A FOURTH copy of the matcher drove the green REF marker and
  the first-take tick default, so a Sal panel offered no Sal plate and said
  nothing. Possessives and hyphens now normalise on both sides. On the user's
  own board: P02 went 1/5 objects with a reference to 5/5, P01 0/10 to 6/10.

- **2026-08-16** — **A redraw holds the reader's place** (user: "the page jumps
  to the top"). The panels host blanked itself to `Loading…` on every redraw,
  not just on load, collapsing the document so the browser clamped the scroll
  to 0. Old DOM stays up until the new one is ready; scroll restored. Found
  alongside it: a shared `/panels/<spec>/<panel>` link had been landing on
  whichever panel was last open, because it looked for a `.panel-card` this
  host stopped rendering when the workbench became one card at a time. No
  table row: both are defects against stated behaviour, not new patterns.

- **2026-08-16** — **REVERSED (user): a filmstrip click stages a take and does
  nothing else.** It also opened the lightbox (ruled 2026-08-15, same user) and
  that was wrong in use: staging is the frequent act — you walk the strip
  comparing takes — and a modal on every step is a door to close before the
  next one. Full size stays one click away on the staged image. No table row:
  this REMOVES a behaviour rather than adding a pattern.

- **2026-08-16** — **Non-canon: Withdraw approval.** The only way out of an
  approval was Reject, whose reason is carried into every future prompt for
  that panel — so unlocking an edit poisoned the work after it. The verb and
  the endpoint had existed since that morning with no caller.

- **2026-08-16** — **Non-canon: a frozen panel says so where the button is.**
  An approved take froze the prompt and the only statement of why was a
  tooltip. Also hardened: a server answering the prompt endpoint without
  `compiled` threw out of the handler, killing Save, Clear and Revert while
  the editor still looked usable.

- **2026-08-16** — **Non-canon: a saved panel prompt**, plus two fixes it
  surfaced. The SUBJECT IDENTITIES block used the same too-narrow name match
  the workbench did, so a character's canon identity never reached the model
  unless the object was written as their full filed name; and a crop saved to
  the library did not appear in the view that made it until you navigated
  away and back.

- **2026-08-16** — **Non-canon: the compiled prompt is editable** (user-caught
  bug). Step 05's verb said `Read & edit` and only read. The override was
  wired end to end already — it was the UI that never offered it.

- **2026-08-16** — **The blank sheet becomes a breakdown door** (user):
  say what you want and the screenplay is read for it, or paste the
  section and that wins outright; name the panels or leave them to the
  model. Nothing typed still makes an empty sheet.
- **2026-08-16** — **RULED (RULE_PASS_2026-08-16 Part B):** stage 02's
  anchor cards. **The direction is ratified in full** — one place to set
  the look, each card a door onto a catalogue, the catalogue teaching its
  axis before offering options. Six corrections inside it. The card is ONE
  component with an empty life and a filled life, rendered by one function
  shared with the catalogue cell — the two drawings were already drifting.
  Diagrams are a stated placeholder, disclosed once per panel, and
  forbidden where real frames exist. Nothing pads to three. Seven text
  roles cut to four, with the key question, the operating principle and the
  prompt behind `Read the grammar`. No italic anywhere; film titles leave
  Courier. The captured card leads with its provenance and a hairline. The
  escape hatch leaves the grid and stops being drawn twice. And B10's
  defect is closed: a take that rode the grammar says `GRAMMAR — <NAME>` on
  the hero and in the lightbox, which is what made the experiment
  evaluable at all.
- **2026-08-16** — **RULED (RULE_PASS_2026-08-16 Parts C, D, E):** the
  sequence surfaces, the film rolls, the ledger, Settings, and the store.
  **Ratified as built:** stage 04's six steps including all four reported
  deviations from its mock — in every case the build followed canon and the
  mock did not; stage 03's transfer of the same vocabulary; the 35mm window
  and the fitted image; the empty frame as a way IN; the composite palette
  plate and `Choose plates`; the stale-tab bar; Productions as Settings'
  first tab. **Corrected:** the evidence ledger freezes on the LOCK, not on
  step 06's confirmation — a confirmation is advisory and cannot gate a
  control's affordance; the reference manifest moves to step 05, beside the
  prompt it becomes; the film rolls gain arrow-key stepping, which is what
  buys them the hidden scrollbar; the Settings strip gains a gap after
  Productions, marking the one tab you ACT on rather than SET. **Store
  (E1):** the fleet table stays whole and gains a headline stating its
  worst state, and `UNREACHABLE` splits — a studio that answers but cannot
  measure itself is `CANNOT MEASURE`, because sending an operator to look
  for a dead host is the wrong errand. Arrange room deferred a second time
  and stays in the table.
- **2026-08-16** — **Casting opens a modal** (user). What the screenplay
  read proposed, editable, with a photo tray that stages files rather
  than uploading them; nothing is written until `Cast` is pressed.
- **2026-08-16** — **Act names come from the reading, divisions from the
  parse** (user: their screenplay is traditionally formatted and prints
  no ACT headings — checked, zero). Naming an act is interpretation, so
  the scene scan is asked for it and returns the name plus the beat the
  act turns on, so the reading can be checked. The slugline parse keeps
  the divisions, because those are arithmetic and must not drift between
  runs. A printed heading always beats an inferred name, and the head
  states which half came from where.
- **2026-08-16** — **Locations read in acts, chronologically** (user),
  five per act behind the existing Expand. Acts come from the screenplay
  when it marks them, titles and all; otherwise the standard split,
  unnamed.
- **2026-08-16** — **Lessons learned leaves stage 02** (user: "I dont
  think this belongs on the Production Design tab at all"). The panel and
  its renderer are deleted. `/api/lessons` still feeds every prompt and
  Status still lists prohibited inventions read-only — what went with the
  panel is the only place to ADD or REMOVE a standing rule by hand.
- **2026-08-16** — **RULED (RULE_PASS_2026-08-16 Part A):** seven rows
  emptied, eight rules folded into canon. A label names its effect, not
  its filing destination (§Copy). A migration has no surface, under three
  conditions — recorded, recoverable, not a preference in disguise (§2.4).
  An act that calls a third party reports on itself where it was fired, as
  `.busy.busy-inline` and NOT a second vocabulary; elapsed appears after
  three seconds (§Components). An asymmetric confirm is correct — guard
  the irreversible direction only (§gates). **Refused:** 16.5px for the
  logline; promote by ink tier and position before size, so it ships at
  15px/400 `--ink` capped at 720px. **Refused:** `✓ CONFIRMED` on a frozen
  step — a tick you made and a fact that settled it must not look
  identical, so the work's word is `✓ SETTLED`, it carries no verb, and
  the head counts `n OF n STEPS SETTLED`. **Ratified:** the 24px Courier
  spine (one 24px element per surface PER VOICE) and the verb/tool
  boundary (the test is whether ONE object is visible beside it).
- **2026-08-16** — **A locked stage offers `help`, not `not-allowed`**
  (user-caught on the condensed band). Clicking one opens the popover
  naming its blocker, so `not-allowed` claimed the one thing that is not
  true of it. It is still not a destination — `aria-disabled` stays and
  the click never navigates — but it IS an explanation. Genuinely inert
  things (`.made-gated`) keep the no-entry cursor.
- **2026-08-16** — **Productions moves into Settings as its first tab**
  (user). The header drops to three tools. Order and default are
  separated: first in the strip, but a first visit still lands on `AI &
  engines`, and `/productions` opens Settings on the tab.
- **2026-08-16** — **The authenticate modal reports on itself** (user).
  Which half is running, how long it has taken, and the failure in
  place. Cancel stays live so a slow provider cannot lock the modal.
- **2026-08-16** — **Two labels start saying what they do** (user), and
  the `?` card binder becomes shared rather than copied a second time.
  Also `scripts/dev.py` — a local polish loop, so a UI change stops
  costing a version bump, a zip, a push and a fleet deploy before it can
  be looked at.
- **2026-08-16** — **A three-frame strip on the page, a lightbox that is
  actually on top, and a logline that leads** (user, three catches). The
  chosen cinematography grammar draws its three frames under the button.
  The lightbox was z-index 100 against every modal's 400, so it had
  ALWAYS opened behind them — the reference viewer had the same bug and
  nobody had looked; the stack is written down now. And the logline, the
  one sentence saying what the read understood, was set quieter than the
  tile labels beneath it.
- **2026-08-16** — **Real reference frames, and the card stops being a
  button** (user: "add the thumbnails in the /docs folder to the
  adventure cine style"). Classical Adventure carries three real frames;
  the other seven keep dashed empty cells. Landing them exposed invalid
  markup that had been there since the rich card shipped — a `<button>`
  card containing the prompt link's `<button>`, which the parser hoists
  OUT, tearing the card apart on screen. The card is a `div` with
  `role="button"`, `tabindex` and Enter/Space handling; its own buttons
  stay buttons. **A card that holds interactive parts cannot itself be a
  button** — worth remembering the next time a card grows a verb.
- **2026-08-16** — **Green means approved, and only approved**
  (user-caught: "selecting the new take made it green border without it
  being approved"). Status and selection were sharing one encoding, so a
  take you had merely clicked read as canon — and an approved take you
  were looking at lost its `APPROVED` caption to `SHOWN`. Status owns
  COLOUR; selection owns an ink OUTLINE, drawn outside the frame so it
  composes with any status instead of replacing it, and the caption
  states the durable fact. Retires the `PANEL_CARD P7` reading that
  shown keeps `--ok`. Added as a rule below the two, not a table row.
- **2026-08-16** — **The grammar's prompt can ride a render, and can be
  taken back** (user). The anchor's words never reached a render
  directly — they feed the bible draft, which writes the sections that
  ride. The document's image-model prompt is written for an image model,
  so it rides the render itself as its own block, after the CAMERA block
  and explicitly subordinate to it on framing. OFF by default; turning
  it off restores the previous prompt byte for byte, which is the
  difference between a rollback and a second variant.
- **2026-08-16** — **The cinematography catalogue is the document**
  (user). The seven hand-written light looks are replaced by the eight
  grammars in `docs/CINEMATOGRAPHY_STYLES.md`, parsed at request time by
  `app/cinematography.py`. The directive that rides a render is the
  style, its operating principle and its mechanics — never the reference
  film titles, per the document's own Usage Note. The panel's definition
  changed with it: a grammar is camera behaviour, lighting, composition,
  depth and movement, not light alone. Subtitles are `--ink-dim`, not
  amber — eight amber subtitles on one surface is eight of nothing.
- **2026-08-16** — **The chosen card stacks, and keeps knowing what it
  is** (user-caught). Picture on top, words underneath. The house card
  now re-matches a saved answer on its opening 110 characters rather
  than the whole string — its value is re-derived from the bible on
  every open, so a bible that gained a line reported the user's own
  answer back as `In your own words` with an empty plate. And the
  capture caps on a line boundary: a directive ending "Board layo" was
  the cap cutting a word in half.
- **2026-08-16** — **The captured card shows the style, not the fact of
  the capture** (user-caught). Its description is the bible's own
  Rendering Language text; where it came from dropped to a Courier
  footnote. `house_style()` also reads a bible written as prose now —
  the first pass took bullets only and returned nothing for those — and
  still never lets the Avoid list in.
- **2026-08-16** — **A selected style is visible without reopening its
  panel** (user): a compact card under the button, plate and all.
- **2026-08-16** — **The house style is captured, not authored**
  (user). `GET /api/bible/house-style` reads the saved bible's Rendering
  Language Required bullets and the newest approved take; the rendering
  catalogue's first card adopts both before the panel opens. Feeding the
  bible's own words back is deliberate — a re-draft then restates the
  established look instead of drifting off it.
- **2026-08-16** — **Words and pictures combine behind one button**
  (user). An anchor card is its button; the panel behind it holds the
  catalogue (each card with an example plate), `Add your own` with a `+`
  for an image and a field for words, and any control the anchor owns
  but does not style — the camera, the never-list — which travel in and
  out with their bindings intact. `app/static/style-plates/` is the
  drop-in slot for real generated images; a key with no picture keeps
  its diagram, so nothing is ever a broken image.
- **2026-08-16** — **Stage 02 loses a step** (user rulings). The look
  interview asked the same four questions the anchors ask; everything
  in it moved to where it acts — per-axis words onto their anchor card,
  the camera onto Cinematography (whose CAMERA block overrides the
  reference's own framing, so the two inputs that can contradict now
  sit together), the never-list onto Board Rendering (whose Avoid list
  it always fed), standing notes beside the Draft button. `touchstones`
  retired: the one input no anchor fenced, reaching the render by the
  weakest route while able to muddy all four deliberate answers. Saved
  values fold into notes at boot.
- **2026-08-16** — **A cinematography look never dictates the lens**
  (user: "a cinematographer will pick any lens to get the shot"). The
  catalogue was mixing two lifetimes — light behaviour is a production
  constant, lens and framing are per-shot. Anamorphic Wide, Long Lens
  Compression, Handheld and Formal Symmetry were shot choices dressed
  as anchors and are gone; the seven that remain are light only.
- **2026-08-16** — **The interview and the anchors stop asking the same
  four questions** (user). The per-axis fields moved onto the anchor
  cards they duplicated; the interview keeps the three no anchor can
  hold. Two new interview keys (`texture`, `light`) give World Texture
  and Cinematography a words half, and each answer is fenced to its own
  anchor's sections in the drafting prompt. Board Rendering and
  Cinematography answer from a catalogue via one shared picker. The
  table stands at sixteen — well past the review threshold.
- **2026-08-16** — **The step vocabulary is scoped to `.steps`**
  (user-caught): `.panel.step` has been the production-design wizard's
  own pattern since long before the sequence existed, and a bare
  `.step { display: flex }` captured it — every wizard panel became a
  flex row with its contents in columns. Recorded in the sequence canon
  above: a shared class name is not a shared component.
- **2026-08-16** — **Four rows added to the queue** — the migration-has-
  no-surface rule, the compact roll, the frame-as-a-way-in, and the
  stale-tab bar (which predates the 2026-08-14 audit but was never among
  the rows it emptied). The table stands at fourteen.
- **2026-08-16** — **Revisions collapse into one breakdown — with no
  surface at all** (user ruling "Yes Collapse"; then, on being shown a
  strip with a verb: "we dont need UI to do this type of consolodation. I
  was asking you to migrate it"). `revisions.consolidate()` folds a
  `_R<n>` chain into the base id and `migrate_all_projects()` runs it over
  every production at boot, ahead of the variant warm. Nothing to find,
  nothing to click. **The design note is the deletion**: a legacy data
  shape is not a state the user should have to read and resolve, so it
  gets no gate strip, no verb and no row in the table below — the rule
  that gates must be readable as state applies to decisions the user
  still has, not to work we should simply have finished.
- **2026-08-15** — **An empty frame is the way to the work that fills
  it** (user): clicking a `NO TAKE YET` frame opens the panels workbench
  with that panel active. A filled frame opens its take full size; an
  empty one has no picture to open, so its click is the act that resolves
  the consequence it states. On a sheet that is not signed off yet the
  frame states the gate instead — stage 04 lists locked breakdowns only,
  so the click would otherwise land on whatever sheet it falls back to.
- **2026-08-15** — **The roll loses its scrollbar and its edge print**
  (user): a bar drawn across a piece of film is chrome, so both rolls
  hide it — honest only because both drag, and wheel/trackpad still work.
  The edge marking is retired: it cost two lines of height on a strip
  whose job is the pictures. (The rule that put OUR data there rather
  than a stock name stands, should it ever return.) A board frame now
  opens its take full size on click, like a take frame; a drag swallows
  exactly one click so ending a swipe never opens the lightbox.
- **2026-08-15** — **One roll, every strip of frames** (user, after four
  rounds of "I don't see it"): the film treatment went on the TAKES strip
  on stage 04 while the user was looking at the BOARD strip on the
  breakdown page the whole time. Both are a row of frames, so the
  treatment is now a `.filmroll` class both wear — perforated base, edge
  marking, frame lines — rather than one page's styling. A visual
  vocabulary that names a THING ("a strip of frames") must be written as
  that thing, or it lands on one surface and silently misses its twin.
- **2026-08-15** — **A perforation is a hole** (user, twice: "I don't
  see the filmstrip look"). The CSS was deployed and correct, but the
  perfs were drawn DARKER than the film base — which reads as an embossed
  rectangle, not a hole. On a lit strip a perforation transmits light and
  reads LIGHTER than the base. Inverted, and the strip is unmistakable.
- **2026-08-15** — **A parked tab now learns about a release** (user:
  "it says live but there are no changes live"). The server was correct —
  `no-cache`, a fresh ETag, the new bytes on disk — but this is a SPA that
  re-renders from in-memory JS, and the staleness check rode on NAVIGATION
  alone. A tab parked on one panel, which is exactly the tab someone has
  open while a fix is being shipped for them, never learned. It now also
  checks on a 60s timer and whenever the tab is brought back to the front.
  Still stated, never auto-reloaded: reloading is the user's act, mid-work.
- **2026-08-15** — **Film, tiers, and full size** (user, three
  corrections). The takes strip now actually looks like 35mm: a dark
  base, ROUNDED perforations along both edges drawn as a repeated inline
  SVG tile, edge markings printed in the margin between the perfs and the
  frames, and thin frame lines between takes. The perf is the one rounded
  corner in the app — it depicts a physical hole, not a control. Strips
  ask for the `thumb` tier (the board strip had been pulling `md` for a
  300px cell). And the lightbox now ENDS at full size without ever
  waiting to open: `md` paints immediately, the raw file loads behind it
  and swaps in when decoded, so the 2026-08-09 no-stall ruling and the
  ask for full size both hold.
- **2026-08-15** — **The board strip stops inventing a blocker**
  (user-caught). Every empty frame carried a hardcoded `SIZE —`, naming a
  problem the panel did not have: a panel that has simply never been
  rendered has no size problem. The frame now reads the SLOT MAP and
  states the real verdict — the true `SIZE — 3136×1344 INTO A 3479×795
  SLOT` where one exists, `NO APPROVED TAKE` where that is the issue, and
  nothing at all for a status it has no line for. Say the true thing or
  say nothing. The frames are also one window shape now (35mm, the take
  fitted inside), because per-take ratios made a strip that would not
  line up.
- **2026-08-15** — **The takes strip is film** (user): 35mm windows with
  each take fitted inside longest-edge first, perforated edges, and an
  edge marking carrying the panel and take count where a stock name would
  sit. Clicking a frame makes that take current and opens it full size —
  the window shows less than the take by design, so the way to the rest
  is the same click that selects it.
- **2026-08-15** — **A board's panels read along one strip** (user): the
  opener wrapped nine panels into three rows and pushed the specification
  off the screen. It is now a single horizontal strip you drag — pointer
  events, so pen and touch behave like a mouse — with momentum on a flick
  that decays per frame and stops at either end rather than coasting into
  a wall. Momentum is motion, so `prefers-reduced-motion` gets the drag
  without the glide.
- **2026-08-15** — **An object's REF shows what actually covers it**
  (user): clicking `REF` on a required object opened the whole library
  group; it now opens the plates SELECTED for that object, with `Show all
  n` one verb away — a set you cannot see is a set you cannot widen
  again. Choosing there writes back to the same per-panel pick the
  reference row reads, so the two can never disagree.
- **2026-08-15** — **Production bug: a paid render was thrown away by
  bookkeeping.** Generation returned `{"detail": "'sha256'"}` — a
  KeyError raised by the take-RECORD write, which runs after the image
  has come back from the engine. The synthetic palette plate carried no
  `sha256`, so one missing field on one reference destroyed a render the
  user had been charged for. The plate now carries its own hash, and the
  record reads every reference field defensively: nothing about
  bookkeeping may discard work that already succeeded.
- **2026-08-15** — **One palette, one reference** (user): the swatches of
  a palette now composite into a single labelled plate and ride as one
  image. Colour by colour, an eight-colour design language quietly spent
  eight of the render's fourteen reference slots — a panel with ONE
  subject group ticked reported "13 SUBJECT" and sat over the cap with
  nothing on screen to explain it. The count now names the palette as its
  own role, and step 04 ends with a manifest of every plate that will
  ride. **And a group's plates are chosen by looking at them** (user):
  `Choose plates` opens the group's photos with a USE tick per plate, so
  a five-plate group can ride as two.
- **2026-08-14** — **A reference row can be ticked, and looks it**
  (user: "nothing there lets me ADD a ref that was not automatically
  selected"). The off rows were tickable the whole time — the marker was
  a 13px `○` with no box, which reads as a bullet, not a control. §2.3
  ruled `○` over a bare dot so the off state read as half of a PAIR
  rather than as absence; an empty bordered box keeps that and adds the
  affordance `○` lacked. The row is now the hit target and says so on
  hover, and a tick confirms itself — the row brightens and states
  `ATTACHED — RIDES THE NEXT TAKE` in `--hold`, because a change you just
  made is your decision, not the app's.
- **2026-08-14** — **A reference row names its plates** (user asked "I
  can't tell what references are being used for the panel"): the rows
  stated a GROUP and a count, the plate ids sat in a hover title, and the
  verb called `Show ids` revealed the always-on anchors' ids only. Show
  ids now names every plate on every row — ticked and unticked — with a
  consecutive run collapsing to its ends (`REF-0028 → REF-0032`). The
  provenance rail and the reference rows share one renderer, so the two
  can never disagree about what rode a render.
- **2026-08-14** — **An approved take keeps its tools** (user-reported
  bug): approving a take hid the entire USE group — Full-size take,
  Repair region and Reject — because the empty-zone check tested only the
  FIRST `.act-items` span in the zone, which after the step-sequence
  rebuild was `act-approve`. Approve panel correctly steps aside once a
  take is approved; everything beside it went too. The zone now counts
  every button it holds. Rejecting an approved take is precisely when
  Reject matters most.
- **2026-08-14** — **A tool in a toolbar is a button** (user): the act
  bar's verbs went back to bordered controls at 13.5px/600. §1.4 still
  governs a verb inline beside its fact; a bar of tools is a different
  thing, and at 11.5px underlined text it stopped reading as tools at
  all. The run facts moved from the bar onto the image — facts about a
  picture ride on it, and in the bar they were folding three tools
  behind the `⋯` to protect a caption.
- **2026-08-14** — **Stage 03 joins the step sequence** (Part 3, mock
  hier-5a): one `seqStep()` now renders both surfaces, so the vocabulary
  cannot drift between them. Seven steps, the questions promoted out of a
  bullet into step 03 with their consequence stated, an approve gate that
  states its condition instead of lying, and the breakdown finally opens
  on the pictures it describes — an approved take per panel, or an empty
  frame at the panel's own ratio stating the blocker that keeps it empty.
  Per the user's rulings: the ledger is a hybrid (selects while drafting,
  a stated record once confirmed or locked), creation cards stay, and the
  forbidden-list duplicates stay. Vocabulary class generalised `.wb-card`
  → `.seq`; stage 02 remains, and only after this survives real use.
- **2026-08-14** — **The palette picker attaches a palette whole**
  (user-caught, twice). First fault: it carried its own inline notes
  reader that assumed the hex sat at index 1, but the shape is `language ·
  name · hex[/pair] · cite` — so it read the NAME as the hex (falling back
  to `#666666` for all nineteen) and the LANGUAGE as the name, printing
  "RESISTANCE #666666" nineteen times. It now reads through
  `swatchNotes()` like every other surface. Second fault: the rebuild
  offered a grid of individual colours, which is the exact shape *a set
  that means something as a set renders as one object* names as wrong —
  the ramp IS the swatch and the colours are its inside. It now offers one
  row per design language drawn with the shelf's own `.sw-ramp` (hero band
  leftmost, luminance order, pair split top/bottom), selection is an amber
  outline, and choosing a row attaches that palette whole.
- **2026-08-14** — **The step sequence** (STEP_SEQUENCE_SPEC, mock
  hier-4a): stage 04 rebuilt as six confirmations ending in a render, and
  Part 1's vocabulary folded into canon above — the image is the hero
  (outranking the rest of Layout patterns), three type sizes, fill
  classifies, verbs ink + underlined on one right edge, the step number as
  the spine, honest gates, row-not-block gutters, capped prose measures;
  three Do-nots (no truncated titles, no unprovable counts, no two words
  for one state). Three tokens added: `--band`, `--tile`, `--hairline`.
  **Fixed a live defect the sequence surfaced**: the Aspect select
  hardcoded 16:9 while the panel head reported the LAST TAKE's ratio, so
  Generate silently re-shaped a 21:9 hero panel — it now opens on the
  panel's established shape and states a mismatch in `--bad`. Also
  removed a headless `.stor-bar` rule body orphaned by canon-pass R6,
  which had left this stylesheet's braces unbalanced since 2026-08-10.
  Scoped to `.wb-card`; stage 03 is the next transfer, stage 02 only
  after this survives real use.
- **2026-08-14** — **RULED (HARNESS_AUDIT_2026-08-14, the first
  audit-by-use):** 16 of 18 Uncanonized rows ruled and emptied; R2
  (arrange room) and four parts of R4 (board looks) deferred pending the
  next recording walk. Six Layout canons added (record-has-no-status-
  colour, person's-sentence-never-Courier, lead-promotes-not-copies,
  knowing-stage-must-not-ask, locked-reads-as-document, artifact-vs-
  chrome typography), the dropdown panel componentized, three Do-nots
  (no wrapping verbs, no two-verbs-one-outcome, no product signals on
  dev tooling). Six use-found defects fixed: carried-notes rail
  repainted as a record (label `CARRIED NOTES · n`, notes in Archivo as
  typed, `Edit` + one reversible `Stop carrying`, hard delete inside the
  Edit modal); Status lead now promotes its blocker out of the list;
  stage 04 lands on the last breakdown worked; `.ghost`/`.text-act`
  never wrap; camera row breaks 3+2; composition check states its clean
  verdict. Dress kinds renamed into the closed block vocabulary;
  md-tier-preview-only enforced in the renderer; recorder chip to
  `--hold`.
- **2026-08-13** — **Harness tooling** (HARNESS_PLAN): `?record=1` loads
  app/static/recorder.js, which wraps `window.fetch`, records every /api/
  response off a real session, and downloads a fixture bundle via an
  amber-bordered Courier chip; `tools/build_harness.py <bundle>` packages
  the shipped frontend byte-identical with a replay shim so the designer
  clicks the actual UI offline. Fixtures are recorded, never authored;
  `/api/healthz` gained `app_sha` so the harness states its own staleness.
- **2026-08-13** — **One board across revisions** (user model): boards key
  on the base spec id; the newest locked revision defines structure;
  Create revision declares its panel scope in a checkbox modal; carried
  panels ride read-only and their approvals flow to the board; a revised
  panel's old take is OFFERED (`REVISED SINCE`) until re-rendered or
  explicitly Kept (journaled); provenance always stated (`FROM R(n)`,
  `KEPT`, `BUILT ON R(n)`).
- **2026-08-13** — **Per-swatch palette selection** (user): the whole
  palette no longer rides every render (all 19 attached via one
  suffix-less group checkbox, colliding with the 14-image cap). A
  `Palette` selector leads the rendering settings; empty = the shelf's
  capped newest-2, any pick owns the role exactly.
- **2026-08-13** — **Rejection notes are indestructible by accident**
  (user ruling): deleting a take archives its note WITH its retired flag
  and the rail keeps showing it (`TAKE DELETED, NOTE CARRIES`); notes are
  edited by their Edit verb and die only by their own confirmed, journaled
  Delete verb. `GET /carried-feedback` is the rail's single source.
- **2026-08-13** — **Correction intake** (user, from the GT40 rejection
  debrief): a saved rejection is parsed into proposed structural deltas
  (camera axis, require/forbid, brief extension) shown as a checklist
  under its CARRIED REJECTIONS row; applying routes through the existing
  journaled amend doors; the verbatim carry coexists until retired.
- **2026-08-13** — **Composition check** (user): a free pre-render verdict —
  the narrative model reads the panel's screenplay scene and judges the
  compiled prompt's subject prominence, angle, action coverage and
  composition; advisory only, rendered in the existing `.report` host with
  an Apply-suggested-camera handoff into the existing camera editor.
- **2026-08-13** — **Camera orientation axis** (user, from the GT40
  rejection debrief): the shared camera row gains a fifth `View` select
  (azimuth — front/three-quarter/side/rear); no baseline, unset = model's
  choice, stated line omits it when unset.
- **2026-08-13** — **The arrange room works in the content field**
  (user bug report, second round: the room still disagreed with the
  board). The sheet grammar renders panels inside the content rect —
  margins plus the masthead band, a ~2.02:1 field on a 16:9 page — but
  the room previewed tiles across a full 16:9 surface and computed its
  pixel readouts against the full canvas, so every panel previewed
  ~14% narrower than the export rendered it, and the advisory readouts
  disagreed with the gate. Corrected: `GET /api/sheets/{id}` states the
  derived `content_rect`, and the room's surface aspect, readouts,
  ratio snap, and crop aspects all work in that field — room, map, gate
  and export now describe identical panels.
- **2026-08-13** — **Dress is additive** (user bug report: exported
  panels cropped differently than arranged, and the slot map disagreed
  with the room). The original model carved dress bands out of the
  fixed canvas and rescaled the panels, warping every slot's aspect —
  and since a crop is framing intent, the display window re-derived
  differently on export. Corrected: the page GROWS to hold the dress
  (Art Board taller, Tech Design wider+taller) and the panel field
  keeps its exact arranged pixels — crops, room, map, and pixel
  verdicts identical bare and dressed; the slot map shows the raw
  arrangement again. Also: swatch labels clip to their own cell,
  compact swatches keyline (VOID BLACK vanished on the dark ground),
  and the atmosphere strip states place/hour only (the render intent
  already reads as the masthead tagline). The assembled record states
  the artifact's real dims.
- **2026-08-13** — **Board looks** (user): an arranged board can carry a
  presentation style — Art Board (parchment, serif masthead + tagline,
  hand annotations from the slots' own annotation text, palette swatch
  strip, atmosphere slug) or Tech Design (near-black, mono, keylined
  panels with registration ticks and panel ids, spec table column,
  material chips, compact hex row) — chosen in the room's `Style…`
  picker from real renders of the board itself. The look is a sheet
  sibling (`look`), survives every arrangement commit, and dresses
  previews, export and assembly ONLY: the room stays INK (user ruling).
  Dress is pure derivation (`looks.dressed`), resolved from canon at
  render time; readiness and the export gate judge the dressed sheet.
  Render faces are now bundled OFL files (EB Garamond, IBM Plex Mono,
  Inter, Zilla Slab, + new hand voice Caveat) — Linux tenants rendered
  bitmap type before this. Non-canon: see the table (seven questions).
- **2026-08-13** — **Lab migration + mode switch** (user): Arrange is a
  MODE — the readiness map hands over to the room and `Done arranging`
  brings it back (two boards on one page read as a copy). Tiles render
  THROUGH the crop's display window; the crop modal is one full-plate
  stage with HAND/CROP icon tools and a live ON-THE-PANEL preview.
  **Crop-as-framing-intent canonized in code** (`sheet.display_window`,
  one function feeding renderer, readiness and the ladder): the drawn
  window re-derives for the frame's aspect and only the plate gates —
  `SHORT — PLATE SHOWS…`. Claims are one-step (through the next panel;
  refugees stack, never dock beside). Boards remember the breakdown and
  drilled board being worked on; slots follow the latest approved take.
- **2026-08-12** — **The arrange room gets its physics** (user-directed,
  iterated in the Reflow Lab artifact until it felt right): tiles are
  the real takes, ghosted; linked resize, split-docking, claim arrows,
  bench/trash/+, ratio + grid snap, live pixel gate. The client edits a
  rows→columns→cells STRUCTURE and commits it whole
  (`PUT /api/sheets/{id}/arrangement`); the server maps structure to
  slot geometry — R2's "geometry computed once" now reads: once, on the
  server, per commit. The stage-05 slot map also shows each panel's
  take, ghosted, under its verdict chrome. Non-canon: see the table.
- **2026-08-12** — **Every page is a shareable address** (user): plain
  paths for every stage and selection — `/breakdowns/<spec>`,
  `/panels/<spec>[/<panel>]`, `/boards/<spec>[/arrange|/<board-id>]`,
  and the tools. The server boots the stamped SPA for any non-API path;
  sign-in carries the destination (`/login?next=`); selections keep the
  address honest; Back/Forward walk history. Non-canon: URL vocabulary
  row in the table (no visible UI).
- **2026-08-12** — **The Lookbook surface is rolled back** (user: "too
  big, and separate from the Board panel"). Gone: the nav tool, the
  shelf, sheet authoring (archetypes/styles/sizes/block tray/captions),
  lookbook PDF sets, and their API routes. Stays: the sheet model as the
  boards' one renderer, and the composer as the **inline arrange room**
  on stage 05 (`Arrange this board` unfolds it under the slot map;
  Fill/Swap/Crop/Clear per slot, drag-resize, stated export gate, PNG +
  PDF export). §13 items amended in place; non-canon row above. The
  band's tool list loses Lookbook everywhere it was enumerated.
- **2026-08-12** — **Review fix batch** (2026-08-12 review of .14–.21): the
  composer's export gate gains the `SLOT_APPROVAL` kind (slots hold
  approved takes only — arrange leaves unapproved panels as empty slots,
  and a take rejected after placement turns the gate red); arrange chunks
  oversized boards into multiple blocks instead of a 422; arranged
  mastheads are born BOUND; legacy autofill shot words (FULL_BODY/DETAIL)
  migrate onto the camera enum everywhere a scale is read. Non-canon: see
  the Uncanonized table (copy-only review).
- **2026-08-10** — **Canonization pass** (CANONIZATION_PASS_2026-08-10,
  R1–R10 + mocks au-*): all nine Uncanonized rows ruled and the table
  emptied. Composer amber exemption REFUSED — two spends survive
  (selection, Export); block chip → tags-ride-the-image, AUTHORED → plain
  Courier fact, stale acts equal ghosts. Overlay drift resolved by
  structure: the renderer emits its geometry manifest and the JS mirror is
  deleted (geometry-computed-once canonized). Unanchored locations become
  a labelled REGISTER under the SCENES grid (card-is-for-a-picture
  canonized; no own shelf). The ramps ARE the STYLE shelf; quarantine
  keeps cards below. Storage bar deleted — Courier number line carries
  the state (no-second-bar canonized). Workbench camera collapses to a
  stated line with `Change camera` (one-control-two-presentations
  canonized); brief stays in place with inheritance stated
  (room-owed-on-inheritance canonized). Board type moves above the brief.
  Remembered-selection copy: `RODE THE PREVIOUS TAKE`.
- **2026-08-10** — **The sheet grammar lands** (SHEET_SYSTEM_PLAN, rulings
  R1–R8): boards and lookbook pages become one mechanism — twelve block
  types, six sheet styles (INK is the boards'; its ground moves to
  #131418 deliberately), the fixed-floor size ladder with elastic
  evidence type, caption bindings that never auto-adopt, and the
  composer (tray · fitted sheet · rail) behind a Lookbook tool button.
  Stage 03 copy renamed **breakdown** (R7 — "sheet" now means exactly one
  thing). Sheet ink is namespaced under `.sheet[data-style]`, never
  `:root` (token-test enforced). Non-canon: see the Uncanonized table.
- **2026-08-08** — **Editable panel brief + remembered reference selection**
  (user): the workbench purpose line gains an `Edit brief` text act (in-place
  textarea, ghost Save, journaled amend, lock re-stamped; APPROVED take
  freezes the brief and the gate reads as state), and the reference
  checkboxes now remember the newest take's selection instead of resetting to
  the matcher. Both in the Uncanonized table.
- **2026-08-07** — **The look interview leads Production Design** (user):
  the rail is now `01 Interview · 02 Anchors · 03 Scan · 04 Cast ·
  05 Bible · 06 Bake-off`. What the director wants it to feel like is
  stated before the machine reads anything; the interview is five
  free-text fields with no dependency on the scan, so nothing gates it.
  Steps 3 and 4 remain swapped per LOCKED_STAGE_PLAN L3 — the interview
  still precedes casting. Also corrected here: three step numbers in this
  file had drifted (Cast documented as 3, implemented as 4; the
  environment card as 2, implemented in the scan step), and the SUBJECTS
  read-tile had been scrolling to the interview instead of Cast since that
  swap.
- **2026-08-07** — One act, one name (user): the link that creates a
  breakdown from a location read `Create Breakdown` on Screenplay and
  `Make sheet` on Production Design. Both are `Create breakdown` now, and
  `Open sheet` is `Open breakdown` — sentence case, like every other
  button. `tests/test_vocabulary.py` holds it.
- **2026-08-08** — Carried rejections become **retirable** (user): a
  correction that was satisfied — or that a newer note supersedes — can be
  retired from the provenance rail and stops entering future prompts; the
  rejection and its history stay, the retirement is logged, and Reinstate
  reverses it. Corrections also order newest-first in the prompt: the
  latest note is the director's current mind. Found when two carried notes
  contradicted — "get rid of the person at the window" lost to an older
  "closer adherence to the reference provided" whose reference contained
  the person; an image plus adhere-closer beats a text negation.
- **2026-08-08** — Take action bar: Approve panel becomes the filled
  amber verdict, the six remaining verbs become text acts in labelled USE
  and DERIVE groups, arrows dropped, DERIVE collapses to ⋯ before the row
  wraps. T2's one-grammar clause superseded; decision-not-code-owns-
  hierarchy canonized. (Supersedes the 14a peer-cluster geometry shipped
  earlier the same day.)
- **2026-08-08** — The screenplay's **locations reach the Reference
  library** (user): the SCENES shelf gains the uncast pattern's twin —
  unanchored places as cards with one act that prefills a titled
  `LOCATION_GEOMETRY` role, anchored-ness judged by the panel matcher's
  own two-way containment so shelf and pre-check cannot disagree, and
  library search covering location names and environments. Casting stays
  subjects-only: subjects ride per panel appearance, places ride per
  scene coverage. Flagged for a full design pass, per the user.
- **2026-08-08** — Take action bar brought to **corrected mock 14a**
  (comparison pass, pending since the mock arrived after T1/T2 shipped
  from written spec): the identity tag moves to the TOP right and states
  `CAND-0008 · TAKE 2 OF 2` — ordinal by creation position, not list
  index; the bar loses its box, fences and internal rule — each verb's
  ghost border is the only chrome, Approve holding the left in its green,
  the cluster right-aligned, wrapping never scrolling. Reported
  deviation: Reject stays at the far end — the mock omits it, but
  removing a verb is functionality, and styling work does not change
  functionality.
- **2026-08-08** — Reference's STYLE shelf **consolidates swatches into
  ramps** (user): the same one-object-per-language presentation as the
  Production Design column, opening the same viewer. Doing it honestly
  meant hoisting the swatch viewer to module scope — one viewer, two
  pages — with the page-specific facts as options: `refresh` names the
  view to re-render, and `onRescan` is absent where no engine picker
  exists, so Rescan only renders where it can actually run. Quarantined
  swatches keep their card; a mixed group offers Approve only on rows
  still provisional.
- **2026-08-07** — Disk space is a **gate, not a 502** (user incident): a
  studio filled its volume and region repair died mid-write with
  `[Errno 28]`. Every render path now refuses before the spend, stating
  what is free and how to reclaim it; Settings carries a storage readout
  with a by-kind breakdown; and the pre-import safety copy is capped at
  ONE, is refused outright when it would not fit, and is finally
  downloadable — it was insurance with no way to collect it.
- **2026-08-07** — The auto breakdown takes a **stated board type** (user
  bug): a scene-seeded draft rewritten as a location study in prose came
  back as the seeded scene. The brief was never dropped — it simply could
  not outweigh a scene anchor that asserted "This board is about THESE
  scenes" for every board, derived only from the location name, so a
  rewritten brief produced a byte-identical anchor. The anchor now supplies
  the evidence base and the board type states the shape; the `scene` field
  stops asking a LOCATION board to describe a scene; and a stated type
  outranks the model's reading of the prose.
- **2026-08-07** — Canonization pass: all seven Uncanonized rows ruled.
  Verb-sits-with-its-object canonized as the pair to act-where-condition-
  is-met; bulk verdicts withheld until everything judged has been seen;
  destructive acts only offered where their object can be read in full;
  amber confirmed as blocking-only, never a report. The approved ramp
  row's × is removed; Rescan leaves the verdict bar.
- **2026-08-07** — Step 2: logline above the counts, stat tiles cut a
  third; environments edit in a full modal that names their inheriting
  sheets; locations capped at five per environment with an expand row.
  Head-and-tail lists and edit-in-a-room canonized.
- **2026-08-07** — Swatches can be **rescanned** (user): aimed at one
  design language or run as a wider **Deep scan**, both taking an optional
  brief. Either way the engine is told what the palette already holds AND
  what was already rejected, so a rescan proposes what is missing instead
  of re-asking a settled question.
- **2026-08-07** — Breakdown **design questions can be answered**, and the
  answers are canon (user): they ride every panel's prompt as DESIGN
  DECISIONS. Unanswered ones are never sent — an open question in a prompt
  is an invitation to invent. The block's copy is mode-aware now; it used
  to tell the user to run a design exploration while they were reading one.
- **2026-08-07** — **Time of day is a select** (user bug): it was an input
  with a datalist, and a datalist filters itself away against a value like
  `SAME`, leaving nothing to pick. `SAME` / `CONTINUOUS` / `LATER` are
  screenplay continuity markers, not hours, and no longer become one at
  extraction; an unrecognised stored value is still offered so opening a
  sheet never silently changes it.
- **2026-08-07** — **Review all N** reaches the approved column too
  (user): the proposal bar's act disappears with the proposals, so a
  finished palette could only be read one language at a time. A text act
  under the ramp rows opens every approved language in one scroll.
- **2026-08-07** — The palette review gains **Review all N** and reaches
  approved swatches (user): `Approve all 19` could act across languages
  nobody had opened, so the viewer now takes a LIST of groups — one for a
  ramp click, all of them for the bar's new act — and the bar states how
  many languages are still unopened. Approved ramp rows open the same
  viewer in an APPROVED mode (`Recolor · Reject`, no `Approve`, no bulk
  verbs); that header case was written into PALETTE_GROUPS_PLAN §2.1 and
  had nothing reaching it, which broke the ramp's own rule that members
  are one click away. `Reject` there demotes out of canon and is NOT the
  row's `×`, which deletes.
- **2026-08-06** — Palette swatches group into one ramp per design
  language (hero leftmost, double width); per-colour facts and verdicts
  move into the swatch viewer. **Set-as-one-object canonized** — see the
  composition section. RULED: the hero chip and `OPEN` carry amber after
  all (the earlier non-canon build made them `--ink-dim`); the recolour
  pencil is retired — `Recolor` is a text act in the viewer, so the app
  still has no action glyph.
- **2026-08-06** — Swatches gain a hero, a shorter tongue and an editable
  colour (user): each design language names ONE hero colour — the one a
  production designer splashes through that faction's sets so the area
  reads on sight; the edit takes a colour picker beside the hex (user), the
  two kept in sync and an unset one hatched rather than shown as black;
  citations become LABELS ("cold GRM white light",
  "GT40 yellow") rather than quoted sentences, clamped to six words on the
  way in; and a pencil on the swatch repaints it in place, keeping the
  reference id so recorded approvals are not orphaned. Generating them now
  states its wait in the canon `.busy` strip instead of swapping a button
  label. Non-canon: see the Uncanonized table.
- **2026-08-06** — Backing up a production states its wait (user): the
  Back up button streamed nothing and showed nothing, so a large
  production packed in silence. It now hosts the canon `.busy` strip on
  its own card — "Packing …", then live bytes as the zip downloads.
  Non-canon: see the Uncanonized table.
- **2026-08-06** — Productions gain **Import backup** (user): restore has
  always made a NEW production; import sets an EXISTING one to the version
  in a zip. The zip is read before the warning is written, so the modal
  names what the archive holds, and the confirmation is the typed
  production name — the same grammar as Delete, because it destroys the
  same things. Non-canon: see the Uncanonized table.
- **2026-08-06** — The compiled prompt gains Download (user): a
  16,000-character prompt is a file, not a clipboard payload. It writes a
  .md whose header carries what the prompt body cannot — engine, size,
  and the references actually attached, or a stated "none, this rendered
  from the spec and style anchors alone".

- **2026-08-06** — Intake widths corrected (user): the blank door's Mode
  and Board type truncated. Mode options shed their explanatory suffixes
  (a select is only as wide as its longest option), the door ratio went
  1.5fr → 1.15fr, and Spec ID took its own row so the two machine-value
  selects have a full half each — mock 13a grouped them on one row, which
  no honest split of that column affords.

- **2026-08-06** — Breakdown intake (BREAKDOWN_INTAKE B1–B5, mock 13a):
  the two ways to make a sheet became one section of two doors with amber
  on the recommended one; the brief leads the auto door; the Spec ID help
  became a `?` card that reassures before it warns; the sheets table is
  data only, with the labelled-table treatment and a count.

- **2026-08-06** — Take viewer (TAKE_ACTIONS T1–T3): state and identity
  moved onto the image, the action row carries verbs only and wraps
  instead of scrolling, and the six peer verbs all render as ghost
  buttons — they were one button and five bare text links, which read as
  one action plus five footnotes.

- **2026-08-06** — The hatch canonized as the only empty-image surface
  (HATCH_RULE H1–H3): three classes, always 135°, never re-declared
  inline. Audit found zero drift in `app/`; the storefront gained a
  mirrored copy with a contract comparing the two stylesheets.

- **2026-08-06** — Swatch generation moved to step 5 beside the saved
  Bible; act-where-condition-is-met canonized as the pair to anchored
  explanation. The Uncanonized table is empty.

- **2026-08-06** — Production Design v3 (PRODUCTION_DESIGN_V3_PLAN D1–D6,
  D8, D9; mock pd3-full-page): states-not-explains canonized app-wide;
  Courier step headings + condition lines; six-step rail; READ FOUND
  stat tiles + accent-ruled logline; labelled locations table (fixed
  tracks, withheld-verb gate, no inner scroll); open questions two-up;
  interview two-column. D8 rulings: swatch proposals persist as
  PROVISIONAL refs, approve-all ghosted, Save gate as dashed tag, update
  bar below the band, four-anchor row and no-use-in-draft ratified —
  Uncanonized table emptied. Preset-look pattern canonized ahead of its
  plate library (D7 pending). Dead reveal-strip CSS deleted.

- **2026-08-05** — Settings control panel (SETTINGS_CONTROL_PANEL_PLAN
  P1–P4, mock 18b): the configured AI & engines tab rebuilt to the
  states-never-explains economy — role cards stripped to name + live
  selector, one equal-row credential list (unconnected rows carry only
  Authenticate), stat tiles replaced by the one-line MODELS summary.
  Third-party brand icons canonized app-wide (P3); dead CSS deleted
  (grep-proofed): ai-head/bill-warn/sec-sub/role-jobs/role-sel-meta/
  rec-*/role-note/cred-tag/cred-ident/cred-foot/cred-mark.none/sec-act/
  reach-*/cred-grid4/cred-connect/ok-k.

- **2026-08-05** — The two-mode band (BAND_CONDENSE_PLAN B1–B3, snippet
  verbatim): the pipeline band condenses while a tool view is open.

- **2026-08-04** — Canonization pass: Uncanonized table emptied under
  CANONIZATION_PASS.md R1–R19; --warn deleted (aliased accent),
  translucent ambers tokenized, mock-16b deviation ratified as the
  truthful-deviation example, notification/mode/refusal/withheld-verb
  vocabularies ruled. Dead CSS deleted (grep-proofed):
  boards-empty/be-*/path-box/path-row, engine-cards/eng-head/eng-model,
  prod-moved, take-label state rules; kept .subj-add and .take-label
  base (still generated).

- **2026-08-04** — Reference snippets delivered and adopted (marquee +
  AI-models notice), all hexes mapped to tokens: the marquee's channel/
  tile anatomy is final; the notice gains the typewriter grammar — a
  one-time amber rule-sweep and a Courier block caret blinking with
  steps(1) (a fading caret reads as a glitch), both under
  prefers-reduced-motion. The verification loop is now EXECUTABLE:
  `.claude/skills/design-verify/` + the standing token contracts in
  `tests/test_design_tokens.py` (CI-enforced), mandated by CLAUDE.md for
  every UI-touching change.

- **2026-08-04** — Conformance audit (21 findings, user-prompted): `.mono`
  utility DEFINED at last — it was used ~45 times but never existed, so a
  swath of canonized Courier (lock-popover steps, prod-card slugs, the
  C2 line, SCOPE, bf-pid…) silently rendered Archivo. Card Approve
  buttons stop multiplying amber (--ok approve grammar); `a.ghost`
  styled; not-yet-done badges move REJECTED→LOCKED grammar; CANDIDATE
  chip, held counts, open-production marks, `+ New production`, toast
  border and pending counts leave the amber budget; warn states ride
  `--warn`; Consolas→`var(--mono)`; wrong token fallbacks dropped;
  `--accent-hover` tokenizes the pre-existing hover tint (ratify);
  selection hygiene extended; structural-board palette marked as a
  content exemption. Open questions logged in the Uncanonized table.

- **2026-08-04** — Verifying-against-mocks process added (MOCK_PARITY
  ruling) and applied to the first-run Settings screen: outer panel
  restored (the dropped-wrapper failure), notice divider at 34px, role
  cards back to one row with text-sized chips, active tab marker moved
  to a 2px bottom border on --bg, Add model set in Archivo, PRODUCTIONS
  MOVED pointer hidden on first run, panel/section spacing per mock.

- **2026-08-04** — F6 backend shipped: the narrative role now runs on
  the Anthropic key or the OpenRouter connection as well as OpenAI and
  Gemini. The credential row's STORED — USED ONCE… interim copy retires
  (it now tests and states NARRATIVE · <model>); the narrative role
  select lists every usable home and persists `narrative_provider`; the
  research selects (Scene Scan, breakdown draft) get their own narrative
  filler — image-model ids had leaked into them since the connectors
  rewrite, where every pick was a server-side 422.

- **2026-08-03** — First-run rebuilt (SETTINGS_FIRST_RUN_PLAN F1–F7): the
  AI & engines page gains two lives — a setup form before any credential
  (OpenRouter quick-start hero with the page's only amber, provider
  marquee from the locally-served LobeHub set, account list with
  Authenticate modals, withheld-verb role tags) and the standing control
  panel after. Connecting OpenRouter sets the recommended defaults
  (gpt-5.6 narrative · GPT Image 2 via OpenRouter). Anthropic Claude row
  ships ahead of its backend — the key stores with the condition stated.
  Section headers renamed: SET DEFAULT MODELS / WHAT PAYS FOR IT / WHAT
  ELSE IS REACHABLE (numeric prefixes retired). New canon: the two-lives
  rule, the withheld-verb tag over disabled dropdowns, the marquee and
  icon-source rules.
- **2026-08-03** — The four-anchor ruling (user, adversarially reviewed):
  style anchors restructure as three MOVIE parameters (WORLD_TEXTURE,
  COLOR_PALETTE, CINEMATOGRAPHY_STYLE — palette explicitly outside
  cinematography's jurisdiction) plus one BOARD parameter
  (BOARD_RENDERING_STYLE, presentation only). All four auto-attach,
  capped at 2 per role so style never starves subject anchoring;
  BOARD_LAYOUT_STYLE leaves Production Design for Assembly (its gate
  already lived there); the bible drafter is forbidden medium language
  outside Rendering Language / Board Presentation.
- **2026-08-03** — Settings rebuilt for two AI roles and connectors
  (CONNECTORS_UI_PLAN C1–C9): recommendation ruled as a stated fact with
  a reason, credentials unified into one list, catalog grouped by
  capability, per-panel picker gains search with server-side reach,
  header dots become one square per role. New canon: three-question
  Settings order, capability-before-vendor grouping, the recommendation /
  credential-row / capability-badge components, role squares and
  typographic tiles under Icons. One truthful deviation from mock 16b:
  OpenRouter's PKCE key IS stored on this machine (calls need it), so the
  row states SCOPED KEY — REVOKE FROM THEIR DASHBOARD rather than the
  mock's "no key held" claim.
- **2026-08-03** — Brand icon lands (designer handoff `icon_update`): new
  **Brand** section (the mark, two-master rule, placement rules); icons
  served at `/icons/` on both surfaces with full favicon/manifest head
  snippets. Handoff spec `brand/BRAND_ICON.md` folded in and deleted.
- **2026-08-03** — Panel card redesign (PANEL_CARD_PLAN P1–P9, designer
  ruling): the card ships as one component with two lives — work order
  (numbered required table with REF/HOLD marks, stated forbidden/scope,
  summarised style anchors, named zero-match state, one amber Generate
  first take + dispatch facts) and light table (one action bar, take
  captions, merged dossier with true shape label and the no-subject-
  references finding, legible navigator). New canon: empty-state rule,
  summarised auto-attachment, the stated zero state, one-bar action
  grouping. GET /api/specs/{id} gained lock_hash for the dispatch line.
- **2026-08-03** — Debug tools (user-directed): Settings gains a Debug
  tools tab (mock engine + page-text edit mode); new UNCANONIZED
  `.text-edit-chip` fixed mode banner (z 60, amber left border). Mock
  output is always stamped MOCK — it can never read as a real render.
  Same day, owner-linked (user ruling): the tab, endpoints and mock
  provider exist only on the owner's installs (`SCREENBOARD_DEBUG_TOOLS`,
  set by the store for OWNER_EMAILS studios) — customers never see them.
- **2026-08-01** — Locked-stage pass (LOCKED_STAGE_PLAN L1–L4): a locked
  stage is a condition, not a destination — unmet stages are inert with a
  LOCKED chip; clicking one opens the anchored explanation under the
  first unmet stage's cell; gate steps read from live state (scan_done
  added to stage_summary); the stage checklist replaces every
  explanation-plus-button empty state and the rows are the navigation;
  Production Design steps 3↔4 swapped (interview before casting).
- **2026-08-01** — Director's ruling: the template default art direction
  (DEFAULT_STYLE_BIBLE — the Beltminers-flavored VISUAL STYLE block) is
  deleted. Every production's rendering style comes only from its own
  bible (Cinematography and Rendering); with no bible the style text is
  empty and rendering is gated, never silently painted with another
  film's look. Breakdowns gate on the bible for the same reason.
- **2026-08-01** — Productions pass ratified: nav order, single amber
  fill, additive rename slug, duplicate/delete gates, reach-band panel
  semantics confirmed as built; "Wrapped" replaced with truthful
  last-activity phrasing; Boards middle state gets a one-line path.
- **2026-08-01** — Productions pass: projects renamed "production" in copy
  and moved out of Settings into their own view as cards with reach bands
  and per-production DO-THIS-NEXT; ACTIVE badge retired for the open-state
  vocabulary; inline rename canonized; backup age escalates as care, never
  as a blocker; first-run and empty-Boards states state the path.
- **2026-07-31** — Cloud/product split (director's ruling): the app gained
  an env-gated workspace login (`SCREENBOARD_ACCESS_TOKEN`; standalone
  installs unaffected) and a Projects panel in Settings (multi-project
  save/load; engines and keys stay install-level). Both logged as
  uncanonized — the auth surface and the switcher need design rulings.
- **2026-07-31** — Board layout grammar (director's ruling): "Aspect" is
  the new default variant — slot geometry derives from the takes' own
  aspect ratios (justified rows, aspect first, scale second, crop last,
  residual crop uniform and minimal); the old sheet-allocation hero
  grammar stays selectable as "Allocation". Variant chip vocabulary
  unchanged otherwise.
- **2026-07-31** — Four user-directed changes logged as uncanonized (see
  table): the Production Design locations verb became "Create Breakdown"
  (diverging from the canonical finder verb pair), design-language cards
  gained a "Derive from screenplay" keywords button, and panel cards
  gained per-panel environment and design-language overrides. The table
  is at the review threshold.
- **2026-07-31** — Stage-02 rebuild (PRODUCTION_DESIGN_PLAN P1–P9): the
  read presents as a reveal (strip with linking counts, answerable open
  questions, capped uncast triage with per-row bulk cast, locations as a
  finder list on the shared `buildLocFinder` code path); Gap 5 landed
  (CONFIRMED/PROPOSED worlds, merge-on-rerun preserving confirmations and
  answers, faction self-check that never adds a language itself); Gap 6
  landed (environments as a first-class axis — extraction with verbatim
  slugline assignment, `## Environments` level-3 Bible container, one
  environment per sheet injected between languages and lessons, grouped
  finder + coverage table, `PROMPT WILL CARRY` receipt). New canon: read
  reveal (Layout), environment card + scope carry line (Components),
  PROPOSED chip state (vocabulary picker); `.text-act` widened to the
  global text-action; step badges cover all six wizard steps.
- **2026-07-30** — One-library restructure (ONE_LIBRARY_PLAN D1–D6):
  Research renamed REFERENCE; the view became three shelves ordered by
  ride-along (STYLE / SUBJECTS / SCENES) with intake behind + Add
  reference; subject cards became the SUBJECTS shelf (one component, two
  hosts) with kind + CAST/UNCAST badges and editable identity text;
  wizard step 3 became "Cast the film" — a door into the shelf with
  grouped uncast proposals; object intake gained provenance-grouped
  suggestion chips (library / scene-paragraph). One-library model added
  to Layout patterns; subject card to Components; vocabulary picker
  amended with grouped suggestion chips.
- **2026-07-30** — Placeholder hatch superseded by user ruling: opaque
  two-tone 135° bands (assembly-style), 7/14px standard, 5/10px fine,
  red-shifted pair for error surfaces.
- **2026-07-30** — Review c: placeholder hatch specced by eye (2px/11px 45°,
  3.5% on --bg2 / 5% on --field, class-applied); pending tiles, take tags,
  finder list, lock strip canonized; object intake row folded into the
  intake-row rule.
- **2026-07-30** — Feature batch pending design review (see uncanonized
  table): pending take tiles, take state tags, scene browser, placeholder
  hatch. Presentation rulings the designer should know: boards now
  COVER-CROP takes to fill their slots (originals one click away; too-small
  takes letterbox and flag — slot-map TOO SMALL is now either-dimension);
  board grammars seed blank sheets (panel count + allocation only, per
  board type); promoted takes carry their reference id; sheet IDs enforce
  CAPS as typed; the screenplay stage gained Read-the-screenplay (reading
  view) and the scene browser.
- **2026-07-30** — Vocabulary picker canonized: suggestion chips stateless,
  facet toggles `.vchip.set` (never amber), conditional stored-as preview.
- **2026-07-30** — Design review: intake row, registry rows, and reading
  view canonized (with role prefix, test-state coloring, identity line);
  pipeline size cap surfaced on the Size select; custom engines stay out of
  repair by ruling. Aspect catalog shipped the same day: film-format names
  (CinemaScope 2.55:1, Scope 2.39:1, VistaVision 3:2, Academy 1.37:1),
  labels "Name — ratio", unsupported ratios disabled per engine, snap on
  model change — the pipeline no longer silently approximates.
- **2026-07-29** — First live-use findings pass: scrollbar amendment applied;
  repair overlay gains Esc + "Close — render continues"; Research intake
  compacted to a top row (uncanonized); custom user engines added to Settings
  (uncanonized rows) and every Model dropdown went dynamic; provenance prompt
  gains Copy / Expand reading view (uncanonized); ChatGPT-pipeline size
  400 fixed (tool presets only). See design_handoff/FEATURE_INVENTORY.md.
- **2026-07-29** — Scrollbar treatment added (thin, square, track invisible,
  thumb --line → --ink-faint on hover).
- **2026-07-29** — Plan v3 built (C1–C14): five-stage band with live
  sublines + engine dots; Status/Screenplay/Assembly views split out; the
  judging room (rail · stage · provenance); canonical blocking rows, recent
  feed, coverage meter, slot map, gate strip, fact rows — all folded into the
  sections above and the uncanonized table cleared. Variant chips, engine
  cards, filter chips, step badges added per mocks 4b/4c/4d/2a. Known
  deliberate ambers beyond the one-per-screen rule, both mock-sanctioned:
  the active variant/filter chip (selection state) and the band's current
  stage. Reject/quarantine copy corrected; Generate is not amber.
- **2026-07-29** — Backend-enablement UI (mocks 1a/4a/4b in the current nav):
  dashboard rebuilt around DO-THIS-NEXT + blocking rows + recent feed;
  screenplay panel gains the location coverage table; assembly gains the slot
  map; reference cards state their render usage; bible shows REV n; settings
  show last engine-test outcome. Four uncanonized patterns logged above —
  table is at the review threshold. Emoji stripped from Crop/Repair buttons
  (mock-sanctioned arrows on → Reference / → Light study kept).
- **2026-07-29** — Initial system. Replaces v1: amber restricted to stage /
  primary action / focus, Courier assigned to machine data, prose capped and
  moved to tooltips, nav rebuilt as the numbered pipeline band, ledger rows given
  a uniform border box. All v1 class names preserved; `app.js` untouched.
