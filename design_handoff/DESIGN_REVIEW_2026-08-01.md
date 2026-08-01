# DESIGN_REVIEW_2026-08-01.md — nine-pattern review

**For the coding agent.** Rulings on all nine uncanonized rows. Apply in
order, fold into DESIGN_SYSTEM.md, clear the table, delete this file.
Rows 3+4 are ruled together — they are one model, not two patterns.

---

## 1. Finder verb divergence — adopt the user's vocabulary EVERYWHERE

"Sheet" is our jargon; "Breakdown" is the product's own word (stage 03 is
called Breakdowns). The user-directed verb is the better one — the divergence
is the only defect.

- Canonical finder verbs, both hosts: **`Create Breakdown`** (no match) and
  **`Open Breakdown`** (matched).
- Change the screenplay coverage table to match; update the canon entry in
  Layout patterns → Finder list (currently "Draft a sheet / Open sheet").
- Sweep for other "sheet" verbs in user-facing copy and align them. Internal
  names (`spec`, `buildLocFinder`) stay as they are — this is a copy pass.

## 2. "Derive from screenplay" — CANONIZED as the derive affordance

Right instinct, and it generalizes: a deterministic scan that *fills a field
the user still owns* is different from generation, and should look it.

Canonical rule (Components): *derive affordance — a ghost button placed at
the field's label row that deterministically fills an editable field from
data the app already has. Never amber (it is not the region's primary
action), never a spinner (it must be instant — if it can't be, it's a
generation and belongs on a primary button with the `.busy` vocabulary).
Disabled with the reason stated when its source is missing. The filled value
is ordinary editable content; the button carries no state and does not mark
the field as derived.*

## 3+4. Panel overrides — ONE model: the sheet is the baseline, panels are exceptions

Both rows are the same question: can a panel diverge from the board's scope?
Answer: **yes, as a declared exception — never as a silent second control.**
A mixed-culture panel is a real need (GRM interior on a frontier board), and
the per-panel light select already established the grammar. But two equal
selects invite "which one is winning?", which is exactly the failure the
scope block was built to end.

**The model (write this into Layout patterns as "Scope inheritance"):**

*Sheet scope is the board's baseline: it applies to every panel. A panel may
declare an exception for design languages and for environment. Exceptions are
opt-in, visible as exceptions, and always reversible to inheritance.*

**Presentation rules:**

1. **Panels inherit by default and say so.** A panel card with no exception
   shows a single quiet Courier line in the scope position — not an empty
   control: `SCOPE — INHERITS BOARD · POST-FALL FRONTIER + RESISTANCE ·
   ENV: FOREST`, followed by a ghost `Override` text action (`.text-act`).
   Never render an empty select that looks unset when it is in fact inherited.
2. **Overriding reveals the controls in place** — the facet chip row
   (`.vchip.set`) and the environment select — plus a `Revert to board` text
   action. Reverting clears the override entirely (empty ≠ override).
3. **An overriding panel is marked.** The panel card head gains a Courier
   `--hold` bordered `SCOPE OVERRIDE` chip (proposed-state family: the panel
   is deliberately not the board). One glance down a sheet shows which panels
   diverge.
4. **The carry line tells the truth in two parts.** When any panel overrides,
   `.scope-carry` splits:
   `BOARD CARRIES — RENDERING LANGUAGE (ALWAYS) · POST-FALL FRONTIER ·
   RESISTANCE · ENV: FOREST · 2 SCENE LESSONS`
   `P03 OVERRIDES — GRM ORDER · ENV: ORBITAL / STATION`
   One override line per diverging panel, Courier `--ink-dim`, same receipt
   grammar. With no overrides the line is unchanged from today.
5. **Environment stays one-per-panel** (the sheet's is one-per-board): a
   panel lives in exactly one place. Languages remain multi-select.
6. **Locking freezes overrides** with the rest of the scope; the lock strip
   needs no new copy.

Amend the environment-card canon line "A sheet carries at most one" to: *"A
sheet carries at most one; a panel may override it with exactly one of its
own."*

## 5. Assembly grid → solo — CANONIZED as the gallery drill-in

Right pattern, and it's the same shape as the judging room (many small, one
big) — say so, so the two stay consistent.

