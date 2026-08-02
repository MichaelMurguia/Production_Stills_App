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
lines      --line #2b3037    --line-soft #23272c
ink        --ink #eceef0     --ink-dim #9aa1a8    --ink-faint #6b7278
accent     --accent #e0a33f  --accent-ink #0b0c0e (text on amber)
status     --ok #6fae7a  --warn #e0a33f  --bad #cd6155  --hold #7d8fd0
type       --sans Archivo    --mono "Courier New"
radius     --radius 0px      (square. do not add rounding)
```

Surfaces layer `--bg` < `--bg2` < `--panel` < `--panel2`. Going deeper means
"more active/selected", never "more important".

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

**Pipeline band.** `nav#nav` is the product's spine: numbered stages 01–04 in
work order, then `.nav-gap`, then off-pipeline tools (Reference, Settings). A new
*stage* gets a number and joins the band in sequence. A new *tool* goes right of
the gap. Stage cells use `minmax(0,1fr)` tracks and their labels are
`white-space: nowrap` — a long label must be shortened, never allowed to inflate
its track.

**One lead per screen.** At most one `.panel.panel-lead` (amber left border,
`--panel2`) per view, and it holds the thing blocking the user. Everything else
is a plain `.panel`. Two leads = no lead.

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
Reference · Productions · Settings) live in the header with the engine
credential dots.

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
Shelf header (`.shelf-head`): Courier bold shelf name · faint Courier
ride-along line (`RIDES ALONG — …`) · right-aligned Courier counts
(`.shelf-count`). Intake lives behind `+ Add reference` (the role
dialog); the search field uses the finder-list vocabulary and filters
every shelf. Production Design step 3 ("Cast the film", `.uncast-block`)
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

**Pending take tile + take state tags** (`.take.pending/.take-spin`).
In-flight work holds its place: a pending tile sits in the filmstrip with
the `.busy` spinner vocabulary (honoring `prefers-reduced-motion`) and
survives closing whatever screen launched it. State reads at a glance in
the strip: approved = `--ok` border + label; promoted = `· REF` suffix on
the tile and a `REFERENCE · REF-xxxx` bordered badge on the stage (status
color border, never filled — the verdict-chip grammar).

---

## Copy

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

| Need | Use | Not |
|---|---|---|
| Primary action | `button.primary` (one per region) | amber on multiple buttons |
| Secondary | `button.ghost` | a second `.primary` |
| Destructive | `button.danger` | red fill |
| State | `.badge.APPROVED / .DRAFT / .REJECTED / .LOCKED` | colored text alone |
| Machine value | `<span class="mini">` + Courier child | Archivo |
| Section title | `.panel h2` (quiet Courier label) | amber headline |

`.badge.LOCKED` is deliberately grey: locked is a fact, not an action.

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
component, two hosts: the SUBJECTS shelf and wizard step 3). Anatomy:
Courier bold name · bordered grey kind badge (`.kind-badge`) ·
CAST/UNCAST badge (`.cast-badge`, `--ok`/`--hold` border, never filled)
· editable identity text (sans 12px `--ink-dim`; click to edit — it
rides in every prompt the subject appears in) · photo mosaic with a `+`
drop slot (`.subj-slot`) · Courier facts line (`n PHOTOS · ROLE — NAME ·
USED IN n RENDERS`, `.subj-facts`). Uncast recommendations are
dashed-border cards with a `Cast this subject` ghost button. In the
wizard the facts line ends with a `VIEW IN REFERENCE` text link
(`.text-act` — Courier bold, ink, never amber).

**Environment card** (`.env-card`, wizard step 2 — mock 6a). Registry-card
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

## Sequence and gates

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

## Do not

- Add a CSS framework, or Inter/Roboto.
- Add gradients, rounded cards, drop shadows for decoration, or emoji.
- Introduce a new accent color, or use a status color decoratively.
- Wrap content in more nested panels — depth was the v1 clutter mechanism.
- Rename existing CSS classes. `app.js` generates markup against these names;
  the stylesheet was written to preserve every one of them.

---

## Uncanonized patterns

**Every new feature lands here until Claude Design reviews it** (rule of
2026-07-31) — genuinely new patterns AND pure-reuse features alike; the
latter noted "built from canon — review placement/copy only". New patterns
are additionally built with existing tokens and marked
`/* UNCANONIZED — date — feature */` in the CSS.

This table is a to-do list, not a home. At ~4 rows, tell the user the UI has
accumulated patterns worth a design review — re-attaching the project folder in
Omelette gets them designed properly and folded into the sections above, and the
rows are then deleted.

