# DESIGN_REVIEW_2026-08-02.md — seven-row review

**For the coding agent.** Rulings on every row in the uncanonized table. Four
canonize with a rule attached, two ratify with a small change, one is a
naming conflict you should resolve my way. Apply, fold into
`DESIGN_SYSTEM.md`, clear the table, delete this file.

---

## 1. A lead may hold a form — CANONIZED as "the verb is the form"

The user's instinct is right and it generalizes. A lead that says *"upload a
screenplay"* and offers a button that reveals an upload field has spent a
click teaching the user where the real control lives.

**Canonical rule** (Components → blocking rows / DO-THIS-NEXT lead):

> A lead may hold the control that resolves it, instead of a link to it, when
> the control is **one or two inputs** and completing it satisfies the blocker
> outright — a file picker, a single named field. Beyond two inputs, or when
> the work needs judgment across several fields, the lead states the verb and
> links. A lead never holds a form that itself only leads somewhere else.

The Screenplay stage's own empty state carrying the same inline upload is
correct — one control, two doors, same outcome.

## 2. `.pd-lock` — CANONIZED as "the withheld verb", and it needs a boundary

This is genuinely new vocabulary, and it conflicts with an existing rule
unless we draw the line. The design system already says a gated action shows
**the disabled control plus its unmet condition**. The new dashed tag
*replaces* the control entirely. Both are right, for different cases:

| Case | Treatment |
|---|---|
| The action becomes available **on this screen**, by work done here | Disabled control, `:disabled` styling, unmet condition stated beside it. (Approve & lock, Assemble 4K board.) |
| The action requires work **somewhere else** | **Withheld verb**: the control is replaced in place by a dashed `--line` bordered Courier tag naming the condition — `COMPLETE PRODUCTION DESIGN`. Never interactive, never amber, never `--bad`. |

The reasoning: a disabled button says *wait here*, and invites clicking. A
tag says *this isn't yours yet, and not from this screen* — which is the
truth when the fix is two stages back. An absence says nothing at all and is
the worst of the three.

Ratified as built. Add both rows to the table in Layout patterns → Sequence
and gates.

## 3. Naming: **Script Scan**, not Script Scene Scan

Conflict to resolve. The changelog logs "Script Scene Scan / Run the Scene
Scan"; the director's later instruction (locked-stage pass) names the step
**"Run the Script Scan"**, and both mocks
(`12b-locked-stage.png`, `12c-stage-empty-state.png`) and
`LOCKED_STAGE_PLAN.md` say Script Scan.

**Ruling: Script Scan.** The later instruction wins, "script" already implies
its scenes, and the gate checklist the user is about to see must match the
step it points at. Sweep the wizard, the gate list, the popover and the
Workflow copy so one name appears everywhere.

## 4. Status error breadcrumb — CANONIZED, and it is the whole notification vocabulary

This is the first notification mark in the product, so the ruling is about
the category, not the dot.

**Canonical rule** (new short section, after Icons):

> **Notification marks.** A tool label in the header may carry a single
> square `--bad` dot, 5px, after its text, when something in that view wants
> the user's eye. That is the entire vocabulary.
>
> - **A dot, never a count.** A number implies a queue to be worked down and
>   invites triage-by-number; these are events in a log, and the only useful
>   message is "something in there."
> - **One dot maximum per tool.** No stacking, no second color — if a state
>   isn't worth `--bad`, it isn't worth a mark. There is no amber "info" dot.
> - **It clears when the view is opened**, not when the underlying item is
>   resolved. The mark's job is to route attention once.
> - Never on a stage cell in the pipeline band — the band already reports
>   state in its own colors, and a dot there would compete with them.

Ratified as built.

## 5. Bible surface unified — RATIFIED, with the amber split reversed

Merging step 5 into one panel is right, and the "vanished draft" it fixes was
a real failure. Keep the overwrite confirm.

**Change: amber follows the unmet step, so it moves.**

- Editor empty → **Draft** is primary (amber), Save is ghost. Drafting is the
  only thing to do.
- Editor holds unsaved text → **Save** is primary (amber), Draft demotes to
  ghost. Save is the act that makes the bible canon and everything downstream
  reads the saved copy, not the editor.
- Saved and unchanged → neither is amber; the status line carries `REV n`.

One amber at all times, always on the step that is actually outstanding. Keep
the status line's three states as built.

## 6. Interview persistence — RATIFIED as built

Per-production save on change, with the stamp. Keep "SAVED — THESE ANSWERS
BIND EVERY BIBLE DRAFT" exactly as written; "bind" is strong on purpose and
it is the reason the step exists.

## 7. QA batch — RATIFIED, one change

All correct. One fix: `NO ENGINE CONFIGURED — ADD A KEY IN SETTINGS` must be
a **link** to Settings, not a sentence about Settings. A stated condition
that names its remedy should carry the reader there — that is the same rule
the blocking rows follow.

---

## Doc pass

- Components: the-verb-is-the-form rule (1); amber-follows-the-unmet-step on
  the bible panel (5).
- Layout patterns → Sequence and gates: the two-case table from (2).
- New short section after Icons: Notification marks (4).
- Sweep **Script Scan** everywhere (3).
- Clear all seven rows; remove the `/* UNCANONIZED */` marker at
  `styles.css` ~1270 if the rename pencil is now the `✎` glyph per
  `ICON_RULING.md`.
- Changelog: `**2026-08-02** — Seven-row review: leads may hold a one-or-two
  input form; withheld-verb tag canonized with the disabled-control boundary;
  notification marks ruled (dot only, one per tool, clears on open); bible
  panel's amber moves to the unmet step; step named Script Scan everywhere;
  no-engine notice becomes a link.`
- Delete this file.
