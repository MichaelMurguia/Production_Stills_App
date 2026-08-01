# PRODUCTIONS_PLAN.md — the project-management pass

**For the coding agent.** Answers every open question in
`design_handoff/MANAGE_PROJECTS_HANDOFF.md` and redesigns the surface.
Mocks: `design_mocks/10a-productions.png`, `10b-switcher-rename.png`,
`10c-empty-states.png`. Read `app/static/DESIGN_SYSTEM.md` first. One task
per commit, M1→M7.

No endpoint changes. No CSS class renames. Everything below is presentation
plus one new view mounted from existing data.

---

## Part A — Rulings on the handoff's open questions

### A1. Vocabulary: **production**

User-facing copy says **production** everywhere. Drop "screenboard" as the
name for a project — it collides with "board", which is a different object,
and *"create a new board"* becomes ambiguous (the user hit exactly this).
"Production" is also what the industry calls the thing.

- API, registry keys, file paths, `data-view` values: `project` stays.
  This is a copy pass, not an identifier pass.
- Sweep: rename toast, Settings copy, marketing, FAQ, Workflow subview.
- The library heading is **Screenboard Library** (the shelf of productions);
  the items on it are productions.

### A2. Productions leaves Settings and becomes its own view

A production is the top of the content hierarchy — every screenplay, bible,
reference and board hangs off one. Settings is install-level configuration
(engines, keys, backups of the install). They do not belong in the same
place, and the registry-row grammar it borrowed from the engine list was the
symptom.

- New view `data-view="projects"`, label **Productions**, placed with the
  off-pipeline tools right of the nav gap (`Status · Productions · Settings`).
- Settings' Projects panel is **removed**, replaced by one line in the
  engines subview: `PRODUCTIONS MOVED — manage them in Productions` with a
  text link. Do not leave a second registry behind.
- `renderProjects()` (~app.js 1066) is rewritten to render cards into the
  new view. `.eng-row` stops being used for projects; leave the class for
  actual engines.

### A3. `ACTIVE` badge retired

Correct instinct to flag it. `.badge.APPROVED` carries approval semantics —
a production is not "approved", it is *open*, which is navigation state. Use
the pipeline band's vocabulary instead: the open production's card gets a
3px `--accent` left border, `--panel2` fill, and a Courier `--accent` `OPEN`
beside its name. Never a badge. Same in the switcher menu.

### A4. Backups are care, not blocking

Consistent with the 2026-08-01 advisory ruling: backup age never enters the
blocking list and is never eligible for DO-THIS-NEXT. It lives as a Courier
line in the card's footer, escalating on `days_since_backup`:

| Age | Treatment |
|---|---|
| < 14 days | `BACKED UP n DAYS AGO`, `--ink-faint` |
| 14–29 days | same text, `--hold` |
| ≥ 30 days | `--bad` text, and the footer's first action becomes `Back up now` with a `--bad-line` border |
| never | `NEVER BACKED UP`, `--ink-faint` (not-yet-done is not a failure) |

The Status view's `ADVISORY` divider may carry **one** row for the active
production only, when it is ≥ 30 days.

### A5. Rename: inline rename, canonized, kept on the header

`#brand-rename` stays — do not remove it. Canonical rule for
`DESIGN_SYSTEM.md` Components:

> **Inline rename.** A label the user owns is renamed in place: the label
> becomes an input at the same position and type size, pre-filled and
> selected; Enter commits, Esc reverts, blur commits. Never a dialog, never
> a separate edit screen. The affordance is a `✎` that appears on hover of
> the label (always present for keyboard/touch — do not gate it on hover
> alone in the accessibility tree).

Mock 10b shows all three states (resting / hover / editing with the amber
focus ring). The Productions card's ghost `Rename` is the secondary door and
uses the same in-place input on the card's name.

### A6. Every card states its own next verb

This is what closes the "how do I create a board?" gap at the root. Each
card carries a `DO THIS NEXT` block (Courier amber kicker + one sentence),
computed per production from the same rule as the Status blocking list:

