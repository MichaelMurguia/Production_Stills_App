# PRODUCTION_DESIGN_V3_PLAN.md — economy pass, preset looks, labelled locations

**For the coding agent.** Rebuilds the Production Design tab. Mocks:
`design_mocks/pd3-full-page.png` (the whole page, 1360px) and
`pd3-look-browser.png` (the preset browser). Read
`app/static/DESIGN_SYSTEM.md` first. One task per commit, D1–D9.
**D1–D6 ship now. D7 needs the plate library (see PRESET_LOOKS_SHOT_LIST.md).**

## The rule this pass applies

Settings v3's rule, now app-wide (canonize it in Layout patterns):

> **A step states what it does to the movie, never what it is.** Prose that
> explains the app's own architecture to the user is cut. Prose that tells the
> user what a control will do to their film stays. When a sentence can become
> a section label, it becomes the label.

## D1 — Cut the explanatory prose

Delete, verbatim, these blocks:

- The six-step preamble ("Six steps produce your Art Direction Bible…") →
  header strip line `SIX STEPS → ART DIRECTION BIBLE`.
- Step 1's four-sentence anchor lecture ("Four anchors, four jurisdictions…")
  → nothing. The group labels and the per-column CONTROLS/NEVER lines already
  say it.
- Step 2's design-language paragraph → the section label
  `DESIGN LANGUAGES — EACH BECOMES A BIBLE SECTION`.
- Step 3's "Questions you answered in step 2 are already included." → the
  header's Courier condition line.
- Step 4's three-sentence casting paragraph → one Courier line:
  `CASTING MAKES A CARD IN REFERENCE / SUBJECTS · ITS SCREENPLAY IDENTITY RIDES EVERY PROMPT`.
- Step 5's compiler paragraph → `context/01_ART_DIRECTION_BIBLE.md · EDITS REACH EVERY FUTURE PROMPT`.
- Step 6's conditions paragraph → `SAME LOCATION · SAME BIBLE · SAME ANCHORS — THE CONDITIONS REAL PANELS RUN UNDER`.
- Lessons Learned's paragraph → `RIDES EVERY FUTURE PROMPT ON EVERY BOARD · REJECTIONS DO NOT LAND HERE`.
- Every parenthetical subtitle on a step heading (`(skip anything — blanks
  come back marked PROPOSED)`, `(cards live in Reference / SUBJECTS — this
  step is the door)`, `(draft it, review it, save it…)`, `(pick your default
  engine by looking, not guessing)`) — the ones carrying a real condition
  survive as the Courier line, the rest go.