Canonical rule (Layout patterns): *gallery drill-in — a stage that holds
many finished artifacts opens on a grid of them; selecting one replaces the
grid with a single contained full-width card carrying that artifact's judge
actions, and a `← All boards` text action returns. The contained image never
crops (finished work is judged whole — unlike takes, which cover-crop into
slots). The generation/assembly bench stays above the grid in both states, so
producing more never requires leaving the drill-in.* If the bench currently
disappears in solo view, fix that.

## 6. Workspace login — CANONIZED as the entry gate

Canonical rule (Layout patterns): *entry gate — a standalone centered
`.panel` (max ~380px) on `--bg`, holding the wordmark, one field, one
`.primary`, and at most one line of `.hint`. No nav band, no header tools, no
brand-sub project name (there is no project context before auth). Errors
render as the field's own state plus one `--bad` line — never a toast, which
can be missed on a page with nothing else on it. The gate is the only screen
allowed to be vertically centered.* Add: the centering styles belong in
`styles.css` under a `.gate-page` class, not inline on `<body>`.

## 7. Projects — the switcher moves to the header; Settings keeps the registry

Two different jobs got merged. Switching projects is navigation and belongs
where project identity already lives; managing them is administration.

- **Header:** the brand-sub project name (`THE BELTMINERS`) becomes the
  switcher — same Courier treatment, plus a `▾` and a hover border. Opens a
  compact menu of projects (Courier names, active one marked with the
  `.cast-badge` grammar — bordered `--ok`, never filled) and one text action
  at the bottom: `Manage projects…` → Settings.
- **Settings:** keeps the Projects panel as the registry (rows + intake +
  backup), minus the switching burden — the `Open` ghost stays as a
  convenience.
- Note in the doc that engines/keys are install-level and projects are not,
  so the panel's placement in the engines subview is acceptable but its
  header must say `PROJECTS — THIS INSTALL` to keep the scopes legible.

## 8. Backup controls — APPROVED as built, no changes

Pure canon reuse (registry rows + intake row). Fold the backup fact into the
registry-rows entry: *a registry row's Courier facts may carry a care state
(`BACKED UP <date>` / `NEVER BACKED UP`) — faint, never a badge.* No amber,
no `--bad` on "never backed up": not-yet-done is not a failure.

## 9. CARE — advisory rows leave the blocking list

Correct instinct to surface it, wrong home. The blocking panel's whole
contract is "these stop the next render." An advisory in that list weakens
every row above it, and it must never be eligible for DO-THIS-NEXT.

- Keep CARE rows in the same panel, but **below a divider** with a Courier
  `--ink-faint` label `ADVISORY`, after all blocking rows.
- CARE kind badge: `--ink-faint` border and text (not `--warn`) — advisory is
  quieter than blocked, and `--warn` is amber, which the blocking panel
  already spends on the DO-THIS-NEXT action.
- Excluded from the blocking count in the reveal/summary, excluded from
  `blocking[0]` promotion. If the list is *only* advisories, the lead states
  the next stage action as it does when empty.
- Canon line (Layout patterns → Blocking rows): *blocking rows report what
  stops the next render. Advisory rows (care of existing work) render below
  an `ADVISORY` divider with a faint kind badge, are never counted as
  blockers, and are never promoted to the lead.*

---

## Doc moves

1. Layout patterns: scope inheritance (§3+4), gallery drill-in (§5), entry
   gate (§6), advisory rows (§9 line appended to blocking rows), finder verb
   correction (§1).
2. Components: derive affordance (§2), registry-row care state (§8),
   environment-card amendment (§3+4), project switcher (§7) beside the
   pipeline-band entry.
3. Clear all nine table rows; remove their `/* UNCANONIZED */` markers.
4. Changelog: `**2026-08-01** — Nine-pattern review: scope inheritance model
   (sheet baseline, declared panel exceptions, two-part carry line), derive
   affordance, gallery drill-in, entry gate, advisory blocking rows, project
   switcher moved to the header, finder verb standardized on Create/Open
   Breakdown.`
5. Delete this file.