- no screenplay → "Upload a screenplay to start the read"
- no bible → "Answer the read's open questions and draft the bible"
- blockers → the first blocker, verbatim (e.g. "3 evidence rows on hold in
  `KYRA_GRM_FIGHT`")
- no sheets → "Pick a location and create its breakdown"
- nothing waiting → kicker becomes `ALL STAGES CLEAR` in `--ink-faint` and
  the line states the last activity date. Not amber — there is no verb.

### A7. Card stage band ≠ nav band. **Both go in the design system.**

The nav band is a **cursor**: where the user is standing. A production
card's band is a **reach** indicator, answering a different question. Same
four colors, different mapping:

| | Nav band (cursor) | Card band (reach) |
|---|---|---|
| `--ok` | stage complete | production has **ever** completed this stage |
| `--accent` | the stage you are on | *not used* |
| `--bad` | stage carries a blocker | any of this production's sheets is blocked here |
| `--line` | not reached | never reached |

So a production may legally read green through 05 with 03 in red — it has
boarded work and one blocked breakdown right now. Write both entries; a
future reader will otherwise "fix" one into the other.

---

## Part B — Build order

### M1 — Copy pass (A1)
Production everywhere in user-facing text. Identifiers untouched.

### M2 — New Productions view (A2)
Mount the view, add the nav tool, move the create and restore forms into it,
leave the Settings pointer line. Registry still rendering old rows at this
point is fine — M3 replaces them.

### M3 — Production cards (A3, A6, A7)
Rewrite `renderProjects()` to emit cards per mock 10a: name + `OPEN` marker
+ slug (`root layout` for the legacy unsluged project) → 5-cell reach band →
Courier counts row → `DO THIS NEXT` block → footer with care line and
actions (`Back up` · `Rename` · `Open` · `⋯`).

**NEEDS DATA:** per-production counts (scenes, panels, boards, refs), stage
reach, and blocker text require reading each project's state. If that is
expensive across many productions, add a read-only
`GET /api/projects/summary` returning one row per project — the same shape
`/api/summary` already computes for the active one. Do not compute it
client-side by opening every project.

`⋯` holds **Duplicate** and **Delete**. Delete requires typing the
production name to confirm (it destroys a screenplay, a library and every
board) — use the app dialog, not `confirm()`.

### M4 — The switcher (A3, and the create gap)
Menu per mock 10b: `SWITCH PRODUCTION` label, one row per production showing
name plus a Courier state preview (`STAGE 03 · 3 HOLDS`, `STAGE 01 · NO
SCREENPLAY`, `WRAPPED · 4 BOARDS`, and a `--bad` `BACKUP 41D` when stale),
the open one marked with the amber left border and `OPEN`. Then a divider
and two items: **`+ New production`** (amber text — navigates to Productions
with the name field focused; do not put a form in the menu) and
`Manage productions…`. Footer note: `SWITCHING RELOADS THE STUDIO. UNSAVED
FORM TEXT IS NOT CARRIED OVER.`

### M5 — Inline rename (A5)
Implement the canonical behavior on the header name and on card names from
one shared helper. Keep `#brand-rename`.

### M6 — The two empty states (mock 10c)
1. **First run, no productions**: standalone centered panel — kicker, "Name
   the show you're working on.", one paragraph, name field + `Create
   production`, then a divider and `Restore a production`. Reuse the entry
   gate pattern.
2. **Boards tab, no boards**: state the path. Headline "A board starts life
   as a breakdown.", one paragraph, primary `Create a breakdown` (opens
   Production Design → Locations, and say so in a Courier line beneath),
   plus a `THE PATH FROM HERE` checklist showing completed steps with `✓`,
   the current step with an amber `→`, and remaining steps faint.

### M7 — Doc pass
`DESIGN_SYSTEM.md`: inline rename → Components; card reach band **and** nav
cursor band → Layout patterns (as the A7 table); production card anatomy →
Components; the backup escalation ladder appended to the registry-row care
state entry. Clear the rename row from the uncanonized table. Changelog:

> **2026-08-01** — Productions pass: projects renamed "production" in copy
> and moved out of Settings into their own view as cards with reach bands
> and per-production DO-THIS-NEXT; ACTIVE badge retired for the open-state
> vocabulary; inline rename canonized; backup age escalates as care, never
> as a blocker; first-run and empty-Boards states state the path.

## Ground rules

Tokens only; no new grey; square corners. Amber per the app system — on the
Productions view that is the open card's border, each card's DO-THIS-NEXT
kicker, and one primary action; in the switcher, the open row plus
`+ New production`. Machine values Courier, prose Archivo. Switching must
keep feeling like navigation (full reload is correct). Backup zips still
exclude `settings.json`, and restore still always creates a new production —
the copy in 10a says so and must stay.