**Kept deliberately:** the CONTROLS/NEVER pair on each anchor column (that is
the column's jurisdiction — the one fact not inferable), and every Courier
machine value.

Copy change while you are in there: `CONTROLS` → `SETS` and `NEVER` → `NOT`.
Shorter, and `NEVER` was colliding with the interview's "it must never look
like".

## D2 — Step rail in the header strip

Six numbered chips, current one bordered `--accent-line` on `--panel2`, done
ones carrying a `--ok` number, hairlines between. Six stacked steps have no
sense of sequence without it. Clicking a chip scrolls to that step (**not**
`scrollIntoView` — use the offset math already used elsewhere).

## D3 — THE READ FOUND becomes stat tiles + a logline column

Five equal tiles (design languages · environments · locations · subjects ·
open questions; the last one's number is `--accent` when > 0), then the
logline in its own `--accent`-left-ruled panel beside them at 360px. They
were one box before, which made the logline read as a footnote to the counts.

## D4 — Locations: label the columns, state what an environment is for

The table's real defect: nothing said why the environment dropdown matters.

1. Section label: `LOCATIONS — N · EACH BECOMES ONE BREAKDOWN SHEET`.
2. Environments section above it retitled
   `ENVIRONMENTS — THE VISUAL RULES A PLACE INHERITS`.
3. **A header row on the table**, fixed tracks
   `minmax(0,1fr) 240px 120px 190px`:
   `LOCATION` · `ENVIRONMENT — ITS VISUAL RULES` · `SHEET` · (actions).
4. The per-row `COMPLETE PRODUCTION DESIGN` button is **wrong** — it is a
   gate, not an act. Replace with the withheld-verb tag `NEEDS THE BIBLE`.
   Once the Bible exists the cell becomes the real verb (`Make sheet` /
   `Open sheet`).
5. Group headers (`DESERT / CRASH RANGE — 2`) stay, on `--field`.
6. Kill the inner scroll container. The table was scrolling inside a short
   fixed-height box, which is what hid the header row and cut rows mid-word.
   The page scrolls; the table does not.

## D5 — Open questions in two columns

Two-track grid, four visible, `▾ N MORE`. Each card: Courier `Qnn`, the
question, and a right-hand stack of `Answer` + `Decide later`. Label states
the consequence: `OPEN QUESTIONS — 0 OF 14 ANSWERED · ANSWERS RIDE THE BIBLE DRAFT`.

## D6 — Interview in two columns

Touchstones · Medium & finish on row one, Palette & light · Must never look
like on row two, Notes spanning. One full-width field per question wasted
half the row and made five short answers look like a long form.

## D7 — Preset looks — NEEDS THE PLATE LIBRARY

In the two board-facing columns only (Cinematography, Board Rendering), above
the upload control:

- Label `PRESET LOOKS (OPTIONAL)` + `Browse 5`.
- Two preset rows visible: name, `5 IMG`, and a five-frame contact strip at
  22px tall. The in-use preset carries a `--line`-lifted border on `--panel`.
- `Browse 5` opens the look browser (mock `pd3-look-browser.png`): filter
  chips, a 3-up grid, each card a 5-plate mosaic (one large + two stacked +
  two wide) with name, a two-line Courier description of what the look sets,
  and `Use this look` / `See all 5 plates`. The in-use card reads `IN USE`
  and its verb becomes `Replace column`.

**Three rules:**

1. **A look is five pre-rendered plates we ship — never a text prompt.**
   Selecting one adds real reference images, so the Bible ends up citing
   images rather than adjectives. This is the whole reason the feature exists.
2. **Looks filter to the column that opened the browser.** A cinematography
   look can never land in board rendering; the jurisdiction rule holds.
3. **Selecting never destroys user uploads.** Plates are added as approved
   refs alongside them, individually removable. Footer states this verbatim:
   `A LOOK ADDS 5 PLATES AS APPROVED REFERENCES · REMOVE ANY ROW AFTERWARDS · YOUR OWN UPLOADS ARE NEVER REPLACED`.

Plates live in `app/static/look_library/<slug>/01..05.jpg` with a
`looks.json` manifest (`slug, column, name, tags[], sets[2 lines]`). They
enter the project's reference library as approved refs with
`source: "look:<slug>"` so provenance survives. **Five looks per column at
launch** — shot list in `PRESET_LOOKS_SHOT_LIST.md`.

## D8 — Rulings on the five uncanonized rows

- **Anchor rows lose "use in draft"** — RATIFY. Inclusion is the selection;
  a checkbox on an already-chosen anchor asked the same question twice. The
  swatch name·hex Courier note line is ratified at the density mocked here.
  Applies app-wide: no confirm-checkbox on a list the user built by adding.
- **Bible Save gate** — RATIFY, corrected to the withheld-verb tag. The
  disabled button stays (it is the same control, unavailable), and its stated
  condition becomes the dashed tag `NOTHING TO SAVE UNTIL A DRAFT EXISTS`
  rather than a sentence. Same treatment as the locations column.
- **Color swatch generate widget** — RATIFY WITH TWO CORRECTIONS. (1) The
  amber Approve-all bar goes: amber is spent on `Draft Art Direction Bible`
  on this page, and approving swatches is not the page's primary act — make
  it a bordered ghost row. (2) Generated proposals **must persist as
  PROVISIONAL refs**, not client-side only. A rejection that leaves no record
  is a judgement the product forgot, and the approval log exists precisely so
  it doesn't. Citation density as built is fine.
- **Four-anchor row** — RATIFY. `THE MOVIE` spanning three tracks and
  `THE BOARDS` one is the jurisdiction split made visible; keep the label row
  inside the same grid so the spans can never drift from the columns.
- **Stale-tab update bar** — RATIFY, placed **below** the band. Above the
  band would push the product's map down for a condition that is not about
  the production. Tone stays flat and Courier; never auto-reload; do not
  announce proactively — a fleet update the user has not hit is not news.

## D9 — Canon

Add to `DESIGN_SYSTEM.md`: the states-not-explains rule (top of this file);
the preset-look pattern and its three rules (D7); the labelled-table header
row with fixed tracks (D4); the gate-not-a-verb correction as a worked
example of the withheld verb. Delete all five uncanonized rows. One
changelog line. Delete this file when D1–D6, D8, D9 ship; keep D7's section
until the library lands.
