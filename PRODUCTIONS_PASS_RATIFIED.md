# PRODUCTIONS_PASS_RATIFIED.md — rulings on the implementation report

**For the coding agent.** Every deviation and open decision in
`design_handoff/PRODUCTIONS_PASS_RESPONSE.md` is ruled below. Nine are
ratified as built — do nothing. Two need a change. One is deferred as its
own pass. Apply the changes, fold the noted lines into
`app/static/DESIGN_SYSTEM.md`, delete this file and the response it answers.

The report's instinct throughout was right: **when a written rule and a mock
disagree, the rule wins, and you say so.** That is the precedence order and
it held. Keep doing exactly that.

---

## Ratified as built — no action

**1. Reference stays in the nav; the order is correct.**
`Status · Reference · Productions · Settings` is right, and not just by
default. The tools are ordered by how often a working artist reaches for
them: Reference is opened constantly mid-task, Productions rarely (the
header switcher handles day-to-day switching — the view is for managing),
Settings almost never. Refusing to silently delete a core surface on a
presentation-scoped plan was the correct call. Ratified; no further pass
needed.

**2. One amber fill on the Productions view.**
Correct, and the rule stands with no exception: `Create` in START SOMETHING
is the view's only fill; every card's `Open` is ghost, in every state,
including a freshly created production. There is no state where a card's
Open earns the fill — creating a production switches to it anyway, so the
"come back here" case doesn't exist. The mock was wrong; the rule was right.

**3. The additive `slug` parameter on rename.**
Ratified, and this is the pattern to reuse: when a mock needs data an
endpoint doesn't carry, extend it with an **optional** parameter whose
absence reproduces the old behavior exactly, and regression-test the old
shape. That is not a breaking change and does not need a plan amendment.
Disabling Rename on closed cards would have been the wrong trade — the whole
point of the library is managing productions you are not currently in.

**4. Duplicate and Delete endpoints.**
Ratified, including refusing deletion of the open production with the reason
stated and showing Delete disabled *with that reason* on the open card.
That is gates-as-state applied correctly to a destructive action, and
enforcing the typed-name confirmation server-side as well as in the modal is
better than what the plan asked for.

**5. Reach band, 04 PANELS = any panel approved.**
Confirmed. A production with approved panels has plainly reached the panel
stage; requiring an assembled board would make the reach band answer the
board question twice. This is exactly why cursor and reach are two entries in
the design system — the nav band keeps its own mapping, unchanged.

**6. Switcher preview grammar.**
Ratified as written, including the priority order. `NO SCREENPLAY` first is
right: it is the only state where the production cannot be worked on at all.

**7. `BIBLE SAVED · REV n`.**
Ratified. A number that is always true beats a number that needs a new
summary field. Do **not** add the language count to `stage_summary` for a
checklist line — if languages become load-bearing elsewhere, that is when it
earns a field.

**8. First-run definition, and hiding the pipeline band during it.**
Ratified. Hiding the band is right: a band with nothing behind it is
scenery, and first run should present exactly one thing to do.

**9. `BACKED UP TODAY`.**
Ratified. "0 days ago" is machine phrasing in a human sentence.

---

## Two changes

### C1. `ALL STAGES CLEAR` — drop "Wrapped"

**Wrapped** is a real production state with a real meaning (principal
photography is finished). Using it for "last activity date" asserts something
the app does not know, on a card whose entire job is to report status
truthfully. Change the line to:

```
NOTHING WAITING · LAST ACTIVITY 12 JUN
```

Courier, `--ink-faint`, same position. When the activity log is empty, drop
the second clause and read `NOTHING WAITING`. Also update the switcher's
all-clear preview from `WRAPPED · n BOARDS` to `CLEAR · n BOARDS`.

If a genuine wrapped/archived state would be useful — hiding finished
productions from the switcher, freezing them from edits — that is a real
feature and its own small pass. Say the word and I will design it; do not
approximate it with a word in the meantime.

### C2. Boards empty state — the middle state gets one line, not the checklist

Right call to scope the stated-path panel to the no-signed-off-breakdowns
dead end. For the middle state (locked sheets exist, no boards yet), the
picker and bench already state the path by being present — a full checklist
there would be nagging. Add **one** Courier `--ink-faint` line above the
bench instead:

```
NO BOARDS YET — APPROVE EVERY PANEL IN A SHEET, THEN ASSEMBLE
```

That is the whole remaining path in one sentence, and it disappears the
moment a board exists.

---

## Deferred — its own pass, not this one

The store-surface items in the report's last section (reliable-door workspace
buttons, the wildcard router's stated pages, the /pipeline true-numbers
correction) are a storefront pass. Keep them logged in
`STORE_DESIGN_SYSTEM.md`'s changelog; I will take them as one batch. Do not
design them in passing — the wildcard pages in particular are somebody's
first experience of a broken link and deserve real copy.

---

## Doc pass

- `DESIGN_SYSTEM.md`: append the C1 phrasing to the production-card entry;
  append the C2 line to the Boards empty-state entry. Add one line to the
  precedence note: **written rule > mock**, with the amber-fill case as the
  worked example.
- Changelog: `**2026-08-01** — Productions pass ratified: nav order, single
  amber fill, additive rename slug, duplicate/delete gates, reach-band panel
  semantics confirmed as built; "Wrapped" replaced with truthful last-activity
  phrasing; Boards middle state gets a one-line path.`
- Delete `PRODUCTIONS_PLAN.md`, `ICON_RULING.md` (if applied),
  `design_handoff/PRODUCTIONS_PASS_RESPONSE.md`, and this file.

## Next time

Fresh screenshots in `design_handoff/` are useful, but for a pass this
structural the live URL is better — I would rather click the switcher than
read a still of it. Leave the cloud instance up and name it in the next
handoff.