| Date | Pattern | Used in | Why nothing existing worked |
|---|---|---|---|
| 2026-08-01 | The verb is the form (user ruling): with no screenplay, Status's DO-THIS-NEXT lead holds the upload form itself — never a button that only reaches another button; side column and Blocking untouched. The Screenplay stage's own empty state gets the same inline upload | Status lead, Screenplay view | Lead previously presented text + a jump button; a form inside the lead is new vocabulary — designer should rule on when a lead may carry a form |
| 2026-08-01 | Production-design gate tag (user ruling): `.pd-lock` dashed faint tag "COMPLETE PRODUCTION DESIGN" replaces Create Breakdown wherever it would appear before the bible is saved (the locked-stage layout itself was ruled by LOCKED_STAGE_PLAN and is canon) | Location finders (Screenplay + wizard) | A dashed non-interactive tag standing in for a verb is new vocabulary; designer should rule on the tag treatment |
| 2026-08-01 | "Script Scene Scan" (user naming): the Production Design step 2 read is named Script Scene Scan ("Run the Scene Scan") so the second read of the screenplay states what it returns | Wizard step 2 | Pure copy — review naming only |
| 2026-08-01 | Status error breadcrumb (user-directed): a square `--bad` dot after the Status tool label whenever the activity log's recent window holds an error | Header tools nav | FIRST NOTIFICATION MARK IN THE PRODUCT — designer must rule on notification vocabulary (dot vs count vs chip) |
| 2026-08-01 | Bible surface unified (user-flagged duplication; INTERIM unification shipped same day after the draft "vanished" into the hidden review box): step 5 is now the single Art Direction Bible panel — Draft (primary) writes into the editor with an overwrite confirm protecting unsaved text, Save (ghost) persists, status line reads NOT DRAFTED YET / DRAFTED BY <MODEL> / REV n. The separate Draft & review box is gone | Wizard step 5 | Designer should ratify the merged surface and rule on the Draft(primary)/Save(ghost) amber split |
| 2026-08-02 | Structural board view (user-directed, NEW PATTERN): an assembled board renders as its layout frames holding the individual panel images — cover-cropped in frame, click-through to the full uncropped take in the lightbox — with an HTML title block matching the drawn grammar; the composite single image becomes an explicit "Export board" download. Assemble lands directly on this view. Legacy boards without recorded rects keep the composite card | Board solo view (Boards stage) | The living-board vs flat-export split is new vocabulary; designer should rule on frame chrome, label treatment, and the export affordance |
| 2026-08-02 | Sticky chrome (user-directed): the header and pipeline band pin to the top (position: sticky, z 45/44); content scrolls beneath; the lock popover switches to fixed positioning so it stays attached to the band. Pipeline-band entry's "spine" role now literally holds the ceiling | App-wide | Built from canon — review only the z-order ladder (toast 50 · popover 55 · menus 60 · lightbox 100 · modal 400) |
| 2026-08-02 | Content-policy refusal treatment (user-directed): when an engine's safety system declines a panel, the bench shows a --hold-bordered stated block — ENGINE REFUSED — CONTENT POLICY, what it means (nothing broken, nothing billed, cannot be bypassed), the craft answer (restage to imply, or another engine), and the provider's own words in Courier | Render bench report area | New failure-state vocabulary (a refusal is neither an error nor a gate); designer should ratify the treatment |
| 2026-08-02 | Persistent UI state (user-directed, invisible — no new visuals): view, open sheet, judging-room panel/take, board & assembly pickers, generation model/size/aspect, settings tab all survive refresh and view switches, namespaced per production in localStorage | App-wide | Nothing to review visually; listed for completeness |
| 2026-08-01 | Interview persistence (user-directed, built from canon — review copy only): the look interview saves per production on every field change, with a mini stamp "SAVED — THESE ANSWERS BIND EVERY BIBLE DRAFT"; answers backstop every draft server-side and the drafter treats them as binding | Wizard step 3 | — |
| 2026-08-01 | QA batch (user-directed, built from canon — review placement/copy only): error activity rows gain `--bad` left border + `--panel2` fill; model selectors list only configured engines and state "NO ENGINE CONFIGURED — ADD A KEY IN SETTINGS" when none; busy meters name the running model; third anchor relabeled "Board Rendering Style"; bible editor moved above the bake-off; wizard's duplicate key forms removed (keys live in Settings only) | Status, wizard, Breakdowns | — |

---

## Changelog

Newest first. One line per change, dated. Amend the relevant section above as
well — this log records what changed, it does not replace the rules.

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
